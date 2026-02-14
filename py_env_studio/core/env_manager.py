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
from pathlib import Path

from .configuration import AppConfig
from .integration import detect_tools
from .runtime import get_runtime_config
from .strategies import run_strategy

runtime = get_runtime_config()

VENV_DIR = str(runtime.venv_dir)
PYTHON_PATH = runtime.python_path
LOG_FILE = str(runtime.log_path)
DB_FILE = str(runtime.db_path)
MATRIX_FILE = str(runtime.matrix_path)
ENV_DATA_FILE = str(runtime.venv_dir / "env_data.json")

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


def _load_env_data():
    path = Path(ENV_DATA_FILE)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_env_data(data):
    try:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        _write_atomic(Path(ENV_DATA_FILE), payload)
    except Exception as exc:
        logging.error("Failed to save env data: %s", exc)


def set_env_data(env_name, recent_location=None, size=None, last_scanned=None, python_version=None):
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

    data[env_name] = entry
    _save_env_data(data)


def get_env_data(env_name):
    data = _load_env_data()
    return data.get(env_name, {})


def calculate_env_size_mb(env_path):
    total_size = 0
    for dirpath, _, filenames in os.walk(env_path):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            if os.path.isfile(full_path):
                total_size += os.path.getsize(full_path)
    size_mb = total_size // (1024 * 1024)
    return f"{size_mb} MB"


def is_valid_python(python_path):
    return shutil.which(python_path) is not None and "python" in python_path.lower()


def is_valid_python_version_detected(python_path):
    try:
        output = subprocess.check_output([python_path, "--version"], text=True).strip()
        return output if output.startswith("Python ") else False
    except Exception:
        return False


def is_valid_env_selected(env_name):
    if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
        return None
    return True


def _is_valid_env_name(name: str) -> bool:
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
    if not name or len(name) > 50 or any(ch not in allowed for ch in name):
        return False
    return True


def create_env(name, python_path=None, upgrade_pip=False, log_callback=None):
    env_path = os.path.join(VENV_DIR, name)
    python_path = python_path or PYTHON_PATH or "python"
    python_version = _extract_python_version(python_path) or "default"

    try:
        if log_callback:
            log_callback(
                f"Creating virtual environment '{name}' at {env_path} with Python: {python_version}"
            )

        os.makedirs(VENV_DIR, exist_ok=True)

        if not _is_valid_env_name(name):
            raise ValueError(
                f"Invalid environment name: {name}. Valid examples are: ('myenv', 'my-env', 'my_env')"
            )

        if os.path.exists(env_path):
            raise FileExistsError(f"Target environment '{name}' already exists")

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
        set_env_data(name, recent_location=env_path, size=size_mb, python_version=detected_version)

        logging.info("Created environment at: %s with Python: %s", env_path, python_path)
        if log_callback:
            log_callback(f"Environment '{name}' created successfully")
    except subprocess.CalledProcessError as exc:
        err_msg = f"Failed to create environment '{name}': {exc}"
        logging.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise
    except Exception as exc:
        err_msg = f"Unexpected error creating environment '{name}': {exc}"
        logging.error(err_msg)
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

        if log_callback:
            log_callback(f"Environment renamed from '{old_name}' to '{new_name}' successfully")
    except Exception as exc:
        err_msg = f"Failed to rename environment '{old_name}' to '{new_name}': {exc}"
        logging.error(err_msg)
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
    try:
        output = subprocess.check_output([python_path, "--version"], text=True).strip()
        if output.startswith("Python "):
            return output.split()[1]
    except Exception:
        return None
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
            logging.info("Deleted environment: %s", name)

            data = _load_env_data()
            if name in data:
                del data[name]
                _save_env_data(data)

        if log_callback:
            log_callback(f"Environment '{name}' deleted successfully")
    except Exception as exc:
        err_msg = f"Failed to delete environment '{name}': {exc}"
        logging.error(err_msg)
        if log_callback:
            log_callback(err_msg)
        raise


def get_env_python(env_name):
    return os.path.join(VENV_DIR, env_name, "Scripts" if os.name == "nt" else "bin", "python")


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
