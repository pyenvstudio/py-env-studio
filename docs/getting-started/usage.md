# Usage Manual: Py Env Studio

This manual provides a comprehensive guide for using the Py Env Studio (PES) application, a Python environment and package management tool with an intuitive graphical interface.

---

## Main Screen Overview

The main screen consists:
- **Environment Tab** - Manage Python virtual environments
- **Package Tab** - Handle package installation and management
- **Menu Bar** - File, View, Tools, Templates, and Help menus
- **Status Bar** - Fixed strip below the tabs showing current activity
- **Console** - On-screen log of task output

---

## Status Bar

The status bar sits in a fixed position between the tab area and the console,
so the layout never jumps while work runs. It shows:

- **Status text** - what the app is doing right now (e.g. `Installing numpy…`)
  or the last completed/failed action. The text turns green after a task
  succeeds and red if it fails, then settles back to the normal colour.
- **Progress gauge** - visible only while a task is actually running: it fills
  steps with a known count (package updates, GitHub imports) or animates as a
  marquee when the duration is unknown (environment creation, scans). When no
  task is running the gauge disappears entirely, leaving just the status text.

The gauge is driven by background tasks and updates automatically; details of
every action are also written to the log file (`py_env_studio.log` in the
platform data directory) and, for warnings and errors, mirrored to the console
at the bottom of the window.

---

## Environment Tab

### Creating a New Environment

To create a new Python virtual environment:

1. Navigate to the **Environment Tab**
2. Locate the **Create Environment** section
3. **New Environment Name:** Enter a name for your environment in the input field
4. **Python Path:** Optionally select a Python installation from the dropdown (automatically detects all available Python installations on your system) or manually specify a Python path
5. **Upgrade pip during creation:** Check this option to automatically upgrade pip to the latest version when creating the environment
6. Click the **Create Environment** button to initialize the new environment

---

### Configuring and Activating an Environment

**Configuration and Activation**

1. **Open at:** Enter the directory path where you want to activate the environment, or click **Browse** to select a folder from the file manager
2. **Open with:** Select a tool to open alongside the activated environment (e.g., VSCode). You can add new tools to this list
3. Now you can Actovates the environment using  **Activate Environment** button or using described other options below.
4. **Shortcuts for Activating Environemnts using the Available Environments Table**
Double-click on any of these columns row to activate the environment:
**ENVIRONMENT | PYTHON VERSION | SIZE | LAST SCANNED**


---

### Searching for Environments

Use the **Search Environment** input field to filter and quickly locate specific environments from your list by typing the environment name or related keywords.

---

### Managing Environments - Available Environments Table

All created environments are displayed in an interactive table with the following columns and actions:

| Column | Description | Action |
|--------|-------------|--------|
| **ENVIRONMENT** | Environment name | Double-click to activate the environment |
| **PYTHON VERSION** | Python version used | Double-click to activate the environment |
| **RECENT LOCATION** | Last used directory path | Click to copy the path to clipboard |
| **SIZE** | Environment folder size | Double-click to activate the environment |
| **RENAME** | Rename option | Click to rename the environment |
| **DELETE** | Delete option | Click to delete the environment |
| **LAST SCANNED** | Last vulnerability scan date | Double-click to activate the environment |
| **MORE** | Additional actions | Click to access vulnerability report and scan now options |

---

## Package Tab

The Package Tab provides comprehensive package management capabilities for selected environments.

**📌 Important Note:**
><span style="color: red;">All package operations require selecting an environment from the environment table first.<span>

### Installing Packages

**Single Package Installation:**

1. Go to **Packages Tab → Install Package Section**
2. Enter the package name in the Package name field
3. Click **Install Package** to install the package

**Multiple Packages Installation (Requirements File):**

1. Go to **Packages Tab → Install Package Section**
2. Click **Install Requirements**
3. Browse and select a text file containing package names (e.g., `requirements.txt`)
4. The application reads the file and installs all listed packages automatically

---

### Exporting Packages

To export installed packages to a requirements file:

1. Go to **Packages Tab → Export Packages**
2. Provide a filename in text format (e.g., `requirements.txt`).
3. The application automatically exports all installed packages of selected environments.

---

### Managing Installed Packages

To view and manage packages in an environment:

1. Click the **Manage Packages** button
2. A table view displays all installed packages with options to:
   - **Delete** individual packages
   - **Update** packages to their latest version

---

## Menu Options

**📌 Important Note:**
><span style="color: red;">All menu operations require selecting an environment from the environment table first.<span>

### File Menu

The File menu provides package installation and export operations:

- **Install Packages** - Install a single package by name
- **Install Requirements** - Install multiple packages from a requirements file
- **Export Packages** - Export installed packages to a requirements file


