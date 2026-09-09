"""Persistence and lifecycle management for user-created templates."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..runtime import get_runtime_config
from .content_filters import is_excluded_path, is_path_safe, is_sensitive_file
from .models import TemplateFile, TemplateSpec

logger = logging.getLogger(__name__)


class UserTemplateError(RuntimeError):
    """Raised when user-template operations fail."""


_TEMPLATE_NAME_MIN_LEN = 3


def generate_template_id(template_name: str) -> str:
    slug = template_name.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")
    slug = slug.strip("-")
    return slug[:63]


def validate_template_name(template_name: str) -> None:
    name = template_name.strip()
    if len(name) < _TEMPLATE_NAME_MIN_LEN:
        raise UserTemplateError("Template name must be at least 3 characters.")


def validate_template_id(template_id: str) -> None:
    value = template_id.strip()
    if not value:
        raise UserTemplateError("Template ID cannot be empty.")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if any(ch not in allowed for ch in value):
        raise UserTemplateError("Template ID may only contain lowercase letters, numbers, and '-'.")
    if ".." in value or value.startswith("/") or value.startswith("\\"):
        raise UserTemplateError("Template ID is invalid.")


@dataclass(frozen=True)
class SourceInspectionResult:
    source_path: Path
    included_files: list[Path]
    excluded_files: list[Path]
    sensitive_files: list[Path]


class UserTemplateStore:
    """Store and load user templates from PES user data directory."""

    def __init__(self, base_dir: Path | None = None) -> None:
        runtime = get_runtime_config()
        self.base_dir = base_dir or (runtime.user_data_dir / "templates" / "user")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def inspect_source(self, source_dir: Path) -> SourceInspectionResult:
        source = source_dir.expanduser().resolve()
        if not source.exists() or not source.is_dir():
            raise UserTemplateError(f"Source directory is invalid: {source}")

        included: list[Path] = []
        excluded: list[Path] = []
        sensitive: list[Path] = []

        for path in sorted(source.rglob("*")):
            rel_path = path.relative_to(source)
            if path.is_dir():
                if is_excluded_path(rel_path, is_dir=True):
                    excluded.append(rel_path)
                continue

            if not is_path_safe(rel_path):
                excluded.append(rel_path)
                continue
            if is_excluded_path(rel_path, is_dir=False):
                excluded.append(rel_path)
                continue
            if is_sensitive_file(rel_path):
                sensitive.append(rel_path)
                continue
            included.append(rel_path)

        return SourceInspectionResult(
            source_path=source,
            included_files=included,
            excluded_files=excluded,
            sensitive_files=sensitive,
        )

    def template_exists(self, template_id: str) -> bool:
        return self._template_dir(template_id).exists()

    def save_template(
        self,
        source_dir: Path,
        template_name: str,
        template_id: str,
        description: str,
        author: str | None,
        version: str,
        category: str,
        python_version: str,
        source_type: str,
        origin: str,
        reserved_template_ids: Iterable[str],
        replace_project_name: bool = False,
    ) -> str:
        validate_template_name(template_name)
        validate_template_id(template_id)

        if template_id in set(reserved_template_ids):
            raise UserTemplateError(f"Template ID conflicts with an existing template: {template_id}")

        target_dir = self._template_dir(template_id)
        if target_dir.exists():
            raise UserTemplateError(f"Template ID already exists: {template_id}")

        inspect = self.inspect_source(source_dir)
        if not inspect.included_files:
            raise UserTemplateError("No importable files were found after applying exclusion rules.")

        content_dir = target_dir / "content"
        content_dir.mkdir(parents=True, exist_ok=False)

        root_name = inspect.source_path.name
        copied_files = 0

        try:
            for rel_path in inspect.included_files:
                source_file = inspect.source_path / rel_path
                target_file = content_dir / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)

                try:
                    text = source_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    logger.warning("Skipping non-text file while saving user template: %s", source_file)
                    continue

                if replace_project_name and root_name:
                    text = text.replace(root_name, "{{ project_name }}")

                target_file.write_text(text, encoding="utf-8")
                copied_files += 1

            if copied_files == 0:
                raise UserTemplateError("No UTF-8 text files were copied into the template.")

            metadata = {
                "id": template_id,
                "name": template_name,
                "version": version or "1.0.0",
                "description": description.strip() or "User-created template",
                "author": author.strip() if author else None,
                "category": category.strip() or "General",
                "source": "user",
                "source_type": source_type,
                "origin": origin,
                "variable_style": "double_brace",
                "supported_python_versions": [python_version],
                "min_python": python_version,
                "architecture": "imported",
                "style": "custom",
                "included_tooling": [],
                "runtime_dependencies": [],
                "dev_dependencies": [],
                "default_license": "MIT",
            }
            (target_dir / "template.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        except Exception:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise

        return template_id

    def delete_template(self, template_id: str) -> None:
        validate_template_id(template_id)
        target_dir = self._template_dir(template_id)
        if not target_dir.exists():
            raise UserTemplateError(f"Template not found: {template_id}")
        shutil.rmtree(target_dir)

    def load_user_templates(self) -> list[TemplateSpec]:
        templates: list[TemplateSpec] = []
        for template_dir in sorted(self.base_dir.iterdir() if self.base_dir.exists() else []):
            if not template_dir.is_dir():
                continue
            meta_file = template_dir / "template.json"
            content_dir = template_dir / "content"
            if not meta_file.exists() or not content_dir.exists():
                continue

            try:
                metadata = json.loads(meta_file.read_text(encoding="utf-8"))
                files: list[TemplateFile] = []
                structure: list[str] = []
                for file_path in sorted(content_dir.rglob("*")):
                    if not file_path.is_file():
                        continue
                    rel_path = file_path.relative_to(content_dir)
                    rel_str = str(rel_path).replace("\\", "/")
                    content = file_path.read_text(encoding="utf-8")
                    files.append(TemplateFile(path=rel_str, content=content))
                    structure.append(rel_str)

                templates.append(
                    TemplateSpec(
                        id=metadata["id"],
                        name=metadata["name"],
                        version=metadata.get("version", "1.0.0"),
                        description=metadata.get("description", "User-created template"),
                        supported_python_versions=metadata.get("supported_python_versions", ["3.11"]),
                        min_python=metadata.get("min_python", "3.11"),
                        architecture=metadata.get("architecture", "imported"),
                        style=metadata.get("style", "custom"),
                        included_tooling=metadata.get("included_tooling", []),
                        runtime_dependencies=metadata.get("runtime_dependencies", []),
                        dev_dependencies=metadata.get("dev_dependencies", []),
                        structure_preview=structure[:120],
                        files=files,
                        default_license=metadata.get("default_license", "MIT"),
                        source=metadata.get("source", "user"),
                        category=metadata.get("category", "General"),
                        author=metadata.get("author"),
                        variable_style=metadata.get("variable_style", "double_brace"),
                    )
                )
            except Exception as exc:
                logger.warning("Failed to load user template from %s: %s", template_dir, exc)
        return templates

    def _template_dir(self, template_id: str) -> Path:
        return self.base_dir / template_id
