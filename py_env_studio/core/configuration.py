from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import re
import tempfile
from typing import Iterable

from platformdirs import PlatformDirs


APP_NAME = "PyEnvStudio"
APP_AUTHOR = "PyEnvStudio"


class ConfigurationError(ValueError):
    """Raised when configuration values are invalid."""


@dataclass(frozen=True)
class AppPreferences:
    default_venv_path: str
    default_python_path: str
    default_python_version: str
    default_package_manager: str
    default_project_tool: str
    open_with_tools: list[str]
    template_create_venv_default: bool
    template_initialize_git_default: bool
    appearance_mode: str
    ui_scaling: str
    runtime_provider: str
    default_python: str


def _user_config_path() -> Path:
    dirs = PlatformDirs(APP_NAME, appauthor=APP_AUTHOR)
    return Path(dirs.user_data_dir).resolve() / "config.ini"


def _package_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config.ini"


def _new_parser() -> ConfigParser:
    return ConfigParser(interpolation=None)


def _normalize_open_with_entries(raw: str | None) -> list[str]:
    if not raw:
        return ["CMD"]
    entries: list[str] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        entries.append(value)
    return entries or ["CMD"]


def _write_atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-config-")
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8", closefd=True) as handle:
            handle.write(text)
            handle.flush()
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


