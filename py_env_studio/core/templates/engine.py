"""Template rendering and project creation engine."""

from __future__ import annotations

import datetime
import logging
import re
import subprocess
from pathlib import Path
from string import Formatter
from typing import Callable, Dict

from .. import env_manager
from .. import package_manager
from .models import TemplateCreationRequest, TemplateCreationResult
from .registry import TemplateRegistry, get_default_registry
from .validator import (
    TemplateValidationError,
    resolve_project_path,
    sanitize_module_name,
    validate_module_name,
    validate_project_name,
    validate_python_version,
    validate_target_directory,
)

logger = logging.getLogger(__name__)


class TemplateEngineError(RuntimeError):
    """Raised when template generation fails."""


class TemplateEngine:
    """Create projects from templates and integrate with PES env management."""

    def __init__(self, registry: TemplateRegistry | None = None) -> None:
        self.registry = registry or get_default_registry()

    def list_templates(self):
        return self.registry.list_all()

    def get_template(self, template_id: str):
        return self.registry.get(template_id)

    def preview(self, template_id: str, request: TemplateCreationRequest) -> Dict[str, object]:
        template = self.registry.get(template_id)
        context = self._build_context(template, request)
        structure = [self._safe_format(item, context) for item in template.structure_preview]
        return {
            "template_id": template.id,
            "name": template.name,
            "description": template.description,
            "source": template.source,
            "category": template.category,
            "supported_python_versions": template.supported_python_versions,
            "architecture": template.architecture,
            "style": template.style,
            "included_tooling": template.included_tooling,
            "runtime_dependencies": template.runtime_dependencies,
            "dev_dependencies": template.dev_dependencies,
            "structure_preview": structure,
        }

    def create_project(
        self,
        request: TemplateCreationRequest,
        log_callback: Callable[[str], None] | None = None,
    ) -> TemplateCreationResult:
        template = self.registry.get(request.template_id)
        project_path = self._validate_request(template, request)
        context = self._build_context(template, request)

        self._log(log_callback, f"Template selected: {template.id}")
        self._log(log_callback, f"Project path: {project_path}")

        try:
            project_path.mkdir(parents=True, exist_ok=True)
            generated = self._render_files(
                template.files,
                project_path,
                context,
                log_callback,
                variable_style=template.variable_style,
            )
            self._verify_generated_files(project_path, generated)
            self._verify_python_files(project_path)
            self._verify_pyproject(project_path)

            if request.initialize_git:
                self._initialize_git(project_path, log_callback)

            created_env = None
            installed_deps: list[str] = []
            if request.create_virtual_environment:
                created_env = self._create_and_configure_environment(
                    request=request,
                    project_path=project_path,
                    template=template,
                    log_callback=log_callback,
                )
                deps = list(template.runtime_dependencies)
                if request.install_dev_dependencies:
                    deps.extend(template.dev_dependencies)
                installed_deps = self._install_dependencies(created_env, deps, log_callback)

            self._log(log_callback, "Template creation completed")
            return TemplateCreationResult(
                template_id=template.id,
                project_path=project_path,
                generated_files=generated,
                created_environment_name=created_env,
                installed_dependencies=installed_deps,
                metadata={
                    "module_name": context["module_name"],
                    "distribution_name": context["distribution_name"],
                    "source": template.source,
                },
            )
        except Exception as exc:
            logger.exception("Template creation failed for %s", template.id)
            raise TemplateEngineError(str(exc)) from exc

    def _validate_request(self, template, request: TemplateCreationRequest) -> Path:
        validate_project_name(request.project_name)
        validate_python_version(request.python_version, template.supported_python_versions)

        module_name = request.package_name or sanitize_module_name(request.project_name)
        validate_module_name(module_name)

        if request.cli_command_name:
            validate_module_name(request.cli_command_name.replace("-", "_"))

        project_path = resolve_project_path(request.project_location, request.project_name)
        validate_target_directory(project_path)
        return project_path

    def _build_context(self, template, request: TemplateCreationRequest) -> Dict[str, str]:
        module_name = request.package_name or sanitize_module_name(request.project_name)
        distribution_name = request.project_name.strip().lower().replace(" ", "-")
        python_tag = request.python_version.replace(".", "")

        return {
            "template_id": template.id,
            "project_name": request.project_name,
            "description": template.description,
            "module_name": module_name,
            "distribution_name": distribution_name,
            "python_version": request.python_version,
            "python_tag": python_tag,
            "cli_command_name": request.cli_command_name or module_name,
            "author": request.author or "Py Env Studio User",
            "license": request.license_name or template.default_license,
            "year": str(datetime.datetime.now().year),
        }

    def _safe_format(self, value: str, context: Dict[str, str]) -> str:
        formatter = Formatter()
        keys = {name for _, name, _, _ in formatter.parse(value) if name}
        missing = [key for key in keys if key not in context]
        if missing:
            raise TemplateEngineError(f"Template contains unknown placeholders: {', '.join(missing)}")
        return value.format(**context)

    def _render_double_brace(self, value: str, context: Dict[str, str]) -> str:
        rendered = value
        for key, key_value in context.items():
            rendered = rendered.replace("{{ " + key + " }}", key_value)
            rendered = rendered.replace("{{" + key + "}}", key_value)
        return rendered

    def _render_value(self, value: str, context: Dict[str, str], variable_style: str) -> str:
        if variable_style == "double_brace":
            return self._render_double_brace(value, context)
        return self._safe_format(value, context)

    def _render_files(self, files, project_path: Path, context: Dict[str, str], log_callback, variable_style: str):
        generated: list[Path] = []
        for item in files:
            if item.condition_key and not context.get(item.condition_key):
                continue
            rel_path = self._render_value(item.path, context, variable_style)
            target = (project_path / rel_path).resolve()
            if project_path not in target.parents and target != project_path:
                raise TemplateEngineError(f"Refusing to write outside project directory: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise TemplateEngineError(f"Refusing to overwrite existing file: {target}")
            content = self._render_value(item.content, context, variable_style)
            target.write_text(content, encoding="utf-8")
            generated.append(target)
        self._log(log_callback, "Generating project structure")
        return generated

    def _verify_generated_files(self, project_path: Path, generated_files: list[Path]) -> None:
        missing = [path for path in generated_files if not path.exists()]
        if missing:
            raise TemplateEngineError(f"Missing generated files: {missing}")
        if not (project_path / "pyproject.toml").exists():
            raise TemplateEngineError("Generated project missing pyproject.toml")

    def _verify_python_files(self, project_path: Path) -> None:
        for py_file in project_path.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            compile(source, str(py_file), "exec")

    def _verify_pyproject(self, project_path: Path) -> None:
        pyproject = project_path / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        if "[project]" not in content:
            raise TemplateEngineError("Invalid pyproject.toml: missing [project] section")

    def _initialize_git(self, project_path: Path, log_callback) -> None:
        self._log(log_callback, "Initializing git repository")
        subprocess.run(["git", "init"], cwd=project_path, check=False, capture_output=True, text=True)

    def _create_and_configure_environment(self, request, project_path, template, log_callback):
        env_name = f"{request.project_name.strip().lower().replace(' ', '-')}-env"
        env_name = env_name.replace("_", "-")[:45]
        self._log(log_callback, f"Creating virtual environment: {env_name}")

        python_path = self._resolve_python_interpreter(request.python_version)
        if not python_path:
            raise TemplateEngineError(
                f"Python {request.python_version} is unavailable on this system. "
                "Install it or choose another version."
            )

        env_manager.create_env(
            env_name,
            python_path=python_path,
            upgrade_pip=True,
            log_callback=log_callback,
        )

        from ..runtime_toggle import save_project_metadata

        env_path = str(Path(env_manager.VENV_DIR) / env_name)
        save_project_metadata(
            Path(project_path),
            {
                "project_name": request.project_name,
                "environment_id": env_name,
                "environment_path": env_path,
                "python_version": request.python_version,
                "package_manager": env_manager.get_preferred_package_manager(),
                "runtime_enabled": True,
                "auto_init": True,
            },
        )
        self._log(log_callback, "Configured project interpreter metadata")
        return env_name

    def _resolve_python_interpreter(self, requested_version: str) -> str | None:
        interpreters = env_manager.list_pythons()
        for interpreter in interpreters:
            detected = env_manager.is_valid_python_version_detected(interpreter)
            if detected and detected.startswith(f"Python {requested_version}"):
                return interpreter
        return None

    def _install_dependencies(self, env_name: str, dependencies: list[str], log_callback):
        installed: list[str] = []
        for dep in dependencies:
            package_manager.install_package(env_name, dep, log_callback=log_callback)
            installed.append(dep)
        if installed:
            self._log(log_callback, f"Installed dependencies: {', '.join(installed)}")
        return installed

    def _log(self, log_callback, message: str) -> None:
        logger.info(message)
        if log_callback:
            log_callback(message)
