#pip_tools.py
import json
import subprocess
import os
import logging
from .env_manager import get_env_python

def list_packages(env_name):
    """
    List installed packages in the specified environment.

    Args:
        env_name (str): Name of the environment.

    Returns:
        list: List of tuples containing (package_name, version).
    """
    python_path = get_env_python(env_name)
    try:
        result = subprocess.run([python_path, "-m", "pip", "list", "--format", "freeze"], capture_output=True, text=True, check=True)
        packages = []
        for line in result.stdout.strip().split("\n"):
            if line:
                name, version = line.split("==")
                packages.append((name, version))
        return packages
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to list packages in {env_name}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error listing packages in {env_name}: {e}")
        raise

def install_package(env_name, package, log_callback=None):
    """
    Install a package in the specified environment.

    Args:
        env_name (str): Name of the environment.
        package (str): Package name to install.
    """
    python_path = get_env_python(env_name)
    try:
        if log_callback:
            log_callback(f"Installing {package} in {env_name}")
        process = subprocess.Popen([python_path, "-m", "pip", "install", package], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if log_callback:
                log_callback(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
        logging.info(f"Installed {package} in {env_name}")
        if log_callback:
            log_callback(f"Installed {package} successfully")
    except subprocess.CalledProcessError as e:
        err_msg = f"Failed to install {package} in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise
    except Exception as e:
        err_msg = f"Unexpected error installing {package} in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise

def uninstall_package(env_name, package, log_callback=None):
    """
    Uninstall a package from the specified environment.

    Args:
        env_name (str): Name of the environment.
        package (str): Package name to uninstall.
    """
    python_path = get_env_python(env_name)
    try:
        if log_callback:
            log_callback(f"Uninstalling {package} from {env_name}")
        process = subprocess.Popen([python_path, "-m", "pip", "uninstall", "-y", package], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if log_callback:
                log_callback(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
        logging.info(f"Uninstalled {package} from {env_name}")
        if log_callback:
            log_callback(f"Uninstalled {package} successfully")
    except subprocess.CalledProcessError as e:
        err_msg = f"Failed to uninstall {package} in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise
    except Exception as e:
        err_msg = f"Unexpected error uninstalling {package} in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise

def update_package(env_name, package, log_callback=None):
    """
    Update a package in the specified environment.

    Args:
        env_name (str): Name of the environment.
        package (str): Package name to update.
    """
    python_path = get_env_python(env_name)
    try:
        if log_callback:
            log_callback(f"Updating {package} in {env_name}")
        process = subprocess.Popen([python_path, "-m", "pip", "install", "--upgrade", package], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if log_callback:
                log_callback(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
        logging.info(f"Updated {package} in {env_name}")
        if log_callback:
            log_callback(f"Updated {package} successfully")
    except subprocess.CalledProcessError as e:
        err_msg = f"Failed to update {package} in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise
    except Exception as e:
        err_msg = f"Unexpected error updating {package} in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise

def check_outdated_packages(env_name, log_callback=None):
    """
    Check for outdated packages in the specified environment.

    Args:
        env_name (str): Name of the environment.

    Returns:
        list: List of tuples containing (package_name, current_version, latest_version).
    """
    python_path = get_env_python(env_name)
    try:
        if log_callback:
            log_callback(f"Checking for outdated packages in {env_name}")
        result = subprocess.run([python_path, "-m", "pip", "list", "--outdated","--format=json"], capture_output=True, text=True, check=True)
    
        logging.info(f"Checked for outdated packages in {env_name}")
        if log_callback:
            log_callback(f"Checked for outdated packages successfully")
            return result.stdout


    except subprocess.CalledProcessError as e:
        err_msg = f"Failed to check for updates in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise
    except Exception as e:
        err_msg = f"Unexpected error checking for updates in {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise
def export_requirements(env_name, file_path):
    """
    Export installed packages to a requirements.txt file.

    Args:
        env_name (str): Name of the environment.
        file_path (str): Path to save the requirements.txt file.
    """
    python_path = get_env_python(env_name)
    try:
        with open(file_path, "w") as f:
            subprocess.run([python_path, "-m", "pip", "freeze"], stdout=f, check=True)
        logging.info(f"Exported requirements for {env_name} to {file_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to export requirements for {env_name}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error exporting requirements for {env_name}: {e}")
        raise

def import_requirements(env_name, file_path, log_callback=None):
    """
    Install packages from a requirements.txt file into the environment.

    Args:
        env_name (str): Name of the environment.
        file_path (str): Path to the requirements.txt file.
    """
    python_path = get_env_python(env_name)
    try:
        if log_callback:
            log_callback(f"Installing requirements from {file_path} to {env_name}")
        process = subprocess.Popen([python_path, "-m", "pip", "install", "-r", file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            if log_callback:
                log_callback(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)
        logging.info(f"Imported requirements from {file_path} to {env_name}")
        if log_callback:
            log_callback(f"Installed requirements successfully")
    except subprocess.CalledProcessError as e:
        err_msg = f"Failed to import requirements to {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise
    except Exception as e:
        err_msg = f"Unexpected error importing requirements to {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise