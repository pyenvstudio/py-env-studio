"""Tests for plugin folder resolution and manifest-driven loading.

Regression guard for plugins whose folder name differs from the ``name`` in
their manifest (``plugins/sample_plugin_v2/plugin.json`` declares
``sample_plugin2``): discovery and the enabled-state file both key on the
manifest name, so ``load_plugin`` must resolve the folder, not assume it.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

from py_env_studio.core.plugins import PluginManager
from py_env_studio.core.plugins.exceptions import PluginLoadError

MODULE_TEMPLATE = '''"""Test plugin module."""
from py_env_studio.core.plugins import BasePlugin, PluginMetadata


class {class_name}(BasePlugin):
    def get_metadata(self):
        return PluginMetadata(
            name="{declared_name}",
            version="1.0.0",
            author="tests",
            description="{description}",
            entry_point="{module_name}:{class_name}",
            hooks=[],
        )

    def initialize(self, app_context):
        self._initialized = True
        self.seen_context = app_context

    def execute(self, hook, context):
        return hook
'''


@pytest.fixture(autouse=True)
def _isolate_plugin_imports():
    """Plugin folders are imported by name; keep each test's imports private."""
    original_path = list(sys.path)
    original_modules = set(sys.modules)
    yield
    sys.path[:] = original_path
    for name in set(sys.modules) - original_modules:
        sys.modules.pop(name, None)


def _write_plugin(
    plugins_dir: Path,
    folder: str,
    *,
    manifest_name: str | None = None,
    declared_name: str | None = None,
    module_name: str = "impl",
    class_name: str = "TestPlugin",
    description: str = "test plugin",
    entry_point: str | None = None,
) -> Path:
    """Create a plugin folder with a module and a manifest."""
    folder_path = plugins_dir / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    (folder_path / "__init__.py").write_text("", encoding="utf-8")
    (folder_path / f"{module_name}.py").write_text(
        MODULE_TEMPLATE.format(
            class_name=class_name,
            declared_name=declared_name or manifest_name or folder,
            description=description,
            module_name=module_name,
        ),
        encoding="utf-8",
    )
    manifest = {
        "name": manifest_name or folder,
        "version": "1.0.0",
        "author": "tests",
        "description": description,
        "entry_point": entry_point or f"{module_name}:{class_name}",
        "required_version": "1.0.0",
        "dependencies": [],
        "hooks": [],
    }
    (folder_path / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return folder_path


class TestPluginDirResolution:
    def test_resolves_folder_named_like_the_plugin(self, tmp_path):
        _write_plugin(tmp_path, "sample_plugin")
        manager = PluginManager(plugins_dir=tmp_path)

        assert manager.resolve_plugin_dir("sample_plugin") == tmp_path / "sample_plugin"

    def test_resolves_folder_whose_manifest_declares_the_name(self, tmp_path):
        _write_plugin(tmp_path, "sample_plugin_v2", manifest_name="sample_plugin2")
        manager = PluginManager(plugins_dir=tmp_path)

        assert manager.resolve_plugin_dir("sample_plugin2") == tmp_path / "sample_plugin_v2"

    def test_unknown_plugin_resolves_to_none(self, tmp_path):
        _write_plugin(tmp_path, "sample_plugin")
        manager = PluginManager(plugins_dir=tmp_path)

        assert manager.resolve_plugin_dir("does_not_exist") is None

    def test_folder_without_manifest_is_ignored(self, tmp_path):
        (tmp_path / "sample_plugin2").mkdir()
        manager = PluginManager(plugins_dir=tmp_path)

        assert manager.resolve_plugin_dir("sample_plugin2") is None

    def test_folder_name_wins_over_a_manifest_name_collision(self, tmp_path):
        _write_plugin(tmp_path, "alpha", manifest_name="beta")
        _write_plugin(tmp_path, "beta", manifest_name="alpha")
        manager = PluginManager(plugins_dir=tmp_path)

        assert manager.resolve_plugin_dir("beta") == tmp_path / "beta"


class TestPluginLoading:
    def test_loads_plugin_whose_folder_differs_from_manifest_name(self, tmp_path):
        _write_plugin(tmp_path, "sample_plugin_v2", manifest_name="sample_plugin2")
        manager = PluginManager(plugins_dir=tmp_path)
        manager.set_app_context(
            {"app": None, "config": None, "logger": logging.getLogger("test")}
        )

        plugin = manager.load_plugin("sample_plugin2")

        assert plugin.get_metadata().name == "sample_plugin2"
        assert plugin.is_initialized is True

    def test_every_discovered_plugin_can_be_auto_loaded(self, tmp_path):
        """The startup path: discover, then load each enabled name."""
        _write_plugin(tmp_path, "sample_plugin")
        _write_plugin(tmp_path, "sample_plugin_v2", manifest_name="sample_plugin2")
        manager = PluginManager(plugins_dir=tmp_path)

        discovered = manager.discover_plugins()
        loaded = [manager.load_plugin(name).get_metadata().name for name in discovered]

        assert discovered == ["sample_plugin", "sample_plugin2"]
        assert loaded == discovered

    def test_utf8_manifest_is_read_correctly(self, tmp_path):
        _write_plugin(tmp_path, "unicode_plugin", description="caf\u00e9 \u2713 \u00dcn\u00efcode")
        manager = PluginManager(plugins_dir=tmp_path)

        plugin = manager.load_plugin("unicode_plugin")

        assert plugin.get_metadata().description == "caf\u00e9 \u2713 \u00dcn\u00efcode"

    def test_same_module_name_in_two_plugins_stays_isolated(self, tmp_path):
        _write_plugin(tmp_path, "plugin_alpha", class_name="AlphaPlugin")
        _write_plugin(tmp_path, "plugin_beta", class_name="BetaPlugin")
        manager = PluginManager(plugins_dir=tmp_path)

        alpha = manager.load_plugin("plugin_alpha")
        beta = manager.load_plugin("plugin_beta")

        assert type(alpha).__name__ == "AlphaPlugin"
        assert type(beta).__name__ == "BetaPlugin"

    def test_manifest_name_mismatch_warns_but_still_loads(self, tmp_path, caplog):
        _write_plugin(
            tmp_path,
            "renamed_folder",
            manifest_name="plugin_from_manifest",
            declared_name="plugin_from_class",
        )
        manager = PluginManager(plugins_dir=tmp_path)

        with caplog.at_level(logging.WARNING, logger="py_env_studio.core.plugins.manager"):
            plugin = manager.load_plugin("plugin_from_manifest")

        assert plugin.is_initialized is False  # no app context was supplied
        assert "metadata name mismatch" in caplog.text

    def test_missing_plugin_raises_load_error_naming_the_plugin(self, tmp_path):
        manager = PluginManager(plugins_dir=tmp_path)

        with pytest.raises(PluginLoadError, match="does_not_exist"):
            manager.load_plugin("does_not_exist")

    def test_invalid_entry_point_raises_load_error(self, tmp_path):
        _write_plugin(tmp_path, "broken_plugin", entry_point="impl")
        manager = PluginManager(plugins_dir=tmp_path)

        with pytest.raises(PluginLoadError, match="Invalid entry point"):
            manager.load_plugin("broken_plugin")

    def test_unimportable_plugin_module_raises_load_error(self, tmp_path):
        _write_plugin(tmp_path, "missing_module", entry_point="nope:TestPlugin")
        manager = PluginManager(plugins_dir=tmp_path)

        with pytest.raises(PluginLoadError, match="Unable to import plugin module"):
            manager.load_plugin("missing_module")
