# Py Env Studio --- Features & Current Implementation

> Single source of truth for Py Env Studio capabilities: user-facing feature
> reference and technical implementation inventory, based on scanning the
> actual Python source (not only README/Markdown documentation).
>
> Py Env Studio provides a desktop GUI and command-line interface for managing
> Python environments, packages, projects, and related developer workflows.
>
> **Current release: v2.1.0.** New in this release: project templates and
> Community Templates, the configuration center, official Python Install
> Manager runtime integration, dashboard remediation actions, native chart
> widgets, informative CLI/GUI progress, and the **beta** MCP control plane for
> AI coding agents. See the [v2.1.0 release notes](../releases/v2.1.0.md).

## 1. Virtual Environment Management

The core environment manager implements:

-   Create environments (with a detected or manually selected Python
    interpreter; optionally upgrade `pip` during creation)
-   Delete environments
-   Rename environments
-   Search/filter environments
-   List environments
-   Refresh environments
-   Detect available Python installations
-   Validate Python executables
-   Detect Python versions
-   Activate environments, including activation in a chosen working directory
-   Launch a selected environment with Command Prompt, VS Code, PyCharm,
    or a user-configured tool
-   Track environment metadata
-   Track recent project/location information
-   Calculate environment size
-   Select preferred package manager per environment
-   Refresh runtime paths
-   Validate environment names
-   Retrieve the Python executable associated with an environment
-   Record the most recently used location, Python version,
    package-manager choice, size, and last scan time for each environment

The GUI exposes environment creation, activation, searching, listing,
and deletion. Environments can be activated from the table with a
double-click, and a recent location can be copied to the clipboard while
pre-filling the working-directory field.

------------------------------------------------------------------------

## 2. pip Package Management

The package manager implements:

-   List installed packages
-   Install packages
-   Uninstall packages
-   Update packages (including updating selected packages from the GUI)
-   Import `requirements.txt`
-   Export requirements
-   Detect outdated packages
-   Generate and consume standardized PEP 751 `pylock.toml` locks

The GUI provides dedicated package-management functionality. Per-environment
locks are generated from installed package versions, validated and verified
without execution, and synchronized only after a change preview and explicit
confirmation. Lock files remain portable TOML artifacts; SQLite stores only
their status and metadata. Package mutations mark an existing lock unchecked.

------------------------------------------------------------------------

## 3. Native `uv` Integration

`uv` is integrated as a package/environment management backend.

Implemented capabilities include:

-   Detect `uv`
-   Get `uv` version
-   List packages using `uv`
-   Install packages
-   Uninstall packages
-   Update packages
-   Import requirements
-   Export requirements
-   Check outdated packages
-   Package information lookup
-   `UVManager` abstraction
-   Native PEP 751 lock generation with `uv pip compile` and synchronization
    with `uv pip sync`

An environment can choose `pip` or `uv` as its package manager, and
package operations are routed through the selected manager, with an
automatic fallback to `pip` if `uv` is unavailable or its operation
fails.

Environment creation can choose `uv` instead of traditional `venv`, with
fallback behavior when `uv` is unavailable.

------------------------------------------------------------------------

## 4. Dependency Preview / Dry Run

The dependency-preview subsystem can simulate package installation
before applying changes, so a proposed installation can be previewed
before it is applied.

It supports:

-   Dependency changes
-   Breaking-change detection
-   Preview results
-   Package specification parsing
-   Installed-package inspection
-   Dependency resolution simulation
-   Manual fallback analysis when dry-run is unavailable

The preview reports expected additions, upgrades, removals, conflicts,
and potential breaking changes.

Conceptual flow:

``` text
Install package
      ↓
Dependency Preview
      ↓
New packages / updates / possible breaking changes
      ↓
User decides
```

------------------------------------------------------------------------

## 5. Automatic Dependency Conflict Resolution

The auto-resolver can:

