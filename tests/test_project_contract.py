"""Tests for Phase A.1 — project contract foundation (pes.config + SQLite).

All persistence uses a throwaway SQLite file; environment lookups are
stubbed so no real environments, subprocesses, or network access occur.
Windows path shapes are covered with platform-safe abstractions.
"""

from __future__ import annotations

import json
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

import pytest

from py_env_studio.core.database import DatabaseManager
from py_env_studio.core.project_contract import (
    ContractError,
    ProjectContract,
    ProjectContractService,
)
from py_env_studio.core.project_contract.repository import normalize_db_key


def make_service(tmp_path, monkeypatch=None):
    dbm = DatabaseManager(db_path=tmp_path / "a1.db")
    dbm.initialize_database()
    return ProjectContractService(db_manager=dbm), dbm


def write_config(root, text):
    root.mkdir(parents=True, exist_ok=True)
    (root / "pes.config").write_text(text, encoding="utf-8")


VALID_CONFIG = """\
[project]
name = cerberus-extended

[python]
version = 3.12
provider = Python Install Manager

[environment]
id = cerberus-extended-217a7026
package_manager = pip

[runtime]
managed = true
enabled = true
auto_init = true
"""

LEGACY_CONFIG = """\
[project]
name = cerberus-extended
root = C:/Users/Lenovo/Desktop/cerberus-extended

[environment]
id = cerberus-extended-217a7026
path = C:/Users/Lenovo/.py_env_studio/venvs/cerberus-extended-217a7026
python_version = 3.12
package_manager = pip

[runtime]
enabled = true
auto_init = true
"""


@pytest.fixture()
def svc(tmp_path):
    service, _dbm = make_service(tmp_path)
    return service


@pytest.fixture()
def stub_env(monkeypatch):
    """Stub environment lookups: only 'env-1' exists."""
    from py_env_studio.core import env_manager

    monkeypatch.setattr(
        env_manager, "get_environment_info",
        lambda name: {
            "environment_id": name, "name": name,
            "path": "/venvs/{}".format(name),
            "python_executable": "/venvs/{}/bin/python".format(name),
            "python_version": "3.12.1", "package_manager": "pip",
            "status": "exists", "metadata": {},
        } if name == "env-1" else None,
    )


def register_env(dbm, name="env-1"):
    from py_env_studio.core import schema as sql

    with dbm.connect() as conn:
        conn.execute(
            sql.get("environments", "create_environment"),
            (name, "/venvs/{}".format(name), datetime.now()),
        )
        conn.commit()


# -- contract parsing -------------------------------------------------------------

def test_parse_valid_config(tmp_path, svc):
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG)
    contract = svc.load(root)
    assert contract is not None
    assert contract.project_name == "cerberus-extended"
    assert contract.python_version == "3.12"
    assert contract.python_provider == "Python Install Manager"
    assert contract.environment_id == "cerberus-extended-217a7026"
    assert contract.package_manager == "pip"
    assert contract.runtime_managed is True
    assert contract.runtime_enabled is True
    assert contract.runtime_auto_init is True
    assert contract.to_dict()["environment"] == {
        "id": "cerberus-extended-217a7026", "package_manager": "pip"}


def test_parse_malformed_config(tmp_path, svc):
    root = tmp_path / "proj"
    write_config(root, "this is not an ini file {{{")
    with pytest.raises(ContractError):
        svc.load(root)
    result = svc.validate(root)
    assert result.valid is False
    assert result.errors


def test_parse_missing_sections(tmp_path, svc):
    root = tmp_path / "proj"
    write_config(root, "[project]\nname = lonely\n")
    with pytest.raises(ContractError) as exc_info:
        svc.load(root)
    assert "environment ID" in str(exc_info.value)


def test_parse_missing_required_values(tmp_path, svc):
    root = tmp_path / "proj"
    write_config(root, "[project]\nname = \n[environment]\nid = env-1\n"
                       "[python]\nversion = 3.12\n")
    with pytest.raises(ContractError) as exc_info:
        svc.load(root)
    assert "project name" in str(exc_info.value)


