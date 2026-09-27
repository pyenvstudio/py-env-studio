import os
from pathlib import Path

import pytest

from py_env_studio.core import project_launcher
from py_env_studio.core.project_launcher import (
    discover_project_open_tools,
    find_tool_by_id,
    open_project_with_tool,
)


def test_discover_tools_reuses_open_with_and_detected(monkeypatch, tmp_path: Path) -> None:
    custom_tool_path = tmp_path / "mytool.exe"
    custom_tool_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        project_launcher,
        "get_available_tools",
        lambda: [
            {"name": "CMD", "path": None},
            {"name": "VSCode", "path": None},
            {"name": "MyTool", "path": str(custom_tool_path)},
        ],
    )
    monkeypatch.setattr(
        project_launcher,
        "detect_tools",
        lambda: [
            {"name": "vscode", "path": "C:/bin/code.cmd", "strategy": "venv_injection"},
            {"name": "cmd", "path": "C:/Windows/System32/cmd.exe", "strategy": "shell_activation"},
        ],
    )
    tools = discover_project_open_tools(["CMD", "VSCode", "MyTool", "Add Tool..."], include_default=True)
    ids = [tool["tool_id"] for tool in tools]
    assert ids[:3] == ["cmd", "vscode", "mytool"]
    assert ids[-1] == "default"


def test_find_tool_by_id() -> None:
    tools = [{"tool_id": "vscode", "display_name": "Visual Studio Code", "path": "code"}]
    assert find_tool_by_id("vscode", tools)["display_name"] == "Visual Studio Code"
    assert find_tool_by_id("missing", tools) is None


def test_open_project_passes_project_path(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_popen(args, *_, **__):
        calls.append(args)

    monkeypatch.setattr(project_launcher.subprocess, "Popen", fake_popen)

    project_dir = tmp_path / "my-cli"
    project_dir.mkdir()
    tool = {"tool_id": "vscode", "display_name": "Visual Studio Code", "path": "C:/Tools/code.cmd"}

    open_project_with_tool(tool, project_dir)
    assert calls
    assert os.path.normcase(os.path.normpath(calls[0][0])) == os.path.normcase(os.path.normpath("C:/Tools/code.cmd"))
    assert calls[0][1] == str(project_dir.resolve())


def test_open_project_unavailable_tool_rejected(tmp_path: Path) -> None:
    project_dir = tmp_path / "my-cli"
    project_dir.mkdir()
    tool = {"tool_id": "vscode", "display_name": "Visual Studio Code", "path": None}

    with pytest.raises(RuntimeError):
        open_project_with_tool(tool, project_dir)


def test_open_project_failure_handled(monkeypatch, tmp_path: Path) -> None:
    def fake_popen(*_, **__):
        raise OSError("launch error")

    monkeypatch.setattr(project_launcher.subprocess, "Popen", fake_popen)

    project_dir = tmp_path / "my-cli"
    project_dir.mkdir()
    tool = {"tool_id": "vscode", "display_name": "Visual Studio Code", "path": "C:/Tools/code.cmd"}

    with pytest.raises(OSError):
        open_project_with_tool(tool, project_dir)
