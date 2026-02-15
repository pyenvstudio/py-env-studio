"""UV Package Manager Tools

Provides integration with the uv package manager for enhanced package management.
uv is 10-100x faster than pip and provides a drop-in replacement with advanced features.

Documentation: https://docs.astral.sh/uv/
"""

import subprocess
import logging
from typing import List, Tuple, Optional
import json
import re
import os
from pathlib import Path
from . import auto_resolve

logger = logging.getLogger(__name__)


def _get_venv_dir_from_python_path(python_path: str) -> str:
    """Convert a python executable path to its venv directory.
    
    Args:
        python_path: Path to python executable (e.g., /path/to/venv/bin/python or /path/to/venv/Scripts/python)
    
    Returns:
        Path to the venv directory
    """
    path = Path(python_path).resolve()
    
    # Go up 2 levels from python executable to get venv root
    # /path/to/venv/Scripts/python -> /path/to/venv
    # /path/to/venv/bin/python -> /path/to/venv
    venv_dir = path.parent.parent
    
    return str(venv_dir)


def is_uv_installed() -> bool:
    """Check if uv is installed on the system.
    
    Returns:
        True if uv is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_uv_version() -> Optional[str]:
    """Get the installed uv version.
    
    Returns:
        Version string (e.g., "0.9.0") or None if uv not installed
    """
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Output format: "uv 0.9.0"
            match = re.search(r"uv (\d+\.\d+\.\d+)", result.stdout)
            if match:
                return match.group(1)
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return None


def list_packages_uv(venv_path: str) -> List[dict]:
    """List packages installed in a uv virtual environment.
    
    Args:
        venv_path: Path to the python executable OR venv directory
    
    Returns:
        List of packages with name and version
    """
    try:
        # Convert python path to venv directory if needed
        venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
        
        
        # Use uv pip list with the venv directory
        result = subprocess.run(
            ["uv", "pip", "list", "--python", str(venv_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to list packages: {result.stderr}")
            return []
        
        packages = []
        lines = result.stdout.split("\n")[2:]  # Skip headers
        
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                packages.append({
                    "name": parts[0],
                    "version": parts[1]
                })
        
        return packages
    
    except Exception as e:
        logger.error(f"Error listing packages with uv: {e}")
        return []


def install_package_uv(venv_path: str, package_name: str, log_callback=None) -> Tuple[bool, str]:
    """Install a package using uv with auto-resolve for dependency conflicts.
    
    Args:
        venv_path: Path to the python executable OR venv directory
        package_name: Package name to install (e.g., "django==4.2")
        log_callback: Optional callback for log messages
    
    Returns:
        Tuple of (success, message)
    """
    def _do_install(venv_path, package, log_callback=None):
        """Internal install function that returns (success, message)."""
        try:
            # Convert python path to venv directory if needed
            venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
            
            if log_callback:
                log_callback(f"[UV] Installing {package}...")
            
            result = subprocess.run(
                ["uv", "pip", "install", "--python", str(venv_dir), package],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if log_callback and result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        log_callback(line.strip())
            
            if result.returncode == 0:
                return True, f"Successfully installed {package}"
            else:
                error_msg = result.stderr or result.stdout
                return False, error_msg
        
        except subprocess.TimeoutExpired:
            return False, f"Installation timeout for {package}"
        except Exception as e:
            logger.error(f"Error installing package with uv: {e}")
            return False, str(e)
    
    # Attempt installation with auto-resolve for dependency conflicts
    return auto_resolve.auto_resolve_install(
        package_name,
        _do_install,
        log_callback=log_callback,
        venv_path=venv_path,
        package=package_name,
    )


def uninstall_package_uv(venv_path: str, package_name: str) -> Tuple[bool, str]:
    """Uninstall a package using uv.
    
    Args:
        venv_path: Path to the python executable OR venv directory
        package_name: Package name to uninstall
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Convert python path to venv directory if needed
        venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
        
        
        result = subprocess.run(
            ["uv", "pip", "uninstall", "--python", str(venv_dir), package_name],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            return True, f"Successfully uninstalled {package_name}"
        else:
            return False, result.stderr
    
    except subprocess.TimeoutExpired:
        return False, f"Uninstallation timeout for {package_name}"
    except Exception as e:
        logger.error(f"Error uninstalling package with uv: {e}")
        return False, str(e)


def update_package_uv(venv_path: str, package_name: str) -> Tuple[bool, str]:
    """Update a package to the latest version using uv.
    
    Args:
        venv_path: Path to the python executable OR venv directory
        package_name: Package name to update
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Convert python path to venv directory if needed
        venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
        
        
        result = subprocess.run(
            ["uv", "pip", "install", "--python", str(venv_dir), "--upgrade", package_name],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            return True, f"Successfully updated {package_name}"
        else:
            return False, result.stderr
    
    except subprocess.TimeoutExpired:
        return False, f"Update timeout for {package_name}"
    except Exception as e:
        logger.error(f"Error updating package with uv: {e}")
        return False, str(e)


def import_requirements_uv(venv_path: str, requirements_file: str) -> Tuple[bool, str]:
    """Install packages from a requirements file using uv.
    
    Args:
        venv_path: Path to the python executable OR venv directory
        requirements_file: Path to requirements.txt file
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Convert python path to venv directory if needed
        venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
        
        result = subprocess.run(
            ["uv", "pip", "install", "--python", str(venv_dir), "-r", requirements_file],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            return True, f"Successfully imported requirements from {requirements_file}"
        else:
            return False, result.stderr
    
    except subprocess.TimeoutExpired:
        return False, "Requirements import timeout"
    except Exception as e:
        logger.error(f"Error importing requirements with uv: {e}")
        return False, str(e)


def export_requirements_uv(venv_path: str, output_file: str) -> Tuple[bool, str]:
    """Export installed packages to a requirements file using uv.
    
    Args:
        venv_path: Path to the python executable OR venv directory
        output_file: Path where to save the requirements file
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Convert python path to venv directory if needed
        venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
        
        # First, get the list of packages
        packages = list_packages_uv(venv_path)
        
        if not packages:
            return False, "No packages found to export"
        
        # Write to file
        with open(output_file, "w") as f:
            for pkg in packages:
                # Skip pip and setuptools as they're typically not user-installed
                if pkg["name"].lower() not in ["pip", "setuptools", "wheel"]:
                    f.write(f"{pkg['name']}=={pkg['version']}\n")
        
        return True, f"Successfully exported requirements to {output_file}"
    
    except Exception as e:
        logger.error(f"Error exporting requirements with uv: {e}")
        return False, str(e)


def check_outdated_packages_uv(venv_path: str) -> Tuple[bool, List[dict]]:
    """Check for outdated packages in a uv environment.
    
    Args:
        venv_path: Path to the python executable OR venv directory
    
    Returns:
        Tuple of (success, list of outdated packages)
    """
    try:
        # Convert python path to venv directory if needed
        venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
        
        result = subprocess.run(
            ["uv", "pip", "list", "--python", str(venv_dir), "--outdated"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to check outdated packages: {result.stderr}")
            return False, []
        
        outdated = []
        lines = result.stdout.split("\n")[2:]  # Skip headers
        
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) >= 3:
                outdated.append({
                    "name": parts[0],
                    "version": parts[1],
                    "latest_version": parts[2]
                })
        
        if outdated:
            pass
        else:
            pass
        
        return True, outdated
    
    except Exception as e:
        logger.error(f"Error checking outdated packages with uv: {e}")
        return False, []


def get_package_info_uv(venv_path: str, package_name: str) -> Optional[dict]:
    """Get detailed information about a package using uv.
    
    Args:
        venv_path: Path to the python executable OR venv directory
        package_name: Package name
    
    Returns:
        Dictionary with package information or None
    """
    try:
        # Convert python path to venv directory if needed
        venv_dir = _get_venv_dir_from_python_path(venv_path) if venv_path.endswith(('python', 'python.exe')) else venv_path
        
        result = subprocess.run(
            ["uv", "pip", "show", "--python", str(venv_dir), package_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        info = {}
        for line in result.stdout.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower()] = value.strip()
        
        return info if info else None
    
    except Exception as e:
        logger.error(f"Error getting package info with uv: {e}")
        return None


class UVManager:
    """High-level manager for uv operations following code ethics and best practices."""
    
    def __init__(self, venv_path: str):
        """Initialize UV manager for a specific virtual environment.
        
        Args:
            venv_path: Path to the virtual environment
        """
        self.venv_path = venv_path
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def is_available(self) -> bool:
        """Check if uv is available on the system."""
        return is_uv_installed()
    
    def get_version(self) -> Optional[str]:
        """Get uv version."""
        return get_uv_version()
    
    def list_packages(self) -> List[dict]:
        """List all packages in the environment."""
        return list_packages_uv(self.venv_path)
    
    def install(self, package_name: str) -> Tuple[bool, str]:
        """Install a package."""
        return install_package_uv(self.venv_path, package_name)
    
    def uninstall(self, package_name: str) -> Tuple[bool, str]:
        """Uninstall a package."""
        return uninstall_package_uv(self.venv_path, package_name)
    
    def update(self, package_name: str) -> Tuple[bool, str]:
        """Update a package."""
        return update_package_uv(self.venv_path, package_name)
    
    def import_requirements(self, requirements_file: str) -> Tuple[bool, str]:
        """Import from requirements file."""
        return import_requirements_uv(self.venv_path, requirements_file)
    
    def export_requirements(self, output_file: str) -> Tuple[bool, str]:
        """Export to requirements file."""
        return export_requirements_uv(self.venv_path, output_file)
    
    def check_outdated(self) -> Tuple[bool, List[dict]]:
        """Check for outdated packages."""
        return check_outdated_packages_uv(self.venv_path)
    
    def get_package_info(self, package_name: str) -> Optional[dict]:
        """Get package information."""
        return get_package_info_uv(self.venv_path, package_name)
