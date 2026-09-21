"""Minimal MCP configuration (local / stdio / read-only defaults)."""

from __future__ import annotations

SERVER_NAME = "py-env-studio"
PROTOCOL_VERSION = "2024-11-05"


def load_mcp_settings():
    """Return MCP settings from existing AppConfig with safe defaults.

    Keys (section ``mcp``): enabled, server_name, transport, log_level.
    Defaults favour local stdio read-only operation; no new files are
    created beyond the existing user config when values are read.
    """
    from py_env_studio.core.configuration import AppConfig

    config = AppConfig()
    return {
        "enabled": (config.get_param("mcp", "enabled", fallback="true") or "true")
        .strip()
        .lower()
        not in ("0", "false", "no", "off"),
        "server_name": config.get_param("mcp", "server_name", fallback=SERVER_NAME)
        or SERVER_NAME,
        "transport": (
            config.get_param("mcp", "transport", fallback="stdio") or "stdio"
        ).strip().lower(),
        "log_level": (
            config.get_param("mcp", "log_level", fallback="INFO") or "INFO"
        ).strip().upper(),
    }
