<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/py_env_studio/ui/static/icons/pes-icon-default.png?raw=true" alt="Py Env Studio Logo" width="150">
</p>

# 🐍🏠 Py Env Studio

[![PyPI Version](https://img.shields.io/pypi/v/py-env-studio.svg?logo=pypi&logoColor=white)](https://pypi.org/project/py-env-studio/)
[![Python Versions](https://img.shields.io/pypi/pyversions/py-env-studio.svg?logo=python&logoColor=yellow)](https://pypi.org/project/py-env-studio/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/pyenvstudio/py-env-studio/blob/main/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/py-env-studio/badge/?version=latest)](https://py-env-studio.readthedocs.io/en/latest/?badge=latest)
[![GitHub Stars](https://img.shields.io/github/stars/pyenvstudio/py-env-studio?style=flat&logo=github)](https://github.com/pyenvstudio/py-env-studio/stargazers)
[![Open Issues](https://img.shields.io/github/issues/pyenvstudio/py-env-studio?logo=github)](https://github.com/pyenvstudio/py-env-studio/issues)

**Py Env Studio (PES)** is a cross-platform **Graphical Environment & Package
Manager for Python**: create and manage virtual environments, install and audit
packages, scan for vulnerabilities, scaffold projects from templates, and expose
a local, read-only **MCP control plane (beta)** for AI coding agents — from one
desktop app and a matching CLI.

Perfect for:

- ✅ Python beginners who want simplicity
- ✅ Data scientists setting up ML/DL stacks
- ✅ Developers managing Django, Flask, FastAPI projects
- ✅ Teams who need **secure, isolated environments**
- ✅ Power users wanting **plugin extensibility**

## ✨ Highlights

- ➕ One-click virtual environment create, delete, activate, rename, and search
- 📦 Package management with selectable **pip** or **uv** backends
  (automatic pip fallback), install/uninstall/update, import/export of
  `requirements.txt`
- 🛡️ Environment vulnerability scanner with insights dashboard, plus
  remediation actions (`Update Now`, `Upgrade all Packages`)
- 🧩 Project templates: built-in Python Script / CLI / Package templates, your
  own local or GitHub templates, and GitHub **Community Templates** discovery
- ⚙️ Configuration center for default venv path, interpreter/runtime, package
  manager, project tool, template defaults, appearance, and UI scaling
  (the default venv path is read-only in the dialog; set `venv_dir` in
  `config.ini` to relocate it)
- 🐍 Official **Python Install Manager** integration to detect, list, install,
  and select official runtimes
- 🔌 Extensible **plugin system** with 18 lifecycle hooks
- 📟 Full CLI with progress gauge and `-v` / `-q` / `--no-progress` controls
- 🧪 **Beta:** local, read-only **MCP control plane** for AI coding agents
  (stdio transport, 8 `pyenv_*` tools, opt-out via `enabled = false`)

## 📥 Installation

```bash
pip install py-env-studio
```

Requires **Python 3.12+**. See the
[installation guide](https://py-env-studio.readthedocs.io/en/latest/getting-started/install.html)
for upgrade, extras, and uninstall steps.

## 🚀 Quick start

Launch the GUI (no arguments opens the desktop application):

```bash
py-env-studio
```

The package installs three equivalent entry points — **`py-env-studio`**,
**`pes`**, and **`pyenvstudio`** — for both the GUI and every CLI command:

```bash
py-env-studio --list        # or: pes --list
py-env-studio --create myenv
py-env-studio --install myenv,numpy
pes run app.py              # run a script inside a managed project
pes mcp                     # start the MCP control plane (beta, stdio)
```

Full CLI reference:
[https://py-env-studio.readthedocs.io/en/latest/getting-started/cli.html](https://py-env-studio.readthedocs.io/en/latest/getting-started/cli.html)

## 🧪 MCP control plane (beta)

Py Env Studio can expose a **local, read-only MCP server** so AI coding agents
(Copilot or any MCP client) consume authoritative Python environment state
instead of guessing it.

- **Read-only beta** — 8 tools covering environments, packages, dependencies,
  cached vulnerabilities, project context, and an aggregate project report
- **Local-first** — stdio only, no ports, no network calls from MCP
- **Opt-out** — set `enabled = false` in the `[mcp]` section of `config.ini`

Setup steps for VS Code and other clients:
[https://py-env-studio.readthedocs.io/en/latest/reference/mcp.html](https://py-env-studio.readthedocs.io/en/latest/reference/mcp.html)

## 📚 Documentation

- Documentation home: [https://py-env-studio.readthedocs.io/](https://py-env-studio.readthedocs.io/)
- Usage manual: [https://py-env-studio.readthedocs.io/en/latest/getting-started/usage.html](https://py-env-studio.readthedocs.io/en/latest/getting-started/usage.html)
- Release notes: [https://py-env-studio.readthedocs.io/en/latest/releases/v2.1.0.html](https://py-env-studio.readthedocs.io/en/latest/releases/v2.1.0.html)
- Source code: [https://github.com/pyenvstudio/py-env-studio](https://github.com/pyenvstudio/py-env-studio)
- Issue tracker: [https://github.com/pyenvstudio/py-env-studio/issues](https://github.com/pyenvstudio/py-env-studio/issues)

## 🌐 Network access

PES uses public, read-only APIs (no authentication required). Ensure HTTPS
access to:

| Service | Purpose | URL |
|----------|----------|-----|
| PyPI | Package metadata | [pypi.org](https://pypi.org) |
| deps.dev | Dependency data | [deps.dev](https://deps.dev) |
| OSV.dev | Vulnerability info | [osv.dev](https://osv.dev) |
| Github | Community templates | [github.com](https://github.com) |

## 🤝 Contributing

Contributions are welcome — fork the repository, raise issues, or submit pull
requests at [https://github.com/pyenvstudio/py-env-studio](https://github.com/pyenvstudio/py-env-studio).

## ⚖️ License

This project is licensed under the MIT License — see
[https://github.com/pyenvstudio/py-env-studio/blob/main/LICENSE](https://github.com/pyenvstudio/py-env-studio/blob/main/LICENSE).

Py Env Studio — Simplifying Python environment management for everyone with a
built-in security scanner.