-   Detect dependency-resolution errors
-   Parse conflicting packages
-   Extract package names
-   Strip version constraints
-   Prepare retry packages
-   Retry installations
-   Work with pip/uv error output

It recovers from common dependency-resolution failures by retrying with
version constraints removed, and it keeps the source requirements file
unchanged.

Conceptual flow:

``` text
Install
  ↓
Dependency conflict
  ↓
Analyze error
  ↓
Prepare resolution
  ↓
Retry
```

------------------------------------------------------------------------

## 6. Vulnerability Scanner

The vulnerability scanner integrates with external security sources
including:

-   PyPI API
-   OSV API
-   deps.dev

Capabilities include:

-   Dependency vulnerability scanning
-   Package security analysis
-   Security matrix generation
-   Environment scanning
-   Package-level scanning
-   Python package metadata/deprecation information
-   Retrieval of package metadata, dependency data, and vulnerability
    information from PyPI, deps.dev, and OSV

Scan results are stored locally and the scan timestamp is retained per
environment.

------------------------------------------------------------------------

## 7. Vulnerability Insights Dashboard

The vulnerability-insights subsystem provides:

-   Vulnerability tree/list
-   Package selection
-   Detailed vulnerability information
-   Dependency, package-detail, and scan-detail views
-   Version comparison
-   Upgrade recommendations
-   Update-now actions
-   Upgrade-all workflow
-   Upgrade planning
-   Historical/trend chart rendering
-   Enterprise/index information
-   Database-backed refresh
-   Package vulnerability status

It tracks fixed package versions and marks the stored vulnerability
status as resolved after package updates. An individual vulnerability
can be remediated directly from its dashboard details with
`Update Now`, which upgrades the affected package to the
remediation-recommended fixed version after confirmation. All actionable
vulnerabilities in an environment can be remediated with
`Upgrade all Packages`, which selects the highest recommended fixed
version for each affected package, reports partial failures, and
refreshes the scan data when the operation finishes. Remediation actions
are disabled when no fixed version is available or the installed package
version already satisfies the recommended fix.

Severity breakdown and trend charts are rendered with native `tkinter-dash`
widgets (`BarChart` / `LineChart`) directly in the CustomTkinter dashboard,
follow the active appearance mode, and show a placeholder label when a
package has no scan history. `matplotlib` is no longer a dependency.

Conceptual flow:

``` text
Environment
    ↓
Security Scan
    ↓
Vulnerability data
    ↓
Vulnerability Insights
    ├── Details
    ├── Versions
    ├── Upgrade
    ├── Upgrade All
    └── Trends
```

------------------------------------------------------------------------

## 8. Plugin Architecture

The plugin system supports:

-   Plugin discovery from user plugin directories
-   Plugin loading
-   Plugin unloading
-   Plugin metadata
-   Plugin enable/disable (from the GUI)
-   Persistent plugin state across restarts
-   Hook registration
-   Hook execution
-   Plugin validation
-   Application context
-   Enabled-plugin loading
-   Application startup and shutdown lifecycle hooks
-   A sample plugin and development documentation for custom extensions

Environment lifecycle hooks include:

-   `before_create_env`
-   `after_create_env`
-   `before_delete_env`
-   `after_delete_env`
-   `before_activate_env`
-   `after_activate_env`
-   `before_rename_env`
-   `after_rename_env`

Package lifecycle hooks include:

-   `before_install_package`
-   `after_install_package`
-   `before_uninstall_package`
-   `after_uninstall_package`
-   `before_update_package`
-   `after_update_package`

Application hooks include:

-   `on_app_start`
-   `on_app_shutdown`
-   `on_scan_complete`

Project template hooks include:

-   `after_template_created` (emitted after a template project is created
    successfully, with project and template context)

The `PluginHook` enumeration declares all 18 hooks; plugin manifests may
subscribe to any of them through their `hooks` list.

