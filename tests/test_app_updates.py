"""Tests for Py Env Studio's application-update workflow."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace

import pytest

from py_env_studio.core import app_updates


def test_installed_distribution_version_is_preferred(monkeypatch):
    monkeypatch.setattr(app_updates, "version", lambda _package: "2.4.1")

    assert app_updates.get_installed_app_version() == "2.4.1"


def test_runtime_package_version_is_used_without_distribution_metadata(monkeypatch):
    def missing_distribution(_package):
        raise PackageNotFoundError("py-env-studio")

    monkeypatch.setattr(app_updates, "version", missing_distribution)
    monkeypatch.setattr(
        app_updates,
        "get_runtime_config",
        lambda: SimpleNamespace(app_version="2.3.0"),
    )

    assert app_updates.get_installed_app_version() == "2.3.0"


def test_check_for_app_update_compares_pypi_release(monkeypatch):
    class Response:
        @staticmethod
        def raise_for_status():
            pass

        @staticmethod
        def json():
            return {"info": {"version": "2.2.0"}}

    requests = []
    monkeypatch.setattr(
        app_updates.requests,
        "get",
        lambda url, **kwargs: requests.append((url, kwargs)) or Response(),
    )

    status = app_updates.check_for_app_update("2.1.0")

    assert status.current_version == "2.1.0"
    assert status.latest_version == "2.2.0"
    assert status.update_available is True
    assert requests[0][1]["timeout"] == 10


def test_check_for_app_update_does_not_downgrade_newer_prerelease(monkeypatch):
    class Response:
        @staticmethod
        def raise_for_status():
            pass

        @staticmethod
        def json():
            return {"info": {"version": "2.1.0"}}

    monkeypatch.setattr(app_updates.requests, "get", lambda *_args, **_kwargs: Response())

    status = app_updates.check_for_app_update("2.2.0rc1")

    assert status.update_available is False


def test_install_uses_current_interpreter_and_pinned_distribution(monkeypatch):
    commands = []
    monkeypatch.setattr(app_updates, "is_frozen_build", lambda: False)
    monkeypatch.setattr(app_updates.sys, "executable", "python-test")
    monkeypatch.setattr(
        app_updates.subprocess,
        "run",
        lambda command, **kwargs: commands.append((command, kwargs))
        or SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    app_updates.install_app_update("2.2.0")

    command, options = commands[0]
    assert command == [
        "python-test", "-m", "pip", "install", "--upgrade", "py-env-studio==2.2.0"
    ]
    assert options["capture_output"] is True
    assert options["text"] is True
    assert options["timeout"] == 600


def test_install_refuses_to_run_pip_from_frozen_build(monkeypatch):
    monkeypatch.setattr(app_updates, "is_frozen_build", lambda: True)
    monkeypatch.setattr(
        app_updates.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("frozen builds must not invoke pip"),
    )

    with pytest.raises(RuntimeError, match="Bundled builds"):
        app_updates.install_app_update("2.2.0")