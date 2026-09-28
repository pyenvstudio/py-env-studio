"""Tests for the PES MCP control plane (Phase 1: read-only)."""

from __future__ import annotations

import io
import json

import pytest

from py_env_studio.core.mcp import READ_ONLY_TOOL_NAMES, create_server
from py_env_studio.core.mcp.tools import TOOL_DEFINITIONS


@pytest.fixture()
def server():
    return create_server("test-pes")


def _call(server, tool, arguments=None, msg_id=1):
    return server.handle_message(
        {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
         "params": {"name": tool, "arguments": arguments or {}}}
    )


def _envelope(response):
    assert response["jsonrpc"] == "2.0"
    return response["result"]["structuredContent"]


# -- server ---------------------------------------------------------------

def test_initialize_and_tools_registered(server):
    init = server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert init["result"]["capabilities"] == {"tools": {}}
    assert init["result"]["serverInfo"]["name"] == "test-pes"

    listed = server.handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    names = [t["name"] for t in listed["result"]["tools"]]
    assert names == list(READ_ONLY_TOOL_NAMES)
    assert set(names) == {
        "pyenv_list_environments",
        "pyenv_get_environment",
        "pyenv_list_packages",
        "pyenv_get_project_context",
        "pyenv_get_environment_status",
        "pyenv_scan_vulnerabilities",
        "pyenv_get_dependency_information",
        "pyenv_analyze_project",
        "pyenv_check_consistency",
    }


def test_malformed_and_unknown_tool(server):
    assert server.handle_message(["not", "a", "dict"])["error"]["code"] == -32600
    assert server.handle_message({"nope": True})["error"]["code"] == -32601
    unknown = _call(server, "no_such_tool")
    assert unknown["error"]["code"] == -32601
    missing = _call(server, "pyenv_get_environment", {})
    assert _envelope(missing)["success"] is False
    assert _envelope(missing)["error"]["code"] == "INVALID_INPUT"


def test_notifications_have_no_response(server):
    assert server.handle_message(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    ) is None
    assert _call(server, "pyenv_list_packages") is not None
    ping = server.handle_message({"jsonrpc": "2.0", "id": 9, "method": "ping", "params": {}})
    assert ping["result"] == {}


# -- environment tools ----------------------------------------------------

def test_list_and_get_environment(server, monkeypatch):
    from py_env_studio.core import env_manager

    monkeypatch.setattr(env_manager, "list_envs", lambda: ["demo"])
    monkeypatch.setattr(
        env_manager,
        "get_environment_info",
        lambda name: {
            "environment_id": name, "name": name, "path": "/venvs/demo",
            "python_executable": "/venvs/demo/bin/python",
            "python_version": "3.12.1", "package_manager": "pip",
            "status": "exists", "metadata": {},
        } if name == "demo" else None,
    )
    env = _envelope(_call(server, "pyenv_list_environments"))
    assert env["success"] is True
    assert env["data"]["count"] == 1
    assert env["data"]["environments"][0]["python_version"] == "3.12.1"

    one = _envelope(_call(server, "pyenv_get_environment", {"environment_id": "demo"}))
    assert one["success"] is True
    assert one["data"]["environment"]["name"] == "demo"

    missing = _envelope(_call(server, "pyenv_get_environment", {"environment_id": "ghost"}))
    assert missing["success"] is False
    assert missing["error"]["code"] == "ENVIRONMENT_NOT_FOUND"


def test_environment_status(server, monkeypatch, tmp_path):
    from py_env_studio.core import env_manager, package_manager

    env_dir = tmp_path / "demo"
    env_dir.mkdir()
    (env_dir / "pyvenv.cfg").write_text("home = /tmp\n")
    python_exe = env_dir / "bin" / "python"
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    python_exe.write_text("#!/bin/sh\n")

    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: {
            "environment_id": "demo", "name": "demo", "path": str(env_dir),
            "python_executable": str(python_exe), "python_version": "3.12",
            "package_manager": "uv", "status": "exists", "metadata": {},
        },
    )
    monkeypatch.setattr(package_manager, "list_packages", lambda name: [("a", "1.0")] * 3)
    status = _envelope(_call(server, "pyenv_get_environment_status", {"environment_id": "demo"}))
    assert status["success"] is True
    assert status["data"]["exists"] is True
    assert status["data"]["python_available"] is True
    assert status["data"]["package_count"] == 3
    assert status["data"]["package_manager"] == "uv"


# -- package tools --------------------------------------------------------

