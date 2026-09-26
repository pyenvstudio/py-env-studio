"""Temporary end-to-end verification of the three reported issues."""
import io
import logging
import tempfile
from pathlib import Path

from py_env_studio.core.plugins import PluginManager
from py_env_studio.core.runtime_providers import (
    PythonInstallManagerProvider,
    find_legacy_python_launcher,
)
from py_env_studio.utils.app_logging import configure_logging

print("=== 1. plugin 'sample_plugin2' (manifest name != folder name) ===")
manager = PluginManager()
manager.set_app_context({"app": None, "config": None, "logger": logging.getLogger("verify")})
print("discovered:", manager.discover_plugins())
print("resolve_plugin_dir('sample_plugin2'):", manager.resolve_plugin_dir("sample_plugin2"))
plugin = manager.load_plugin("sample_plugin2")
print("loaded:", plugin.get_metadata().name, "| initialized:", plugin.is_initialized)
print("enabled state:", manager.get_enabled_plugins_list())

print()
print("=== 2. legacy py.exe must not be mistaken for Python Install Manager ===")
provider = PythonInstallManagerProvider()
print("resolved executable:", provider._py)
print("is_available():", provider.is_available())
print("find_legacy_python_launcher():", find_legacy_python_launcher())

print()
print("=== 3. cp1252 console logging must not raise UnicodeEncodeError ===")
raw = io.BytesIO()
stream = io.TextIOWrapper(raw, encoding="cp1252")
errors = []
configure_logging(
    "info",
    log_file=Path(tempfile.gettempdir()) / "pes_verify.log",
    console_stream=stream,
)
logging.Handler.handleError = lambda self, record: errors.append(record)
logger = logging.getLogger("verify")
logger.info("\u2713 Executed on_app_start hook for all plugins")
logger.error("\u2717 Failed to auto-load plugin 'sample_plugin2'")
stream.flush()
print("handler errors:", errors)
print("console bytes ->", repr(raw.getvalue().decode("cp1252").strip()))