class ConfigurationService:
    """Single source of truth for user configuration persistence and validation."""

    SUPPORTED_PACKAGE_MANAGERS = ("pip", "uv")
    SUPPORTED_RUNTIME_PROVIDERS = ("Python Install Manager", "System", "Custom")
    SUPPORTED_APPEARANCE_MODES = ("Light", "Dark", "System")
    SUPPORTED_UI_SCALING = ("80%", "90%", "100%", "110%", "120%")

    def __init__(
        self,
        config_path: Path | None = None,
        package_defaults_path: Path | None = None,
    ) -> None:
        self.config_path = config_path.resolve() if config_path else _user_config_path()
        self.package_defaults_path = (
            package_defaults_path.resolve() if package_defaults_path else _package_config_path()
        )
        self._ensure_bootstrapped()

    def _ensure_bootstrapped(self) -> None:
        if self.config_path.exists():
            return

        parser = self._load_default_parser()

        # Migrate existing package settings if present.
        legacy = _new_parser()
        legacy.read(self.package_defaults_path, encoding="utf-8")
        for key in (
            "venv_dir",
            "python_path",
            "default_python_version",
            "preferred_package_manager",
            "open_with_tools",
            "preferred_project_editor",
        ):
            value = legacy.get("settings", key, fallback=None)
            if value is not None:
                if not parser.has_section("settings"):
                    parser.add_section("settings")
                parser.set("settings", key, value)

        self._save_parser(parser)

    def _load_default_parser(self) -> ConfigParser:
        parser = _new_parser()
        parser.read(self.package_defaults_path, encoding="utf-8")
        if not parser.has_section("settings"):
            parser.add_section("settings")
        defaults = {
            "venv_dir": "~/.py_env_studio/venvs",
            "python_path": "",
            "default_python_version": "",
            "preferred_package_manager": "pip",
            "open_with_tools": "CMD",
            "preferred_project_editor": "",
            "template_create_venv_default": "true",
            "template_initialize_git_default": "true",
            "appearance_mode": "System",
            "ui_scaling": "100%",
            "runtime_provider": "Python Install Manager",
            "default_python": "",
        }
        for option, value in defaults.items():
            if not parser.has_option("settings", option):
                parser.set("settings", option, value)
        return parser

    def _load_parser(self) -> ConfigParser:
        parser = self._load_default_parser()
        if self.config_path.exists():
            parser.read(self.config_path, encoding="utf-8")
        return parser

    def _save_parser(self, parser: ConfigParser) -> None:
        from io import StringIO

        buffer = StringIO()
        parser.write(buffer)
        _write_atomic_text(self.config_path, buffer.getvalue())

    @staticmethod
    def _parse_bool(raw_value: str | bool | None, default_value: bool) -> bool:
        if isinstance(raw_value, bool):
            return raw_value
        if raw_value is None:
            return default_value
        value = raw_value.strip().lower()
        return value in {"1", "true", "yes", "on"}

    def load_preferences(self) -> AppPreferences:
        parser = self._load_parser()
        settings = parser["settings"]
        return AppPreferences(
            default_venv_path=settings.get("venv_dir", "~/.py_env_studio/venvs"),
            default_python_path=settings.get("python_path", ""),
            default_python_version=settings.get("default_python_version", ""),
            default_package_manager=settings.get("preferred_package_manager", "pip").lower(),
            default_project_tool=settings.get("preferred_project_editor", "").strip(),
            open_with_tools=_normalize_open_with_entries(settings.get("open_with_tools", "CMD")),
            template_create_venv_default=self._parse_bool(
                settings.get("template_create_venv_default"), True
            ),
            template_initialize_git_default=self._parse_bool(
                settings.get("template_initialize_git_default"), True
            ),
            appearance_mode=settings.get("appearance_mode", "System"),
            ui_scaling=settings.get("ui_scaling", "100%"),
            runtime_provider=settings.get("runtime_provider", "Python Install Manager"),
            default_python=settings.get("default_python", ""),
        )

    def validate_preferences(
        self,
        preferences: AppPreferences,
        available_project_tools: Iterable[str] | None = None,
    ) -> None:
        venv_path = Path(preferences.default_venv_path).expanduser()
        try:
            venv_path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise ConfigurationError(f"Virtual environment path is not writable: {venv_path}") from exc

        if preferences.default_python_path:
            python_path = Path(preferences.default_python_path).expanduser()
            if not python_path.exists():
                raise ConfigurationError(
                    f"Configured Python executable does not exist: {python_path}"
                )

        if preferences.default_package_manager not in self.SUPPORTED_PACKAGE_MANAGERS:
            supported = ", ".join(self.SUPPORTED_PACKAGE_MANAGERS)
            raise ConfigurationError(
                f"Unsupported package manager: {preferences.default_package_manager}. Supported: {supported}"
            )

        if preferences.default_package_manager == "uv":
            from . import uv_tools

            if not uv_tools.is_uv_installed():
                raise ConfigurationError("Selected package manager 'uv' is not installed.")

        if preferences.appearance_mode not in self.SUPPORTED_APPEARANCE_MODES:
            raise ConfigurationError(
                f"Unsupported appearance mode: {preferences.appearance_mode}"
            )



        if preferences.runtime_provider not in self.SUPPORTED_RUNTIME_PROVIDERS:
            supported = ", ".join(self.SUPPORTED_RUNTIME_PROVIDERS)
            raise ConfigurationError(
                f"Unsupported runtime provider: {preferences.runtime_provider}. Supported: {supported}"
            )
        if preferences.default_python and not re.match(r"^\d+(?:\.\d+)*$", preferences.default_python):
            raise ConfigurationError(
                f"Invalid default Python identifier: {preferences.default_python}"
            )

        if preferences.ui_scaling not in self.SUPPORTED_UI_SCALING:
            raise ConfigurationError(
                f"Unsupported UI scaling value: {preferences.ui_scaling}"
            )

        if available_project_tools is not None and preferences.default_project_tool:
            normalized = {item.strip().lower() for item in available_project_tools if item.strip()}
            if preferences.default_project_tool.strip().lower() not in normalized:
                raise ConfigurationError(
                    f"Selected project tool is unavailable: {preferences.default_project_tool}"
                )

    def save_preferences(self, preferences: AppPreferences) -> None:
        parser = self._load_parser()
        if not parser.has_section("settings"):
            parser.add_section("settings")
        parser.set("settings", "venv_dir", preferences.default_venv_path)
        parser.set("settings", "python_path", preferences.default_python_path)
        parser.set("settings", "default_python_version", preferences.default_python_version)
        parser.set("settings", "preferred_package_manager", preferences.default_package_manager)
        parser.set("settings", "preferred_project_editor", preferences.default_project_tool)
        parser.set("settings", "open_with_tools", ",".join(preferences.open_with_tools))
        parser.set(
            "settings",
            "template_create_venv_default",
            str(preferences.template_create_venv_default).lower(),
        )
        parser.set(
            "settings",
            "template_initialize_git_default",
            str(preferences.template_initialize_git_default).lower(),
        )
        parser.set("settings", "appearance_mode", preferences.appearance_mode)
        parser.set("settings", "ui_scaling", preferences.ui_scaling)
        parser.set("settings", "runtime_provider", preferences.runtime_provider)
        parser.set("settings", "default_python", preferences.default_python)
        self._save_parser(parser)

    def reset_to_defaults(self) -> AppPreferences:
        parser = self._load_default_parser()
        self._save_parser(parser)
        return self.load_preferences()


class AppConfig:
    def __init__(self, config_path: str | None = None):
        default_path = _user_config_path()
        self.config_path = Path(config_path).resolve() if config_path else default_path
        self._service = ConfigurationService(config_path=self.config_path)
        self.version = self._load_version()

    def _load_version(self) -> str:
        config = _new_parser()
        config.read(_package_config_path(), encoding="utf-8")
        return config.get("project", "version", fallback="1.0.0")

    def get_param(self, section: str, option: str, fallback: str | None = None) -> str | None:
        config = self._service._load_parser()
        return config.get(section, option, fallback=fallback)

    def set_param(self, section: str, option: str, value: str) -> None:
        config = self._service._load_parser()
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)
        self._service._save_parser(config)