def test_list_packages_and_missing_env(server, monkeypatch):
    from py_env_studio.core import env_manager, package_manager

    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: {"environment_id": name, "name": name, "path": "/x",
                      "python_executable": "/x/bin/python", "python_version": "3.12",
                      "package_manager": "pip", "status": "exists", "metadata": {}}
        if name == "demo" else None,
    )
    monkeypatch.setattr(
        package_manager, "list_packages", lambda name: [("numpy", "1.26.0")]
    )
    monkeypatch.setattr(package_manager, "get_env_package_manager", lambda name: "pip")
    ok = _envelope(_call(server, "pyenv_list_packages", {"environment_id": "demo"}))
    assert ok["success"] is True
    assert ok["data"]["packages"] == [{"name": "numpy", "version": "1.26.0"}]

    missing = _envelope(_call(server, "pyenv_list_packages", {"environment_id": "ghost"}))
    assert missing["error"]["code"] == "ENVIRONMENT_NOT_FOUND"


# -- project context ------------------------------------------------------

def test_project_context_with_and_without_environment(server, monkeypatch, tmp_path):
    from py_env_studio.core import env_manager, package_manager, runtime_toggle

    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(runtime_toggle, "get_project_root", lambda start=None: root)
    monkeypatch.setattr(
        runtime_toggle, "load_project_metadata",
        lambda r: {"project_name": "proj", "environment_id": "demo",
                   "environment_path": "/venvs/demo", "python_version": "3.12",
                   "package_manager": "pip", "runtime_enabled": True},
    )
    monkeypatch.setattr(
        runtime_toggle, "get_project_status",
        lambda r=None: {"initialized": True, "project_root": str(root),
                        "project_name": "proj", "runtime_enabled": True,
                        "environment_id": "demo", "environment_exists": True,
                        "environment_path": "/venvs/demo", "python_version": "3.12"},
    )
    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: {"environment_id": "demo", "name": "demo", "path": "/venvs/demo",
                      "python_executable": "/venvs/demo/bin/python",
                      "python_version": "3.12.0", "package_manager": "pip",
                      "status": "exists", "metadata": {}},
    )
    monkeypatch.setattr(package_manager, "list_packages", lambda name: [("a", "1")])
    ctx = _envelope(_call(server, "pyenv_get_project_context", {"project_path": str(root)}))
    assert ctx["success"] is True
    assert ctx["data"]["project"]["name"] == "proj"
    assert ctx["data"]["environment"]["python_version"] == "3.12.0"
    assert ctx["data"]["runtime"]["status"] == "on"
    assert ctx["data"]["packages"]["installed_count"] == 1


def test_project_context_uninitialized(server, monkeypatch):
    from py_env_studio.core import runtime_toggle

    monkeypatch.setattr(
        runtime_toggle, "get_project_status",
        lambda r=None: {"initialized": False, "project_root": "/tmp/x",
                        "runtime_enabled": False},
    )
    ctx = _envelope(_call(server, "pyenv_get_project_context", {}))
    assert ctx["success"] is True
    assert ctx["data"]["environment"] is None
    assert ctx["data"]["runtime"]["managed"] is False


def test_project_context_missing_path(server):
    env = _envelope(
        _call(server, "pyenv_get_project_context", {"project_path": "/no/such/dir-xyz"})
    )
    assert env["success"] is False
    assert env["error"]["code"] == "PROJECT_NOT_FOUND"


def test_ambiguity_helper_reports_instead_of_guessing():
    from py_env_studio.core.mcp.context import detect_ambiguity
    from py_env_studio.core.mcp.errors import McpError

    with pytest.raises(McpError) as exc_info:
        detect_ambiguity(["/a", "/b"])
    assert exc_info.value.code == "AMBIGUOUS_PROJECT"


# -- security -------------------------------------------------------------