------------------------------------------------------------------------

## 9. Project Template Engine

The template subsystem includes:

-   Template registration
-   Template discovery
-   Template preview
-   Template rendering
-   Variable substitution
-   File generation
-   Python-file verification
-   `pyproject.toml` verification
-   Project-name, module-name, Python-version, and target-directory
    validation
-   Git initialization
-   Environment creation
-   Dependency installation

The same template registry and engine serve built-in and user
templates.

The template architecture contains dedicated components for the engine,
registry, workflow, models, validation, built-in templates, user
templates, GitHub import, community discovery, and content filtering.

------------------------------------------------------------------------

## 10. Built-in Project Templates

The code contains built-in templates for at least:

-   Python script project
-   CLI project
-   Python package project

The package template uses a `src` layout and tests.

Conceptual flow:

``` text
New Project
   ↓
Template
   ├── Script
   ├── CLI
   └── Package
```

------------------------------------------------------------------------

## 11. User-Created Templates

The user-template store supports:

-   Saving templates
-   Loading templates
-   Deleting templates
-   Template IDs
-   Template names
-   Descriptions
-   Template metadata
-   Custom metadata
-   Source/origin tracking (source provenance)
-   Duplicate detection (duplicate-origin detection)
-   File filtering
-   UTF-8 validation
-   Template validation

This supports saving a user's own project structure as a reusable
template, created from a local project or a GitHub repository, through
the existing template creation workflow. Imported templates are managed
through add, preview, use, and delete actions.

------------------------------------------------------------------------

## 12. GitHub Template Import

GitHub repository importing supports:

-   GitHub URL validation
-   Repository-name extraction
-   Repository cloning into temporary storage
-   Exclusion of sensitive or irrelevant files
-   Cleanup of temporary clones
-   Conversion into a user template

Conceptual flow:

``` text
GitHub repository
       ↓
Validate
       ↓
Clone
       ↓
Inspect
       ↓
Save as Py Env Studio template
```

------------------------------------------------------------------------

## 13. Community Template Discovery

The community-template service supports:

-   GitHub searching
-   Candidate discovery
-   Repository inspection
-   README reading
-   File detection
-   Candidate metadata
-   Existing-import detection
-   Inspection cleanup
-   Rate-limit handling
-   Search with lightweight categories, sorting, and pagination
-   Short-lived in-memory result caching

The GUI includes a Community Templates dialog and provides
warning/preview functionality for third-party templates. Community
repositories are previewed through static inspection before import;
repository code, build hooks, dependencies, Docker files, and GitHub
workflows are never executed by the discovery or import flow.

------------------------------------------------------------------------

## 14. Project Creation Workflow

The template workflow can perform:

``` text
Template
 ↓
Generate project
 ↓
Validate generated files
 ↓
Initialize Git
 ↓
Create environment
 ↓
Resolve Python interpreter
 ↓
Install dependencies
```

Project creation runs as a non-blocking workflow that exposes creation
state, success, and failure to the GUI. Template files can be previewed
before creation. Creating a virtual environment and initializing Git are
optional steps governed by configured defaults.

This makes the template system a project bootstrapper rather than just a
file copier.

------------------------------------------------------------------------

## 15. IDE / Tool Integration

Project-launching/integration components provide:

-   Detection of installed developer tools
-   Identification of available project openers
-   Preferred project editor configuration
-   Opening projects using a selected tool
-   Adding custom "Open With" tools
-   Associating tools with environments
-   A recovery path to choose another tool when launching fails

The GUI supports selecting a project-opening tool such as VS Code, and a
generated project can be opened with a detected or preferred editor.

------------------------------------------------------------------------

## 16. Project Runtime Toggle

The project runtime subsystem provides CLI commands including:

``` text
py-env-studio init
py-env-studio on
py-env-studio off
py-env-studio status
py-env-studio run
```

It supports:

