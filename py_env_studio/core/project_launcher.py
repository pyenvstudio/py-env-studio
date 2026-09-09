"""Open project directories using existing open_with tool configuration."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .env_manager import get_available_tools
from .integration import detect_tools


DISPLAY_NAMES = {
    "vscode": "Visual Studio Code",
    "pycharm": "PyCharm",
    "cursor": "Cursor",
    "sublime": "Sublime Text",
    "positron": "Positron",
    "cmd": "Command Prompt",
    "powershell": "PowerShell",
    "terminal": "Terminal",
    "default": "Default Application",
}


def _normalize(name: str) -> str:
    return name.strip().lower()


def discover_project_open_tools(open_with_names: list[str], include_default: bool = True) -> list[dict]:
    """Return available project open tools based on existing open_with config + detection."""
    configured = get_available_tools()
    detected = detect_tools()
    configured_by_name = {_normalize(item["name"]): item for item in configured}
    detected_by_name = {_normalize(item["name"]): item for item in detected}

    tools: list[dict] = []
    seen: set[str] = set()

    for name in open_with_names:
        if name == "Add Tool...":
            continue
        tool_id = _normalize(name)
        if not tool_id or tool_id in seen:
            continue

        tool = None
        if tool_id in detected_by_name:
            detected_item = detected_by_name[tool_id]
            tool = {
                "tool_id": tool_id,
                "display_name": DISPLAY_NAMES.get(tool_id, detected_item["name"]),
                "path": detected_item["path"],
            }
        else:
            configured_item = configured_by_name.get(tool_id)
            if configured_item and configured_item.get("path"):
                path = Path(configured_item["path"])
                if path.exists():
                    tool = {
                        "tool_id": tool_id,
                        "display_name": DISPLAY_NAMES.get(tool_id, configured_item["name"]),
                        "path": str(path),
                    }

        if tool is not None:
            seen.add(tool_id)
            tools.append(tool)

    if include_default:
        tools.append(
            {
                "tool_id": "default",
                "display_name": DISPLAY_NAMES["default"],
                "path": None,
            }
        )

    return tools


def find_tool_by_id(tool_id: str, tools: list[dict]) -> dict | None:
    for tool in tools:
        if tool.get("tool_id") == tool_id:
            return tool
    return None


def open_project_with_tool(tool: dict, project_path: Path) -> None:
    """Open a project directory using a discovered tool."""
    target = project_path.expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise RuntimeError(f"Project path does not exist: {target}")

    tool_id = tool.get("tool_id", "")
    executable = tool.get("path")

    if tool_id == "default":
        if os.name == "nt":
            os.startfile(str(target))
        elif os.sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return

    if not executable:
        raise RuntimeError(f"Tool is unavailable: {tool.get('display_name', tool_id)}")

    if tool_id == "cmd":
        subprocess.Popen([executable, "/K", f'cd /d "{target}"'])
        return
    if tool_id == "powershell":
        subprocess.Popen([executable, "-NoExit", "-Command", f'Set-Location "{target}"'])
        return

    subprocess.Popen([executable, str(target)])