def test_vulnerability_scan_cached_and_empty(server, monkeypatch):
    from py_env_studio.core import env_manager
    from py_env_studio.utils import handlers

    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: {"environment_id": name, "name": name, "path": "/v",
                      "python_executable": "/v/bin/python", "python_version": "3.12",
                      "package_manager": "pip", "status": "exists", "metadata": {}},
    )
    payload = {"vulnerability_insights": {"metadata": {"package": "django", "version": "2.1.2"},
                                          "developer_view": [{
                                              "vulnerability_id": "GHSA-x",
                                              "summary": "s", "affected_components": ["django"],
                                              "severity": {"level": "High", "score": "CVSS:3.1/AV:N"},
                                              "fixed_versions": ["2.2.0"],
                                              "remediation_steps": "Upgrade to 2.2.0",
                                              "status": "not fixed", "references": []}]}}
    monkeypatch.setattr(handlers.DBHelper, "get_vulnerability_info", staticmethod(lambda env: payload))
    ok = _envelope(_call(server, "pyenv_scan_vulnerabilities", {"environment_id": "demo"}))
    assert ok["success"] is True
    assert ok["data"]["count"] == 1
    assert ok["data"]["findings"][0]["vulnerability_id"] == "GHSA-x"
    assert ok["metadata"]["cached"] is True

    monkeypatch.setattr(
        handlers.DBHelper, "get_vulnerability_info",
        staticmethod(lambda env: {"vulnerability_insights": []}),
    )
    empty = _envelope(_call(server, "pyenv_scan_vulnerabilities", {"environment_id": "demo"}))
    assert empty["success"] is True
    assert empty["data"]["scan_available"] is False


def test_vulnerability_scan_does_not_touch_network(server, monkeypatch):
    """MCP must read the SQLite cache only — no requests/OSV/PyPI calls."""
    import py_env_studio.utils.vulneribility_scanner as scanner
    from py_env_studio.core import env_manager
    from py_env_studio.utils import handlers

    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: {"environment_id": name, "name": name, "path": "/v",
                      "python_executable": "/v/bin/python", "python_version": "3.12",
                      "package_manager": "pip", "status": "exists", "metadata": {}},
    )
    monkeypatch.setattr(
        handlers.DBHelper, "get_vulnerability_info",
        staticmethod(lambda env: {"vulnerability_insights": []}),
    )
    for attr in ("PyPIAPI", "OSVAPI", "DepsDevAPI", "SecurityMatrix"):
        monkeypatch.setattr(scanner, attr, None)
    # requests must never be exercised; fail loudly if it is.
    import requests

    def _boom(*args, **kwargs):
        raise AssertionError("MCP performed a network request")

    monkeypatch.setattr(requests, "get", _boom)
    monkeypatch.setattr(requests, "post", _boom)
    env = _envelope(_call(server, "pyenv_scan_vulnerabilities", {"environment_id": "demo"}))
    assert env["success"] is True


# -- dependencies ---------------------------------------------------------

def test_dependency_information_local_only(server, monkeypatch):
    from py_env_studio.core import dependency_preview, env_manager

    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: {"environment_id": name, "name": name, "path": "/v",
                      "python_executable": "/v/bin/python", "python_version": "3.12",
                      "package_manager": "pip", "status": "exists", "metadata": {}},
    )
    monkeypatch.setattr(env_manager, "get_env_python", lambda name: "/v/bin/python")
    monkeypatch.setattr(
        dependency_preview, "get_installed_packages",
        lambda name: {"flask": "3.0.0", "requests": "2.31.0"},
    )
    monkeypatch.setattr(
        dependency_preview, "get_package_dependencies",
        lambda python, pkg: {"click": "click>=8"} if pkg == "flask" else {},
    )
    info = _envelope(_call(server, "pyenv_get_dependency_information",
                            {"environment_id": "demo"}))
    assert info["success"] is True
    assert info["data"]["count"] == 2


# -- safety ---------------------------------------------------------------

def test_phase1_exposes_no_mutation_or_shell():
    names = [entry["name"] for entry in TOOL_DEFINITIONS]
    forbidden = ("install", "uninstall", "delete", "create", "remove", "update",
                 "execute", "shell", "run", "exec", "write", "rollback",
                 "snapshot", "enable", "disable")
    for name in names:
        lowered = name.lower()
        assert not any(token in lowered for token in forbidden), name
    handlers_src = " ".join(
        entry["handler"].__module__ + "." + entry["handler"].__name__ for entry in TOOL_DEFINITIONS
    )
    assert "subprocess" not in handlers_src
    assert "os.system" not in handlers_src


def test_stdio_roundtrip_never_logs_to_stdout(server, monkeypatch):
    from py_env_studio.core import env_manager

    monkeypatch.setattr(env_manager, "list_envs", lambda: [])
    monkeypatch.setattr(env_manager, "get_environment_info", lambda name: None)
    stdin = io.StringIO(
        '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}\n'
        '{"jsonrpc": "2.0", "id": 2, "method": "tools/call",'
        ' "params": {"name": "pyenv_list_environments", "arguments": {}}}\n'
    )
    stdout = io.StringIO()
    server.serve_stdio(stdin=stdin, stdout=stdout)
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # every stdout line must be protocol JSON