-   Project initialization
-   Managed project environment creation
-   Runtime enable/disable
-   Project metadata
-   Global project registry
-   Runtime interception
-   Running scripts inside the managed environment
-   Project status
-   Registered-project listing
-   Environment ID generation

Project settings persist in `pes.config`, including environment
identity, path, Python version, package manager, and runtime state. A
global registry of managed projects and environments is maintained.

This gives Py Env Studio a project-level managed-runtime concept beyond
ordinary venv management.

------------------------------------------------------------------------

## 17. CLI

The CLI is available under the `py-env-studio`, `pyenvstudio`, and
`pes` command aliases.

The CLI provides commands including:

``` text
create
delete
list
activate
install
uninstall
export
import
init
on
off
status
list-projects
run
mcp
```

Core environment and requirements operations use the flag form
(`--create`, `--delete`, `--list`, `--activate`, `--install`,
`--uninstall`, `--export`, `--import-reqs`). `pes run <script.py>
[args...]` runs a script in its managed environment, `pes status` and
`pes list-projects` inspect the current and all registered projects,
and `pes mcp` starts the local read-only MCP control plane over stdio
for AI clients (beta — see section 25 below and
[the MCP reference](mcp.md)).

The CLI shares common output controls (`-v`/`--verbose`, `-q`/`--quiet`,
`--no-progress`, plus `PES_LOG_LEVEL`, `PES_NO_PROGRESS`, and `PES_PROGRESS`)
and draws a single-line progress gauge on stderr for long-running commands when
stderr is a TTY. Failures print one `ERROR <component>: …` line on stderr and
exit with status `1`; the full traceback stays in the rotating log file.

This gives the GUI and CLI complementary workflows.

------------------------------------------------------------------------

## 18. Configuration System

The configuration service provides persistent application preferences
including:

-   Default virtual-environment path (read-only in the configuration dialog;
    change `venv_dir` in the PES `config.ini` instead)
-   Default package manager
-   Default Python
-   Default project tool/editor
-   Template defaults
-   Git initialization preference
-   UI appearance
-   UI scaling
-   Runtime provider

Configuration validation and atomic writes are also implemented.
Preferences can be applied, saved, cancelled, or reset through the
configuration UI. User preferences, runtime paths, environment metadata,
setup state, and database data live in application-managed locations.

------------------------------------------------------------------------

## 19. SQLite Database

The project has a dedicated database manager providing:

-   SQLite lifecycle management
-   Database initialization
-   Foreign-key enforcement
-   Schema creation
-   Migration handling
-   Legacy schema migration
-   Application metadata
-   Environment records
-   Vulnerability records

Current database tables include:

``` text
app_metadata
environments
env_vulnerability_info
python_runtime_metadata
python_runtime_cache_state
project_contract
```

### Table schemas

Authoritative DDL lives in `core/schema/*.sql` and is executed in file
order by `DatabaseManager.initialize_database`. Reproduced here so this
document stays a complete reference.

From `core/schema/schema_core.sql`:

``` sql
CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_name TEXT UNIQUE NOT NULL,
    env_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS env_vulnerability_info (
    vid INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL,
    vulnerabilities TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (env_id) REFERENCES environments(env_id)
);
```

`app_metadata` stores schema flags (e.g. `legacy_migrated`) and
application metadata. `environments` registers environments by unique
name. `env_vulnerability_info` stores one vulnerability-scan payload per
row, linked to its environment.

From `core/schema/schema_runtime_cache.sql`:

``` sql
CREATE TABLE IF NOT EXISTS python_runtime_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    version TEXT NOT NULL,
    release_status TEXT,
    architecture TEXT,
    implementation TEXT,
    metadata_json TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, version)
);

CREATE TABLE IF NOT EXISTS python_runtime_cache_state (
    provider TEXT PRIMARY KEY,
    last_updated TIMESTAMP NOT NULL,
    last_error TEXT
);
```

