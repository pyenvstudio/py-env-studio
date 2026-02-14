"""PyEnvStudio Plugin System.

This module provides the plugin infrastructure for extending PyEnvStudio functionality.
"""

from py_env_studio.core.plugins.base import BasePlugin, PluginMetadata, PluginHook
from py_env_studio.core.plugins.manager import PluginManager
from py_env_studio.core.plugins.exceptions import (
    PluginException,
    PluginLoadError,
    PluginValidationError,
)

__all__ = [
    "BasePlugin",
    "PluginMetadata",
    "PluginHook",
    "PluginManager",
    "PluginException",
    "PluginLoadError",
    "PluginValidationError",
]
