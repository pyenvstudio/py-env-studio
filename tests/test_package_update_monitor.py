"""Tests for per-environment package-update opt-in and caching."""

from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from py_env_studio.core import env_manager, package_manager, package_update_monitor
from py_env_studio.core.database import DatabaseManager


def _make_monitor(tmp_path: Path, monkeypatch, manager: str = "pip", ttl=timedelta(hours=6)):
    envs = tmp_path / "envs"
    env_dir = envs / "sample"
    python = env_dir / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    (env_dir / "pyvenv.cfg").write_text("home = test\n", encoding="utf-8")
    monkeypatch.setattr(package_update_monitor, "VENV_DIR", str(envs))
    monkeypatch.setattr(package_update_monitor, "get_env_python", lambda _name: str(python))
    monkeypatch.setattr(package_update_monitor, "get_env_package_manager", lambda _name: manager)
    db_manager = DatabaseManager(tmp_path / "updates.sqlite")
    monitor = package_update_monitor.PackageUpdateMonitor(db_manager, ttl=ttl)
    return monitor, python


@pytest.mark.parametrize("enabled", [False, True])
def test_create_env_persists_package_update_opt_in(tmp_path, monkeypatch, enabled):
    envs = tmp_path / "envs"
    monkeypatch.setattr(env_manager, "VENV_DIR", str(envs))
    monkeypatch.setattr(env_manager, "ENV_DATA_FILE", str(envs / "env_data.json"))
    monkeypatch.setattr(env_manager, "get_preferred_package_manager", lambda: "pip")
    monkeypatch.setattr(env_manager, "_extract_python_version", lambda _path: "3.12")
    monkeypatch.setattr(env_manager, "calculate_env_size_mb", lambda _path: 1.0)

    class SuccessfulProcess:
        stdout = ()
        returncode = 0

        @staticmethod
        def wait():
            return 0

    monkeypatch.setattr(env_manager.subprocess, "Popen", lambda *_args, **_kwargs: SuccessfulProcess())

    env_manager.create_env(
        "sample",
        python_path="python",
        package_update_check_enabled=enabled,
    )

    metadata = json.loads((envs / "env_data.json").read_text(encoding="utf-8"))
    assert metadata["sample"]["package_update_check_enabled"] is enabled


def test_existing_env_metadata_defaults_to_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(env_manager, "ENV_DATA_FILE", str(tmp_path / "env_data.json"))
    env_manager.set_env_data("legacy")

    assert env_manager.get_env_data("legacy")["package_update_check_enabled"] is False


def test_get_env_python_uses_platform_executable_name(tmp_path, monkeypatch):
    monkeypatch.setattr(env_manager, "VENV_DIR", str(tmp_path / "envs"))

    python_path = Path(env_manager.get_env_python("sample"))

    assert python_path.name == ("python.exe" if env_manager.os.name == "nt" else "python")


def test_existing_database_keeps_environments_and_adds_cache_table(tmp_path):
    database_path = tmp_path / "existing.sqlite"
    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TABLE environments (env_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "env_name TEXT UNIQUE NOT NULL, env_path TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    connection.execute(
        "INSERT INTO environments (env_name, env_path) VALUES (?, ?)",
        ("legacy", str(tmp_path / "legacy")),
    )
    connection.execute(
        "CREATE TABLE package_update_cache (env_id INTEGER PRIMARY KEY, outdated_count INTEGER, "
        "last_checked_at TEXT NOT NULL, package_manager TEXT NOT NULL, error TEXT, "
        "FOREIGN KEY (env_id) REFERENCES environments(env_id))"
    )
    connection.commit()
    connection.close()

    DatabaseManager(database_path).initialize_database()

    connection = sqlite3.connect(database_path)
    try:
        existing = connection.execute(
            "SELECT env_name FROM environments WHERE env_name='legacy'"
        ).fetchone()
        cache_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='package_update_cache'"
        ).fetchone()
        cache_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(package_update_cache)")
        }
    finally:
        connection.close()
    assert existing == ("legacy",)
    assert cache_table == ("package_update_cache",)
    assert "outdated_packages" in cache_columns


