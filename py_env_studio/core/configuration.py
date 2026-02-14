from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path


class AppConfig:
    def __init__(self, config_path: str | None = None):
        default_path = Path(__file__).resolve().parents[1] / "config.ini"
        self.config_path = Path(config_path).resolve() if config_path else default_path
        self.version = self._load_version()

    def _load_version(self) -> str:
        config = ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        return config.get("project", "version", fallback="1.0.0")

    def get_param(self, section: str, option: str, fallback: str | None = None) -> str | None:
        config = ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        return config.get(section, option, fallback=fallback)

    def set_param(self, section: str, option: str, value: str) -> None:
        config = ConfigParser()
        config.read(self.config_path, encoding="utf-8")
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)
        with open(self.config_path, "w", encoding="utf-8") as config_file:
            config.write(config_file)