def test_parse_unknown_package_manager_flagged(tmp_path, svc, stub_env):
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("package_manager = pip",
                                            "package_manager = conda"))
    contract = svc.load(root)  # parses leniently...
    assert contract.package_manager == "conda"
    result = svc.validate(root)  # ...but validation rejects it
    assert result.valid is False
    assert any("package manager" in e for e in result.errors)


def test_parse_unknown_provider_flagged(tmp_path, svc, stub_env):
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("provider = Python Install Manager",
                                            "provider = mystery"))
    assert svc.load(root).python_provider == "mystery"
    result = svc.validate(root)
    assert result.valid is False
    assert any("provider" in e for e in result.errors)


def test_kebab_case_provider_alias_accepted(tmp_path, svc):
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("provider = Python Install Manager",
                                            "provider = python-install-manager"))
    assert svc.load(root).python_provider == "Python Install Manager"


# -- persistence ---------------------------------------------------------------------

def test_save_creates_portable_config_and_row(tmp_path, svc):
    root = tmp_path / "proj"
    root.mkdir()
    contract = ProjectContract(
        project_name="cerberus-extended", python_version="3.12",
        python_provider="Python Install Manager",
        environment_id="env-9", package_manager="uv",
        runtime_managed=True, runtime_enabled=True, runtime_auto_init=True)
    assert svc.save(root, contract) is contract

    parser = ConfigParser(interpolation=None)
    parser.read(root / "pes.config", encoding="utf-8")
    assert not parser.has_option("environment", "path")
    assert not parser.has_option("project", "root")
    assert parser.get("environment", "id") == "env-9"

    row = svc.registered(root)
    assert row is not None
    assert row["project_name"] == "cerberus-extended"
    assert row["environment_id"] == "env-9"
    assert row["package_manager"] == "uv"
    assert row["runtime_enabled"] is True
    assert row["config_path"] == str(root / "pes.config")


def test_roundtrip_read_update(tmp_path, svc):
    root = tmp_path / "proj"
    root.mkdir()
    base = dict(project_name="p", python_version="3.12",
                python_provider="System", environment_id="env-9",
                package_manager="pip")
    svc.save(root, ProjectContract(**base))
    assert svc.load(root).package_manager == "pip"
    svc.save(root, ProjectContract(**dict(base, package_manager="uv")))
    reloaded = svc.load(root)
    assert reloaded.package_manager == "uv"
    assert svc.registered(root)["package_manager"] == "uv"


def test_reload_after_restart(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    svc1, _ = make_service(tmp_path)
    svc1.save(root, ProjectContract(
        project_name="p", python_version="3.11",
        python_provider="System", environment_id="env-9",
        package_manager="pip"))
    svc2, _ = make_service(tmp_path)  # new instances, same DB file
    assert svc2.load(root).python_version == "3.11"
    assert svc2.registered(root)["environment_id"] == "env-9"


def test_duplicate_project_handling_single_row(tmp_path, svc):
    from py_env_studio.core import schema as sql

    root = tmp_path / "proj"
    root.mkdir()
    contract = ProjectContract(
        project_name="p", python_version="3.12",
        python_provider="System", environment_id="env-9",
        package_manager="pip")
    svc.save(root, contract)
    svc.save(root, contract)
    svc.save(str(root) + "/", contract)
    dbm = svc._db()
    with dbm.connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM project_contract").fetchone()[0]
    assert count == 1
    assert sql.get("project_contract", "upsert_project_contract")


def test_project_path_normalization(tmp_path):
    root = tmp_path / "proj"
    assert normalize_db_key(root) == normalize_db_key(str(root) + "/")
    assert normalize_db_key(root) == normalize_db_key(root.resolve())


def test_save_rejects_invalid_contract(tmp_path, svc):
    root = tmp_path / "proj"
    root.mkdir()
    with pytest.raises(ContractError):
        svc.save(root, ProjectContract(
            project_name="p", python_version="3.12",
            python_provider="System", environment_id="",
            package_manager="pip"))


def test_save_missing_directory(tmp_path, svc):
    with pytest.raises(ContractError):
        svc.save(tmp_path / "nope", ProjectContract(
            project_name="p", python_version="3.12",
            python_provider="System", environment_id="env-9",
            package_manager="pip"))


# -- resolution --------------------------------------------------------------------------

def test_resolve_valid_environment(tmp_path, svc, stub_env):
    _service, dbm = make_service(tmp_path)
    register_env(dbm)
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("cerberus-extended-217a7026", "env-1"))
    resolved = svc.resolve(root)
    assert resolved.contract.environment_id == "env-1"
    assert resolved.environment.registered is True
    assert resolved.environment.exists is True
    assert resolved.environment.path == "/venvs/env-1"
    assert resolved.config_path == str(root / "pes.config")