def test_cache_hit_prevents_another_package_check(tmp_path, monkeypatch):
    monitor, _python = _make_monitor(tmp_path, monkeypatch)
    checks = []
    monkeypatch.setattr(
        package_update_monitor,
        "check_outdated_packages",
        lambda name: checks.append(name) or json.dumps([{"name": "demo"}, {"name": "other"}]),
    )

    result = monitor.check_environment("sample")

    assert result["outdated_count"] == 2
    cached = monitor.get_cached_result("sample", "pip")
    assert cached["outdated_count"] == 2
    assert [package["name"] for package in cached["outdated_packages"]] == ["demo", "other"]
    assert not monitor.needs_check("sample", "pip")
    assert checks == ["sample"]


def test_check_if_stale_reuses_fresh_result(tmp_path, monkeypatch):
    monitor, _python = _make_monitor(tmp_path, monkeypatch)
    checks = []
    monkeypatch.setattr(
        package_update_monitor,
        "check_outdated_packages",
        lambda name: checks.append(name) or "[]",
    )

    first = monitor.check_if_stale("sample")
    second = monitor.check_if_stale("sample")

    assert first["outdated_count"] == second["outdated_count"] == 0
    assert checks == ["sample"]


def test_manual_result_can_be_saved_to_shared_cache(tmp_path, monkeypatch):
    monitor, _python = _make_monitor(tmp_path, monkeypatch, manager="uv")

    details = [{"name": "demo", "version": "1", "latest_version": "2"}]
    result = monitor.record_result("sample", 1, outdated_packages=details)
    cached = monitor.get_cached_result("sample", "uv")

    assert result["outdated_count"] == cached["outdated_count"] == 1
    assert cached["package_manager"] == "uv"
    assert cached["last_checked_at"]
    assert cached["outdated_packages"] == details


def test_missing_and_stale_cache_require_a_check(tmp_path, monkeypatch):
    monitor, _python = _make_monitor(
        tmp_path, monkeypatch, ttl=timedelta(seconds=-1)
    )
    monkeypatch.setattr(package_update_monitor, "check_outdated_packages", lambda _name: "[]")

    assert monitor.needs_check("sample", "pip")
    monitor.check_environment("sample")
    assert monitor.needs_check("sample", "pip")


def test_invalidating_environment_removes_its_cached_result(tmp_path, monkeypatch):
    monitor, _python = _make_monitor(tmp_path, monkeypatch)
    monkeypatch.setattr(package_update_monitor, "check_outdated_packages", lambda _name: "[]")
    monitor.check_environment("sample")
    assert not monitor.needs_check("sample", "pip")

    monitor.invalidate_cache("sample")

    assert monitor.needs_check("sample", "pip")


def test_failed_check_is_unavailable_not_up_to_date(tmp_path, monkeypatch):
    monitor, _python = _make_monitor(tmp_path, monkeypatch)

    def fail(_name):
        raise RuntimeError("index unavailable")

    monkeypatch.setattr(package_update_monitor, "check_outdated_packages", fail)
    result = monitor.check_environment("sample")
    cached = monitor.get_cached_result("sample", "pip")

    assert result["outdated_count"] is None
    assert result["error"] == "index unavailable"
    assert cached["error"] == "index unavailable"
    assert monitor.needs_check("sample", "pip") is False