These cache Python Install Manager online metadata: normalized release
rows per provider/version, plus one freshness/error row per provider. A
failed online refresh never touches existing rows.

From `core/schema/project_contract.sql` (Phase A.1):

``` sql
CREATE TABLE IF NOT EXISTS project_contract (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT UNIQUE NOT NULL,
    project_name TEXT NOT NULL,
    environment_id TEXT NOT NULL,
    python_version TEXT NOT NULL,
    python_provider TEXT NOT NULL,
    package_manager TEXT NOT NULL,
    runtime_managed INTEGER NOT NULL DEFAULT 1,
    runtime_enabled INTEGER NOT NULL DEFAULT 0,
    runtime_auto_init INTEGER NOT NULL DEFAULT 1,
    config_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

One row per PES-managed project, keyed on the normalized project path.
It stores the registered contract state resolved from `pes.config` (see
section 26); upserts refresh `updated_at` on conflict.

The existing database infrastructure provides a foundation for runtime
metadata caching.

------------------------------------------------------------------------

## 20. Setup / Installation Health

`SetupStateManager` provides:

-   Setup-state tracking
-   Installation health checks
-   State-path management

Local application state and the SQLite database are initialized during
startup. Legacy database state is repaired or migrated when needed, and
the Windows Apps shortcut is created when supported.

This supports more reliable first-run/setup behavior.

------------------------------------------------------------------------

## 21. PyTonic --- Interactive Python Learning

The PyTonic subsystem provides an interactive learning layer with:

-   Learning topics
-   Learning modes
-   Challenge bank
-   Random challenges
-   Challenge answer evaluation
-   User profile (persisted user learning profile)
-   Notification frequency (notification preferences)
-   Daily/weekly/manual notification modes
-   Personalized advice
-   Python best-practice guidance

Topics include:

-   Dependency management
-   Environment isolation
-   Package updates
-   Requirements validation
-   Python best practices

------------------------------------------------------------------------

## 22. Desktop GUI / UX

The application runs as a CustomTkinter desktop application on supported
Python platforms and includes:

-   Sidebar
-   Tabs
-   Status bar with a live activity gauge (determinate for known step counts,
    marquee for unknown durations)
-   Dark/Light/System appearance
-   UI scaling
-   Custom icons
-   Environment tables
-   Package management views
-   Configuration dialogs
-   Template dialogs
-   Community-template browser
-   Plugin management
-   Vulnerability insights (with native severity/trend charts)
-   Console/log output
-   Notifications
-   Async operations

------------------------------------------------------------------------

## 23. Async / Background Operations

The main UI provides an explicit asynchronous execution mechanism and
log queues.

It is used for longer operations such as:

-   Environment creation
-   Package installation
-   Vulnerability scans
-   Updates
-   Template workflows
-   Runtime installation

This prevents long-running package/environment operations from blocking
the Tkinter UI.

------------------------------------------------------------------------

## 24. Official Python Install Manager Integration

The current runtime-provider architecture includes:

``` text
PythonRuntime
RuntimeProvider
PythonInstallManagerProvider
```

with support for:

-   Detecting PyManager
-   Installed Python runtimes
-   Available official Python versions
-   Version normalization
-   Runtime metadata
-   Python installation
-   Runtime selection
-   Environment creation integration
-   Provider abstraction

Conceptual architecture:

``` text
                 Py Env Studio
                       │
                Runtime Provider
                       │
            Python Install Manager
                       │
        ┌──────────────┼──────────────┐
       3.11           3.12           3.13
```

------------------------------------------------------------------------

## 25. MCP Control Plane for AI Agents (Beta)

```{admonition} Beta feature
:class: warning

