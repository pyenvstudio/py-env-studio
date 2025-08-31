<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/py_env_studio/ui/static/icons/pes-icon-default.png?raw=true" alt="Py Env Studio Logo" width="150">
</p>
# 🐍🏠 Py Env Studio

**Py Env Studio** is a cross-platform **Graphical Environment & Package Manager for Python** that makes managing virtual environments and packages effortless without using the command line.

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

- 🛡️ Environment Vulnerability Scanner with Insights Dashboard
> Scan environments for known security vulnerabilities in installed packages.  
  Generate insightful reports with risk levels, recommended updates, and a dashboard overview to keep your projects secure.
---

📝 Installation
Install via PyPI:

    pip install py-env-studio


## 🖥️ Launch the GUI (Recommended)

    py-env-studio

<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.environment-screen.PNG?raw=true" alt="Environment Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/2.0.package-screen.PNG?raw=true" alt="Package Screen" width="400">
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
    ├── core/
    │   ├── __init__.py
    │   ├── env_manager.py
    │   └── pip_tools.py
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

🔄 Environment renaming support

🔍 Global environment search ✅

🔍 Global package search

⬆️ One-click upgrade of all packages

📝 Package version locking

🐳 Dockerized version


**🤝 Contributing**
We welcome contributions!
Feel free to fork the repository, raise issues, or submit pull requests.

**📜 License**
This project is licensed under the MIT License.

Py Env Studio — Simplifying Python environment management for everyone with security scanning.
---