def test_one_failed_environment_does_not_stop_another(tmp_path, monkeypatch):
    envs = tmp_path / "envs"
    for name in ("broken", "working"):
        env_dir = envs / name
        (env_dir / "Scripts").mkdir(parents=True)
        (env_dir / "Scripts" / "python.exe").touch()
        (env_dir / "pyvenv.cfg").write_text("home = test\n", encoding="utf-8")
    monkeypatch.setattr(package_update_monitor, "VENV_DIR", str(envs))
    monkeypatch.setattr(
        package_update_monitor,
        "get_env_python",
        lambda name: str(envs / name / "Scripts" / "python.exe"),
    )
    monkeypatch.setattr(package_update_monitor, "get_env_package_manager", lambda _name: "pip")
    monitor = package_update_monitor.PackageUpdateMonitor(DatabaseManager(tmp_path / "updates.sqlite"))

    def detect(name):
        if name == "broken":
            raise RuntimeError("offline")
        return json.dumps([{"name": "demo"}])

    monkeypatch.setattr(package_update_monitor, "check_outdated_packages", detect)

    assert monitor.check_environment("broken")["error"] == "offline"
    assert monitor.check_environment("working")["outdated_count"] == 1


@pytest.mark.parametrize("manager", ["pip", "uv"])
def test_existing_package_manager_path_is_used(tmp_path, monkeypatch, manager):
    monitor, python = _make_monitor(tmp_path, monkeypatch, manager=manager)
    monkeypatch.setattr(package_manager, "get_env_package_manager", lambda _name: manager)
    monkeypatch.setattr(package_manager, "get_env_python", lambda _name: str(python))

    if manager == "uv":
        calls = []

        def check_uv(path):
            calls.append(path)
            return True, [{"name": "demo", "version": "1", "latest_version": "2"}]

        monkeypatch.setattr(package_manager.uv_tools, "check_outdated_packages_uv", check_uv)
    else:
        calls = []

        def check_pip(name, log_callback=None):
            calls.append(name)
            return json.dumps([{"name": "demo"}])

        monkeypatch.setattr(package_manager.pip_tools, "check_outdated_packages", check_pip)

    monkeypatch.setattr(
        package_update_monitor,
        "check_outdated_packages",
        package_manager.check_outdated_packages,
    )
    result = monitor.check_environment("sample")

    assert result["package_manager"] == manager
    assert result["outdated_count"] == 1
    assert len(calls) == 1


@pytest.mark.parametrize("manager", ["pip", "uv"])
@pytest.mark.parametrize(
    ("operation", "pip_function", "uv_function", "arguments"),
    [
        ("install_package", "install_package", "install_package_uv", ("sample", "demo")),
        ("uninstall_package", "uninstall_package", "uninstall_package_uv", ("sample", "demo")),
        ("update_package", "update_package", "update_package_uv", ("sample", "demo")),
        ("import_requirements", "import_requirements", "import_requirements_uv", ("sample", "requirements.txt")),
    ],
)
def test_successful_package_mutations_invalidate_update_cache(
    monkeypatch, manager, operation, pip_function, uv_function, arguments
):
    invalidated = []
    monkeypatch.setattr(package_manager, "get_env_package_manager", lambda _name: manager)
    monkeypatch.setattr(package_manager, "get_env_python", lambda _name: "sample-python")
    monkeypatch.setattr(package_manager, "_invalidate_package_update_cache", invalidated.append)
    if manager == "pip":
        monkeypatch.setattr(package_manager.pip_tools, pip_function, lambda *_args, **_kwargs: None)
    else:
        monkeypatch.setattr(package_manager.uv_tools, uv_function, lambda *_args, **_kwargs: (True, "ok"))

    getattr(package_manager, operation)(*arguments)

    assert invalidated == ["sample"]


def test_failed_package_mutation_preserves_cached_update_result(monkeypatch):
    invalidated = []
    monkeypatch.setattr(package_manager, "get_env_package_manager", lambda _name: "pip")
    monkeypatch.setattr(package_manager, "_invalidate_package_update_cache", invalidated.append)

    def fail(*_args, **_kwargs):
        raise RuntimeError("install failed")

    monkeypatch.setattr(package_manager.pip_tools, "install_package", fail)

    with pytest.raises(RuntimeError, match="install failed"):
        package_manager.install_package("sample", "demo")

    assert invalidated == []


