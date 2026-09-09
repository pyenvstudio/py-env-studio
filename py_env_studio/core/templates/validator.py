"""Validation helpers for template generation requests."""

from __future__ import annotations

import re
from pathlib import Path


class TemplateValidationError(ValueError):
    """Raised when a template request fails validation."""


_PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{1,79}$")
_MODULE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{1,62}$")


def sanitize_module_name(project_name: str) -> str:
    candidate = project_name.strip().lower().replace("-", "_").replace(" ", "_")
    candidate = re.sub(r"[^a-z0-9_]", "", candidate)
    if not candidate:
        candidate = "my_project"
    if candidate[0].isdigit():
        candidate = f"p_{candidate}"
    return candidate


def validate_project_name(project_name: str) -> None:
    if not _PROJECT_NAME_PATTERN.match(project_name.strip()):
        raise TemplateValidationError(
            "Invalid project name. Use letters, numbers, spaces, '-', '_' or '.'."
        )


def validate_module_name(module_name: str) -> None:
    if not _MODULE_NAME_PATTERN.match(module_name):
        raise TemplateValidationError(
            "Invalid package/module name. Use a valid Python identifier style name."
        )


def validate_python_version(requested_version: str, supported_versions: list[str]) -> None:
    if requested_version not in supported_versions:
        supported = ", ".join(supported_versions)
        raise TemplateValidationError(
            f"Python version '{requested_version}' is not supported by this template. "
            f"Supported versions: {supported}."
        )


def resolve_project_path(project_location: str, project_name: str) -> Path:
    root = Path(project_location).expanduser().resolve()
    if not root.exists():
        raise TemplateValidationError(f"Project location does not exist: {root}")
    if not root.is_dir():
        raise TemplateValidationError(f"Project location is not a directory: {root}")

    project_path = (root / project_name).resolve()
    if root not in project_path.parents:
        raise TemplateValidationError("Project path escapes selected project location.")
    return project_path


def validate_target_directory(project_path: Path) -> None:
    if project_path.exists():
        if any(project_path.iterdir()):
            raise TemplateValidationError(
                f"Target directory already exists and is not empty: {project_path}"
            )
    else:
        parent = project_path.parent
        if not parent.exists():
            raise TemplateValidationError(
                f"Parent directory does not exist for target path: {parent}"
            )
