# Templates Phase 1.2

Phase 1.2 extends template management with user-created templates and GitHub import.

## Scope

- Add template from local project directory.
- Import template from public GitHub repository URL.
- Save user-defined template metadata and template ID.
- Store user templates in PES user data directory.
- Use user templates through the same registry/engine pipeline as built-in templates.
- Delete user templates with confirmation.

## Architecture

Core modules:

- `py_env_studio/core/templates/user_template_store.py`
  - source inspection
  - metadata validation
  - template save/load/delete
  - user-template storage lifecycle
- `py_env_studio/core/templates/github_import.py`
  - GitHub URL validation
  - safe `git clone --depth 1` import
- `py_env_studio/core/templates/content_filters.py`
  - centralized exclusions
  - sensitive file detection
- `py_env_studio/core/templates/registry.py`
  - unified built-in + user template discovery
- `py_env_studio/core/templates/engine.py`
  - shared generation for both built-in and user templates
  - supports `format` and `double_brace` variable styles

## Storage

User templates are stored under the PES runtime user-data directory:

`<user_data_dir>/templates/user/<template_id>/`

Each template directory contains:

- `template.json` metadata
- `content/` copied UTF-8 text files used by template rendering

Built-in templates remain embedded and are not overwritten by user actions.

## Security

Import behavior treats source repositories as untrusted input.

- No project code is executed during import.
- No dependency installation or build hooks are run.
- Git clone uses safe argument arrays.
- Exclusion rules filter common generated/IDE/cache paths.
- Sensitive files (for example `.env`, `*.pem`, `*.key`) are excluded and surfaced as warning.
- Relative-path safety checks prevent unsafe paths.

## UI Flow

`Templates -> Manage Templates`

- Built-in Templates section
- My Templates section
- `+ Add Template` flow:
  - Local Project
  - GitHub Repository

GitHub flow is async and status-driven:

- validating URL
- cloning repository
- inspecting project
- metadata + preview
- save template

## Template Engine Reuse

Both template sources resolve through one path:

- Built-in template -> registry -> template engine -> project
- User template -> registry -> template engine -> project

No separate user-template project-generation engine is introduced.

## Testing

Primary tests:

- `tests/test_user_template_store.py`
- `tests/test_github_template_import.py`
- `tests/test_template_registry.py` (built-in + user discovery)
- `tests/test_template_engine.py` (double-brace user-template rendering)