def test_resolve_missing_environment(tmp_path, svc, stub_env):
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("cerberus-extended-217a7026", "ghost"))
    resolved = svc.resolve(root)
    assert resolved.environment.registered is False
    assert resolved.environment.exists is False
    assert resolved.environment.path is None


def test_resolve_deleted_environment(tmp_path, svc, stub_env):
    _service, dbm = make_service(tmp_path)
    register_env(dbm, name="gone-env")
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("cerberus-extended-217a7026", "gone-env"))
    resolved = svc.resolve(root)
    assert resolved.environment.registered is True
    assert resolved.environment.exists is False
    result = svc.validate(root)
    assert result.valid is False
    assert any("no longer exists" in e for e in result.errors)


def test_resolve_without_contract_raises(tmp_path, svc):
    with pytest.raises(ContractError):
        svc.resolve(tmp_path / "empty")


def test_validate_unregistered_environment(tmp_path, svc, stub_env):
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("cerberus-extended-217a7026", "ghost"))
    result = svc.validate(root)
    assert result.valid is False
    assert any("not registered" in e for e in result.errors)


def test_validate_ok(tmp_path, svc, stub_env):
    _service, dbm = make_service(tmp_path)
    register_env(dbm)
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("cerberus-extended-217a7026", "env-1"))
    result = svc.validate(root)
    assert result.valid is True
    assert result.errors == []


# -- Windows paths --------------------------------------------------------------------------

@pytest.mark.parametrize("dirname", [
    "My Project",
    "项目",
    "project (test)",
    "nested/inner/deep",
])
def test_windows_style_dirs_roundtrip(tmp_path, svc, dirname):
    root = tmp_path / dirname
    root.mkdir(parents=True)
    svc.save(root, ProjectContract(
        project_name="w", python_version="3.12",
        python_provider="Python Install Manager", environment_id="env-9",
        package_manager="pip"))
    assert svc.load(root).project_name == "w"
    assert svc.registered(root)["project_name"] == "w"


@pytest.mark.parametrize("raw", [
    "C:\\Users\\Lenovo\\Desktop\\My Project",
    "C:\\Users\\Lenovo\\Desktop\\项目",
    "C:\\Users\\Lenovo\\Desktop\\project (test)",
    "D:\\workspace\\project",
])
def test_windows_drive_paths_do_not_crash(raw, svc):
    assert svc.load(raw) is None  # no such dir here: no contract, no crash
    result = svc.validate(raw)
    assert result.valid is False
    assert result.errors
    with pytest.raises(ContractError):
        svc.save(raw, ProjectContract(
            project_name="w", python_version="3.12",
            python_provider="System", environment_id="env-9",
            package_manager="pip"))


# -- backward compatibility ----------------------------------------------------------------------

def test_legacy_config_loads_with_warnings(tmp_path, svc, stub_env):
    _service, dbm = make_service(tmp_path)
    register_env(dbm)
    root = tmp_path / "proj"
    write_config(root, LEGACY_CONFIG.replace("cerberus-extended-217a7026", "env-1"))
    contract = svc.load(root)
    assert contract.environment_id == "env-1"
    assert contract.python_version == "3.12"  # from legacy [environment] key
    assert contract.python_provider == "Python Install Manager"  # defaulted
    result = svc.validate(root)
    assert result.valid is True
    assert any("legacy absolute" in w for w in result.warnings)


