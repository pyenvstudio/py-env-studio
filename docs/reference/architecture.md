# Py Env Studio Architecture

This document describes the implemented architecture of Py Env Studio. The application has two entry surfaces: a CustomTkinter desktop GUI and the `pes` command-line interface. Both use the same core services for environments, packages, templates, runtime-managed projects, configuration, and persistence.

```text
flowchart TB
    GUI[CustomTkinter GUI: PyEnvStudio] --> UI[ui/main_window.py]
    CLI[CLI aliases: py-env-studio, pyenvstudio, pes] --> Commands[commands.py]
    Commands --> Bootstrap[bootstrap.initialize_app_runtime]
    Commands --> Env
    Commands --> Packages
    Commands --> Runtime
    UI --> Env
    UI --> Packages
    UI --> Templates
    UI --> Config
    UI --> Plugins
    UI --> Learning

    subgraph Core[Core services]
        Env[env_manager: environment lifecycle and launch]
        Packages[package_manager: unified package operations]
        Templates[templates: registry, engine, workflow, user store]
        Runtime[runtime_toggle: managed project environments]
        Config[configuration and runtime: preferences and paths]
        Plugins[plugins: discovery, lifecycle, hooks]
        Learning[py_tonic: learning profile and challenges]
        Preview[dependency_preview: pre-install impact analysis]
        Resolver[auto_resolve: install recovery]
    end

    Packages --> Pip[pip_tools]
    Packages --> Uv[uv_tools]
    Pip --> Venv[Python virtual environments]
    Uv --> Venv
    Env --> Venv
    Runtime --> Venv
    Templates --> Env
    Templates --> Plugins
    Resolver --> Pip
    Resolver --> Uv
    Preview --> Pip

    UI --> SecurityUI[Vulnerability reports and insights]
    SecurityUI --> Scanner[vulneribility_scanner]
    Scanner --> PyPI[PyPI API]
    Scanner --> DepsDev[deps.dev API]
    Scanner --> OSV[OSV API]
    Scanner --> Database[(SQLite scan database)]
    SecurityUI --> Database

    Bootstrap --> Database
    Config --> Preferences[User preferences and app configuration]
    Env --> EnvData[Environment metadata]
    Runtime --> ProjectConfig[Project pes.config]
    Runtime --> Registry[Global project registry]
    Plugins --> PluginFiles[User plugin directories]
    Templates --> TemplateFiles[Built-in and user template storage]
    Learning --> LearningProfile[Persisted learning profile]
```

## Main components

| Component | Responsibility |
| --- | --- |
| `py_env_studio.commands` | Parses CLI flags and subcommands, initializes the application runtime, and starts the GUI when no command is supplied. |
| `py_env_studio.ui.main_window` | Implements the CustomTkinter desktop application, including environment, package, configuration, template, plugin, and vulnerability-report workflows. |
| `py_env_studio.core.env_manager` | Creates, validates, lists, renames, deletes, activates, and records metadata for environments. |
| `py_env_studio.core.package_manager` | Selects the environment's `pip` or `uv` backend and provides a consistent package-management interface. |
| `py_env_studio.core.templates` | Defines built-in templates, stores user templates, validates requests, generates projects, and coordinates creation state. |
| `py_env_studio.core.runtime_toggle` | Manages project-local `pes.config`, the global project registry, managed environments, and runtime execution. |
| `py_env_studio.core.configuration` and `runtime` | Load, validate, and persist preferences and determine application data paths. |
| `py_env_studio.core.plugins` | Discovers plugins, persists enablement, loads plugin classes, and dispatches lifecycle hooks. |
| `py_env_studio.utils.vulneribility_scanner` | Aggregates package, dependency, and vulnerability information from external public APIs. |
| `py_env_studio.utils.vulneribility_insights` | Presents stored scan data as an interactive vulnerability report. |

## Persistence and integrations

- The startup bootstrap ensures application setup state and the SQLite database are ready before GUI or CLI work begins.
- Environment metadata and preferences are stored under the application runtime data location resolved by the configuration service.
- Runtime-managed projects use a project-local `pes.config` plus a global JSON registry.
- Template, plugin, and Py-Tonic data are persisted separately in their respective managed storage locations.
- Package and security workflows use local virtual environments plus public PyPI, deps.dev, and OSV services.
