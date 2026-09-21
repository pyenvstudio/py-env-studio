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

- **17 Available Hooks** - Respond to environment and package operations
- **State Management** - Plugins persist across application restarts
- **Easy Development** - Simple plugin API with lifecycle management
- **Examples Included** - Full working sample plugin with documentation

See the [v2.0.8 release notes](docs/releases/v2.0.8.md) and the [plugin development guide](docs/plugins/development.md).

### Additional implemented capabilities

- Selectable `pip` or `uv` package backends, with automatic `pip` fallback
- Dependency-impact preview and AutoResolver install recovery
- Project templates, reusable local/GitHub templates, and guided project creation
- Runtime-managed projects through `pes init`, `pes on`, `pes off`, and `pes run`
- Persisted configuration for default paths, interpreters, tools, themes, scaling, and template defaults
- Py-Tonic learning challenges and profile-based notifications

See [the complete feature reference](docs/reference/current-implementation.md) and [the architecture overview](docs/reference/architecture.md).

### 🛠️ Self-Healing Install System (AutoResolver)

PES now includes **AutoResolver**, a self-healing install system for pip/uv workflows. On dependency resolution failure, it automatically:

- Detects common resolution errors (`ResolutionImpossible`, etc.)
- Strips version constraints (e.g. `click==8.3.1` → `click`)
- Retries installs up to 3 times without modifying your requirement files
- No other major Python tool (pip, uv, poetry, hatch, pixi) does this natively

Because when installs stop breaking, **PES finally means peace.🤗**

## ☕ Support  

If you find **Py Env Studio** helpful, consider supporting me:  

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-24292e?logo=github&style=for-the-badge)](https://github.com/sponsors/contactshaikhwasim)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-yellow?logo=buymeacoffee&style=for-the-badge)](https://buymeacoffee.com/contactshaikhwasim)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20me-ff5e5b?logo=ko-fi&logoColor=white&style=for-the-badge)](https://ko-fi.com/contactshaikhwasim)
[![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal&style=for-the-badge)](https://www.paypal.me/paypalwasimshaikh)


---

📥 Install via PyPI:

    pip install py-env-studio


## 🖥️ Launch the GUI (Recommended)

    py-env-studio

You can also launch the same utility with these aliases:

    pyenvstudio
    pes

Refer usage documentation here: https://py-env-studio.readthedocs.io/en/latest/

<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.environment-screen.PNG?raw=true" alt="Environment Screen" width="400">

  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/plugin-screen.PNG?raw=true" alt="Plugin Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/2.0.package-screen.PNG?raw=true" alt="Package Screen" width="400"><br>
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.2.1_vulneribility_scan_report.PNG?raw=true" alt="Package Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.2.2_vulneribility_scan_report.PNG?raw=true" alt="Package Screen" width="400">
</p>

**📁 Project Structure**

    py-env-studio/
    ├── __init__.py
    ├──resources
    ├── core/
    │   ├── __init__.py
    │   ├── env_manager.py
    │   └── pip_tools.py
    ├── utils/
    │   ├── __init__.py
    │   ├── handlers.py
    │   └── vulneribility_scanner.py
    │   └── vulneribility_insights.py  
    ├── ui/
    │   ├── __init__.py
    │   └── main_window.py
    └── static/
        └── icons/
    ├── main.py
    ├── config.ini
    ├── requirements.txt
    ├── README.md
    └── pyproject.toml

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

Ensure HTTPS access to these domains.  
APIs are public, read-only, no auth required.  

**Terms:** [PSF](https://policies.python.org/pypi.org/Terms-of-Service/) · [Google](https://developers.google.com/terms) · [OSV](https://google.github.io/osv.dev/api/)


**🤝 Contributing**
We welcome contributions!
Feel free to fork the repository, raise issues, or submit pull requests.

**⚖️ License**
This project is licensed under the MIT License.

Py Env Studio — Simplifying Python environment management for everyone with built-in security scanner.

> ⭐ Star this repo if you find it useful! | 💬 Join us on Telegram

---
