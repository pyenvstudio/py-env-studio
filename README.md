<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/py_env_studio/ui/static/icons/pes-icon-default.png?raw=true" alt="Py Env Studio Logo" width="150">
</p>

# 🐍🏠 Py Env Studio  

[![PyPI Version](https://img.shields.io/pypi/v/py-env-studio.svg?logo=pypi&logoColor=white)](https://pypi.org/project/py-env-studio/)
[![Python Versions](https://img.shields.io/pypi/pyversions/py-env-studio.svg?logo=python&logoColor=yellow)](https://pypi.org/project/py-env-studio/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/pyenvstudio/py-env-studio/blob/main/LICENSE)
![Total Downloads](https://static.pepy.tech/badge/py-env-studio)
![Monthly Downloads](https://static.pepy.tech/badge/py-env-studio/month)
![Weekly Downloads](https://static.pepy.tech/badge/py-env-studio/week)
[![Documentation Status](https://readthedocs.org/projects/py-env-studio/badge/?version=latest)](https://py-env-studio.readthedocs.io/en/latest/?badge=latest)
[![GitHub Stars](https://img.shields.io/github/stars/pyenvstudio/py-env-studio?style=flat&logo=github)](https://github.com/pyenvstudio/py-env-studio/stargazers)
[![Open Issues](https://img.shields.io/github/issues/pyenvstudio/py-env-studio?logo=github)](https://github.com/pyenvstudio/py-env-studio/issues)
[![Last Commit](https://img.shields.io/github/last-commit/pyenvstudio/py-env-studio?logo=git)](https://github.com/pyenvstudio/py-env-studio/commits/main)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-blue?logo=python)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/pyenvstudio/py-env-studio/pulls)
[![Telegram](https://img.shields.io/badge/Join%20Community-Telegram-2CA5E0?logo=telegram&logoColor=white)](https://t.me/pyenvstudio)

**Py Env Studio** is a comprehensive cross-platform **Graphical Environment & Package Manager for Python** with advanced features including vulnerability scanning, interactive learning, and an extensible plugin system for custom functionality.

Perfect for:  
- ✅ Python beginners who want simplicity  
- ✅ Data scientists setting up ML/DL stacks  
- ✅ Developers managing Django, Flask, FastAPI projects  
- ✅ Teams who need **secure, isolated environments**
- ✅ Power users wanting **plugin extensibility**

---

## 🆕 What's new in v2.1.0

- 🧪 **MCP control plane (beta)** — a local, read-only MCP server lets AI coding
  agents (VS Code Copilot and other MCP clients) read authoritative
  environment, package, dependency, security, and project state.
  → [Setup steps](docs/reference/mcp.md)
- 🧩 **Project templates** — built-in Python Script / CLI / Package templates,
  your own templates from a local folder or GitHub, and GitHub
  **Community Templates** discovery.
- ⚙️ **Configuration center** (Tools → Configuration) — default venv path,
  interpreter/runtime, package manager, project tool, template defaults,
  appearance, and UI scaling in one validated dialog.
- 🐍 **Official Python Install Manager integration** — detect, list, install,
  and select official runtimes, with System/Custom providers alongside.
- 🛡️ **Remediate from the dashboard** — `Update Now` per vulnerability and
  `Upgrade all Packages` per environment, with partial-failure reporting.
- 📊 **Native dashboard charts** (`tkinter-dash`, no matplotlib), 📶 a CLI
  progress gauge and GUI status gauge, and consistent application icons.

→ [Full v2.1.0 release notes](docs/releases/v2.1.0.md)

---

## 🌟 GUI Key Features

- ➕ Create and delete virtual environments
>Easily set up new virtual environments or remove unused ones with a single click, without touching the command line.

- ⚡ One click environment activation
> Instantly activate environments directly from the GUI, eliminating the need to type activation commands manually.

- 📁 Open environment at a specific location (choose working directory)
> Launch the environment’s working directory in your file explorer to quickly access project files and scripts.

- 🔷 Integrated launch: CMD, VSCode, PyCharm
> Open your environment directly in your preferred editor or terminal, streamlining your workflow.

- 🛡️ Environment Vulnerability Scanner with Insights Dashboard
> Scan environments for known security vulnerabilities in installed packages.  
  Generate insightful reports with risk levels, recommended updates, and a dashboard overview to keep your projects secure.


- 🔍 Search environments instantly
> Use the built-in search bar to quickly locate any environment, even in large collections.

- ✏️ Rename environments
> Quickly rename environments to maintain clarity and organization in your workspace.

- 🕑 View recent used location for each environment
> Track where each environment was last accessed, making it easy to jump back into active projects.

- 📏 See environment size details
> View the size of each environment to identify heavy setups and manage disk space effectively.

- 💫 Visual management of all environments
> Manage all your environments through a clean, organized, and user-friendly interface with minimal clutter.

- 📦 Package Management
> Install, update, and uninstall packages visually without typing a single command.

- 🚚📄 Export or import requirements
> Import dependencies from a requirements file or export your current setup with just a click.

- 🔌 **Extensible Plugin System**
> Create custom plugins to extend PyEnvStudio functionality without modifying core code. Hook into environment operations, package management, app lifecycle, and vulnerability scanning.


## 🔌 Plugin System

PyEnvStudio now features a powerful plugin system that allows developers to extend functionality:

- **18 Available Hooks** - Respond to environment, package, application, and template operations
- **State Management** - Plugins persist across application restarts
- **Easy Development** - Simple plugin API with lifecycle management
- **Examples Included** - Full working sample plugin with documentation

See the [v2.1.0 release notes](docs/releases/v2.1.0.md) and the [plugin development guide](docs/plugins/development.md).

### Additional implemented capabilities

- Selectable `pip` or `uv` package backends, with automatic `pip` fallback
- Dependency-impact preview and AutoResolver install recovery
- Project templates, reusable local/GitHub templates, and guided project creation
- Runtime-managed projects through `pes init`, `pes on`, `pes off`, and `pes run`
- Persisted configuration for default paths, interpreters, tools, package manager, themes, scaling, template defaults, and runtime provider
- Py-Tonic learning challenges and profile-based notifications
- GitHub Community Templates discovery with static preview before import
- Vulnerability remediation (`Update Now`, `Upgrade all Packages`) with native dashboard charts
- Informative CLI progress gauge plus `-v` / `-q` / `--no-progress` output controls
- 🧪 **Beta:** a local, read-only **MCP control plane** for AI coding agents

See [the complete feature reference](docs/reference/current-implementation.md), [the architecture overview](docs/reference/architecture.md), and the [MCP reference (beta)](docs/reference/mcp.md).

### 🛠️ Self-Healing Install System (AutoResolver)

PES now includes **AutoResolver**, a self-healing install system for pip/uv workflows. On dependency resolution failure, it automatically:

- Detects common resolution errors (`ResolutionImpossible`, etc.)
- Strips version constraints (e.g. `click==8.3.1` → `click`)
- Retries installs up to 3 times without modifying your requirement files
- No other major Python tool (pip, uv, poetry, hatch, pixi) does this natively

Because when installs stop breaking, **PES finally means peace.🤗**

## 🧪 MCP Control Plane (Beta)

Py Env Studio can expose a **local, read-only MCP server** so AI coding agents
(Copilot or any MCP client) consume authoritative Python environment state
instead of guessing it. PES is the infrastructure, not the model.

```bash
py-env-studio mcp        # stdio transport, no GUI, no network required
```

- **Read-only beta** — 8 tools covering environments, packages, dependencies,
  cached vulnerabilities, project context, and one aggregate project report.
- **Local-first** — stdio only, no ports, no network calls from MCP.
- **Opt-out** — set `enabled = false` in the `[mcp]` section of `config.ini`.

Setup steps for VS Code, portable client configs, the tool list, and
troubleshooting: [docs/reference/mcp.md](docs/reference/mcp.md).

## ☕ Support  

If you find **Py Env Studio** helpful, consider supporting me:  

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-24292e?logo=github&style=for-the-badge)](https://github.com/sponsors/contactshaikhwasim)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-yellow?logo=buymeacoffee&style=for-the-badge)](https://buymeacoffee.com/contactshaikhwasim)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20me-ff5e5b?logo=ko-fi&logoColor=white&style=for-the-badge)](https://ko-fi.com/contactshaikhwasim)
[![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal&style=for-the-badge)](https://www.paypal.me/paypalwasimshaikh)

<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/bmc-qr-code.png?raw=true" alt="Buy Me a Coffee QR Code" width="200">
</p>

---

📥 Install via PyPI:

    pip install py-env-studio


## 🖥️ Launch the GUI (Recommended)

    py-env-studio

You can also launch the same utility with these aliases:

    pyenvstudio
    pes

The same aliases apply to every CLI command shown in the documentation
(`pes --list`, `pes mcp`, `pyenvstudio init`, …).

Refer usage documentation here: https://py-env-studio.readthedocs.io/en/latest/

## 📸 Screenshots

<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.environment-screen.PNG?raw=true" alt="Environment Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.1.more_options.PNG?raw=true" alt="Environment More Options" width="400"><br>
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.2.1_vulneribility_scan_report.PNG?raw=true" alt="Vulnerability Scan Report" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.2.2_vulneribility_scan_report.PNG?raw=true" alt="Vulnerability Scan Report Details" width="400"><br>
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.2.3_vulneribility_scan_report.PNG?raw=true" alt="Vulnerability Scan Report Insights" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/2.0.package-screen.PNG?raw=true" alt="Package Screen" width="400"><br>
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/2.1.package-screen.PNG?raw=true" alt="Package Screen Details" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/plugin-screen.PNG?raw=true" alt="Plugin Screen" width="400"><br>
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/templates.PNG?raw=true" alt="Templates Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/python-manager.PNG?raw=true" alt="Python Manager Screen" width="400"><br>
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/configuration.PNG?raw=true" alt="Configuration Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/3.about-sceeen.PNG?raw=true" alt="About Screen" width="400">
</p>

**📁 Project Structure**

    py_env_studio/
    ├── __init__.py
    ├── commands.py                 # CLI flags, subcommands, output controls
    ├── config.ini                  # packaged defaults (version, settings, [mcp])
    ├── main.py                     # application entry helpers
    ├── core/
    │   ├── env_manager.py          # environment lifecycle and metadata
    │   ├── package_manager.py      # unified pip/uv routing
    │   ├── pip_tools.py / uv_tools.py
    │   ├── auto_resolve.py         # dependency-conflict recovery
    │   ├── dependency_preview.py   # pre-install impact analysis
    │   ├── configuration.py        # preferences service
    │   ├── runtime_toggle.py       # managed project runtime (pes.config)
    │   ├── runtime_providers.py    # Python Install Manager / System / Custom
    │   ├── project_intelligence.py # aggregate project report
    │   ├── project_contract.py     # pes.config contract service
    │   ├── database.py + schema/   # SQLite manager and SQL templates
    │   ├── mcp/                    # beta read-only MCP server (stdio)
    │   ├── plugins/                # plugin framework and hooks
    │   └── templates/              # template engine, registry, user store
    ├── utils/
    │   ├── handlers.py
    │   ├── vulneribility_scanner.py
    │   ├── vulneribility_insights.py
    │   ├── app_logging.py / progress.py
    │   └── version_utils.py
    ├── ui/
    │   ├── main_window.py          # CustomTkinter application
    │   ├── status_bar.py           # activity text + progress gauge
    │   ├── ui_tasks.py             # background task helpers
    │   └── static/icons/
    └── main.py

    docs/ · examples/ · tests/ · pyproject.toml · README.md

**🚀 Roadmap**

<del>🏙️ Multiple Python based Environements 

🔍 Global package search

<del>⬆️ One-click upgrade of all packages

📝 Package version locking

🐳 Dockerized version

## 🌐 References & Network Access

This project uses public APIs for core features:

| Service | Purpose | URL |
|----------|----------|-----|
| PyPI | Package metadata | [pypi.org](https://pypi.org) |
| deps.dev | Dependency data | [deps.dev](https://deps.dev) |
| OSV.dev | Vulnerability info | [osv.dev](https://osv.dev) |
| Github | Community templates | [github.com](https://github.com) |

Ensure HTTPS access to these domains.  
APIs are public, read-only, no auth required.  

**Terms:** [PSF](https://policies.python.org/pypi.org/Terms-of-Service/) · [Google](https://developers.google.com/terms) · [OSV](https://google.github.io/osv.dev/api/)


**🤝 Contributing**
We welcome contributions!
Feel free to fork the repository, raise issues, or submit pull requests.

## Acknowledgements

Py Env Studio is built on the work of the Python community and the broader open-source ecosystem.

**Built with:** [Python](https://www.python.org/), [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), which provides the desktop UI foundation, and [Pillow](https://python-pillow.org/) for image and icon handling.

**Integrates with:** the [Python Install Manager](https://docs.python.org/3/using/windows.html#python-install-manager) for Python runtime management; [PyPI](https://pypi.org/) and the [Python Packaging community](https://packaging.python.org/) for package distribution and metadata; and [pip](https://pip.pypa.io/) and [uv](https://docs.astral.sh/uv/) for package management.

Thanks to the maintainers and contributors behind these projects and to everyone building Python and open-source software. These acknowledgements do not imply endorsement, affiliation, or official partnership.

*Built with Python. Powered by open source.*

**⚖️ License**
This project is licensed under the MIT License.

Py Env Studio — Simplifying Python environment management for everyone with built-in security scanner.

> ⭐ Star this repo if you find it useful! | 💬 Join us on Telegram

---
