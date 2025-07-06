import os
import subprocess
import shutil
import logging
from configparser import ConfigParser
import sys

# Load configuration
config = ConfigParser()
config.read('config.ini')
VENV_DIR = os.path.expanduser(config.get('settings', 'venv_dir', fallback='~/.venvs'))
PYTHON_PATH = config.get('settings', 'python_path', fallback=None)
logging.basicConfig(filename=config.get('settings', 'log_file', fallback='venv_manager.log'), level=logging.INFO)

def is_valid_python(python_path):
    """
    Validate that the provided path points to a Python executable.

    Args:
        python_path (str): Path to the Python executable.

    Returns:
        bool: True if the path is valid, False otherwise.
    """
    return shutil.which(python_path) is not None and 'python' in python_path.lower()

def create_env(name, python_path=None, upgrade_pip=False):
    """
    Create a virtual environment using the specified Python interpreter.

    Args:
        name (str): Name of the virtual environment.
        python_path (str, optional): Path to the Python interpreter. Defaults to config value.
        upgrade_pip (bool, optional): Whether to upgrade pip after creation.

    Raises:
        ValueError: If no valid Python interpreter is specified.
        subprocess.CalledProcessError: If environment creation fails.
    """
    env_path = os.path.join(VENV_DIR, name)
    python_path = 'python' if python_path is None else python_path
    try:
        if not os.path.exists(VENV_DIR):
            os.makedirs(VENV_DIR)
        subprocess.run([python_path, "-m", "venv", env_path], check=True)
        venv_python = os.path.join(env_path, "Scripts" if os.name == "nt" else "bin", "python")
        subprocess.run([venv_python, "-m", "ensurepip", "--upgrade", "--default-pip"], check=True)
        if upgrade_pip:
            subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        logging.info(f"Created environment at : {env_path} with Python: {python_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to create environment {name}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error creating environment {name}: {e}")
        raise

def list_envs():
    """
    List all virtual environments in the predefined directory.

    Returns:
        list: Names of detected virtual environments.
    """
    if not os.path.exists(VENV_DIR):
        return []
    return [d for d in os.listdir(VENV_DIR) if os.path.isdir(os.path.join(VENV_DIR, d)) and os.path.exists(os.path.join(VENV_DIR, d, 'pyvenv.cfg'))]

def delete_env(name):
    """
    Delete the specified virtual environment.

    Args:
        name (str): Name of the environment to delete.
    """
    env_path = os.path.join(VENV_DIR, name)
    try:
        if os.path.exists(env_path):
            shutil.rmtree(env_path)
            logging.info(f"Deleted environment: {name}")
    except Exception as e:
        logging.error(f"Failed to delete environment {name}: {e}")
        raise

def get_env_python(env_name):
    """
    Get the Python executable path for the specified environment.

    Args:
        env_name (str): Name of the environment.

    Returns:
        str: Path to the Python executable.
    """
    return os.path.join(VENV_DIR, env_name, "Scripts" if os.name == "nt" else "bin", "python")

def activate_env(env_name):
    """
    Activate the specified environment in a new CMD window (Windows only).

    Args:
        env_name (str): Name of the environment to activate.
    """
    venv_activate_path = os.path.join(VENV_DIR, env_name, "Scripts" if os.name == "nt" else "bin", "activate")
    if not os.path.exists(venv_activate_path):
        print(f"Environment '{env_name}' not found.")
        return

    command = f'start cmd /K "{venv_activate_path}"'
    subprocess.Popen(command, shell=True)

def is_exact_env_active(python_exe_path):
    return os.path.abspath(sys.executable).lower() == os.path.abspath(python_exe_path).lower()