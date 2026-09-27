"""Focused tests for pyenv_check_consistency (probe stub, read-only, offline).

The tool must reuse the existing ProjectAnalysis (no new subsystem, no new
SQL, no network, no mutation) and must never invent a consistency verdict.
Service seams (runtime_toggle, env_manager, package_manager,
dependency_preview, handlers.DBHelper) are stubbed so no real environments,
subprocesses, or network access occur.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from py_env_studio.core.mcp import READ_ONLY_TOOL_NAMES, create_server
from py_env_studio.core.project_intelligence import analyze_project

TOOL = "pyenv_check_consistency"

DESCRIPTION = (
    "Before modifying any Python project's dependencies or running its tests, "
    "call this to determine which interpreter, environment, lockfile, and "
    "manifest the project actually uses, and whether they agree."
)

STATUS = {
    "initialized": True,
    "project_root": None,  # filled per-test
    "project_name": "my-api",
    "runtime_enabled": True,
    "environment_id": "my-api-env",
    "environment_exists": True,
    "environment_path": None,  # filled per-test
    "python_version": "3.12",
}

METADATA = {
    "project_name": "my-api",
    "project_root": None,  # filled per-test
    "environment_id": "my-api-env",
    "environment_path": None,  # filled per-test
    "python_version": "3.12",
    "package_manager": "pip",
    "runtime_enabled": True,
    "auto_init": True,
}

ENV_INFO = {
    "environment_id": "my-api-env",
    "name": "my-api-env",
    "path": None,  # filled per-test
    "python_executable": None,  # filled per-test
    "python_version": "3.12.8",
    "package_manager": "pip",
    "status": "exists",
    "metadata": {"size": "120 MB", "last_scanned": "2026-01-01T00:00:00"},
}


@pytest.fixture()
def project_dir(tmp_path):
    root = tmp_path / "my-api"
    root.mkdir()
    return root


@pytest.fixture()
def wired(monkeypatch, project_dir):
    """A managed PES project with an environment and two installed packages."""
    from py_env_studio.core import (
        dependency_preview,
        env_manager,
        package_manager,
        runtime_toggle,
    )
    from py_env_studio.utils import handlers

    status = dict(STATUS, project_root=str(project_dir),
                  environment_path=str(project_dir / ".venv"))
    metadata = dict(METADATA, project_root=str(project_dir),
                    environment_path=str(project_dir / ".venv"))
    env_info = dict(ENV_INFO, path=str(project_dir / ".venv"),
                    python_executable=str(project_dir / ".venv" / "python"))

    monkeypatch.setattr(runtime_toggle, "get_project_root", lambda start=None: project_dir)
    monkeypatch.setattr(runtime_toggle, "get_project_status", lambda r=None: dict(status))
    monkeypatch.setattr(runtime_toggle, "load_project_metadata", lambda r: dict(metadata))
    monkeypatch.setattr(env_manager, "get_environment_info",
                        lambda name: dict(env_info) if name == "my-api-env" else None)
    monkeypatch.setattr(env_manager, "get_env_python",
                        lambda name: str(project_dir / ".venv" / "python"))
    monkeypatch.setattr(package_manager, "list_packages",
                        lambda name: [("flask", "3.0.0"), ("click", "8.1.0")])
    monkeypatch.setattr(package_manager, "get_env_package_manager", lambda name: "pip")
    monkeypatch.setattr(
        dependency_preview, "get_package_dependencies",
        lambda python, pkg: {"click": "click>=8.0"} if pkg == "flask" else {},
    )
    monkeypatch.setattr(
        package_manager, "check_outdated_packages",
        lambda name: json.dumps([{"name": "click", "version": "8.1.0",
                                  "latest_version": "8.2.0"}]),
    )
    monkeypatch.setattr(
        handlers.DBHelper, "get_vulnerability_info",
        staticmethod(lambda env: {"vulnerability_insights": []}),
    )
    return {"status": status, "metadata": metadata, "env_info": env_info}


@pytest.fixture()
def unmanaged(monkeypatch, project_dir):
    """A real directory that PES does not manage (no environment at all)."""
    from py_env_studio.core import runtime_toggle

    monkeypatch.setattr(runtime_toggle, "get_project_root", lambda start=None: project_dir)
    monkeypatch.setattr(
        runtime_toggle, "get_project_status",
        lambda r=None: {"initialized": False, "project_root": str(project_dir),
                        "runtime_enabled": False, "environment_exists": False,
                        "environment_path": None, "python_version": "3.12"},
    )
    monkeypatch.setattr(runtime_toggle, "load_project_metadata", lambda r: {})
    return project_dir


def _call(tool, arguments=None):
    server = create_server("test-pes")
    return server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": tool, "arguments": arguments or {}}}
    )


def _envelope_of(response):
    assert response["jsonrpc"] == "2.0"
    return response["result"]["structuredContent"]


def _tools():
    server = create_server("test-pes")
    listed = server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    return {entry["name"]: entry for entry in listed["result"]["tools"]}


# -- 1. tool registration ----------------------------------------------------


def test_tool_registration_and_description():
    tools = _tools()
    assert TOOL in tools
    assert TOOL in READ_ONLY_TOOL_NAMES

    entry = tools[TOOL]
    assert entry["description"] == DESCRIPTION
    # Agent-oriented: exactly one sentence, no branding/implementation talk.
    assert entry["description"].count(".") == 1
    for banned in ("Py Env Studio", "PES", "uv", "MCP", "Skill", "AI setup"):
        assert banned.lower() not in entry["description"].lower()

    schema = entry["inputSchema"]
    assert schema["type"] == "object"
    assert set(schema["properties"]) == {"path", "project_path"}
    assert "required" not in schema
    assert schema["additionalProperties"] is False


def test_tool_handler_signature_matches_mcp_contract():
    import inspect

    from py_env_studio.core.mcp.tools import analysis as handler

    assert list(inspect.signature(handler.check_consistency).parameters) == ["arguments"]


def test_existing_tools_are_unchanged():
    """The new tool must not alter any previously exposed tool definition."""
    tools = _tools()
    assert set(tools) - {TOOL} == {
        "pyenv_list_environments",
        "pyenv_get_environment",
        "pyenv_list_packages",
        "pyenv_get_project_context",
        "pyenv_get_environment_status",
        "pyenv_scan_vulnerabilities",
        "pyenv_get_dependency_information",
        "pyenv_analyze_project",
    }
    assert tools["pyenv_analyze_project"]["description"].startswith(
        "Analyze a Python project using Py Env Studio"
    )
    assert tools["pyenv_analyze_project"]["inputSchema"]["properties"] == {
        "project_path": {"type": "string"}
    }


# -- 2. minimal input --------------------------------------------------------


def test_minimal_input_uses_the_same_path_semantics_as_analysis(wired):
    """No arguments at all behaves like analyze_project() with no path."""
    envelope = _envelope_of(_call(TOOL, {}))
    assert envelope["success"] is True
    assert envelope["metadata"]["source"] == "pes"
    assert envelope["metadata"]["cached"] is True
    assert envelope["data"]["project"] == analyze_project(None).to_dict()


def test_invalid_input_matches_the_analysis_contract():
    envelope = _envelope_of(_call(TOOL, {"path": 42}))
    assert envelope["success"] is False
    assert envelope["error"]["code"] == "INVALID_INPUT"
    assert set(envelope["error"]) == {"code", "message", "details"}


# -- 3. valid project --------------------------------------------------------


def test_valid_project_returns_declared_resolved_installed(wired, project_dir):
    response = _call(TOOL, {"path": str(project_dir)})
    envelope = _envelope_of(response)
    assert response["result"]["isError"] is False
    assert envelope["success"] is True

    data = envelope["data"]
    assert set(data) == {"project", "declared", "resolved", "installed", "consistent"}
    # The existing analysis is reused verbatim, not recalculated.
    assert data["project"] == analyze_project(str(project_dir)).to_dict()
    assert set(data["project"]) == {
        "project", "environment", "python", "package_manager", "runtime",
        "dependencies", "outdated", "security", "pes_config", "summary",
    }
    assert data["installed"] == {"available": True,
                                 "environment_id": "my-api-env",
                                 "count": 2}


def test_project_path_alias_keeps_existing_conventions(wired, project_dir):
    via_alias = _envelope_of(_call(TOOL, {"project_path": str(project_dir)}))["data"]
    via_path = _envelope_of(_call(TOOL, {"path": str(project_dir)}))["data"]
    assert via_alias == via_path
    assert via_alias["project"]["project"]["path"] == str(project_dir)


# -- 4. missing project ------------------------------------------------------


def test_missing_project_reports_structured_failure():
    envelope = _envelope_of(_call(TOOL, {"path": "/no/such/dir-xyz-123"}))
    assert envelope["success"] is False
    assert envelope["error"]["code"] == "PROJECT_NOT_FOUND"
    assert set(envelope["error"]) == {"code", "message", "details"}


def test_project_path_semantics_match_analysis_errors():
    from py_env_studio.core.mcp.errors import McpError

    with pytest.raises(McpError) as exc_info:
        analyze_project("/no/such/dir-xyz-123")
    envelope = _envelope_of(_call(TOOL, {"path": "/no/such/dir-xyz-123"}))
    assert exc_info.value.code == "PROJECT_NOT_FOUND"
    assert envelope["error"]["code"] == exc_info.value.code


# -- 5. missing declared / resolved / installed data -------------------------


def test_missing_declared_resolved_installed_report_unavailable(unmanaged, project_dir):
    envelope = _envelope_of(_call(TOOL, {"path": str(project_dir)}))
    assert envelope["success"] is True
    data = envelope["data"]
    assert data["declared"]["available"] is False
    assert data["resolved"]["available"] is False
    assert data["installed"] == {"available": False}
    # Nothing invented: unavailable blocks carry only a reason.
    assert set(data["declared"]) == {"available", "reason"}
    assert set(data["resolved"]) == {"available", "reason"}
    assert data["declared"]["reason"] and data["resolved"]["reason"]


def test_declared_and_resolved_are_not_parsed_from_disk(wired, project_dir):
    """Even with a manifest and a lockfile on disk both stay unavailable.

    This pins the stub boundary: no manifest parsing, no lockfile parsing,
    no uv detection, no resolver.
    """
    (project_dir / "pyproject.toml").write_text(
        "[project]\nname = 'my-api'\ndependencies = ['flask==3.0.0']\n"
    )
    (project_dir / "requirements.txt").write_text("flask==3.0.0\nclick==8.1.0\n")
    (project_dir / "pylock.toml").write_text("lock-version = '1.0'\n[[packages]]\n")
    (project_dir / ".python-version").write_text("3.11.9\n")

    data = _envelope_of(_call(TOOL, {"path": str(project_dir)}))["data"]
    assert data["declared"]["available"] is False
    assert data["resolved"]["available"] is False
    assert "pyproject" not in json.dumps(data["declared"])
    assert "pylock" not in json.dumps(data["resolved"])
    assert data["consistent"] == "unknown"


# -- 6. consistent == "unknown" ---------------------------------------------


def test_consistent_is_unknown_for_a_managed_project(wired, project_dir):
    data = _envelope_of(_call(TOOL, {"path": str(project_dir)}))["data"]
    assert data["installed"]["available"] is True
    assert data["consistent"] == "unknown"
    assert data["consistent"] is not True
    assert data["consistent"] is not False


def test_consistent_is_unknown_without_environment(unmanaged, project_dir):
    data = _envelope_of(_call(TOOL, {"path": str(project_dir)}))["data"]
    assert data["installed"] == {"available": False}
    assert data["consistent"] == "unknown"


def test_unknown_is_not_reported_as_consistent(unmanaged, project_dir):
    data = _envelope_of(_call(TOOL, {"path": str(project_dir)}))["data"]
    assert data["consistent"] == "unknown"
    assert data["consistent"] not in ("consistent", "inconsistent", True, False)


# -- 7. no mutation ----------------------------------------------------------


def test_check_consistency_changes_nothing(wired, project_dir, monkeypatch, tmp_path):
    """Snapshot project files, registry, and DB bytes; fail if anything mutates."""
    from py_env_studio.core import env_manager, package_manager, runtime_toggle
    from py_env_studio.utils import handlers

    (project_dir / "pes.config").write_text("[project]\nname = my-api\n")
    (project_dir / "pyproject.toml").write_text("[project]\nname = 'my-api'\n")
    (project_dir / "requirements.txt").write_text("flask==3.0.0\n")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text('{"my-api": {"runtime_enabled": true}}')
    db_path = tmp_path / "cache.db"
    db_path.write_bytes(b"\x00" * 64)

    def _snapshot():
        snapshot = {
            str(path.relative_to(project_dir)): path.read_bytes()
            for path in sorted(project_dir.rglob("*"))
            if path.is_file()
        }
        snapshot["registry.json"] = registry_path.read_bytes()
        snapshot["cache.db"] = db_path.read_bytes()
        return snapshot

    before = _snapshot()
    calls = []

    def _guard(label):
        def _recorder(*args, **kwargs):
            calls.append((label, args, kwargs))
        return _recorder

    monkeypatch.setattr(runtime_toggle, "save_project_metadata",
                        _guard("save_project_metadata"))
    monkeypatch.setattr(runtime_toggle, "save_registry", _guard("save_registry"))
    monkeypatch.setattr(runtime_toggle, "init_project", _guard("init_project"))
    monkeypatch.setattr(handlers.DBHelper, "save_vulnerability_info",
                        staticmethod(_guard("save_vulnerability_info")))
    for module, names in (
        (package_manager, ("install_package", "uninstall_package", "update_package")),
        (env_manager, ("create_env", "delete_env", "rename_env", "activate_env")),
    ):
        for name in names:
            assert hasattr(module, name), "{}.{} is missing".format(module.__name__, name)
            monkeypatch.setattr(module, name, _guard("{}.{}".format(module.__name__, name)))

    import sqlite3

    real_connect = sqlite3.connect

    def _guarded_connect(*a, **k):
        calls.append(("sqlite.connect", a, k))
        return real_connect(*a, **k)

    monkeypatch.setattr(sqlite3, "connect", _guarded_connect)

    data = _envelope_of(_call(TOOL, {"path": str(project_dir)}))["data"]
    assert data["project"]["project"]["managed_by_pes"] is True
    assert calls == []
    assert _snapshot() == before
    assert data["consistent"] == "unknown"


# -- 8. no network access ----------------------------------------------------


def test_check_consistency_does_not_touch_network(wired, project_dir, monkeypatch):
    import urllib.request

    import requests

    def _boom(*args, **kwargs):
        raise AssertionError("pyenv_check_consistency performed a network request")

    monkeypatch.setattr(requests, "get", _boom)
    monkeypatch.setattr(requests, "post", _boom)
    monkeypatch.setattr(requests, "request", _boom)
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    monkeypatch.setattr(socket.socket, "connect", _boom)

    data = _envelope_of(_call(TOOL, {"path": str(project_dir)}))["data"]
    assert data["project"]["summary"]["environment_available"] is True
    assert data["consistent"] == "unknown"


# -- stdio contract ----------------------------------------------------------


def test_stdio_roundtrip_stays_protocol_clean(wired, project_dir):
    import io

    server = create_server("test-pes")
    stdin = io.StringIO(
        '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}\n'
        '{"jsonrpc": "2.0", "id": 2, "method": "tools/call",'
        ' "params": {"name": "%s", "arguments": {"path": %s}}}\n'
        % (TOOL, json.dumps(str(project_dir)))
    )
    stdout = io.StringIO()
    server.serve_stdio(stdin=stdin, stdout=stdout)
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == 2
    payloads = [json.loads(line) for line in lines]  # every line is protocol JSON
    assert payloads[1]["result"]["isError"] is False
    assert payloads[1]["result"]["structuredContent"]["data"]["consistent"] == "unknown"
    assert payloads[1]["result"]["structuredContent"]["success"] is True
