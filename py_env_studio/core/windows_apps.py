"""Windows Start Menu integration for showing Py Env Studio in Apps."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from py_env_studio.utils.app_icon import get_app_icon_path

LOGGER = logging.getLogger(__name__)


def _resolve_python_gui_executable() -> Path:
    executable = Path(sys.executable).resolve()
    if executable.name.lower() == "python.exe":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.exists():
            return pythonw
    return executable


def _resolve_icon_path() -> Path | None:
    """Return the shared Py Env Studio icon used for the Start Menu shortcut."""
    return get_app_icon_path()


def _get_start_menu_shortcut_path() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    programs_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return programs_dir / "Py Env Studio.lnk"


def ensure_windows_apps_shortcut() -> None:
    """Create/update Start Menu shortcut so the app appears in Windows Apps."""
    if os.name != "nt":
        return

    shortcut_path = _get_start_menu_shortcut_path()
    if shortcut_path is None:
        return

    target = _resolve_python_gui_executable()
    icon_path = _resolve_icon_path()

    shortcut_path.parent.mkdir(parents=True, exist_ok=True)

    # Use PowerShell + WScript.Shell COM to create a .lnk without extra deps.
    icon_location = str(icon_path) if icon_path else str(target)
    escaped_shortcut = str(shortcut_path).replace("'", "''")
    escaped_target = str(target).replace("'", "''")
    escaped_workdir = str(Path.home()).replace("'", "''")
    escaped_icon = icon_location.replace("'", "''")
    ps_command = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{escaped_shortcut}'); "
        f"$shortcut.TargetPath = '{escaped_target}'; "
        "$shortcut.Arguments = '-m py_env_studio --gui'; "
        f"$shortcut.WorkingDirectory = '{escaped_workdir}'; "
        f"$shortcut.IconLocation = '{escaped_icon},0'; "
        "$shortcut.Description = 'Py Env Studio'; "
        "$shortcut.Save();"
    )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            LOGGER.warning(
                "Windows Apps shortcut command failed (code=%s): %s",
                result.returncode,
                (result.stderr or "").strip(),
            )
    except Exception as exc:
        LOGGER.warning("Failed to create Windows Apps shortcut: %s", exc)