---

### View Menu

**Refresh Environments:**
1. Go to **Menu → View → Refresh Environments**
2. This refreshes the environment list and updates status if any changes were made outside the PES tool

---

### Tools Menu

The Tools menu provides advanced features for environment analysis and maintenance. 

#### Scan Now

Generates a comprehensive dependency and vulnerability report for the selected environment's packages.

1. Go to **Menu → Tools → Scan Now**
2. The tool analyzes dependencies and security vulnerabilities

---

#### Vulnerability Report

Displays detailed vulnerability and dependency information for packages:

1. Go to **Menu → Tools → Vulnerability Report**
2. Select a package from the list
3. View information across three tabs:
   - **Dependencies** - Shows the dependency tree and relationships
   - **Basic Details** - Displays package metadata and basic information
   - **Scan Details** - *(enterprise level external tool integration option [Compliance/ Training/ Incident Response]Currently not implemented)*
4. The dashboard also renders a severity breakdown and a package trend chart
   natively (no external plotting dependency); the charts follow the active
   appearance mode and show a placeholder when a package has no scan history.

#### Remediate Vulnerabilities

The Vulnerability Report can apply available fixes without leaving the dashboard.

1. Run **Tools -> Scan Now**, then open **Tools -> Vulnerability Report** for the environment.
2. Select a package and the vulnerability you want to address.
3. In the vulnerability details, select **Update Now** beside the remediation recommendation.
4. Confirm the versioned package upgrade. Py Env Studio installs the recommended fixed version in the selected environment, marks the vulnerability as fixed, and refreshes the report.

To remediate every package with an available recommended fix, select **Upgrade all Packages**. The confirmation dialog lists the planned upgrades. The dashboard reports successful and failed upgrades separately, then refreshes resolved statuses.

The actions are unavailable when the report has no recommended fixed version, or when the installed version already meets or exceeds the recommended fix.

---

#### Check for Package Updates

Identifies outdated packages and enables batch updating:

1. Go to **Menu → Tools → Check for Package Updates**
2. A popup table displays:
   - Package name
   - Current version
   - New version available
3. Select packages to update:
   - **Ctrl + Click** to select multiple specific packages
   - **Ctrl + A** to select all packages
4. Click **Update Selected** to upgrade the chosen packages to their latest versions.

---

#### Configuration (Tools → Configuration)

The Configuration dialog is the single place to set persistent preferences.

1. Go to **Menu → Tools → Configuration**.
2. Set the values you need:
   - **Default virtual environment path** - shown **read-only**: it displays
     where new environments are created (`venv_dir` in the PES `config.ini`
     in the platform user-data directory). To relocate environments, edit
     `venv_dir` in that file directly; the dialog keeps the field read-only so
     existing environments are never orphaned by a GUI edit.
   - **Default Python / runtime** - preferred interpreter and runtime provider
     (Python Install Manager, System, or Custom)
   - **Default package manager** - `pip` or `uv` (unavailable managers are
     rejected with a message)
   - **Default project tool** and the **Open with** tool list
   - **Template defaults** - create a virtual environment and/or initialize Git
   - **Appearance mode** - Light, Dark, or System
   - **UI scaling** - 80 % to 120 %
3. Use **Apply** to preview the change, **Save** to persist it, **Cancel** to
   discard, or **Reset** to restore defaults. Environment and runtime views
   refresh after saving.

Preferences are validated before they are written, and saved atomically to the
PES `config.ini` in the platform user-data directory.

---

#### Plugins (Tools → Plugins)

1. Go to **Menu → Tools → Plugins** to open the plugin manager.
2. Place a plugin folder containing `plugin.json` in the PES plugins directory
   (`~/.py_env_studio/plugins/<plugin_name>/`).
3. Enable the plugin in the dialog; enablement is persisted across restarts.
4. Startup and shutdown hooks run automatically, and plugin messages appear in
   the console and the log file.

Plugin code runs inside the PES process, so review a plugin's source before
enabling it. See the [plugin overview](../plugins/index.md) and
[plugin development guide](../plugins/development.md).

---

### Templates Menu

The **Templates** menu creates new projects from reusable template definitions.

#### Create a project from a template

1. Go to **Menu → Templates** and pick **Python Script**, **Python CLI**, or
   **Python Package**.
2. In the wizard, fill in the fields:
   - **Project Name** and **Project Location** (use **Browse** to pick a
     directory)
   - **Python Version**
   - **Package Name** (optional, defaults to a sanitized project name),
     **CLI Command Name** (optional), **Author** (optional), and **License**
3. Review the **Template Preview** pane, which lists the files that will be
   generated.
