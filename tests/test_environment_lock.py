from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.markers import default_environment

from py_env_studio.core import environment_lock as lock_module
from py_env_studio.core import package_manager as package_manager_module
from py_env_studio.core.database import DatabaseManager
from py_env_studio.core.environment_lock import EnvironmentLockService


def _lock_text(*packages: tuple[str, str]) -> str:
    lines = [
        'lock-version = "1.0"',
        'created-by = "uv"',
        'requires-python = ">=3.12"',
        "",
    ]
    for name, version in packages:
        wheel_name = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
        lines.extend(
            [
                "[[packages]]",
                f'name = "{name}"',
                f'version = "{version}"',
                f'sdist = {{ url = "https://example.invalid/{name}-{version}.tar.gz", '
                'hashes = { sha256 = "' + "0" * 64 + '" } }',
                f'wheels = [{{ url = "https://example.invalid/{wheel_name}", '
                'hashes = { sha256 = "' + "1" * 64 + '" } }]',
                "",
            ]
        )
    return "\n".join(lines)


def _service(tmp_path: Path, monkeypatch, packages=None):
    env_root = tmp_path / "environments"
    env_path = env_root / "demo"
    env_path.mkdir(parents=True)
    (env_path / "pyvenv.cfg").write_text("home = test\n", encoding="utf-8")
    monkeypatch.setattr(lock_module, "VENV_DIR", env_root)
    monkeypatch.setattr(lock_module, "get_env_python", lambda _name: sys.executable)
    monkeypatch.setattr(lock_module, "get_env_package_manager", lambda _name: "pip")
    state = list(packages or [])
    monkeypatch.setattr(lock_module, "list_packages", lambda _name: list(state))
    service = EnvironmentLockService(DatabaseManager(db_path=tmp_path / "locks.db"))
    return service, env_path, state


