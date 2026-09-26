"""Core environment management API used by GUI and CLI."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from .configuration import AppConfig
from .integration import detect_tools
from .runtime import get_runtime_config
from .strategies import run_strategy

runtime = get_runtime_config()

LOGGER = logging.getLogger(__name__)

VENV_DIR = ""
PYTHON_PATH = None
LOG_FILE = ""
DB_FILE = ""
MATRIX_FILE = ""
ENV_DATA_FILE = ""


def refresh_runtime_paths() -> None:
    """Refresh module-level paths from current runtime configuration."""
    global runtime
    global VENV_DIR
    global PYTHON_PATH
    global LOG_FILE
    global DB_FILE
    global MATRIX_FILE
    global ENV_DATA_FILE

    runtime = get_runtime_config()
    VENV_DIR = str(runtime.venv_dir)
    PYTHON_PATH = runtime.python_path
    LOG_FILE = str(runtime.log_path)
    DB_FILE = str(runtime.db_path)
    MATRIX_FILE = str(runtime.matrix_path)
    ENV_DATA_FILE = str(runtime.venv_dir / "env_data.json")


refresh_runtime_paths()

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    tmp = Path(tmp_path)
    try:
        with os.fdopen(tmp_fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def search_envs(query):
    all_envs = list_envs()
    if not query:
        return all_envs
    query_lower = query.lower()
    return [env for env in all_envs if query_lower in env.lower()]


def get_available_tools():
    app_config = AppConfig()
    tools_raw = app_config.get_param("settings", "open_with_tools", fallback=None)

    config_tools = []
    if tools_raw:
        for entry in tools_raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                name, path = entry.split(":", 1)
                config_tools.append({"name": name.strip(), "path": path.strip()})
            else:
                config_tools.append({"name": entry.strip(), "path": None})

    detected_tools = detect_tools()
    all_tools = config_tools.copy()
    configured = {tool["name"].lower() for tool in config_tools}
    for tool in detected_tools:
        if tool["name"].lower() not in configured:
            all_tools.append(tool)
    return all_tools


def add_tool(name, path=None):
    app_config = AppConfig()
    tools_raw = app_config.get_param("settings", "open_with_tools", fallback="") or ""
    entries = [entry.strip() for entry in tools_raw.split(",") if entry.strip()]

    new_entry = f"{name}:{path}" if path else name
    lowered_name = name.lower()
    existing_names = {
        (entry.split(":", 1)[0].strip().lower() if ":" in entry else entry.strip().lower())
        for entry in entries
    }
    if lowered_name not in existing_names:
        entries.append(new_entry)
        app_config.set_param("settings", "open_with_tools", ",".join(entries))


# Memoization for hot-path reads --------------------------------------------
# The GUI reads the registry once per table row while building the environment
# list (previously N JSON parses + N uv subprocess probes per search keystroke)
# and probes interpreter paths with subprocesses from click handlers on the Tk
# main thread. Small stamp/TTL caches keep those off the hot path; every write
# invalidates so results stay coherent.
_ENV_DATA_LOCK = threading.Lock()
_ENV_DATA_CACHE: dict = {"stamp": object(), "data": {}}

_VERSION_PROBES: dict[str, tuple[float, str | bool]] = {}
_VERSION_PROBE_LOCK = threading.Lock()
_VERSION_PROBE_TTL = 300.0  # seconds


def _env_data_file_stamp():
    """File identity (path, mtime, size, inode) used to invalidate the cache."""
    try:
        st = os.stat(ENV_DATA_FILE)
    except OSError:
        return None
    return (ENV_DATA_FILE, st.st_mtime_ns, st.st_size, st.st_ino)


def _copy_env_data(raw: dict) -> dict:
    # One level deep: entries are flat scalar dicts, and callers mutate them
    # before saving, so the cached original must never be handed out directly.
    return {k: (dict(v) if isinstance(v, dict) else v) for k, v in raw.items()}


def _load_env_data():
    stamp = _env_data_file_stamp()
    if stamp is None:
        return {}
    with _ENV_DATA_LOCK:
        if _ENV_DATA_CACHE["stamp"] == stamp:
            return _copy_env_data(_ENV_DATA_CACHE["data"])
    try:
        raw = json.loads(Path(ENV_DATA_FILE).read_text(encoding="utf-8"))
    except Exception:
        # Don't cache unreadable files: a transient failure must not stick
        # until the next mtime change.
        return {}
    if not isinstance(raw, dict):
        raw = {}
    with _ENV_DATA_LOCK:
        _ENV_DATA_CACHE["stamp"] = stamp
        _ENV_DATA_CACHE["data"] = raw
    return _copy_env_data(raw)


def _save_env_data(data):
    try:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        _write_atomic(Path(ENV_DATA_FILE), payload)
        with _ENV_DATA_LOCK:
            _ENV_DATA_CACHE["stamp"] = object()  # force reload on next read
    except Exception as exc:
        LOGGER.error("Failed to save env data: %s", exc)


def set_env_data(env_name, recent_location=None, size=None, last_scanned=None, python_version=None, package_manager=None, package_update_check_enabled=None):
    data = _load_env_data()
    entry = data.get(env_name, {})

    if recent_location is not None:
        entry["recent_location"] = recent_location
    if size is not None:
        entry["size"] = size
    if last_scanned is not None:
        entry["last_scanned"] = last_scanned
    if python_version is not None:
        entry["python_version"] = python_version
    if package_manager is not None:
        entry["package_manager"] = package_manager
    if package_update_check_enabled is not None:
        entry["package_update_check_enabled"] = package_update_check_enabled is True

    data[env_name] = entry
    _save_env_data(data)


def get_env_data(env_name):
    data = _load_env_data()
    entry = data.get(env_name, {})
    if "package_update_check_enabled" not in entry:
        entry["package_update_check_enabled"] = False
    return entry


def calculate_env_size_mb(env_path):
    # Path.walk (3.12) walks without building path strings up front, and the
    # old os.path.isfile() + getsize() pair stat'ed every file twice; a single
    # entry.stat() now suffices.
    total_size = 0
    for dirpath, _, filenames in Path(env_path).walk(on_error=lambda _err: None):
        for filename in filenames:
            try:
                total_size += (dirpath / filename).stat().st_size
            except OSError:
                pass
    size_mb = total_size // (1024 * 1024)
    return f"{size_mb} MB"


def is_valid_python(python_path):
    return shutil.which(python_path) is not None and "python" in python_path.lower()


def is_valid_python_version_detected(python_path):
    """Run ``<python> --version``, memoized per path for a short TTL.

    Called from click handlers and the configuration dialog on the Tk main
    thread; each probe is a 100-500ms subprocess spawn, so successful answers
    are reused for 5 minutes. Subprocess failures are never cached.
    """
    now = time.monotonic()
    with _VERSION_PROBE_LOCK:
        hit = _VERSION_PROBES.get(python_path)
    if hit is not None and now - hit[0] <= _VERSION_PROBE_TTL:
        return hit[1]
    try:
        output = subprocess.check_output([python_path, "--version"], text=True).strip()
        result = output if output.startswith("Python ") else False
    except Exception:
        return False
    with _VERSION_PROBE_LOCK:
        _VERSION_PROBES[python_path] = (now, result)
    return result


def is_valid_env_selected(env_name):
    if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
        return None
    return True


def get_preferred_package_manager() -> str:
    """Get the user's preferred package manager (pip or uv).
    
    Returns:
        "pip" or "uv", defaults to "pip" if not configured
    """
    try:
        app_config = AppConfig()
        manager = app_config.get_param("settings", "preferred_package_manager", fallback="pip")
        # Only return valid managers
        return "uv" if manager.lower() == "uv" else "pip"
    except Exception:
        return "pip"


def set_preferred_package_manager(manager: str) -> None:
    """Set the user's preferred package manager.
    
    Args:
        manager: "pip" or "uv"
    """
    if manager not in ("pip", "uv"):
        raise ValueError(f"Invalid package manager: {manager}. Must be 'pip' or 'uv'")
    
    try:
        app_config = AppConfig()
        app_config.set_param("settings", "preferred_package_manager", manager)
    except Exception as e:
        LOGGER.error(f"Failed to set preferred package manager: {e}")


def get_package_manager_display(manager: str = None) -> str:
    """Get a display string for the package manager with version.
    
    Args:
        manager: "pip" or "uv", or None to use preferred
    
    Returns:
        Display string like "pip v25.5" or "uv 0.9.0"
    """
    if manager is None:
        manager = get_preferred_package_manager()
    
    # Validate the manager
    if manager not in ("pip", "uv"):
        manager = "pip"
    
    try:
        if manager == "uv":
            from . import uv_tools
            if uv_tools.is_uv_installed():
                version = uv_tools.get_uv_version()
                if version:
                    return f"uv {version}"
            return "pip (uv unavailable)"
        else:
            from . import pip_tools
            version = pip_tools.get_pip_version()
            if version:
                return f"pip {version}"
    except Exception as e:
        LOGGER.warning(f"Error getting package manager version: {e}")
    
    return "pip"


def _is_valid_env_name(name: str) -> bool:
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
    if not name or len(name) > 50 or any(ch not in allowed for ch in name):
        return False
    return True


def create_env(name, python_path=None, upgrade_pip=False, log_callback=None, package_update_check_enabled=False):
    env_path = os.path.join(VENV_DIR, name)
    python_path = python_path or PYTHON_PATH or "python"
    python_version = _extract_python_version(python_path) or "default"
    started_at = time.monotonic()
    
    # Get the preferred package manager at creation time
    package_manager = get_preferred_package_manager()
    use_uv = package_manager == "uv"

    try:
        if log_callback:
            tool_name = "uv" if use_uv else "venv"
            log_callback(
                f"Creating virtual environment '{name}' at {env_path} with Python: {python_version} using {tool_name}"
            )

        os.makedirs(VENV_DIR, exist_ok=True)

        if not _is_valid_env_name(name):
            raise ValueError(
                f"Invalid environment name: {name}. Valid examples are: ('myenv', 'my-env', 'my_env')"
            )

        if os.path.exists(env_path):
            raise FileExistsError(f"Target environment '{name}' already exists")

        # Use uv if selected and available, otherwise fallback to venv
        if use_uv:
            try:
                from . import uv_tools
                if not uv_tools.is_uv_installed():
                    if log_callback:
                        log_callback("uv not installed, falling back to venv")
                    use_uv = False
            except Exception:
                use_uv = False
        
        if use_uv:
            # Create venv using uv
            if log_callback:
                log_callback("Creating virtual environment with uv...")
            # Build uv command with python version if specified
            uv_cmd = ["uv", "venv"]
            if python_path and python_path not in ("python", "python3"):
                # Add python version specification if a custom path was provided
                uv_cmd.extend(["--python", python_path])
            uv_cmd.append(env_path)
            process = subprocess.Popen(
                uv_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in process.stdout:
                if log_callback:
                    log_callback(line.strip())
            process.wait()
            if process.returncode != 0:
                if log_callback:
                    log_callback("uv venv creation failed, falling back to python venv")
                use_uv = False
        
        if not use_uv:
            # Fallback to standard python venv
            if log_callback:
                log_callback("Creating virtual environment with python -m venv...")
            process = subprocess.Popen(
                [python_path, "-m", "venv", env_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in process.stdout:
                if log_callback:
                    log_callback(line.strip())
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args)
            package_manager = "pip"  # If uv failed, we used pip

        venv_python = os.path.join(env_path, "Scripts" if os.name == "nt" else "bin", "python")

        if log_callback:
            log_callback("Ensuring pip is installed")
        process = subprocess.Popen(
            [venv_python, "-m", "ensurepip", "--upgrade", "--default-pip"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in process.stdout:
            if log_callback:
                log_callback(line.strip())
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)

        if upgrade_pip:
            if log_callback:
                log_callback("Upgrading pip")
            process = subprocess.Popen(
                [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in process.stdout:
                if log_callback:
                    log_callback(line.strip())
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args)

        size_mb = calculate_env_size_mb(env_path)
        detected_version = _extract_python_version(venv_python)
        # Store which package manager was actually used to create this environment
        set_env_data(
            name,
            recent_location=env_path,
            size=size_mb,
            python_version=detected_version,
            package_manager=package_manager,
            package_update_check_enabled=package_update_check_enabled,
        )

        LOGGER.info(
            "Created environment at: %s with Python: %s using %s (%.1fs)",
            env_path,
            python_path,
            package_manager,
            time.monotonic() - started_at,
        )
        if log_callback:
            log_callback(f"Environment '{name}' created successfully with {package_manager}")
    except subprocess.CalledProcessError as exc:
        err_msg = f"Failed to create environment '{name}': {exc}"
        LOGGER.error("%s (%.1fs)", err_msg, time.monotonic() - started_at)
        if log_callback:
            log_callback(err_msg)
        raise
    except Exception as exc:
        err_msg = f"Unexpected error creating environment '{name}': {exc}"
        LOGGER.error("%s (%.1fs)", err_msg, time.monotonic() - started_at)
        if log_callback:
            log_callback(err_msg)
        raise


def rename_env(old_name, new_name, log_callback=None):
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

        with open(requirements_file, "w", encoding="utf-8") as handle:
            subprocess.check_call([old_python, "-m", "pip", "freeze"], stdout=handle)

        if log_callback:
            log_callback(f"Preparing environment '{new_name}'")
        create_env(new_name, python_path=PYTHON_PATH, upgrade_pip=False, log_callback=log_callback)

        new_python = get_env_python(new_name)
        if os.path.exists(requirements_file):
            if log_callback:
                log_callback(f"Installing dependencies into '{new_name}'")
            subprocess.check_call([new_python, "-m", "pip", "install", "-r", requirements_file])

        os.remove(requirements_file)

        if log_callback:
            log_callback(f"Deleting old environment '{old_name}'")
        delete_env(old_name, log_callback=log_callback)

        data = _load_env_data()
        if old_name in data:
            data[new_name] = data.pop(old_name)
            _save_env_data(data)

        LOGGER.info("Renamed environment '%s' to '%s'", old_name, new_name)
        if log_callback:
            log_callback(f"Environment renamed from '{old_name}' to '{new_name}' successfully")
    except Exception as exc:
        err_msg = f"Failed to rename environment '{old_name}' to '{new_name}': {exc}"
        LOGGER.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise


def list_envs():
    if not os.path.exists(VENV_DIR):
        return []
    return [
        directory
        for directory in os.listdir(VENV_DIR)
        if os.path.isdir(os.path.join(VENV_DIR, directory))
        and os.path.exists(os.path.join(VENV_DIR, directory, "pyvenv.cfg"))
    ]


def _extract_python_version(python_path):
    detected = is_valid_python_version_detected(python_path)
    if detected:
        return detected.split(" ", 1)[1]
    return None


def list_pythons():
    path_list = set()
    paths = os.environ.get("PATH", "").split(os.pathsep)

    pattern = re.compile(r"^python(\d+(\.\d+)?)?(\.exe)?$", re.IGNORECASE)
    for path in paths:
        if os.path.isdir(path):
            try:
                for filename in os.listdir(path):
                    if pattern.match(filename):
                        full_path = os.path.join(path, filename)
                        if is_valid_python(full_path):
                            path_list.add(full_path)
            except PermissionError:
                pass

    return sorted(path_list)


def delete_env(name, log_callback=None):
    env_path = os.path.join(VENV_DIR, name)
    try:
        if log_callback:
            log_callback(f"Deleting environment '{name}' at {env_path}")
        if os.path.exists(env_path):
            shutil.rmtree(env_path)
            LOGGER.info("Deleted environment: %s", name)

            try:
                from .package_update_monitor import PackageUpdateMonitor

                PackageUpdateMonitor().invalidate_cache(name)
            except Exception as exc:
                LOGGER.warning("Could not invalidate package-update cache for '%s': %s", name, exc)

            data = _load_env_data()
            if name in data:
                del data[name]
                _save_env_data(data)

        if log_callback:
            log_callback(f"Environment '{name}' deleted successfully")
    except Exception as exc:
        err_msg = f"Failed to delete environment '{name}': {exc}"
        LOGGER.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise


def get_env_python(env_name):
    executable = "python.exe" if os.name == "nt" else "python"
    return os.path.join(VENV_DIR, env_name, "Scripts" if os.name == "nt" else "bin", executable)


def activate_env(env_name, directory=None, open_with="vscode", open_in_venv_cwd=False, log_callback=None):
    venv_dir = os.path.join(VENV_DIR, env_name)
    target_dir = directory or os.getcwd()

    set_env_data(env_name, recent_location=target_dir)

    if not Path(venv_dir).exists():
        raise FileNotFoundError(f"Environment '{env_name}' not found at {venv_dir}")

    tools = detect_tools()
    tool_entry = next((tool for tool in tools if tool["name"].lower() == open_with.lower()), None)
    if not tool_entry:
        raise RuntimeError(f"Tool '{open_with}' not found on system")

    LOGGER.info(
        "Activating environment '%s' with %s (target=%s)",
        env_name,
        open_with,
        target_dir,
    )
    return run_strategy(
        tool_entry["strategy"],
        tool_entry["path"],
        venv_dir,
        target_dir,
        open_in_venv_cwd=open_in_venv_cwd,
        log_callback=log_callback,
    )


def is_exact_env_active(python_exe_path):
    return os.path.abspath(sys.executable).lower() == os.path.abspath(python_exe_path).lower()


def get_environment_info(env_name):
    """Public read-only summary of a single environment for API consumers.

    Used by the MCP control plane (and future LSP layer) so tool handlers
    do not duplicate discovery logic. Returns None when the environment
    does not exist.
    """
    env_path = os.path.join(VENV_DIR, env_name)
    if not os.path.isdir(env_path):
        return None
    if not os.path.exists(os.path.join(env_path, "pyvenv.cfg")):
        return None
    python_exe = get_env_python(env_name)
    data = get_env_data(env_name)
    return {
        "environment_id": env_name,
        "name": env_name,
        "path": env_path,
        "python_executable": python_exe,
        "python_version": data.get("python_version") or _extract_python_version(python_exe),
        "package_manager": data.get("package_manager") or get_preferred_package_manager(),
        "status": "exists",
        "metadata": data,
    }