4. Choose the optional steps: **Create Virtual Environment** and/or
   **Initialize Git**.
5. Select **Create Project**. Creation runs in the background (the window
   minimizes while it works, and the status bar tracks progress); when it
   finishes, PES reports success or failure and offers to open the project in
   your preferred editor.

#### Manage Templates

1. Go to **Menu → Templates → Manage Templates**.
2. Use **+ Add Template** to save a template from:
   - **Local Project** - pick an existing project directory.
   - **GitHub Repository** - paste a public repository URL; PES validates the
     URL, clones it into a temporary directory, inspects it, and shows a
     preview before saving.
3. Review the detected metadata, adjust the template name/ID, and save.
4. Imported templates appear under **My Templates** and can be used or deleted
   like built-in templates.

#### Community Templates

1. Go to **Menu → Templates → Community Templates**.
2. Search GitHub (`FastAPI`, `Django`, `CLI`, …), pick a category and sort
   order, then choose **Search**.
3. Use **Preview** to inspect a candidate (README excerpt, project structure,
   dependency files, sensitive files that will be excluded) - nothing is
   executed.
4. Select **Import as Template**, name the template, and then use it through
   the normal project creation wizard.

See [Community Templates](../project-templates/community-templates.md) for the
full safety model.

---

## Runtime-Managed Projects

PES can own the Python environment of an existing project directory and run
scripts inside it:

1. Open a terminal in the project directory.
2. Run `pes init` to create `pes.config` and the managed environment.
3. Run `pes on` to enable runtime interception, or `pes off` to disable it.
4. Run `pes status` to inspect the project and `pes list-projects` to list every
   registered project.
5. Run scripts with `pes run app.py --debug` (or simply `pes app.py --debug`).

Dynamic data (installed packages, scan results, sizes, timestamps) is never
stored in `pes.config`; it stays in the runtime and the PES database.

---

## AI Coding Agents (MCP, Beta)

🧪 **Beta.** PES can expose a local, read-only MCP server so an AI coding agent
such as VS Code Copilot can read authoritative environment and project state
instead of guessing it.

1. Confirm the CLI works: `py-env-studio --list` (the aliases `pes --list` and
   `pyenvstudio --list` are equivalent).
2. Run `py-env-studio mcp` (or `pes mcp`) once from a terminal to verify
   startup, then stop it with `Ctrl+C`.
3. Register the server in your MCP client - for VS Code, either run
   **MCP: Add Server** (stdio → `py-env-studio` → `mcp`) or create
   `.vscode/mcp.json` with a `servers` entry.
4. Start the server from **MCP: List Servers**, trust it, then enable the
   `pyenv_*` tools in chat.

MCP is read-only, stdio-only, and never triggers a network scan. Full steps,
client snippets, tunable settings, and troubleshooting are in the
[MCP reference](../reference/mcp.md).

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl + Click** | Select multiple packages in the update table |
| **Ctrl + A** | Select all packages in the update table |
| **Double-click** (table columns) | Activate environment or copy path (context-dependent) |

---

## Quick Reference Workflow Guide

### Common Workflows

**Setting Up a New Project Environment:**
1. Create Environment (Environment Tab)
2. Install Requirements (File → Install Requirements)
3. Scan Now (Tools → Scan Now)

**Daily Development Work:**
1. Search Environment (locate your project)
2. Activate Environment (double-click or use Activate section)
3. Manage Packages as needed

**Maintenance and Updates:**
1. Refresh Environments (View → Refresh Environments)
2. Check for Package Updates (Tools → Check for Package Updates)
3. Review Vulnerability Report (Tools → Vulnerability Report)

**Sharing Environment Configuration:**
1. Select environment
2. Export Packages (File → Export Packages)
3. Share the generated requirements.txt file

**Bootstrapping a New Project from a Template:**
1. Templates → Python Script / CLI / Package (or Community Templates)
2. Fill in the wizard, preview the files, and choose the optional venv/Git steps
3. Open the generated project in your preferred editor

**Connecting an AI Coding Agent (Beta):**
1. Check `py-env-studio --list` works (aliases: `pes`, `pyenvstudio`)
2. Register `py-env-studio mcp` (or `pes mcp`) as a stdio MCP server in your client
3. Start and trust the server, then enable the `pyenv_*` tools in chat

**Keeping PES Current:**
1. `pip install --upgrade py-env-studio`
2. Tools → Configuration to review defaults after an upgrade

---

## Summary

Py Env Studio streamlines Python environment management by consolidating creation, activation, package management, and security scanning into a unified interface. The combination of table-based environment selection, menu-driven operations, and interactive reporting makes it efficient for both beginners and advanced Python developers to maintain clean, secure, and well-documented development environments.
