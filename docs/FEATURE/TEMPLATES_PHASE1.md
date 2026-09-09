# Templates Phase 1

This document describes the Phase 1 Templates architecture in Py Env Studio.

## Goals

- Provide reusable project templates for Python Script, Python CLI, and Python Package projects.
- Keep template definitions declarative and separate from GUI code.
- Reuse existing environment and package management services.
- Make future template additions possible without changing core generation workflow.

## Architecture

Template flow:

1. UI collects template configuration from the wizard.
2. `TemplateEngine` validates inputs and renders project files.
3. Engine optionally creates a virtual environment via existing environment APIs.
4. Engine installs dependencies via existing package manager APIs.
5. UI reports status and emits plugin hook `after_template_created`.

Core modules:

- `py_env_studio/core/templates/models.py`
Defines `TemplateSpec`, `TemplateFile`, `TemplateCreationRequest`, and `TemplateCreationResult`.
- `py_env_studio/core/templates/registry.py`
Template registration and discovery (`TemplateRegistry` and default registry factory).
- `py_env_studio/core/templates/builtin_templates.py`
Phase 1 built-in templates and declarative file definitions.
- `py_env_studio/core/templates/validator.py`
Input and path validation, module naming checks, and collision checks.
- `py_env_studio/core/templates/engine.py`
Creation orchestration, rendering, basic validation checks, and environment/dependency integration.

## Template Specification

Templates are represented by typed dataclasses (`TemplateSpec` and `TemplateFile`) instead of embedding generation logic in GUI buttons.

Each spec includes:

- Metadata (`id`, `name`, `version`, `description`)
- Python compatibility (`supported_python_versions`, `min_python`)
- Architecture/tooling (`architecture`, `style`, `included_tooling`)
- Dependency groups (`runtime_dependencies`, `dev_dependencies`)
- Structure preview (`structure_preview`)
- Files (`TemplateFile(path, content, condition_key)`)

## Registration

Built-in templates are registered in `register_builtin_templates(registry)`.

Default registry loading:

1. `get_default_registry()` creates `TemplateRegistry` once.
2. Built-in registration function is invoked.
3. UI and engine use the same registry instance.

Because the UI reads template entries from the registry, new templates appear in the Templates menu and landing view automatically.

## Variables and Rendering

Supported context values include:

- `project_name`
- `module_name`
- `distribution_name`
- `python_version`
- `python_tag`
- `cli_command_name`
- `author`
- `year`

Rendering uses safe string formatting and fails if unknown placeholders remain.

## Validation and Safety

Validation checks include:

- project name format
- module/package identifier format
- supported Python version
- destination directory and collision checks
- path safety (no writes outside selected project directory)
- generated Python compile checks
- minimal `pyproject.toml` sanity check

Safety guarantees:

- no arbitrary code execution during rendering
- no silent overwrite of existing files
- no shell commands composed from untrusted template content

## Environment Integration

Template engine reuses existing services:

- environment creation via `py_env_studio.core.env_manager.create_env`
- dependency installation via `py_env_studio.core.package_manager.install_package`
- project interpreter metadata via `py_env_studio.core.runtime_toggle.save_project_metadata`

## Testing

Tests are located at:

- `tests/test_template_registry.py`
- `tests/test_template_engine.py`

Coverage includes:

- registry registration and lookup behavior
- unknown and duplicate template handling
- generation for all three Phase 1 templates
- placeholder substitution behavior
- existing-directory collision handling
- invalid project-name handling
- environment/dependency integration contract via monkeypatching

## Add a New Template

1. Add a new `TemplateSpec` in `py_env_studio/core/templates/builtin_templates.py` or another template provider module.
2. Register it through `TemplateRegistry.register(...)`.
3. Ensure spec includes metadata, structure preview, dependencies, and files.
4. Add tests under `tests/` for generation and validation.
5. Validate generated files compile and project startup behavior.

No UI code changes are required if the template is added to the registry used by `TemplateEngine`.
