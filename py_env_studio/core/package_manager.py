"""Unified package manager interface supporting both pip and uv.

This module provides a wrapper layer that intelligently routes package management
operations to either pip or uv based on which manager was used to create the environment.
"""

import logging
import shutil
import subprocess
from typing import List, Tuple, Optional

from packaging.utils import canonicalize_name

from .env_manager import get_env_data, get_env_python
from . import pip_tools
from . import uv_tools

logger = logging.getLogger(__name__)


def _invalidate_package_update_cache(env_name: str) -> None:
    """Drop update results after a successful package mutation."""
    try:
        from .package_update_monitor import PackageUpdateMonitor

        PackageUpdateMonitor().invalidate_cache(env_name)
    except Exception as exc:
        logger.warning("Could not invalidate package-update cache for '%s': %s", env_name, exc)
    try:
        from .environment_lock import EnvironmentLockService

        EnvironmentLockService().mark_drift(env_name)
    except Exception as exc:
        logger.debug("Could not mark environment lock unchecked for '%s': %s", env_name, exc)


def get_env_package_manager(env_name: str) -> str:
    """Get the package manager that was used to create this environment.
    
    Args:
        env_name: Name of the environment
    
    Returns:
        "pip" or "uv" (defaults to "pip" if not specified)
    """
    try:
        env_data = get_env_data(env_name)
        manager = env_data.get("package_manager", "pip")
        
        # Validate the manager
        if manager not in ("pip", "uv"):
            return "pip"
        
        # If uv is selected but not installed, fallback to pip
        if manager == "uv" and not uv_tools.is_uv_installed():
            logger.warning(f"Environment '{env_name}' was created with uv but uv is not installed, falling back to pip")
            return "pip"
        
        return manager
    except Exception as e:
        logger.error(f"Error getting environment package manager for '{env_name}': {e}")
        return "pip"


def list_packages(env_name):
    """List packages using the environment's package manager.
    
    Args:
        env_name: Name of the environment
    
    Returns:
        List of (name, version) tuples
    """
    manager = get_env_package_manager(env_name)
    
    if manager == "uv":
        try:
            venv_python = get_env_python(env_name)
            packages = uv_tools.list_packages_uv(venv_python)
            # Convert to same format as pip_tools
            return [(pkg["name"], pkg["version"]) for pkg in packages]
        except Exception as e:
            logger.error(f"uv list_packages failed, falling back to pip: {e}")
            return pip_tools.list_packages(env_name)
    else:
        return pip_tools.list_packages(env_name)


def install_package(env_name, package, log_callback=None):
    """Install a package using the environment's package manager.
    
    Args:
        env_name: Name of the environment
        package: Package name/spec to install
        log_callback: Optional callback for log messages
    """
    manager = get_env_package_manager(env_name)
    
    if manager == "uv":
        try:
            venv_python = get_env_python(env_name)
            success, msg = uv_tools.install_package_uv(venv_python, package, log_callback=log_callback)
            if log_callback and not success:
                log_callback(msg)
            if not success:
                raise Exception(msg)
            _invalidate_package_update_cache(env_name)
        except Exception as e:
            logger.error(f"uv install_package failed, falling back to pip: {e}")
            result = pip_tools.install_package(env_name, package, log_callback)
            _invalidate_package_update_cache(env_name)
            return result
    else:
        result = pip_tools.install_package(env_name, package, log_callback)
        _invalidate_package_update_cache(env_name)
        return result


def uninstall_package(env_name, package, log_callback=None):
    """Uninstall a package using the environment's package manager.
    
    Args:
        env_name: Name of the environment
        package: Package name to uninstall
        log_callback: Optional callback for log messages
    """
    manager = get_env_package_manager(env_name)
    
    if manager == "uv":
        try:
            venv_python = get_env_python(env_name)
            success, msg = uv_tools.uninstall_package_uv(venv_python, package)
            if log_callback:
                log_callback(msg)
            if not success:
                raise Exception(msg)
            _invalidate_package_update_cache(env_name)
        except Exception as e:
            logger.error(f"uv uninstall_package failed, falling back to pip: {e}")
            result = pip_tools.uninstall_package(env_name, package, log_callback)
            _invalidate_package_update_cache(env_name)
            return result
    else:
        result = pip_tools.uninstall_package(env_name, package, log_callback)
        _invalidate_package_update_cache(env_name)
        return result


