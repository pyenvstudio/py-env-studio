from pathlib import Path

import pytest

from py_env_studio.core.configuration import (
    AppPreferences,
    ConfigurationError,
    ConfigurationService,
)


def _write_package_defaults(path: Path) -> None:
    path.write_text(
        """[project]
version = 2.0.8

[settings]
venv_dir = ~/.py_env_studio/venvs
python_path =
preferred_package_manager = pip
open_with_tools = CMD
preferred_project_editor = default
""",
        encoding="utf-8",
    )


def test_load_preferences_bootstraps_defaults(tmp_path: Path) -> None:
    defaults_path = tmp_path / "package-config.ini"
    _write_package_defaults(defaults_path)

    service = ConfigurationService(
        config_path=tmp_path / "user-config.ini",
        package_defaults_path=defaults_path,
    )

    prefs = service.load_preferences()

    assert prefs.default_venv_path == "~/.py_env_studio/venvs"
    assert prefs.default_package_manager == "pip"
    assert prefs.template_create_venv_default is True
    assert prefs.template_initialize_git_default is True


def test_save_and_reload_preferences_roundtrip(tmp_path: Path) -> None:
    defaults_path = tmp_path / "package-config.ini"
    _write_package_defaults(defaults_path)

    service = ConfigurationService(
        config_path=tmp_path / "user-config.ini",
        package_defaults_path=defaults_path,
    )

    target_venv = tmp_path / "venvs-custom"
    prefs = AppPreferences(
        default_venv_path=str(target_venv),
        default_python_path="",
        default_python_version="3.11",
        default_package_manager="pip",
        default_project_tool="default",
        open_with_tools=["CMD", "PowerShell"],
        template_create_venv_default=False,
        template_initialize_git_default=True,
        appearance_mode="Dark",
        ui_scaling="110%",
        runtime_provider="Python Install Manager",
        default_python="",
    )

    service.validate_preferences(prefs, available_project_tools=["default", "vscode"])
    service.save_preferences(prefs)

    reloaded = service.load_preferences()
    assert reloaded.default_venv_path == str(target_venv)
    assert reloaded.template_create_venv_default is False
    assert reloaded.appearance_mode == "Dark"
    assert reloaded.ui_scaling == "110%"


def test_validate_preferences_rejects_unavailable_uv(tmp_path: Path, monkeypatch) -> None:
    defaults_path = tmp_path / "package-config.ini"
    _write_package_defaults(defaults_path)

    service = ConfigurationService(
        config_path=tmp_path / "user-config.ini",
        package_defaults_path=defaults_path,
    )

    monkeypatch.setattr("py_env_studio.core.uv_tools.is_uv_installed", lambda: False)

    prefs = AppPreferences(
        default_venv_path=str(tmp_path / "venvs"),
        default_python_path="",
        default_python_version="",
        default_package_manager="uv",
        default_project_tool="default",
        open_with_tools=["CMD"],
        template_create_venv_default=True,
        template_initialize_git_default=True,
        appearance_mode="System",
        ui_scaling="100%",
        runtime_provider="Python Install Manager",
        default_python="",
    )

    with pytest.raises(ConfigurationError):
        service.validate_preferences(prefs, available_project_tools=["default"])


def test_reset_to_defaults_restores_default_package_manager(tmp_path: Path) -> None:
    defaults_path = tmp_path / "package-config.ini"
    _write_package_defaults(defaults_path)

    service = ConfigurationService(
        config_path=tmp_path / "user-config.ini",
        package_defaults_path=defaults_path,
    )

    customized = AppPreferences(
        default_venv_path=str(tmp_path / "venvs"),
        default_python_path="",
        default_python_version="3.12",
        default_package_manager="pip",
        default_project_tool="default",
        open_with_tools=["CMD"],
        template_create_venv_default=False,
        template_initialize_git_default=False,
        appearance_mode="Light",
        ui_scaling="90%",
        runtime_provider="Python Install Manager",
        default_python="",
    )
    service.save_preferences(customized)

    defaults = service.reset_to_defaults()

    assert defaults.default_package_manager == "pip"
    assert defaults.template_create_venv_default is True
    assert defaults.template_initialize_git_default is True