MCP support is **beta**. It is read-only, stdio-only and local-first: no tool
mutates environments, packages or projects, and no MCP call performs a network
request. Tool names, schemas and response envelopes can change until the
interface is declared stable. Setup steps for VS Code and other clients are in
[the MCP reference](mcp.md).
```

Py Env Studio exposes a local, read-only MCP server so AI coding agents
(such as VS Code Copilot) can consume authoritative environment,
package, dependency, security, runtime, and project information. Copilot
provides the reasoning; PES provides the Python environment operations
and context. PES is **not** an AI model.

```text
Copilot / AI agent  (reasoning layer)
        │
       MCP (stdio, local-first)
        │
        ▼
Py Env Studio (infrastructure)
   Environment · Packages · Security · Project · Database
        │
        ▼
Local Python environments
```

### Starting the server

```bash
py-env-studio mcp        # stdio transport, no GUI, no network required
```

Configure VS Code Copilot (or any MCP client) to launch that command over
stdio — the ready-to-paste client configuration, trust steps and
troubleshooting are in [the MCP reference](mcp.md). Defaults favour
`local / stdio / read-only`:

| Setting (`config.ini [mcp]`) | Default |
|---|---|
| `enabled` | `true` |
| `server_name` | `py-env-studio` |
| `transport` | `stdio` |
| `log_level` | `INFO` |

Logs always go to **stderr** — stdout is reserved for MCP protocol traffic.

### Beta toolset (read-only)

| Tool | Input | Source service |
|---|---|---|
| `pyenv_list_environments` | — | `core.env_manager.get_environment_info` |
| `pyenv_get_environment` | `environment_id` | `core.env_manager` |
| `pyenv_list_packages` | `environment_id` | `core.package_manager.list_packages` (pip/uv aware) |
| `pyenv_get_project_context` | `project_path?` | `core.runtime_toggle` + package count |
| `pyenv_get_environment_status` | `environment_id` | env + package count + registry |
| `pyenv_scan_vulnerabilities` | `environment_id` | SQLite cache via `utils.handlers.DBHelper` (never scans/networks from MCP) |
| `pyenv_get_dependency_information` | `environment_id`, `package?` | `core.dependency_preview` (`pip show` based, offline) |
| `pyenv_analyze_project` | `project_path?` | `core.project_intelligence.ProjectIntelligenceService` (aggregates registry, environment, package, dependency, outdated, security cache) |

Example `tools/call`:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "pyenv_get_project_context", "arguments": {}}}
```

### Response envelope

```json
{"success": true, "data": {...},
 "metadata": {"source": "pes", "cached": true, "timestamp": "..."}}
```

```json
{"success": false,
 "error": {"code": "ENVIRONMENT_NOT_FOUND", "message": "...", "details": {}}}
```

Ambiguous project detection returns `AMBIGUOUS_PROJECT` with candidates
instead of guessing; missing scans return `scan_available: false` instead of
performing network lookups.

### MCP architecture

```text
MCP Tool  →  PES Core Service  →  DB / package manager / runtime / security
```

MCP handlers are thin adapters. The only new service API added for MCP is
`core.env_manager.get_environment_info()` (read-only summary), plus the
`core.project_intelligence.ProjectIntelligenceService` orchestrator behind
`pyenv_analyze_project` (aggregation only, no business logic of its own).
No new SQL was needed — existing `core/schema/*.sql` templates are reused
through `DBHelper`. A future Streamable HTTP transport can reuse
`PesMcpServer.handle_message()` without redesigning tools, and a future LSP
layer can share the same core services:

```text
        PES Core
         /    \
      MCP      LSP
       │        │
   AI Agent    IDE
```

Mutation tools (`install_package`, `create_environment`, …) are intentionally
absent from the beta; the registry test asserts that no such capability exists.
A future release can add them behind explicit opt-in once the read-only surface
is stable.

------------------------------------------------------------------------

## 26. Project Contract Foundation (Phase A.1)

`pes.config` is the project-level Python environment contract for
PES-managed projects: it declares project intent, while SQLite holds the
resolved/registered state.

