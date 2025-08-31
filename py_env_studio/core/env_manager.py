#env_manager.py

def search_envs(query):
    """
    Return a list of environment names matching the query (case-insensitive substring match).
    """
    all_envs = list_envs()
    if not query:
        return all_envs
    query_lower = query.lower()
    return [env for env in all_envs if query_lower in env.lower()]


# =============================
# Imports and Configuration
# =============================
import os
import sys
import subprocess
import shutil
import logging
import json
import re
from configparser import ConfigParser

# Load configuration once
config = ConfigParser()
config.read('config.ini')
# base dir is one step down from the current file
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.expanduser(config.get('settings', 'venv_dir', fallback='~/.venvs'))
PYTHON_PATH = config.get('settings', 'python_path', fallback=None)
LOG_FILE = os.path.join(base_dir, config.get('settings', 'log_file', fallback='venv_manager.log'))
DB_FILE = os.path.join(base_dir, config.get('settings', 'db_file', fallback='resources/py_env_studio.db'))
MATRIX_FILE = os.path.join(base_dir, config.get('settings', 'matrix_file', fallback='security_matrix_lts.json'))
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

# Path to environment data tracking file
ENV_DATA_FILE = os.path.join(VENV_DIR, "env_data.json")

# =============================
# Data Management
# =============================
def _load_env_data():
    """Load environment tracking data from JSON file."""
    if not os.path.exists(ENV_DATA_FILE):
        return {}
    try:
        with open(ENV_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_env_data(data):
    """Save environment tracking data to JSON file."""
    try:
        with open(ENV_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save env data: {e}")

def set_env_data(env_name, recent_location=None, size=None,last_scanned=None):
    """
    Update the tracking data for an environment. Only updates provided fields.
    Structure: { env_name: {"recent_location": str, "size": str} }
    """
    data = _load_env_data()
    entry = data.get(env_name, {})
    if recent_location is not None:
        entry['recent_location'] = recent_location
    if size is not None:
        entry['size'] = size

    if last_scanned is not None:
        entry['last_scanned'] = last_scanned
    data[env_name] = entry
    _save_env_data(data)

def get_env_data(env_name):
    """
    Get the tracking data for an environment.
    Returns a dict with keys: recent_location, size (may be missing if not set).
    """
    data = _load_env_data()
    return data.get(env_name, {})

def calculate_env_size_mb(env_path):
    """
    Calculate the size of the environment directory in whole megabytes.
    Returns a string like '142 MB'.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(env_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    size_mb = total_size // (1024 * 1024)
    return f"{size_mb} MB"

def is_valid_python(python_path):
    """
    Validate that the provided path points to a Python executable.
    Returns True if valid, False otherwise.
    """
    return shutil.which(python_path) is not None and 'python' in python_path.lower()

def _is_valid_env_name(name: str) -> bool:
    """
    Validate environment name.
    Allowed: letters, numbers, underscores, hyphens.
    """
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
    if not name or len(name) > 50 or any(c not in allowed_chars for c in name):
        return False
    return True

def create_env(name, python_path=None, upgrade_pip=False, log_callback=None):
    """
    Create a virtual environment using the specified Python interpreter.
    """
    env_path = os.path.join(VENV_DIR, name)
    python_path = 'python' if python_path is None else python_path
    try:
        if log_callback:
            log_callback(f"Creating virtual environment '{name}' at {env_path} with Python: {python_path}")

        if not os.path.exists(VENV_DIR):
            os.makedirs(VENV_DIR)

        if not _is_valid_env_name(name):
            valid_examples = ("myenv", "my-env", "my_env")
            raise ValueError(f"Invalid environment name: {name}. Valid examples are: {valid_examples}")

        if os.path.exists(env_path):
            raise FileExistsError(f"Target environment '{name}' already exists")
        
        process = subprocess.Popen([python_path, "-m", "venv", env_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if log_callback:
                log_callback(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
        
        venv_python = os.path.join(env_path, "Scripts" if os.name == "nt" else "bin", "python")
        if log_callback:
            log_callback("Ensuring pip is installed")
        process = subprocess.Popen([venv_python, "-m", "ensurepip", "--upgrade", "--default-pip"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if log_callback:
                log_callback(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
        
        if upgrade_pip:
            if log_callback:
                log_callback("Upgrading pip")
            process = subprocess.Popen([venv_python, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                if log_callback:
                    log_callback(line.strip())
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args)
        
        logging.info(f"Created environment at: {env_path} with Python: {python_path}")
        if log_callback:
            log_callback(f"Environment '{name}' created successfully")
    except subprocess.CalledProcessError as e:
        err_msg = f"Failed to create environment '{name}': {e}"
        logging.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise
    except Exception as e:
        err_msg = f"Unexpected error creating environment '{name}': {e}"
        logging.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise

def rename_env(old_name, new_name, log_callback=None):
    """
    Safely rename a virtual environment by recreating it with the new name and
    reinstalling dependencies.
    """
    try:
        if not _is_valid_env_name(new_name):
            raise ValueError(f"Invalid environment name: {new_name}")

        old_env_path = os.path.join(VENV_DIR, old_name)
        new_env_path = os.path.join(VENV_DIR, new_name)

        if not os.path.exists(old_env_path):
            raise FileNotFoundError(f"Environment '{old_name}' does not exist")

        if os.path.exists(new_env_path):
            raise FileExistsError(f"Target environment '{new_name}' already exists")

        if log_callback:
            log_callback(f"Copying dependencies from '{old_name}'")

        old_python = get_env_python(old_name)
        requirements_file = os.path.join(VENV_DIR, f"{old_name}_requirements.txt")

        # Freeze dependencies
        with open(requirements_file, "w", encoding="utf-8") as f:
            subprocess.check_call([old_python, "-m", "pip", "freeze"], stdout=f)

        # Create new environment
        if log_callback:
            log_callback(f"Preparing environment '{new_name}'")
        create_env(new_name, python_path=PYTHON_PATH, upgrade_pip=False, log_callback=log_callback)

        # Install dependencies in new env
        new_python = get_env_python(new_name)
        if os.path.exists(requirements_file):
            if log_callback:
                log_callback(f"Installing dependencies into '{new_name}'")
            subprocess.check_call([new_python, "-m", "pip", "install", "-r", requirements_file])

        # Clean up requirements file
        os.remove(requirements_file)

        # Delete old environment
        if log_callback:
            log_callback(f"Deleting old environment '{old_name}'")
        delete_env(old_name, log_callback=log_callback)

        # Update env_data.json
        data = _load_env_data()
        if old_name in data:
            data[new_name] = data.pop(old_name)
            _save_env_data(data)

        if log_callback:
            log_callback(f"Environment renamed from '{old_name}' to '{new_name}' successfully")

    except Exception as e:
        err_msg = f"Failed to rename environment '{old_name}' to '{new_name}': {e}"
        logging.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise


def list_envs():
    """
    List all virtual environments in the predefined directory.
    Returns a list of environment names.
    """
    if not os.path.exists(VENV_DIR):
        return []
    return [d for d in os.listdir(VENV_DIR)
            if os.path.isdir(os.path.join(VENV_DIR, d)) and os.path.exists(os.path.join(VENV_DIR, d, 'pyvenv.cfg'))]

def delete_env(name, log_callback=None):
    """
    Delete the specified virtual environment and remove its tracking data.
    """
    env_path = os.path.join(VENV_DIR, name)
    try:
        if log_callback:
            log_callback(f"Deleting environment '{name}' at {env_path}")
        if os.path.exists(env_path):
            shutil.rmtree(env_path)
            logging.info(f"Deleted environment: {name}")
            # Remove from env_data.json
            data = _load_env_data()
            if name in data:
                del data[name]
                _save_env_data(data)
        if log_callback:
            log_callback(f"Environment '{name}' deleted successfully")
    except Exception as e:
        err_msg = f"Failed to delete environment '{name}': {e}"
        logging.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise

def get_env_python(env_name):
    """
    Get the Python executable path for the specified environment.
    """
    return os.path.join(VENV_DIR, env_name, "Scripts" if os.name == "nt" else "bin", "python")

def activate_env(env_name, directory=None, open_with=None):
    """
    Activate the specified environment in a new CMD window (Windows only), or open the environment directory with an IDE.
    Optionally open the environment at a specific directory or with a supported IDE (VSCode, PyCharm).
    """
    venv_activate_path = os.path.join(VENV_DIR, env_name, "Scripts" if os.name == "nt" else "bin", "activate")
    env_dir = os.path.join(VENV_DIR, env_name)
    target_dir = directory if directory else env_dir

    # Save recent location and update size
    try:
        env_path = os.path.join(VENV_DIR, env_name)
        size_mb = calculate_env_size_mb(env_path)
        set_env_data(env_name, recent_location=target_dir, size=size_mb)
    except Exception as e:
        logging.warning(f"Could not save recent location/size for {env_name}: {e}")

    if not os.path.exists(venv_activate_path):
        print(f"Environment '{env_name}' not found.")
        return

    # If open_with is specified, open the directory with the selected IDE
    if open_with and target_dir and os.path.isdir(target_dir):
        if open_with.lower() == "vs-code":
            vscode_dir = os.path.join(target_dir, ".vscode")
            os.makedirs(vscode_dir, exist_ok=True)
            settings_path = os.path.join(vscode_dir, "settings.json")
            python_path = get_env_python(env_name)
            settings = {}
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        settings = json.load(f)
                except Exception:
                    settings = {}
            settings["python.defaultInterpreterPath"] = python_path
            if os.name == "nt":
                scripts_dir = os.path.join(VENV_DIR, env_name, "Scripts")
                command = f'cd /d {scripts_dir} && activate && cd /d {target_dir}'
                shell_args = ["/K", command]
                settings["terminal.integrated.defaultProfile.windows"] = "Command Prompt"
                settings["terminal.integrated.profiles.windows"] = settings.get("terminal.integrated.profiles.windows", {})
                settings["terminal.integrated.profiles.windows"]["Command Prompt"] = {
                    "path": "cmd.exe",
                    "args": shell_args
                }
                settings["terminal.integrated.cwd"] = scripts_dir
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            subprocess.Popen(["code", target_dir], shell=True)
            print(f"Opened VSCode in {target_dir} with interpreter {python_path} and auto-activation")
            return
        elif open_with.lower() == "pycharm(beta)":
            subprocess.Popen(["charm", target_dir], shell=True)
            return

    # Default: open CMD and activate environment
    if os.name == "nt":
        command = f'start cmd /K "cd /d {target_dir} && {venv_activate_path}"'
    else:
        command = f'cd "{target_dir}" && source "{venv_activate_path}"'
    subprocess.Popen(command, shell=True)

def is_exact_env_active(python_exe_path):
    """
    Check if the current Python executable matches the given path (case-insensitive).
    """
    return os.path.abspath(sys.executable).lower() == os.path.abspath(python_exe_path).lower()