# 🐍 Py Env Studio

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

```bash
py-env-studio --gui
The GUI lets you:

➕ Create or delete environments

📦 Install/uninstall packages

📄 Export or import requirements

⚡ View and manage all environments visually

⚙️ Command-Line Interface (Optional)
For scripting or quick tasks, the CLI supports:

bash
# Create environment
py-env-studio --create myenv

# Create and upgrade pip
py-env-studio --create myenv --upgrade-pip

# Delete environment
py-env-studio --delete myenv

# List environments
py-env-studio --list

# Activate (prints activation command)
py-env-studio --activate myenv

# Install package
py-env-studio --install myenv,numpy

# Uninstall package
py-env-studio --uninstall myenv,numpy

# Export requirements
py-env-studio --export myenv,requirements.txt

# Import requirements
py-env-studio --import-reqs myenv,requirements.txt
📝 Installation
bash
pip install py-env-studio
Or clone the repository:

bash
git clone https://github.com/pyenvstudio/py-env-studio.git
cd py-env-studio
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
🔑 Activating Environments
Manually activate your environment as follows:

Windows:

bash
.\envs\myenv\Scripts\activate
Linux/macOS:

bash
source envs/myenv/bin/activate


📁 Project Structure
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
│       └── icons
│
├── main.py
├── config.ini
├── requirements.txt
├── README.md
└── pyproject.toml