def test_environment_rows_only_schedule_opted_in_checks(monkeypatch):
    from py_env_studio.ui import main_window

    environments = ["disabled", "enabled"]
    monkeypatch.setattr(main_window, "search_envs", lambda _query: environments)
    monkeypatch.setattr(
        main_window,
        "get_env_data",
        lambda name: {"package_update_check_enabled": name == "enabled"},
    )
    monkeypatch.setattr(main_window, "get_env_package_manager", lambda _name: "pip")
    monkeypatch.setattr(main_window, "get_package_manager_display", lambda _manager: "pip")

    class Monitor:
        calls = []

        def get_cached_result(self, name, _manager):
            self.calls.append(name)
            return None

    monitor = Monitor()
    rows, checks = main_window.PyEnvStudio._collect_env_rows("", monitor)

    assert checks == ["enabled"]
    assert monitor.calls == ["enabled"]
    assert [row[3] for row in rows] == ["Disabled", "Not checked"]


def test_environment_update_labels_cover_cached_checking_and_failure():
    from py_env_studio.ui.main_window import PyEnvStudio

    assert PyEnvStudio._package_update_label(False, None) == "Disabled"
    assert PyEnvStudio._package_update_label(True, None, checking=True) == "Checking…"
    assert PyEnvStudio._package_update_label(True, None) == "Not checked"
    assert PyEnvStudio._package_update_label(True, {"outdated_count": 3}) == "3 updates"
    assert PyEnvStudio._package_update_label(True, {"outdated_count": 0}) == "Up to date"
    assert PyEnvStudio._package_update_label(True, {"error": "offline"}) == "Unavailable"


def test_cached_update_details_open_for_the_environment_whose_row_was_clicked():
    from py_env_studio.ui.main_window import PyEnvStudio

    class View:
        opened = None

        def show_updatable_packages(self, rows, env_name=None):
            self.opened = (rows, env_name)

    view = View()
    details = [{
        "name": "demo",
        "version": "1.0",
        "latest_version": "2.0",
        "latest_filetype": "wheel",
    }]
    cached = {"outdated_count": 1, "outdated_packages": details, "error": None}

    PyEnvStudio._show_cached_package_updates(view, "clicked-env", cached)

    assert view.opened == ([
        ("demo", "1.0", "2.0", "wheel"),
    ], "clicked-env")


@pytest.mark.parametrize("confirmed", [False, True])
def test_clicking_disabled_updates_prompts_before_enabling(monkeypatch, confirmed):
    from py_env_studio.ui import main_window

    class View:
        started_checks = []

        def _start_package_update_check(self, env_name):
            self.started_checks.append(env_name)

    view = View()
    saved = []
    monkeypatch.setattr(main_window, "get_env_data", lambda _name: {"package_update_check_enabled": False})
    monkeypatch.setattr(main_window, "set_env_data", lambda name, **kwargs: saved.append((name, kwargs)))
    monkeypatch.setattr(main_window.messagebox, "askyesno", lambda *_args: confirmed)

    main_window.PyEnvStudio._open_cached_package_updates(view, "sample")

    if confirmed:
        assert saved == [("sample", {"package_update_check_enabled": True})]
        assert view.started_checks == ["sample"]
    else:
        assert saved == []
        assert view.started_checks == []


@pytest.mark.parametrize("was_enabled", [False, True])
def test_double_click_updates_cell_toggles_only_that_environment(monkeypatch, was_enabled):
    from py_env_studio.ui import main_window

    saved = []

    class View:
        started_checks = []
        labels = []

        def _start_package_update_check(self, env_name):
            self.started_checks.append(env_name)

        def _set_env_update_label(self, env_name, label):
            self.labels.append((env_name, label))

    view = View()
    monkeypatch.setattr(
        main_window,
        "get_env_data",
        lambda env_name: {"package_update_check_enabled": was_enabled if env_name == "target" else False},
    )
    monkeypatch.setattr(main_window, "set_env_data", lambda name, **kwargs: saved.append((name, kwargs)))

    main_window.PyEnvStudio._toggle_package_update_check(view, "target")

    assert saved == [("target", {"package_update_check_enabled": not was_enabled})]
    assert view.started_checks == ([] if was_enabled else ["target"])
    assert view.labels == ([("target", "Disabled")] if was_enabled else [])


