<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/py-env-studio/static/icons/logo.png?raw=true" alt="Py Env Studio Logo" width="150">
</p>
# 🐍🏠 Py Env Studio

**Py Env Studio** is a cross-platform **Graphical Environment & Package Manager for Python** that makes managing virtual environments and packages effortless—without using the command line.

---

## 🌟 Key Features

- ✅ Create and delete virtual environments  
- ✅ Activate environments easily  
- ✅ Install, update, and uninstall packages  
- ✅ Import and export `requirements.txt`  
- ✅ Clean and user-friendly **Graphical User Interface (GUI)**  
- ✅ Optional **Command-Line Interface (CLI)** for advanced users  

---

## 🖥️ Launch the GUI (Recommended)

    py main.py

<p align="center">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/1.environment-screen.PNG?raw=true" alt="Environment Screen" width="400">
  <img src="https://github.com/pyenvstudio/py-env-studio/blob/main/screenshots/2.0.package-screen.PNG?raw=true" alt="Package Screen" width="400">
</p>

The GUI lets you:


➕ Create or delete environments

📦 Install or uninstall packages

📄 Export or import requirements

⚡ View and manage all environments visually

⚙️ Command-Line Interface (Optional)
For scripting or quick tasks, the CLI supports:
# Create environment

    py-env-studio --create myenv

# Create environment and upgrade pip

    py-env-studio --create myenv --upgrade-pip

# Delete environment

    py-env-studio --delete myenv

# List all environments

    py-env-studio --list

# Activate environment (prints activation command)

    py-env-studio --activate myenv

# Install package

    py-env-studio --install myenv,numpy

# Uninstall package

    py-env-studio --uninstall myenv,numpy

# Export requirements to file

    py-env-studio --export myenv,requirements.txt

# Import requirements from file
py-env-studio --import-reqs myenv,requirements.txt
📝 Installation
Install via PyPI:

    pip install py-env-studio

Or clone and run locally:

    git clone https://github.com/pyenvstudio/py-env-studio.git

    cd py-env-studio

    python -m venv venv

    venv\Scripts\activate   # On Windows

    source venv/bin/activate  # On Linux/macOS

    pip install -r requirements.txt

🔑 Activating Environments
Manually activate your environment after creation:

Windows:

    .\envs\myenv\Scripts\activate

Linux/macOS:

    source envs/myenv/bin/activate

The GUI and CLI will print the correct activation command for you.

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
🔄 Environment renaming support

🔍 Global package search

⬆️ One-click upgrade of all packages

📝 Package version locking

🐳 Dockerized version

**🤝 Contributing**
We welcome contributions!
Feel free to fork the repository, raise issues, or submit pull requests.

**📜 License**
This project is licensed under the MIT License.

Py Env Studio — Simplifying Python environment management for everyone.
---
