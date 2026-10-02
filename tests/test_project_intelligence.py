"""Tests for pes_analyze_project (Windows-first, read-only, local-first).

Service seams (runtime_toggle, env_manager, package_manager,
dependency_preview, uv_tools, handlers.DBHelper) are stubbed so no real
environments, subprocesses, or network access occur. Windows path shapes
(spaces, Unicode, parentheses, drive letters) are covered with
platform-safe abstractions that run on any OS.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from py_env_studio.core.mcp import create_server
from py_env_studio.core.mcp.errors import McpError
from py_env_studio.core.project_intelligence import analyze_project

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
    """Wire every PES seam to in-memory fakes for one managed project."""
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


def _envelope_of(response):
    assert response["jsonrpc"] == "2.0"
    return response["result"]["structuredContent"]


def _call(tool, arguments=None):
    server = create_server("test-pes")
    return server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": tool, "arguments": arguments or {}}}
    )


# -- project detection --------------------------------------------------------

def test_explicit_project_path(wired, project_dir):
    data = analyze_project(str(project_dir)).to_dict()
    assert data["project"]["managed_by_pes"] is True
    assert data["project"]["path"] == str(project_dir)
    assert data["project"]["name"] == "my-api"
    assert data["runtime"] == {"managed_by_pes": True, "status": "enabled"}
    assert data["summary"]["environment_available"] is True


def test_current_project_detection(wired, project_dir, monkeypatch):
    monkeypatch.chdir(project_dir)
    analysis = analyze_project()
    assert analysis.to_dict()["project"]["path"] == str(project_dir)


def test_missing_project_path_is_not_guessed():
    with pytest.raises(McpError) as exc_info:
        analyze_project("/no/such/dir-xyz-123")
    assert exc_info.value.code == "PROJECT_NOT_FOUND"


def test_unregistered_ordinary_project(tmp_path, monkeypatch):
    """A real directory with pyproject.toml but no pes.config is reported,
    never initialized."""
    from py_env_studio.core import runtime_toggle

    root = tmp_path / "plain"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='plain'\n")
    monkeypatch.setattr(runtime_toggle, "get_project_root", lambda start=None: root)
    monkeypatch.setattr(
        runtime_toggle, "get_project_status",
        lambda r=None: {"initialized": False, "project_root": str(root),
                        "runtime_enabled": False, "environment_exists": False,
                        "environment_path": None, "python_version": "3.12"},
    )
    monkeypatch.setattr(runtime_toggle, "load_project_metadata", lambda r: {})
    created = []
    monkeypatch.setattr(runtime_toggle, "init_project",
                        lambda **kwargs: created.append(kwargs) or {"success": True})
    data = analyze_project(str(root)).to_dict()
    assert data["project"]["managed_by_pes"] is False
    assert data["runtime"] == {"managed_by_pes": False, "status": None}
    assert data["environment"]["available"] is False
    assert created == []


def test_ambiguous_project(tmp_path, monkeypatch):
    from py_env_studio.core import runtime_toggle

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(runtime_toggle, "get_project_root", lambda start=None: None)
    monkeypatch.setattr(
        runtime_toggle, "list_registered_projects",
        lambda: [{"name": "a", "project_root": "/projects/a"},
                 {"name": "b", "project_root": "/projects/b"}],
    )
    with pytest.raises(McpError) as exc_info:
        analyze_project()
    assert exc_info.value.code == "AMBIGUOUS_PROJECT"
    assert len(exc_info.value.details["candidates"]) == 2


def test_invalid_project_path_type():
    with pytest.raises(McpError) as exc_info:
        analyze_project(12345)
    assert exc_info.value.code == "INVALID_INPUT"


# -- Windows path handling ----------------------------------------------------

def _rewire_root(monkeypatch, root):
    """Point root-dependent PES seams at an arbitrary directory."""
    from py_env_studio.core import runtime_toggle

    monkeypatch.setattr(runtime_toggle, "get_project_root", lambda start=None: root)
    monkeypatch.setattr(
        runtime_toggle, "get_project_status",
        lambda r=None: dict(STATUS, project_root=str(root),
                            environment_path=str(root / ".venv")),
    )
    monkeypatch.setattr(
        runtime_toggle, "load_project_metadata",
        lambda r: dict(METADATA, project_root=str(root),
                       environment_path=str(root / ".venv")),
    )


@pytest.mark.parametrize("dirname", [
    "my-api",
    "My Projects",
    "Python App (v2)",
    "my-api_2026 (final)",
])
def test_project_dirs_with_spaces_and_parentheses(tmp_path, wired, monkeypatch, dirname):
    root = tmp_path / "shapes" / dirname
    root.mkdir(parents=True)
    _rewire_root(monkeypatch, root)
    analysis = analyze_project(str(root))
    assert analysis.to_dict()["project"]["path"] == str(root)


def test_project_dir_with_unicode(tmp_path, wired, monkeypatch):
    root = tmp_path / "项目-my-api"
    root.mkdir()
    _rewire_root(monkeypatch, root)
    analysis = analyze_project(str(root))
    assert analysis.to_dict()["project"]["path"] == str(root)


@pytest.mark.parametrize("raw", [
    "C:\\Users\\Developer\\Projects\\my-api",
    "C:\\Users\\Developer\\My Projects\\Python App",
    "C:\\Users\\开发者\\Projects\\my-api",
    "C:\\Users\\Dev (x86)\\my-api",
])
def test_windows_style_paths_never_crash(raw):
    """Windows drive-letter paths that do not exist here must produce a
    structured PROJECT_NOT_FOUND error, never an exception or a guess."""
    with pytest.raises(McpError) as exc_info:
        analyze_project(raw)
    assert exc_info.value.code == "PROJECT_NOT_FOUND"


def test_nested_project_path_resolves_deterministically(wired, project_dir):
    nested = project_dir / "src" / "pkg"
    nested.mkdir(parents=True)
    analysis = analyze_project(str(nested))
    assert analysis.to_dict()["project"]["path"] == str(project_dir)


def test_invalid_environment_path(wired, project_dir, monkeypatch):
    from py_env_studio.core import runtime_toggle

    monkeypatch.setattr(
        runtime_toggle, "get_project_status",
        lambda r=None: dict(STATUS, project_root=str(project_dir),
                            environment_id="ghost-env", environment_exists=False,
                            environment_path=str(project_dir / "ghost")),
    )
    monkeypatch.setattr(
        runtime_toggle, "load_project_metadata",
        lambda r: dict(METADATA, project_root=str(project_dir),
                       environment_id="ghost-env"),
    )
    data = analyze_project(str(project_dir)).to_dict()
    assert data["environment"]["available"] is False
    assert data["summary"]["environment_available"] is False
    assert data["dependencies"]["analysis_available"] is False


# -- environment ----------------------------------------------------------------

def test_environment_fields(wired, project_dir):
    data = analyze_project(str(project_dir)).to_dict()["environment"]
    assert data["available"] is True
    assert data["id"] == "my-api-env"
    assert data["name"] == "my-api-env"
    assert data["path"] == str(project_dir / ".venv")
    assert data["python_version"] == "3.12.8"
    assert data["package_manager"] == "pip"
    assert data["status"] == "exists"
    assert data["size"] == "120 MB"
    assert data["last_scanned"] == "2026-01-01T00:00:00"


def test_unavailable_python_executable(wired, project_dir):
    """The stubbed executable path does not exist on disk: reported, not fatal."""
    data = analyze_project(str(project_dir)).to_dict()["python"]
    assert data["available"] is True
    assert data["version"] == "3.12.8"
    assert data["executable_available"] is False


def test_present_python_executable(wired, project_dir, tmp_path, monkeypatch):
    from py_env_studio.core import env_manager

    exe = tmp_path / "python"
    exe.write_text("#!/bin/sh\n")

    def patched(name):
        info = dict(ENV_INFO, path=str(project_dir / ".venv"),
                    python_executable=str(exe))
        return info if name == "my-api-env" else None

    monkeypatch.setattr(env_manager, "get_environment_info", patched)
    data = analyze_project(str(project_dir)).to_dict()["python"]
    assert data["executable_available"] is True


# -- package manager --------------------------------------------------------------

def test_package_manager_pip(wired, project_dir):
    data = analyze_project(str(project_dir)).to_dict()["package_manager"]
    assert data == {"available": True, "manager": "pip",
                    "configured": "pip", "reason": None}


def test_package_manager_uv(wired, project_dir, monkeypatch):
    from py_env_studio.core import env_manager, package_manager, uv_tools

    monkeypatch.setattr(package_manager, "get_env_package_manager", lambda name: "uv")
    monkeypatch.setattr(uv_tools, "is_uv_installed", lambda: True)
    base = dict(ENV_INFO)
    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: dict(base, package_manager="uv",
                          metadata={"package_manager": "uv"}),
    )
    data = analyze_project(str(project_dir)).to_dict()["package_manager"]
    assert data["manager"] == "uv"
    assert data["available"] is True


def test_package_manager_unavailable(wired, project_dir, monkeypatch):
    from py_env_studio.core import env_manager, package_manager, uv_tools

    monkeypatch.setattr(package_manager, "get_env_package_manager", lambda name: "uv")
    monkeypatch.setattr(uv_tools, "is_uv_installed", lambda: False)
    base = dict(ENV_INFO)
    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: dict(base, package_manager="uv",
                          metadata={"package_manager": "uv"}),
    )
    data = analyze_project(str(project_dir)).to_dict()["package_manager"]
    assert data["manager"] == "uv"
    assert data["available"] is False
    assert "not installed" in (data["reason"] or "")


# -- runtime ------------------------------------------------------------------------

def test_runtime_disabled(wired, project_dir, monkeypatch):
    from py_env_studio.core import runtime_toggle

    monkeypatch.setattr(
        runtime_toggle, "get_project_status",
        lambda r=None: dict(STATUS, project_root=str(project_dir),
                            runtime_enabled=False,
                            environment_path=str(project_dir / ".venv")),
    )
    monkeypatch.setattr(
        runtime_toggle, "load_project_metadata",
        lambda r: dict(METADATA, project_root=str(project_dir), runtime_enabled=False,
                       environment_path=str(project_dir / ".venv")),
    )
    data = analyze_project(str(project_dir)).to_dict()
    assert data["runtime"] == {"managed_by_pes": True, "status": "disabled"}
    assert data["pes_config"]["runtime_enabled"] is False


# -- dependencies ---------------------------------------------------------------------

def test_dependencies_available_no_conflicts(wired, project_dir):
    data = analyze_project(str(project_dir)).to_dict()["dependencies"]
    assert data["analysis_available"] is True
    assert data["installed"] == 2
    assert data["conflicts"]["count"] == 0
    assert data["conflicts"]["items"] == []
    assert "scope" in data and data["scope"]


def test_dependency_conflicts_reported(wired, project_dir, monkeypatch):
    from py_env_studio.core import dependency_preview

    monkeypatch.setattr(
        dependency_preview, "get_package_dependencies",
        lambda python, pkg: {"click": "click>=99.0"} if pkg == "flask" else {},
    )
    data = analyze_project(str(project_dir)).to_dict()
    conflicts = data["dependencies"]["conflicts"]
    assert conflicts["count"] == 1
    item = conflicts["items"][0]
    assert item["package"] == "flask"
    assert item["requirement"] == "click>=99.0"
    assert "click" in item["reason"]
    assert data["summary"]["dependency_conflicts"] == 1


def test_missing_dependency_reported(wired, project_dir, monkeypatch):
    from py_env_studio.core import dependency_preview

    monkeypatch.setattr(
        dependency_preview, "get_package_dependencies",
        lambda python, pkg: {"sphinx": "sphinx>=1.0"} if pkg == "flask" else {},
    )
    conflicts = analyze_project(str(project_dir)).to_dict()["dependencies"]["conflicts"]
    assert conflicts["count"] == 1
    assert "not installed" in conflicts["items"][0]["reason"]


def test_dependencies_unavailable(wired, project_dir, monkeypatch):
    from py_env_studio.core import package_manager

    def _boom(name):
        raise RuntimeError("no python here")

    monkeypatch.setattr(package_manager, "list_packages", _boom)
    data = analyze_project(str(project_dir)).to_dict()
    assert data["dependencies"]["analysis_available"] is False
    assert data["dependencies"]["reason"]
    assert data["summary"]["dependency_analysis_available"] is False
    assert data["summary"]["dependency_conflicts"] is None


# -- outdated ---------------------------------------------------------------------------

def test_outdated_available(wired, project_dir):
    data = analyze_project(str(project_dir)).to_dict()
    assert data["outdated"]["analysis_available"] is True
    assert data["outdated"]["count"] == 1
    assert data["outdated"]["items"] == [
        {"name": "click", "current_version": "8.1.0", "latest_version": "8.2.0"}
    ]
    assert data["summary"]["outdated_packages"] == 1


def test_outdated_none(wired, project_dir, monkeypatch):
    from py_env_studio.core import package_manager

    monkeypatch.setattr(package_manager, "check_outdated_packages", lambda name: "[]")
    data = analyze_project(str(project_dir)).to_dict()
    assert data["outdated"]["analysis_available"] is True
    assert data["outdated"]["count"] == 0
    assert data["summary"]["outdated_packages"] == 0


def test_outdated_unavailable_offline(wired, project_dir, monkeypatch):
    from py_env_studio.core import package_manager

    def _boom(name):
        raise RuntimeError("network unreachable")

    monkeypatch.setattr(package_manager, "check_outdated_packages", _boom)
    data = analyze_project(str(project_dir)).to_dict()
    assert data["outdated"]["analysis_available"] is False
    assert data["outdated"]["reason"]
    assert data["summary"]["outdated_packages"] is None


# -- security -----------------------------------------------------------------------------

SEV_PAYLOAD = {
    "vulnerability_insights": {
        "metadata": {"package": "django", "version": "2.1.3"},
        "developer_view": [
            {"vulnerability_id": "GHSA-1", "affected_components": ["django"],
             "severity": {"level": "High", "score": "CVSS:3.1/AV:N"},
             "fixed_versions": ["2.2.0"]},
            {"vulnerability_id": "GHSA-2", "affected_components": ["django"],
             "severity": {"level": "Critical", "score": "CVSS:3.1/AV:N"},
             "fixed_versions": []},
            {"vulnerability_id": "GHSA-3", "affected_components": ["django"],
             "severity": {"level": "Medium", "score": "CVSS:3.1/AV:N"},
             "fixed_versions": ["2.2.0"]},
            {"vulnerability_id": "GHSA-4", "affected_components": ["django"],
             "severity": {"level": "Weird", "score": None},
             "fixed_versions": []},
        ],
    }
}


def test_security_cached_counts(wired, project_dir, monkeypatch):
    from py_env_studio.utils import handlers

    monkeypatch.setattr(handlers.DBHelper, "get_vulnerability_info",
                        staticmethod(lambda env: SEV_PAYLOAD))
    data = analyze_project(str(project_dir)).to_dict()
    assert data["security"]["scan_available"] is True
    assert data["security"]["vulnerabilities"] == {
        "total": 4, "critical": 1, "high": 1, "medium": 1,
        "low": 0, "unknown": 1,
    }
    assert data["summary"]["security_scan_available"] is True
    assert data["summary"]["vulnerabilities"] == 4


def test_security_no_scan_is_not_zero_vulns(wired, project_dir):
    data = analyze_project(str(project_dir)).to_dict()
    assert data["security"]["scan_available"] is False
    assert data["security"]["vulnerabilities"]["total"] is None
    assert data["security"]["reason"]
    assert data["summary"]["vulnerabilities"] is None


# -- cache / offline ------------------------------------------------------------------------

def test_uses_cache_and_no_network(wired, project_dir, monkeypatch):
    """With every seam stubbed, the analysis must succeed even if the
    network stack raises on any use."""
    import requests

    def _boom(*args, **kwargs):
        raise AssertionError("analyze_project performed a network request")

    monkeypatch.setattr(requests, "get", _boom)
    monkeypatch.setattr(requests, "post", _boom)
    monkeypatch.setattr(requests, "request", _boom)
    data = analyze_project(str(project_dir)).to_dict()
    assert data["summary"]["environment_available"] is True


# -- read-only guarantee ----------------------------------------------------------------------

def test_analysis_changes_nothing(wired, project_dir, monkeypatch, tmp_path):
    """Snapshot project files, registry, and DB bytes; fail if anything mutates."""
    from py_env_studio.core import runtime_toggle
    from py_env_studio.utils import handlers

    pes_config = project_dir / "pes.config"
    pes_config.write_text("[project]\nname = my-api\n")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text('{"my-api": {"runtime_enabled": true}}')
    db_path = tmp_path / "cache.db"
    db_path.write_bytes(b"\x00" * 64)

    before = {
        "pes_config": pes_config.read_bytes(),
        "registry": registry_path.read_bytes(),
        "db": db_path.read_bytes(),
    }
    calls = []
    monkeypatch.setattr(
        runtime_toggle, "save_project_metadata",
        lambda *a, **k: calls.append(("save_project_metadata", a, k)),
    )
    monkeypatch.setattr(
        runtime_toggle, "save_registry",
        lambda *a, **k: calls.append(("save_registry", a, k)),
    )
    monkeypatch.setattr(
        handlers.DBHelper, "save_vulnerability_info",
        staticmethod(lambda *a, **k: calls.append(("save_vulnerability_info", a, k))),
    )
    import sqlite3

    real_connect = sqlite3.connect

    def _guarded_connect(*a, **k):
        calls.append(("sqlite.connect", a))
        return real_connect(*a, **k)

    monkeypatch.setattr(sqlite3, "connect", _guarded_connect)

    data = analyze_project(str(project_dir)).to_dict()
    assert data["project"]["managed_by_pes"] is True
    assert calls == []
    assert pes_config.read_bytes() == before["pes_config"]
    assert registry_path.read_bytes() == before["registry"]
    assert db_path.read_bytes() == before["db"]


# -- MCP surface -------------------------------------------------------------------------------

def test_mcp_tool_registered_and_called(wired, project_dir):
    server = create_server("test-pes")
    names = [t["name"] for t in
             server.handle_message(
                 {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})["result"]["tools"]]
    assert "pes_analyze_project" in names
    response = _call("pes_analyze_project", {"project_path": str(project_dir)})
    envelope = _envelope_of(response)
    assert envelope["success"] is True
    data = envelope["data"]
    assert set(data) == {"project", "environment", "python", "package_manager",
                         "runtime", "dependencies", "outdated", "security",
                         "pes_config", "summary"}
    assert envelope["metadata"]["source"] == "pes"
    assert response["result"]["isError"] is False


def test_mcp_tool_contract_shapes():
    import inspect

    from py_env_studio.core.mcp.tools import analysis as handler

    assert list(inspect.signature(handler.analyze_project).parameters) == ["arguments"]
    failure = _envelope_of(_call("pes_analyze_project",
                                 {"project_path": "/no/such/dir-xyz-123"}))
    assert failure["success"] is False
    assert failure["error"]["code"] == "PROJECT_NOT_FOUND"
    assert set(failure["error"]) == {"code", "message", "details"}


def test_mcp_invalid_input_type():
    envelope = _envelope_of(_call("pes_analyze_project", {"project_path": 42}))
    assert envelope["success"] is False
    assert envelope["error"]["code"] == "INVALID_INPUT"


def test_mcp_stdio_roundtrip_stays_clean(wired, project_dir, monkeypatch):
    import io
    import json as json_module

    server = create_server("test-pes")
    stdin = io.StringIO(
        '{"jsonrpc": "2.0", "id": 1, "method": "tools/call",'
        ' "params": {"name": "pes_analyze_project",'
        ' "arguments": {"project_path": %s}}}\n'
        % json_module.dumps(str(project_dir))
    )
    stdout = io.StringIO()
    server.serve_stdio(stdin=stdin, stdout=stdout)
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json_module.loads(lines[0])
    assert payload["result"]["structuredContent"]["success"] is True
