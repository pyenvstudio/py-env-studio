# Features

Py Env Studio provides a desktop GUI and command-line interface for managing
Python environments, packages, projects, and related developer workflows.

## Environment management

- Create virtual environments with a detected or manually selected Python interpreter.
- Optionally upgrade `pip` during environment creation.
- List, search, rename, delete, and refresh environments.
- Activate an environment in a chosen working directory.
- Launch a selected environment with Command Prompt, VS Code, PyCharm, or a user-configured tool.
- Record the most recently used location, Python version, package-manager choice, size, and last scan time for each environment.
- Calculate and display environment sizes.
- Activate environments from the table with a double-click, and copy a recent location to the clipboard while pre-filling the working-directory field.

## Package and dependency management

- List the packages installed in an environment.
- Install, update, and uninstall individual packages.
- Import dependencies from a requirements file and export an environment to `requirements.txt`.
- Check for outdated packages and update selected packages from the GUI.
- Choose `pip` or `uv` as the package manager for an environment.
- Route package operations through the selected manager, with an automatic fallback to `pip` if `uv` is unavailable or its operation fails.
- Preview a proposed installation before applying it. The dependency-preview service reports expected additions, upgrades, removals, conflicts, and potential breaking changes.
- Recover from common dependency-resolution failures with AutoResolver. It detects resolver errors, retries with version constraints removed, and keeps the source requirements file unchanged.

## Security insights

- Scan installed packages for known vulnerabilities.
- Retrieve package metadata, dependency data, and vulnerability information from PyPI, deps.dev, and OSV.
- Store scan results locally and retain the scan timestamp per environment.
- Present a vulnerability insights dashboard with dependency, package-detail, and scan-detail views.
- Track fixed package versions and mark stored vulnerability status as resolved after package updates.
- Remediate an individual vulnerability directly from its dashboard details with `Update Now`; the action upgrades the affected package to the remediation-recommended fixed version after confirmation.
- Remediate all actionable vulnerabilities in an environment with `Upgrade all Packages`; the dashboard selects the highest recommended fixed version for each affected package, reports partial failures, and refreshes the scan data when the operation finishes.
- Disable remediation actions when no fixed version is available or the installed package version already satisfies the recommended fix.

## Project templates

- Start projects from built-in Python Script, Python CLI, and Python Package templates.
- Preview template files before creation and validate project names, module names, Python versions, and target directories.
- Create a project through a non-blocking workflow that exposes creation state, success, and failure to the GUI.
- Optionally create a virtual environment and initialize Git as part of project creation, using configured defaults.
- Open a generated project with a detected or preferred editor, with a recovery path to choose another tool when launching fails.
- Create reusable user templates from a local project or a GitHub repository.
- Validate GitHub repository URLs, clone imports safely into temporary storage, exclude sensitive or irrelevant files, and clean up temporary clones.
- Manage imported templates through add, preview, use, and delete actions.
- Use the same template registry and engine for built-in and user templates.

## Runtime-managed projects and CLI

- Initialize the current project for Py Env Studio with `pes init`.
- Enable or disable runtime interception with `pes on` and `pes off`.
- Run a script in its managed environment with `pes run <script.py> [args...]`.
- Inspect the current project with `pes status` and view all registered projects with `pes list-projects`.
- Persist project settings in `pes.config`, including environment identity, path, Python version, package manager, and runtime state.
- Maintain a global registry of managed projects and environments.
- Perform core environment and requirements operations from the CLI using `--create`, `--delete`, `--list`, `--activate`, `--install`, `--uninstall`, `--export`, and `--import-reqs`.

## Configuration and personalization

- Configure default environment location, Python interpreter, package manager, project-opening tool, and template project defaults.
- Choose light, dark, or system appearance mode and configure UI scaling.
- Apply, save, cancel, or reset preferences through the configuration UI.
- Store user preferences, runtime paths, environment metadata, setup state, and database data in application-managed locations.

## Plugins and learning support

- Discover plugins from user plugin directories and enable or disable them from the GUI.
- Persist plugin state across restarts and run application startup and shutdown lifecycle hooks.
- Let plugins handle environment create, delete, activate, and rename events; package install, uninstall, and update events; scan completion; and template creation completion.
- Provide a sample plugin and development documentation for custom extensions.
- Include Py-Tonic learning support with topic-based challenges, answer evaluation, contextual advice, notification preferences, and a persisted user learning profile.

## Platform support and installation resilience

- Run as a CustomTkinter desktop application on supported Python platforms.
- Provide the `py-env-studio`, `pyenvstudio`, and `pes` command aliases.
- Initialize local application state and the SQLite database during startup.
- Repair or migrate legacy database state when needed, and create the Windows Apps shortcut when supported.

For the relationships between these components, see [Architecture](architecture.md).