def test_package_manager_cache_invalidation_uses_monitor_lazily(monkeypatch):
    class Monitor:
        invalidated = []

        def invalidate_cache(self, env_name):
            self.invalidated.append(env_name)

    monitor = Monitor()
    monkeypatch.setattr(package_update_monitor, "PackageUpdateMonitor", lambda: monitor)

    package_manager._invalidate_package_update_cache("sample")

    assert monitor.invalidated == ["sample"]


def test_ui_refreshes_environment_rows_after_cache_invalidation(monkeypatch):
    from py_env_studio.ui import main_window

    class Monitor:
        invalidated = []

        def invalidate_cache(self, env_name):
            self.invalidated.append(env_name)

    class View:
        _package_update_monitor = Monitor()
        refreshed = 0

        def refresh_env_list(self):
            self.refreshed += 1

    view = View()
    monkeypatch.setattr(
        main_window,
        "run_in_background",
        lambda work, ui, on_done, on_error: on_done(work()),
    )

    main_window.PyEnvStudio._refresh_package_update_status(view, "sample")

    assert view._package_update_monitor.invalidated == ["sample"]
    assert view.refreshed == 1


def test_create_environment_form_opens_on_demand_and_reuses_dialog(monkeypatch):
    from py_env_studio.ui import main_window

    class Button:
        def __init__(self, command):
            self.command = command
            self.grid_args = None

        def grid(self, **kwargs):
            self.grid_args = kwargs

    class Dialog:
        def __init__(self):
            self.exists = True
            self.deiconified = 0
            self.lifted = 0
            self.grabbed = 0
            self.withdrawn = 0

        def title(self, _title):
            pass

        def geometry(self, _geometry):
            pass

        def minsize(self, *_size):
            pass

        def transient(self, _parent):
            pass

        def grid_columnconfigure(self, *_args, **_kwargs):
            pass

        def protocol(self, *_args):
            pass

        def grab_set(self):
            self.grabbed += 1

        def grab_release(self):
            pass

        def deiconify(self):
            self.deiconified += 1

        def lift(self):
            self.lifted += 1

        def withdraw(self):
            self.withdrawn += 1

        def winfo_exists(self):
            return self.exists

        def update_idletasks(self):
            pass

        def focus_force(self):
            pass

    class View:
        icons = {"create-env": None}

        def __init__(self):
            self.buttons = []
            self.dialog_builds = []
            self._create_env_dialog = None

        def btn(self, _parent, text, command, _image):
            button = Button(command)
            button.text = text
            self.buttons.append(button)
            return button

        def _build_env_create_form(self, dialog):
            self.dialog_builds.append(dialog)

        def winfo_screenwidth(self):
            return 1280

        def winfo_screenheight(self):
            return 800

        def open_create_environment_dialog(self):
            PyEnvStudio.open_create_environment_dialog(self)

        def close_create_environment_dialog(self):
            PyEnvStudio.close_create_environment_dialog(self)

    view = View()
    PyEnvStudio = main_window.PyEnvStudio
    PyEnvStudio._env_create_section(view, object())

    assert [button.text for button in view.buttons] == ["Create Environment"]
    assert view.dialog_builds == []

    dialog = Dialog()
    monkeypatch.setattr(main_window.ctk, "CTkToplevel", lambda _parent: dialog)
    view.buttons[0].command()
    assert view.dialog_builds == [dialog]
    assert dialog.grabbed == 1

    PyEnvStudio.close_create_environment_dialog(view)
    view.buttons[0].command()

    assert view.dialog_builds == [dialog]
    assert dialog.withdrawn == 1
    assert dialog.deiconified == 1
    assert dialog.lifted == 2