def test_missing_optional_fields_defaulted(tmp_path, svc):
    root = tmp_path / "proj"
    write_config(root, "[project]\nname = p\n[environment]\nid = env-9\n"
                       "[python]\nversion = 3.12\n")
    contract = svc.load(root)
    assert contract.package_manager == "pip"
    assert contract.runtime_managed is True
    assert contract.runtime_enabled is False
    assert contract.runtime_auto_init is True


def test_no_config_means_unmanaged(tmp_path, svc):
    root = tmp_path / "proj"
    root.mkdir()
    assert svc.load(root) is None
    result = svc.validate(root)
    assert result.valid is False
    assert any("not PES-managed" in e for e in result.errors)


def test_invalid_python_version_rejected(tmp_path, svc, stub_env):
    root = tmp_path / "proj"
    write_config(root, VALID_CONFIG.replace("version = 3.12", "version = three"))
    result = svc.validate(root)
    assert result.valid is False
    assert any("Python version" in e for e in result.errors)


def test_old_loader_still_reads_new_portable_config(tmp_path):
    """Round-trip compatibility with runtime_toggle.load_project_metadata."""
    from py_env_studio.core import runtime_toggle

    root = tmp_path / "proj"
    root.mkdir()
    svc, _ = make_service(tmp_path)
    svc.save(root, ProjectContract(
        project_name="p", python_version="3.12",
        python_provider="System", environment_id="env-9",
        package_manager="uv", runtime_enabled=True))
    meta = runtime_toggle.load_project_metadata(root)
    assert meta["project_name"] == "p"
    assert meta["environment_id"] == "env-9"
    assert meta["package_manager"] == "uv"
    assert meta["runtime_enabled"] is True


# -- safety: A.1 changes nothing else ------------------------------------------------------------------

def test_a1_has_no_side_effects(tmp_path, svc, stub_env, monkeypatch):
    import requests
    import subprocess

    from py_env_studio.core import env_manager, pip_tools, runtime_toggle

    def _boom(*args, **kwargs):
        raise AssertionError("A.1 performed a forbidden operation")

    for name in ("run", "check_output", "Popen", "call", "check_call"):
        monkeypatch.setattr(subprocess, name, _boom)
    for name in ("get", "post", "request"):
        monkeypatch.setattr(requests, name, _boom)
    monkeypatch.setattr(env_manager, "create_env", _boom)
    monkeypatch.setattr(runtime_toggle, "create_managed_environment", _boom)
    monkeypatch.setattr(pip_tools, "install_package", _boom)

    root = tmp_path / "proj"
    root.mkdir()
    (root / "notes.txt").write_text("leave me alone", encoding="utf-8")
    contract = ProjectContract(
        project_name="p", python_version="3.12",
        python_provider="System", environment_id="env-1",
        package_manager="pip")
    svc.save(root, contract)
    svc.load(root)
    svc.validate(root)

    assert not (root / ".vscode").exists()
    assert (root / "notes.txt").read_text(encoding="utf-8") == "leave me alone"
    assert sorted(p.name for p in root.iterdir()) == ["notes.txt", "pes.config"]
    parser = ConfigParser(interpolation=None)
    parser.read(root / "pes.config", encoding="utf-8")
    assert set(parser.sections()) <= {"project", "python", "environment", "runtime"}


def test_registry_json_untouched(tmp_path, svc, stub_env, monkeypatch):
    """The contract service never consults or writes the project registry."""
    from py_env_studio.core import runtime_toggle

    def _boom(*args, **kwargs):
        raise AssertionError("A.1 touched the project registry")

    monkeypatch.setattr(runtime_toggle, "load_registry", _boom)
    monkeypatch.setattr(runtime_toggle, "save_registry", _boom)
    monkeypatch.setattr(runtime_toggle, "init_project", _boom)

    root = tmp_path / "proj"
    root.mkdir()
    svc.save(root, ProjectContract(
        project_name="p", python_version="3.12",
        python_provider="System", environment_id="env-1",
        package_manager="pip"))
    svc.load(root)
    svc.validate(root)
    svc.resolve(root)