def update_package(env_name, package, log_callback=None):
    """Update a package using the environment's package manager.
    
    Args:
        env_name: Name of the environment
        package: Package name to update
        log_callback: Optional callback for log messages
    """
    manager = get_env_package_manager(env_name)
    
    if manager == "uv":
        try:
            venv_python = get_env_python(env_name)
            success, msg = uv_tools.update_package_uv(venv_python, package)
            if log_callback:
                log_callback(msg)
            if not success:
                raise Exception(msg)
            _invalidate_package_update_cache(env_name)
        except Exception as e:
            logger.error(f"uv update_package failed, falling back to pip: {e}")
            result = pip_tools.update_package(env_name, package, log_callback)
            _invalidate_package_update_cache(env_name)
            return result
    else:
        result = pip_tools.update_package(env_name, package, log_callback)
        _invalidate_package_update_cache(env_name)
        return result


def export_requirements(env_name, output_file, log_callback=None):
    """Export requirements using the environment's package manager.
    
    Args:
        env_name: Name of the environment
        output_file: Path to save requirements file
        log_callback: Optional callback for log messages
    """
    manager = get_env_package_manager(env_name)
    
    if manager == "uv":
        try:
            venv_python = get_env_python(env_name)
            success, msg = uv_tools.export_requirements_uv(venv_python, output_file)
            if log_callback:
                log_callback(msg)
            if not success:
                raise Exception(msg)
        except Exception as e:
            logger.error(f"uv export_requirements failed, falling back to pip: {e}")
            return pip_tools.export_requirements(env_name, output_file)
    else:
        return pip_tools.export_requirements(env_name, output_file)


def import_requirements(env_name, requirements_file, log_callback=None):
    """Import requirements using the environment's package manager.
    
    Args:
        env_name: Name of the environment
        requirements_file: Path to requirements file
        log_callback: Optional callback for log messages
    """
    manager = get_env_package_manager(env_name)
    
    if manager == "uv":
        try:
            venv_python = get_env_python(env_name)
            success, msg = uv_tools.import_requirements_uv(venv_python, requirements_file)
            if log_callback:
                log_callback(msg)
            if not success:
                raise Exception(msg)
            _invalidate_package_update_cache(env_name)
        except Exception as e:
            logger.error(f"uv import_requirements failed, falling back to pip: {e}")
            result = pip_tools.import_requirements(env_name, requirements_file, log_callback)
            _invalidate_package_update_cache(env_name)
            return result
    else:
        result = pip_tools.import_requirements(env_name, requirements_file, log_callback)
        _invalidate_package_update_cache(env_name)
        return result


def sync_from_lock_file(env_name: str, lock_file, expected_package_names: set[str]) -> None:
    """Synchronize one environment from a validated pylock.toml via its manager."""
    from pathlib import Path

    path = Path(lock_file)
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"Environment lock is unavailable: {path}")

    manager = get_env_package_manager(env_name)
    python = get_env_python(env_name)
    mutation_started = False
    try:
        mutation_started = True
        if manager == "uv":
            uv = shutil.which("uv")
            if not uv:
                raise RuntimeError("uv is no longer available to synchronize this environment")
            result = subprocess.run(
                [uv, "pip", "sync", "--python", python, "--strict", str(path)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                details = (result.stderr or result.stdout or "uv sync failed").strip()
                raise RuntimeError(details)
            return

        result = subprocess.run(
            [python, "-m", "pip", "install", "--requirement", str(path)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout or "pip lock installation failed").strip()
            raise RuntimeError(details)

        installed_names = {
            canonicalize_name(name)
            for name, _version in list_packages(env_name)
        }
        for package_name in sorted(installed_names - expected_package_names):
            uninstall_package(env_name, package_name)
    finally:
        if mutation_started:
            _invalidate_package_update_cache(env_name)


def check_outdated_packages(env_name, log_callback=None):
    """Check for outdated packages using the environment's package manager.
    
    Args:
        env_name: Name of the environment
        log_callback: Optional callback for log messages
    
    Returns:
        JSON string of outdated packages list
    """
    import json
    manager = get_env_package_manager(env_name)
    
    if manager == "uv":
        try:
            venv_python = get_env_python(env_name)
            success, outdated = uv_tools.check_outdated_packages_uv(venv_python)
            if not success:
                raise Exception("Failed to check outdated packages with uv")
            # Convert list to JSON string to match pip_tools format
            return json.dumps(outdated)
        except Exception as e:
            logger.error(f"uv check_outdated_packages failed, falling back to pip: {e}")
            return pip_tools.check_outdated_packages(env_name, log_callback)
    else:
        return pip_tools.check_outdated_packages(env_name, log_callback)
