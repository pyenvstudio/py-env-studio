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
def get_available_tools():
    """
    Get available open_with tools from config and system detection.
    Returns a list of dicts: {"name": str, "path": str or None}
    """
    # Import integration logic for plug-and-play tool detection
    from .integration import detect_tools
    config_path = os.path.join(base_dir, 'config.ini')
    parser = ConfigParser()
    parser.read(config_path)
    tools_raw = parser.get('settings', 'open_with_tools', fallback=None)
    config_tools = []
    if tools_raw:
        for entry in tools_raw.split(','):
            if ':' in entry:
                name, path = entry.split(':', 1)
                config_tools.append({"name": name.strip(), "path": path.strip()})
            else:
                config_tools.append({"name": entry.strip(), "path": None})
    # System-detected tools (plug-and-play)
    detected_tools = detect_tools()
    # Merge config and detected tools, preferring config if duplicate names
    all_tools = config_tools.copy()
    config_names = {t["name"].lower() for t in config_tools}
    for dt in detected_tools:
        if dt["name"].lower() not in config_names:
            all_tools.append(dt)
    return all_tools

def add_tool(name, path=None):
    """
    Add a new open_with tool to config.
    """
    config_path = os.path.join(base_dir, 'config.ini')
    parser = ConfigParser()
    parser.read(config_path)
    tools_raw = parser.get('settings', 'open_with_tools', fallback='')
    entries = [e for e in tools_raw.split(',') if e.strip()]
    entry = f"{name}:{path}" if path else name
    entries.append(entry)
    parser.set('settings', 'open_with_tools', ','.join(entries))
    with open(config_path, 'w', encoding='utf-8') as f:
        parser.write(f)

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

def set_env_data(env_name, recent_location=None, size=None,last_scanned=None,python_version=None):
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

    if python_version is not None:
        entry['python_version'] = python_version

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
    python_version = _extract_python_version(python_path) if python_path else "default"
    python_path = 'python' if python_path is None else python_path
    try:
        if log_callback:
            log_callback(f"Creating virtual environment '{name}' at {env_path} with Python: {python_version}")

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
        
        # Save initial env data
        size_mb = calculate_env_size_mb(env_path)
        python_version = _extract_python_version(venv_python)
        set_env_data(name, recent_location=env_path, size=size_mb, python_version=python_version)

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
def _extract_python_version(python_path):
    """
    Extract the Python version from the given executable path.
    Returns version string like '3.9.1' or None if not valid.
    """
    try:
        output = subprocess.check_output([python_path, "--version"], text=True).strip()
        if output.startswith("Python "):
            return output.split()[1]
    except Exception:
        return None
    return None

def list_pythons():
    """
    List all Python executables available on the system PATH.
    Returns a list of paths to Python executables.
    """

    path_list = set()
    paths = os.environ.get("PATH", "").split(os.pathsep)

    # Regex to match python executables with optional version and extensions
    pattern = re.compile(r'^python(\d+(\.\d+)?)?(\.exe)?$', re.IGNORECASE)
    id = 0
    for path in paths:
        if os.path.isdir(path):
            try:
                for file in os.listdir(path):
                    if pattern.match(file):
                        full_path = os.path.join(path, file)
                        if is_valid_python(full_path):
                            path_list.add(full_path)
                           
            except PermissionError:
                # skip folders without permission
                pass

    return sorted(path_list)

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

import os
import subprocess
import logging
import shutil

from .integration import detect_tools

def activate_env(env_name, directory=None, open_with=None, log_callback=None):
    venv_dir = os.path.join(VENV_DIR, env_name)
    target_dir = directory or venv_dir

    tools = detect_tools()
    tool_entry = next((t for t in tools if t["name"].lower() == (open_with or "").lower()), None)

    if not tool_entry:
        logging.error(f"Tool {open_with} not detected.")
        return

    tool_name = tool_entry["name"].lower()
    tool_path = tool_entry["path"]

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        logging.error(f"No handler defined for {tool_name}.")
        return

    try:
        handler(tool_path, venv_dir, target_dir)
        if log_callback:
            log_callback(f"Opened {tool_name} with environment {env_name}")
    except Exception as e:
        logging.error(f"Failed to activate env {env_name} with {tool_name}: {e}")
        if log_callback:
            log_callback(f"Failed to activate env {env_name} with {tool_name}: {e}")
            
def is_exact_env_active(python_exe_path):
    """
    Check if the current Python executable matches the given path (case-insensitive).
    """
    return os.path.abspath(sys.executable).lower() == os.path.abspath(python_exe_path).lower()