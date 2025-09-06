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

**Py Env Studio** is a cross-platform **Graphical Environment & Package Manager for Python** that makes managing virtual environments and packages effortless without using the command line.

Perfect for:  
- ✅ Python beginners who want simplicity  
- ✅ Data scientists setting up ML/DL stacks  
- ✅ Developers managing Django, Flask, FastAPI projects  
- ✅ Teams who need **secure, isolated environments**  

---

## 🌟 GUI Key Features

- ➕ Create and delete virtual environments
>Easily set up new virtual environments or remove unused ones with a single click, without touching the command line.

- ⚡ One click environment activation
> Instantly activate environments directly from the GUI, eliminating the need to type activation commands manually.

- 📁 Open environment at a specific location (choose working directory)
> Launch the environment’s working directory in your file explorer to quickly access project files and scripts.

- 🔷 Integrated launch: CMD, VSCode, PyCharm (Beta)
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

## ☕ Support  

If you find **Py Env Studio** helpful, consider supporting me:  

<a href="https://www.buymeacoffee.com/wasimshaikh" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="45" width="170">
</a>

---

📥 Install via PyPI:

    pip install py-env-studio


## 🖥️ Launch the GUI (Recommended)

    py-env-studio

<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.environment-screen.PNG?raw=true" alt="Environment Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/2.0.package-screen.PNG?raw=true" alt="Package Screen" width="400"><br>
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.2.1_vulneribility_scan_report.PNG?raw=true" alt="Package Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.2.2_vulneribility_scan_report.PNG?raw=true" alt="Package Screen" width="400">
</p>

### Command-Line Options (For Advanced Users)
###### Create environment
    py-env-studio --create <environment name>

###### Create environment and upgrade pip
    py-env-studio --create <environment name> --upgrade-pip

###### Delete environment
    py-env-studio --delete <environment name>

###### List all environments
    py-env-studio --list

###### Activate environment (prints activation command)
    py-env-studio --activate <environment name>

###### Install package
    py-env-studio --install <environment name>,numpy

###### Uninstall package
    py-env-studio --uninstall <environment name>,numpy

###### Export requirements to file
    py-env-studio --export <environment name>,requirements.txt

###### Import requirements from file
py-env-studio --import-reqs <environment name>,requirements.txt


🔑 Activating Environments
Manually activate your environment after creation:

Windows:

    .\envs\<environment name>\Scripts\activate

Linux/macOS:

    source envs/<environment name>/bin/activate


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

🏙️ Multiple Python based Environements 

🔍 Global package search

⬆️ One-click upgrade of all packages

📝 Package version locking

🐳 Dockerized version


**🤝 Contributing**
We welcome contributions!
Feel free to fork the repository, raise issues, or submit pull requests.

**⚖️ License**
This project is licensed under the MIT License.

Py Env Studio — Simplifying Python environment management for everyone with built-in security scanner.

> ⭐ Star this repo if you find it useful! | 💬 Join us on Telegram

---