```text
pes.config
    ↓
declared project contract
    ↓
PES SQLite / registry
    ↓
resolved environment
```

Portable declared format (no absolute paths; the environment is
referenced by ID and resolved through PES services):

```toml
[project]
name = "cerberus-extended"

[python]
version = "3.12"
provider = "python-install-manager"

[environment]
id = "cerberus-extended-217a7026"
package_manager = "pip"

[runtime]
managed = true
enabled = true
auto_init = true
```

Dynamic information (installed packages, vulnerability results,
environment size, scan timestamps, executable status) is never stored in
`pes.config`; it remains runtime/database state. Legacy files that still
contain absolute `project:root` / `environment:path` entries keep
loading: those keys are read as fallback hints with a portability
warning and are never written back.

### Source-of-truth rules

`pes.config` is the source of truth for project intent, the Python
requirement, the environment ID, the package-manager preference, and
the runtime management preference. SQLite (`project_contract` table,
keyed on the normalized project path, plus the existing `environments`
table) is the source of truth for environment registration, the
resolved environment path, environment existence, runtime state, and
dynamic metadata. The runtime filesystem is the source of truth for
actual files, the actual Python executable, and actual installed
packages.

### Service

`core.project_contract.ProjectContractService` provides
`load` / `save` / `resolve` / `validate` over the existing
`DatabaseManager` and a dedicated `core/schema/project_contract.sql`
template file. Validation is structural only (missing name/ID, bad
Python version format, unknown package manager/provider, unregistered
or deleted environment) and never repairs anything. The phase creates
no environments, installs nothing, touches no IDE files, and performs
no network access.

------------------------------------------------------------------------

# Overall Architecture

Based on the implementation, Py Env Studio is substantially broader than
a basic virtual-environment GUI.

It combines several major areas:

``` text
                     Py Env Studio
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
 Environment             Project            Package
 Management             Factory            Management
       │                   │                   │
       │             Templates/GitHub          │
       │                   │                pip + uv
       │                   │                   │
       ├───────────────────┼───────────────────┤
       │                   │                   │
 Security             Developer            Extensibility
       │                Learning                │
       │                   │                    │
 Vulnerability         PyTonic              Plugins
 Scanner              Challenges            Hooks
       │
       └──────────── Runtime Platform ──────────
                    PyManager
                    Project runtime
                    CLI
                    MCP (beta, read-only)
```

For the relationships between these components, see
[Architecture](architecture.md).

# Strongest Technically Implemented Areas

The substantial implementation areas are:

1.  Environment lifecycle management
2.  pip + uv package management
3.  Dependency preview / dry-run
4.  Automatic dependency conflict resolution
5.  Vulnerability scanning + vulnerability insights
6.  Project template engine
7.  User template persistence
8.  GitHub template import
9.  Community template discovery
10. Plugin architecture with lifecycle hooks
11. Project runtime interception (`init/on/off/run`)
12. IDE/project launcher integration
13. PyTonic interactive Python learning
14. SQLite persistence + migrations
15. Official Python Install Manager integration
16. Configuration service with validation and atomic writes
17. Read-only MCP control plane + project intelligence (beta)

These are backed by dedicated core modules, workflows, validation,
persistence, and/or tests rather than being purely documentation-level
features.

# Persistence Architecture Observation

The current implementation uses several persistence mechanisms:

``` text
SQLite
  → environments / vulnerability info / metadata

JSON/files
  → project runtime registry / user templates / preferences

In-memory
  → template registry / plugin runtime state
```

As PyManager metadata caching is added, avoid creating another ad-hoc
persistence mechanism.

The cleaner direction is:

``` text
core/schema/
     ↓
SQL definitions
     ↓
DatabaseManager / repositories
     ↓
Runtime metadata cache
     ↓
PyManager provider
```

This keeps SQL definitions separate from Python business logic while
reusing the existing database infrastructure.
