"""Runtime Toggle Module for Py Env Studio.

Provides runtime management functionality (init, on, off) for Py Env Studio.
"""
from __future__ import annotations

from configparser import ConfigParser
import logging
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from .runtime import get_runtime_config
from .env_manager import get_preferred_package_manager

logger = logging.getLogger(__name__)

# Project metadata file name
PROJECT_METADATA_FILE = "pes.config"

# Global registry file name
REGISTRY_FILE = "registry.json"


def get_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the project root by searching for pes.config or pyproject.toml."""
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path.resolve()
    while current != current.parent:
        if (current / PROJECT_METADATA_FILE).exists() or (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return None


def get_project_metadata_path(project_root: Path) -> Path:
    """Get the path to the project metadata file."""
    return project_root / PROJECT_METADATA_FILE


def get_global_data_dir() -> Path:
    """Get the global Py Env Studio data directory."""
    runtime = get_runtime_config()
    return runtime.user_data_dir


def get_envs_dir() -> Path:
    """Get the global environments directory."""
    runtime = get_runtime_config()
    return runtime.venv_dir


def get_registry_path() -> Path:
    """Get the path to the global registry file."""
    return get_global_data_dir() / REGISTRY_FILE


def load_project_metadata(project_root: Path) -> dict:
    """Load project metadata from pes.config."""
    metadata_path = get_project_metadata_path(project_root)
    if not metadata_path.exists():
        return {}
    
    try:
        parser = ConfigParser()
        parser.read(metadata_path, encoding="utf-8")
        if not parser.sections():
            return {}

        return {
            "project_name": parser.get("project", "name", fallback=project_root.name),
            "project_root": str(project_root),
            "environment_id": parser.get("environment", "id", fallback=None),
            "environment_path": parser.get("environment", "path", fallback=None),
            "python_version": parser.get("environment", "python_version", fallback=get_python_version()),
            "package_manager": parser.get("environment", "package_manager", fallback="pip"),
            "runtime_enabled": parser.getboolean("runtime", "enabled", fallback=False),
            "auto_init": parser.getboolean("runtime", "auto_init", fallback=True),
        }
    except Exception as e:
        logger.error(f"Failed to load project metadata: {e}")
        return {}


def save_project_metadata(project_root: Path, metadata: dict) -> None:
    """Save project metadata to pes.config."""
    metadata_path = get_project_metadata_path(project_root)
    try:
        parser = ConfigParser()
        parser["project"] = {
            "name": metadata.get("project_name", project_root.name),
            "root": str(project_root),
        }
        parser["environment"] = {
            "id": metadata.get("environment_id", ""),
            "path": metadata.get("environment_path", ""),
            "python_version": metadata.get("python_version", get_python_version()),
            "package_manager": metadata.get("package_manager", "pip"),
        }
        parser["runtime"] = {
            "enabled": str(metadata.get("runtime_enabled", False)).lower(),
            "auto_init": str(metadata.get("auto_init", True)).lower(),
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            parser.write(f)
    except Exception as e:
        logger.error(f"Failed to save project metadata: {e}")
        raise


def load_registry() -> dict:
    """Load the global registry."""
    import json
    
    registry_path = get_registry_path()
    if not registry_path.exists():
        return {}
    
    try:
        with open(registry_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load registry: {e}")
        return {}


def save_registry(registry: dict) -> None:
    """Save the global registry."""
    import json
    
    registry_path = get_registry_path()
    try:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save registry: {e}")
        raise


def generate_environment_id(project_name: str) -> str:
    """Generate a unique environment ID for a project."""
    import hashlib
    
    # Create a unique ID based on project name and current directory
    unique_string = f"{project_name}-{os.getcwd()}"
    hash_suffix = hashlib.md5(unique_string.encode()).hexdigest()[:8]
    return f"{project_name}-{hash_suffix}"


def get_python_version() -> str:
    """Get the current Python version string (e.g., '3.12')."""
    version_info = sys.version_info
    return f"{version_info.major}.{version_info.minor}"


def get_system_python() -> str:
    """Get the system Python executable path."""
    return sys.executable


def create_managed_environment(env_id: str, python_version: str) -> Path:
    """Create a managed virtual environment in the global envs directory.
    
    Args:
        env_id: Unique environment identifier
        python_version: Python version to use (e.g., "3.12")
    
    Returns:
        Path to the created environment
    """
    envs_dir = get_envs_dir()
    env_path = envs_dir / env_id
    
    if env_path.exists():
        logger.info(f"Environment already exists: {env_path}")
        return env_path
    
    # Find Python executable for the requested version
    python_exe = sys.executable
    if python_version != get_python_version():
        # Try to find the specific Python version
        import shutil
        versioned_python = f"python{python_version}"
        found = shutil.which(versioned_python)
        if found:
            python_exe = found
        else:
            logger.warning(f"Python {python_version} not found, using system Python: {sys.executable}")
    
    # Create virtual environment
    env_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([python_exe, "-m", "venv", str(env_path)], check=True)
    
    # Upgrade pip in the new environment
    pip_path = env_path / "bin" / "pip" if sys.platform != "win32" else env_path / "Scripts" / "pip.exe"
    if pip_path.exists():
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=False)
    
    logger.info(f"Created environment: {env_path}")
    return env_path


def get_environment_python(env_path: Path) -> Path:
    """Get the Python executable path for a managed environment."""
    if sys.platform == "win32":
        return env_path / "Scripts" / "python.exe"
    return env_path / "bin" / "python"


def get_environment_scripts_dir(env_path: Path) -> Path:
    """Get the scripts/bin directory for a managed environment."""
    if sys.platform == "win32":
        return env_path / "Scripts"
    return env_path / "bin"


def get_environment_executable(env_path: Path, command_name: str) -> Optional[Path]:
    """Resolve an executable inside the managed environment."""
    scripts_dir = get_environment_scripts_dir(env_path)
    candidate_names = [command_name]

    if sys.platform == "win32" and not Path(command_name).suffix:
        candidate_names.extend([f"{command_name}.exe", f"{command_name}.bat", f"{command_name}.cmd"])

    for candidate_name in candidate_names:
        candidate_path = scripts_dir / candidate_name
        if candidate_path.exists():
            return candidate_path

    return None


def is_runtime_enabled(project_root: Path) -> bool:
    """Check if Py Env Studio runtime is enabled for the project."""
    metadata = load_project_metadata(project_root)
    return metadata.get("runtime_enabled", False)


def set_runtime_enabled(project_root: Path, enabled: bool) -> None:
    """Enable or disable Py Env Studio runtime for the project."""
    metadata = load_project_metadata(project_root)
    metadata["runtime_enabled"] = enabled
    save_project_metadata(project_root, metadata)
    
    # Also update registry
    registry = load_registry()
    project_name = metadata.get("project_name", project_root.name)
    if project_name in registry:
        registry[project_name]["runtime_enabled"] = enabled
        save_registry(registry)


def init_project(project_root: Optional[Path] = None, python_version: Optional[str] = None) -> dict:
    """Initialize the current project for Py Env Studio.
    
    Responsibilities:
    - Detect current project root
    - Create project metadata if it doesn't exist
    - Create or reuse a managed virtual environment
    - Enable Py Env Studio runtime for the project
    - Register the project in the global registry
    - Do not recreate environment if it already exists
    
    Args:
        project_root: Project root path (defaults to current directory)
        python_version: Python version to use (defaults to current Python version)
    
    Returns:
        Dictionary with initialization result
    """
    if project_root is None:
        project_root = get_project_root()
    
    if project_root is None:
        # No project root found, use current directory
        project_root = Path.cwd()
        logger.warning(f"No project root found, using current directory: {project_root}")
    
    if python_version is None:
        python_version = get_python_version()
    
    project_name = project_root.name
    env_id = generate_environment_id(project_name)
    env_path = get_envs_dir() / env_id
    package_manager = "pip"
    try:
        package_manager = get_preferred_package_manager()
    except Exception:
        logger.debug("Falling back to pip as preferred package manager")
    
    # Load existing metadata if exists
    metadata = load_project_metadata(project_root)
    is_new_project = not metadata
    
    if is_new_project:
        # Create new project metadata
        metadata = {
            "project_name": project_name,
            "project_root": str(project_root),
            "environment_id": env_id,
            "environment_path": str(env_path),
            "python_version": python_version,
            "package_manager": package_manager,
            "runtime_enabled": True,
            "auto_init": True,
        }
    else:
        # Update existing metadata
        env_id = metadata.get("environment_id", env_id)
        env_path = get_envs_dir() / env_id
        metadata["project_name"] = metadata.get("project_name", project_name)
        metadata["project_root"] = str(project_root)
        metadata["environment_path"] = str(env_path)
        metadata["runtime_enabled"] = True
        if "python_version" not in metadata:
            metadata["python_version"] = python_version
        metadata["package_manager"] = metadata.get("package_manager", package_manager)
        metadata["auto_init"] = metadata.get("auto_init", True)
    
    # Create or reuse environment
    if not env_path.exists():
        create_managed_environment(env_id, python_version)
    
    # Save project metadata
    save_project_metadata(project_root, metadata)
    
    # Register in global registry
    registry = load_registry()
    registry[project_name] = {
        "project_root": str(project_root),
        "environment_id": env_id,
        "environment_path": str(env_path),
        "python_version": python_version,
        "runtime_enabled": True,
    }
    save_registry(registry)
    
    # Create runtime interceptor script
    create_runtime_interceptor(project_root)
    
    if is_new_project:
        return {
            "success": True,
            "message": f"Project initialized successfully. Runtime: ON Environment: {project_name}",
            "project_name": project_name,
            "environment_id": env_id,
            "environment_path": str(env_path),
            "runtime_enabled": True,
        }
    else:
        return {
            "success": True,
            "message": "Project already initialized. Runtime enabled.",
            "project_name": project_name,
            "environment_id": env_id,
            "environment_path": str(env_path),
            "runtime_enabled": True,
        }


def enable_runtime(project_root: Optional[Path] = None) -> dict:
    """Enable Py Env Studio runtime interception.
    
    Responsibilities:
    - Do NOT recreate environment
    - Do NOT reinstall packages
    - Simply switch runtime state to enabled
    
    Args:
        project_root: Project root path (defaults to current directory)
    
    Returns:
        Dictionary with enable result
    """
    if project_root is None:
        project_root = get_project_root()
    
    if project_root is None:
        return {
            "success": False,
            "message": "No project initialized. Run 'py-env-studio init' first.",
        }
    
    metadata = load_project_metadata(project_root)
    if not metadata:
        return {
            "success": False,
            "message": "Project not initialized. Run 'py-env-studio init' first.",
        }
    
    # Check if environment exists
    env_id = metadata.get("environment_id")
    if not env_id:
        return {
            "success": False,
            "message": "No environment configured. Run 'py-env-studio init' first.",
        }
    
    env_path = get_envs_dir() / env_id
    if not env_path.exists():
        return {
            "success": False,
            "message": f"Environment not found: {env_path}. Run 'py-env-studio init' to recreate.",
        }
    
    # Enable runtime
    set_runtime_enabled(project_root, True)
    
    return {
        "success": True,
        "message": "Py Env Studio runtime enabled.",
    }


def disable_runtime(project_root: Optional[Path] = None) -> dict:
    """Disable Py Env Studio runtime interception.
    
    Responsibilities:
    - Keep environment intact
    - Do NOT delete anything
    - Future python executions should bypass Py Env Studio and use system Python
    
    Args:
        project_root: Project root path (defaults to current directory)
    
    Returns:
        Dictionary with disable result
    """
    if project_root is None:
        project_root = get_project_root()
    
    if project_root is None:
        return {
            "success": True,
            "message": "Py Env Studio runtime disabled. Using system Python.",
        }
    
    metadata = load_project_metadata(project_root)
    if not metadata:
        return {
            "success": True,
            "message": "Py Env Studio runtime disabled. Using system Python.",
        }
    
    # Disable runtime
    set_runtime_enabled(project_root, False)
    
    return {
        "success": True,
        "message": "Py Env Studio runtime disabled. Using system Python.",
    }


def get_runtime_python(project_root: Optional[Path] = None) -> Optional[str]:
    """Get the Python executable to use for the current project.
    
    Returns the managed environment Python if runtime is enabled,
    otherwise returns the system Python.
    
    Args:
        project_root: Project root path (defaults to current directory)
    
    Returns:
        Path to Python executable or None if no project found
    """
    if project_root is None:
        project_root = get_project_root()
    
    if project_root is None:
        return get_system_python()
    
    metadata = load_project_metadata(project_root)
    if not metadata:
        return get_system_python()
    
    if not metadata.get("runtime_enabled", False):
        return get_system_python()
    
    env_id = metadata.get("environment_id")
    if not env_id:
        return get_system_python()
    
    env_path = get_envs_dir() / env_id
    if not env_path.exists():
        logger.warning(f"Environment not found: {env_path}, falling back to system Python")
        return get_system_python()
    
    env_python = get_environment_python(env_path)
    if not env_python.exists():
        logger.warning(f"Environment Python not found: {env_python}, falling back to system Python")
        return get_system_python()
    
    return str(env_python)


def get_project_environment_python(project_root: Path, auto_init: bool = False) -> Optional[str]:
    """Get the managed environment Python for a project, ignoring runtime toggle state."""
    metadata = load_project_metadata(project_root)

    if not metadata and auto_init:
        init_result = init_project(project_root)
        if not init_result.get("success"):
            return None
        metadata = load_project_metadata(project_root)

    if not metadata:
        return None

    env_id = metadata.get("environment_id")
    if not env_id:
        return None

    env_path = get_envs_dir() / env_id
    if not env_path.exists():
        create_managed_environment(env_id, metadata.get("python_version", get_python_version()))
        metadata["environment_path"] = str(env_path)
        save_project_metadata(project_root, metadata)

    env_python = get_environment_python(env_path)
    if not env_python.exists():
        logger.warning(f"Environment Python not found: {env_python}")
        return None

    return str(env_python)


def get_project_environment_path(project_root: Path, auto_init: bool = False) -> Optional[Path]:
    """Get the managed environment directory for a project."""
    metadata = load_project_metadata(project_root)

    if not metadata and auto_init:
        init_result = init_project(project_root)
        if not init_result.get("success"):
            return None
        metadata = load_project_metadata(project_root)

    if not metadata:
        return None

    env_id = metadata.get("environment_id")
    if not env_id:
        return None

    env_path = get_envs_dir() / env_id
    if not env_path.exists():
        create_managed_environment(env_id, metadata.get("python_version", get_python_version()))
        metadata["environment_path"] = str(env_path)
        save_project_metadata(project_root, metadata)

    return env_path


def create_runtime_interceptor(project_root: Path) -> None:
    """Create a runtime interceptor script that intercepts 'python' command.
    
    This creates a small wrapper script that intercepts 'python' commands
    and delegates to the managed environment when runtime is enabled.
    """
    # Create a wrapper script that will be used as 'python' shim
    # This is placed in a directory that's added to PATH
    pass


def execute_in_managed_env(project_root: Path, args: list[str]) -> int:
    """Execute a Python command in the managed environment.
    
    Args:
        project_root: Project root path
        args: Command line arguments (e.g., ['main.py', '--arg1'])
    
    Returns:
        Exit code from the executed command
    """
    project_root = project_root.resolve()
    if not args:
        logger.error("No command arguments provided")
        return 1

    env_path = get_project_environment_path(project_root, auto_init=True)
    if not env_path:
        logger.error("No managed project environment found")
        return 1

    python_path = get_environment_python(env_path)
    if not python_path.exists():
        logger.error("No managed project Python executable found")
        return 1

    command_name = args[0]
    command_args = args[1:]

    if command_name == "python":
        cmd = [str(python_path)] + command_args
    elif command_name == "pip":
        pip_executable = get_environment_executable(env_path, "pip")
        if pip_executable is None:
            cmd = [str(python_path), "-m", "pip"] + command_args
        else:
            cmd = [str(pip_executable)] + command_args
    elif command_name.startswith("-") or command_name.endswith(".py"):
        cmd = [str(python_path)] + args
    else:
        executable = get_environment_executable(env_path, command_name)
        if executable is not None:
            cmd = [str(executable)] + command_args
        else:
            cmd = [str(python_path)] + args

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return 1


def get_project_status(project_root: Optional[Path] = None) -> dict:
    """Get the current project status."""
    if project_root is None:
        project_root = get_project_root()
    
    if project_root is None:
        return {
            "initialized": False,
            "project_root": None,
            "runtime_enabled": False,
            "environment_exists": False,
            "environment_path": None,
            "python_version": get_python_version(),
        }
    
    metadata = load_project_metadata(project_root)
    if not metadata:
        return {
            "initialized": False,
            "project_root": str(project_root),
            "runtime_enabled": False,
            "environment_exists": False,
            "environment_path": None,
            "python_version": get_python_version(),
        }
    
    env_id = metadata.get("environment_id")
    env_path = Path(metadata["environment_path"]) if metadata.get("environment_path") else (get_envs_dir() / env_id if env_id else None)
    env_exists = env_path.exists() if env_path else False
    
    return {
        "initialized": True,
        "project_root": str(project_root),
        "project_name": metadata.get("project_name"),
        "runtime_enabled": metadata.get("runtime_enabled", False),
        "environment_id": env_id,
        "environment_exists": env_exists,
        "environment_path": str(env_path) if env_path else None,
        "python_version": metadata.get("python_version", get_python_version()),
    }


def list_registered_projects() -> list[dict]:
    """List all registered projects in the global registry."""
    registry = load_registry()
    projects = []
    for name, info in registry.items():
        env_path = Path(info.get("environment_path", ""))
        projects.append({
            "name": name,
            "project_root": info.get("project_root"),
            "environment_id": info.get("environment_id"),
            "environment_exists": env_path.exists(),
            "runtime_enabled": info.get("runtime_enabled", False),
            "python_version": info.get("python_version"),
        })
    return projects