@pytest.mark.parametrize("manager", ["pip", "uv"])
def test_create_lock_uses_native_manager_and_writes_pep751(tmp_path, monkeypatch, manager):
    service, _env_path, _state = _service(tmp_path, monkeypatch)
    monkeypatch.setattr(lock_module, "get_env_package_manager", lambda _name: manager)
    monkeypatch.setattr(
        service,
        "_capture_freeze",
        lambda _env_name, _manager, _python: "demo-pkg==1.2.3\n",
    )
    if manager == "uv":
        monkeypatch.setattr(lock_module.shutil, "which", lambda _name: "uv")

    commands = []

    def fake_run_tool(command, *, timeout, operation):
        commands.append(command)
        output_option = "--output-file" if manager == "uv" else "--output"
        output_file = Path(command[command.index(output_option) + 1])
        output_file.write_text(_lock_text(("demo-pkg", "1.2.3")), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(lock_module, "_run_tool", fake_run_tool)

    status = service.create_lock("demo")

    document = tomllib.loads(service.read_lock_text("demo"))
    assert document["lock-version"] == "1.0"
    assert document["packages"][0]["version"] == "1.2.3"
    assert document["packages"][0]["wheels"][0]["hashes"]["sha256"] == "1" * 64
    assert status["status"] == "Locked"
    assert "pip" in commands[0] if manager == "uv" else "lock" in commands[0]
    assert ("--format" in commands[0]) is (manager == "uv")


def test_verify_detects_external_lock_edit_and_keeps_only_metadata(tmp_path, monkeypatch):
    service, env_path, _state = _service(tmp_path, monkeypatch, [("demo-pkg", "1.2.3")])
    lock_path = env_path / "pylock.toml"
    lock_path.write_text(_lock_text(("demo-pkg", "1.2.3")), encoding="utf-8")

    assert service.verify("demo").status == "Verified"
    lock_path.write_text(_lock_text(("demo-pkg", "2.0.0")), encoding="utf-8")
    assert service.get_status("demo")["status"] == "Unchecked"
    result = service.verify("demo")

    assert result.status == "Drift Detected"
    assert result.differences[0].expected == "2.0.0"
    row = service._metadata_row("demo")
    assert row[1] == "PEP 751"
    with service._db.connect() as connection:
        columns = {
            item[1]
            for item in connection.execute("PRAGMA table_info(environment_lock_metadata)")
        }
    assert not columns.intersection({"lock_contents", "lock_payload", "packages"})


def test_package_mutation_marks_verified_lock_unchecked_without_rewriting(
    tmp_path, monkeypatch
):
    service, env_path, _state = _service(tmp_path, monkeypatch, [("demo-pkg", "1.2.3")])
    lock_path = env_path / "pylock.toml"
    lock_contents = _lock_text(("demo-pkg", "1.2.3"))
    lock_path.write_text(lock_contents, encoding="utf-8")
    assert service.verify("demo").status == "Verified"

    from py_env_studio.core import package_update_monitor

    cache_invalidations = []

    class Monitor:
        def invalidate_cache(self, env_name):
            cache_invalidations.append(env_name)

    monkeypatch.setattr(package_update_monitor, "PackageUpdateMonitor", Monitor)
    monkeypatch.setattr(lock_module, "EnvironmentLockService", lambda: service)

    package_manager_module._invalidate_package_update_cache("demo")

    assert cache_invalidations == ["demo"]
    assert service.get_status("demo")["status"] == "Unchecked"
    assert lock_path.read_text(encoding="utf-8") == lock_contents


def test_preview_classifies_add_upgrade_and_remove(tmp_path, monkeypatch):
    service, env_path, _state = _service(
        tmp_path,
        monkeypatch,
        [("demo-pkg", "1.0.0"), ("extra-pkg", "0.1.0")],
    )
    (env_path / "pylock.toml").write_text(
        _lock_text(("demo-pkg", "2.0.0"), ("new-pkg", "1.0.0")),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "py_env_studio.core.dependency_preview.preview_install",
        lambda *_args: SimpleNamespace(conflicts=[], breaking_changes=[]),
    )

    plan = service.preview_sync("demo")

    assert len(plan.additions) == 1
    assert plan.additions[0].package == "new-pkg"
    assert len(plan.upgrades) == 1
    assert plan.upgrades[0].package == "demo-pkg"
    assert len(plan.removals) == 1
    assert plan.removals[0].package == "extra-pkg"
    assert plan.change_count == 3


def test_preview_blocks_sync_for_unverifiable_source_version(tmp_path, monkeypatch):
    service, env_path, _state = _service(tmp_path, monkeypatch, [("demo-pkg", "1.2.3")])
    (env_path / "pylock.toml").write_text(
        _lock_text(("demo-pkg", "1.2.3")).replace('version = "1.2.3"\n', ""),
        encoding="utf-8",
    )

    plan = service.preview_sync("demo")

    assert plan.change_count == 0
    assert plan.preview_errors == [
        "Cannot verify the installed source version for demo-pkg"
    ]


def test_sync_uses_confirmed_preview_without_recomputing_it(tmp_path, monkeypatch):
    service, env_path, state = _service(tmp_path, monkeypatch, [("demo-pkg", "1.0.0")])
    (env_path / "pylock.toml").write_text(
        _lock_text(("demo-pkg", "2.0.0")), encoding="utf-8"
    )
    monkeypatch.setattr(
        service,
        "preview_sync",
        lambda _env_name: (_ for _ in ()).throw(AssertionError("preview repeated")),
    )
    calls = []

    def fake_sync(env_name, lock_path, package_names):
        calls.append((env_name, Path(lock_path), package_names))
        state[:] = [("demo-pkg", "2.0.0")]

    monkeypatch.setattr(lock_module, "sync_from_lock_file", fake_sync)

    result = service.sync_from_lock("demo")

    assert result.status == "Verified"
    assert calls == [("demo", env_path / "pylock.toml", {"demo-pkg"})]


def test_verify_rejects_malformed_lock_without_executing_content(tmp_path, monkeypatch):
    service, env_path, _state = _service(tmp_path, monkeypatch)
    (env_path / "pylock.toml").write_text(
        'lock-version = "1.0"\ncreated-by = "test"\npackages = [\n',
        encoding="utf-8",
    )

    result = service.verify("demo")

    assert result.status == "Invalid Lock"
    assert "Cannot parse pylock.toml" in result.error


def test_verify_rejects_package_without_installable_source(tmp_path, monkeypatch):
    service, env_path, _state = _service(tmp_path, monkeypatch)
    (env_path / "pylock.toml").write_text(
        'lock-version = "1.0"\ncreated-by = "test"\n'
        '[[packages]]\nname = "demo-pkg"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    result = service.verify("demo")

    assert result.status == "Invalid Lock"
    assert "no installable source" in result.error


def test_environment_path_rejects_traversal_names(tmp_path, monkeypatch):
    service, _env_path, _state = _service(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="Invalid environment name"):
        service.environment_path("../outside")


def test_status_and_verify_reject_oversized_lock_before_hashing(tmp_path, monkeypatch):
    service, env_path, _state = _service(tmp_path, monkeypatch)
    lock_path = env_path / "pylock.toml"
    with lock_path.open("wb") as lock_file:
        lock_file.truncate(lock_module.MAX_LOCK_SIZE + 1)

    status = service.get_status("demo")
    verification = service.verify("demo")

    assert status["status"] == "Invalid Lock"
    assert "16 MiB" in status["error"]
    assert verification.status == "Invalid Lock"
    assert "16 MiB" in verification.error


def test_verify_classifies_invalid_marker_types_as_invalid_lock(tmp_path, monkeypatch):
    service, env_path, _state = _service(tmp_path, monkeypatch)
    (env_path / "pylock.toml").write_text(
        _lock_text(("demo-pkg", "1.2.3")).replace(
            'version = "1.2.3"', 'version = "1.2.3"\nmarker = 42'
        ),
        encoding="utf-8",
    )

    result = service.verify("demo")

    assert result.status == "Invalid Lock"
    assert "marker" in result.error


def test_marker_filtered_package_is_not_required(tmp_path, monkeypatch):
    service, env_path, _state = _service(tmp_path, monkeypatch)
    lock_text = _lock_text(("demo-pkg", "1.2.3")).replace(
        'version = "1.2.3"',
        'version = "1.2.3"\nmarker = "sys_platform == \'never-a-platform\'"',
    )
    (env_path / "pylock.toml").write_text(lock_text, encoding="utf-8")
    monkeypatch.setattr(
        service,
        "_marker_environment",
        lambda _python: (default_environment(), "3.13.7"),
    )

    result = service.verify("demo")

    assert result.status == "Verified"


@pytest.mark.parametrize("manager", ["pip", "uv"])
def test_package_manager_sync_routes_pylock_and_invalidates_caches(
    tmp_path, monkeypatch, manager
):
    lock_path = tmp_path / "pylock.toml"
    lock_path.write_text(_lock_text(("demo-pkg", "1.2.3")), encoding="utf-8")
    monkeypatch.setattr(
        package_manager_module, "get_env_package_manager", lambda _name: manager
    )
    monkeypatch.setattr(
        package_manager_module, "get_env_python", lambda _name: "python.exe"
    )
    monkeypatch.setattr(
        package_manager_module,
        "list_packages",
        lambda _name: [("demo_pkg", "1.2.3"), ("extra-pkg", "0.1.0")],
    )
    removed = []
    invalidated = []
    calls = []
    monkeypatch.setattr(
        package_manager_module,
        "uninstall_package",
        lambda _env, name: removed.append(name),
    )
    monkeypatch.setattr(
        package_manager_module,
        "_invalidate_package_update_cache",
        invalidated.append,
    )
    monkeypatch.setattr(
        package_manager_module.subprocess,
        "run",
        lambda command, **_kwargs: calls.append(command)
        or SimpleNamespace(returncode=0, stderr="", stdout=""),
    )
    if manager == "uv":
        monkeypatch.setattr(package_manager_module.shutil, "which", lambda _name: "uv")

    package_manager_module.sync_from_lock_file("demo", lock_path, {"demo-pkg"})

    assert len(calls) == 1
    assert str(lock_path) in calls[0]
    if manager == "uv":
        assert calls[0][:3] == ["uv", "pip", "sync"]
        assert "--strict" in calls[0]
        assert removed == []
    else:
        assert calls[0][1:4] == ["-m", "pip", "install"]
        assert removed == ["extra-pkg"]
    assert invalidated == ["demo"]


def test_failed_lock_sync_invalidates_environment_after_mutation_starts(
    tmp_path, monkeypatch
):
    lock_path = tmp_path / "pylock.toml"
    lock_path.write_text(_lock_text(("demo-pkg", "1.2.3")), encoding="utf-8")
    invalidated = []
    monkeypatch.setattr(
        package_manager_module, "get_env_package_manager", lambda _name: "pip"
    )
    monkeypatch.setattr(
        package_manager_module, "get_env_python", lambda _name: "python.exe"
    )
    monkeypatch.setattr(
        package_manager_module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1, stderr="installation failed", stdout=""
        ),
    )
    monkeypatch.setattr(
        package_manager_module, "_invalidate_package_update_cache", invalidated.append
    )

    with pytest.raises(RuntimeError, match="installation failed"):
        package_manager_module.sync_from_lock_file("demo", lock_path, {"demo-pkg"})

    assert invalidated == ["demo"]