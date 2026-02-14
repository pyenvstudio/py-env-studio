#pip_tools.py
import subprocess
import logging
import re
from .env_manager import get_env_python
from . import auto_resolve

def get_pip_version() -> str:
    """Get the version of pip installed on the system.
    
    Returns:
        Version string (e.g., "25.5") or empty string if pip not available
    """
    try:
        result = subprocess.run(
            ["pip", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Output format: "pip 25.5 from /path/to/pip (python 3.x)"
            match = re.search(r"pip (\d+\.\d+(?:\.\d+)?)", result.stdout)
            if match:
                return match.group(1)
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return ""

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
        # Log the command
        
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
    Install a package in the specified environment with auto-resolve for dependency conflicts.

    Args:
        env_name (str): Name of the environment.
        package (str): Package name to install.
        log_callback: Optional callback for log messages.
    """
    python_path = get_env_python(env_name)
    
    def _do_install(python_path, env_name, package, log_callback=None):
        """Internal install function that returns (success, message)."""
        try:
            if log_callback:
                log_callback(f"Installing {package} in {env_name}")
            process = subprocess.Popen(
                [python_path, "-m", "pip", "install", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            output_lines = []
            for line in process.stdout:
                output_lines.append(line.strip())
                if log_callback:
                    log_callback(line.strip())
            process.wait()
            
            if process.returncode != 0:
                error_output = "\n".join(output_lines)
                return False, error_output
            
            logging.info(f"Installed {package} in {env_name}")
            if log_callback:
                log_callback(f"Installed {package} successfully")
            return True, f"Installed {package} successfully"
        except Exception as e:
            err_msg = f"Unexpected error installing {package} in {env_name}: {e}"
            if log_callback:
                log_callback(err_msg)
            logging.error(err_msg)
            return False, err_msg
    
    # Attempt installation with auto-resolve for dependency conflicts
    success, message = auto_resolve.auto_resolve_install(
        package,
        _do_install,
        log_callback=log_callback,
        python_path=python_path,
        env_name=env_name,
        package=package,
    )
    
    if not success:
        raise Exception(message)

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
    Install packages from a requirements.txt file into the environment with auto-resolve for conflicts.

    Args:
        env_name (str): Name of the environment.
        file_path (str): Path to the requirements.txt file.
        log_callback: Optional callback for log messages.
    """
    python_path = get_env_python(env_name)
    
    def _do_install_requirements(python_path, file_path, log_callback=None):
        """Internal requirements install function that returns (success, message)."""
        try:
            if log_callback:
                log_callback(f"Installing requirements from {file_path}...")
            
            output_lines = []
            process = subprocess.Popen(
                [python_path, "-m", "pip", "install", "-r", file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                output_lines.append(line.strip())
                if log_callback:
                    log_callback(line.strip())
            process.wait()
            
            if process.returncode != 0:
                error_output = "\n".join(output_lines)
                return False, error_output
            
            logging.info(f"Imported requirements from {file_path} to {env_name}")
            if log_callback:
                log_callback(f"Installed requirements successfully")
            return True, "Requirements installed successfully"
        except Exception as e:
            err_msg = f"Unexpected error installing requirements: {e}"
            if log_callback:
                log_callback(err_msg)
            logging.error(err_msg)
            return False, err_msg
    
    # For requirements files, we use a special resolver that doesn't strip individual packages
    # Instead, we attempt with --no-deps first to diagnose, then with full deps if needed
    try:
        if log_callback:
            log_callback(f"Installing requirements from {file_path} to {env_name}")
        
        # First attempt: normal installation with all dependencies
        success, message = _do_install_requirements(python_path, file_path, log_callback)
        
        if success:
            return
        
        # If failed, check if it's a resolution error
        if auto_resolve.is_resolution_error(message):
            if log_callback:
                log_callback("[Auto-Resolve] Detected dependency conflict in requirements file")
                log_callback("[Auto-Resolve] Attempting to install with conflict resolution...")
            
            # For requirements files, use --no-deps followed by installing individual packages
            # This is safer than modifying the requirements file
            try:
                # Try with pip's auto-resolver (newer pip versions handle this better)
                if log_callback:
                    log_callback("[Auto-Resolve] Attempting with pip's built-in resolver...")
                
                output_lines = []
                process = subprocess.Popen(
                    [python_path, "-m", "pip", "install", "-r", file_path, "--use-deprecated=legacy-resolver"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                for line in process.stdout:
                    output_lines.append(line.strip())
                    if log_callback:
                        log_callback(line.strip())
                process.wait()
                
                if process.returncode == 0:
                    if log_callback:
                        log_callback("[Auto-Resolve] ✓ Successfully installed requirements")
                    logging.info(f"Imported requirements from {file_path} to {env_name}")
                    return
                else:
                    # Legacy resolver also failed
                    error_output = "\n".join(output_lines)
                    err_msg = f"Failed to import requirements to {env_name}: {error_output}"
                    if log_callback:
                        log_callback(err_msg)
                    logging.error(err_msg)
                    raise Exception(error_output)
            except Exception as e:
                # All resolution attempts failed
                err_msg = f"Failed to import requirements to {env_name} even with conflict resolution: {e}"
                if log_callback:
                    log_callback(err_msg)
                logging.error(err_msg)
                raise
        else:
            # Not a resolution error, re-raise original error
            err_msg = f"Failed to import requirements to {env_name}: {message}"
            if log_callback:
                log_callback(err_msg)
            logging.error(err_msg)
            raise Exception(message)
    except Exception as e:
        err_msg = f"Unexpected error importing requirements to {env_name}: {e}"
        if log_callback:
            log_callback(err_msg)
        logging.error(err_msg)
        raise