"""Runtime paths and configuration resolution for Py Env Studio."""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from platformdirs import PlatformDirs

from .configuration import APP_AUTHOR, APP_NAME


@dataclass(frozen=True)
class RuntimeConfig:
    app_name: str
    app_version: str
    user_data_dir: Path
    state_dir: Path
    data_dir: Path
    log_dir: Path
    venv_dir: Path
    db_path: Path
    matrix_path: Path
    log_path: Path
    python_path: str | None
    legacy_db_path: Path


def _load_package_config() -> ConfigParser:
    parser = ConfigParser(interpolation=None)
    config_path = Path(__file__).resolve().parents[1] / "config.ini"
    parser.read(config_path, encoding="utf-8")
    return parser


def _load_user_config(user_data_dir: Path) -> ConfigParser:
    parser = ConfigParser(interpolation=None)
    parser.read(user_data_dir / "config.ini", encoding="utf-8")
    return parser


def _resolve_data_path(value: str | None, default_name: str, user_data_dir: Path) -> Path:
    if value:
        configured = Path(value).expanduser()
        if configured.is_absolute():
            return configured
        return (user_data_dir / configured).resolve()
    return (user_data_dir / default_name).resolve()


@lru_cache(maxsize=1)
def get_runtime_config() -> RuntimeConfig:
    parser = _load_package_config()
    dirs = PlatformDirs(APP_NAME, appauthor=APP_AUTHOR)

    user_data_dir = Path(dirs.user_data_dir).resolve()
    user_parser = _load_user_config(user_data_dir)
    state_dir = user_data_dir / "state"
    data_dir = user_data_dir / "data"
    log_dir = user_data_dir / "logs"

    app_version = parser.get("project", "version", fallback="stable")
    python_path = user_parser.get(
        "settings",
        "python_path",
        fallback=parser.get("settings", "python_path", fallback=None),
    )

    configured_venv = user_parser.get(
        "settings", "venv_dir", fallback=parser.get("settings", "venv_dir", fallback=None)
    )
    configured_db = user_parser.get(
        "settings", "db_file", fallback=parser.get("settings", "db_file", fallback=None)
    )
    configured_matrix = user_parser.get(
        "settings", "matrix_file", fallback=parser.get("settings", "matrix_file", fallback=None)
    )
    configured_log = user_parser.get(
        "settings", "log_file", fallback=parser.get("settings", "log_file", fallback=None)
    )

    venv_dir = _resolve_data_path(configured_venv, "venvs", user_data_dir)
    db_path = _resolve_data_path(configured_db, "py_env_studio.db", user_data_dir)
    matrix_path = _resolve_data_path(configured_matrix, "security_matrix_lts.json", user_data_dir)
    log_path = _resolve_data_path(configured_log, "py_env_studio.log", user_data_dir)

    package_root = Path(__file__).resolve().parents[1]
    legacy_db_path = (package_root / (configured_db or "data/py_env_studio.db")).resolve()

    for path in (user_data_dir, state_dir, data_dir, log_dir, venv_dir):
        path.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    return RuntimeConfig(
        app_name=APP_NAME,
        app_version=app_version,
        user_data_dir=user_data_dir,
        state_dir=state_dir,
        data_dir=data_dir,
        log_dir=log_dir,
        venv_dir=venv_dir,
        db_path=db_path,
        matrix_path=matrix_path,
        log_path=log_path,
        python_path=python_path,
        legacy_db_path=legacy_db_path,
    )


def refresh_runtime_config() -> RuntimeConfig:
    """Clear runtime cache and return a fresh configuration snapshot."""
    get_runtime_config.cache_clear()
    return get_runtime_config()
