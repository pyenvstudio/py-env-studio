"""Check and apply Py Env Studio package updates."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

import requests
from packaging.version import InvalidVersion, Version

from .runtime import get_runtime_config

logger = logging.getLogger(__name__)

PACKAGE_NAME = "py-env-studio"
PYPI_JSON_URL = "https://pypi.org/pypi/py-env-studio/json"
RELEASES_URL = "https://github.com/pyenvstudio/py-env-studio/releases/latest"


@dataclass(frozen=True)
class AppUpdateStatus:
    current_version: str
    latest_version: str
    update_available: bool


def get_installed_app_version() -> str:
    """Return the installed distribution version, falling back to package config."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        configured_version = get_runtime_config().app_version
        return configured_version if configured_version != "stable" else "Unknown"


def check_for_app_update(current_version: str | None = None) -> AppUpdateStatus:
    """Fetch PyPI's latest release metadata and compare it with this install."""
    current = current_version or get_installed_app_version()
    response = requests.get(
        PYPI_JSON_URL,
        headers={"Accept": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    try:
        latest = str(response.json()["info"]["version"])
        update_available = Version(latest) > Version(current)
    except (KeyError, TypeError, InvalidVersion) as exc:
        raise RuntimeError("PyPI returned invalid Py Env Studio version metadata") from exc
    return AppUpdateStatus(current, latest, update_available)


def is_frozen_build() -> bool:
    """Whether this process is running from a bundled executable."""
    return bool(getattr(sys, "frozen", False))


def install_app_update(target_version: str) -> None:
    """Upgrade this interpreter's Py Env Studio distribution through pip."""
    try:
        Version(target_version)
    except InvalidVersion as exc:
        raise ValueError(f"Invalid Py Env Studio version: {target_version}") from exc
    if is_frozen_build():
        raise RuntimeError("Bundled builds must be updated from the release download page")

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        f"{PACKAGE_NAME}=={target_version}",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "pip exited with an error").strip()
        raise RuntimeError(f"pip could not install Py Env Studio {target_version}: {details}")
    logger.info("Installed Py Env Studio %s", target_version)


def restart_app() -> subprocess.Popen:
    """Start a fresh GUI process using the same Python interpreter."""
    command = [sys.executable, "-m", "py_env_studio"]
    options = {"close_fds": True}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        options["start_new_session"] = True
    return subprocess.Popen(command, **options)