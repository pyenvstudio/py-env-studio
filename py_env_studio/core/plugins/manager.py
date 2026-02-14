"""Plugin manager for loading, validating, and executing plugins.

Implements the Factory pattern for plugin discovery and lifecycle management.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from importlib import import_module
from dataclasses import asdict

from py_env_studio.core.plugins.base import BasePlugin, PluginMetadata, PluginHook
from py_env_studio.core.plugins.exceptions import (
    PluginException,
    PluginLoadError,
    PluginValidationError,
)


logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin lifecycle: discovery, loading, validation, and execution.
    
    Follows Factory Pattern for plugin instantiation and Observer Pattern
    for hook subscriptions.
    """
    
    def __init__(self, plugins_dir: Path = None):
        """Initialize plugin manager.
        
        Args:
            plugins_dir: Directory to search for plugins (default: ~/.py_env_studio/plugins)
        """
        self.plugins_dir = plugins_dir or (Path.home() / ".py_env_studio" / "plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self._plugins: Dict[str, BasePlugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._metadata_cache: Dict[str, PluginMetadata] = {}
        self._app_context: Optional[Dict[str, Any]] = None
        
        # Plugin state management
        self._state_file = Path.home() / ".py_env_studio" / "plugin_state.json"
        self._enabled_plugins: Dict[str, bool] = self._load_plugin_state()
    
    def set_app_context(self, context: Dict[str, Any]) -> None:
        """Set application context for plugins.
        
        Args:
            context: Dictionary with app references (app, config, logger, etc.)
        """
        self._app_context = context
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugins directory.
        
        Looks for plugin.json manifest files.
        
        Returns:
            List of plugin names found
        """
        discovered = []
        if not self.plugins_dir.exists():
            return discovered
        
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            manifest_file = plugin_dir / "plugin.json"
            if manifest_file.exists():
                try:
                    manifest = json.loads(manifest_file.read_text())
                    discovered.append(manifest.get("name", plugin_dir.name))
                    logger.debug(f"Discovered plugin: {manifest.get('name')}")
                except Exception as e:
                    logger.warning(f"Failed to discover plugin in {plugin_dir}: {e}")
        
        return discovered
    
    def load_plugin(self, plugin_name: str) -> BasePlugin:
        """Load and initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to load
        
        Returns:
            Loaded plugin instance
        
        Raises:
            PluginLoadError: If plugin fails to load
        """
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]
        
        try:
            plugin_dir = self.plugins_dir / plugin_name
            manifest_file = plugin_dir / "plugin.json"
            
            if not manifest_file.exists():
                raise PluginLoadError(f"Plugin manifest not found: {manifest_file}")
            
            # Load manifest
            manifest = json.loads(manifest_file.read_text())
            metadata = self._manifest_to_metadata(manifest)
            
            # Add plugin directory to sys.path for imports
            plugin_parent = str(self.plugins_dir)
            if plugin_parent not in sys.path:
                sys.path.insert(0, plugin_parent)
            
            # Import and instantiate plugin
            entry_point = metadata.entry_point
            module_path, class_name = entry_point.split(":")
            
            module = import_module(module_path)
            plugin_class = getattr(module, class_name)
            plugin = plugin_class()
            
            # Validate plugin
            if not self._validate_plugin(plugin, metadata):
                raise PluginValidationError(f"Plugin validation failed: {plugin_name}")
            
            # Initialize plugin
            if self._app_context:
                plugin._app_context = self._app_context
                plugin.initialize(self._app_context)
                plugin._initialized = True
            
            self._plugins[plugin_name] = plugin
            self._metadata_cache[plugin_name] = metadata
            
            # Register hooks
            for hook in metadata.hooks:
                self._register_hook(plugin_name, hook, plugin)
            
            logger.info(f"Loaded plugin: {plugin_name} (v{metadata.version})")
            return plugin
        
        except PluginException:
            raise
        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin '{plugin_name}': {str(e)}")
    
    def unload_plugin(self, plugin_name: str) -> None:
        """Unload and cleanup a plugin.
        
        Args:
            plugin_name: Name of the plugin to unload
        """
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin not loaded: {plugin_name}")
            return
        
        plugin = self._plugins[plugin_name]
        
        # Cleanup plugin
        try:
            plugin.cleanup()
        except Exception as e:
            logger.error(f"Error during plugin cleanup: {e}")
        
        # Remove from hooks
        for hook_list in self._hooks.values():
            hook_list[:] = [h for h in hook_list if not self._is_plugin_hook(h, plugin_name)]
        
        del self._plugins[plugin_name]
        logger.info(f"Unloaded plugin: {plugin_name}")
    
    def execute_hook(self, hook: str, context: Dict[str, Any] = None) -> List[Any]:
        """Execute all subscribed handlers for a hook.
        
        Args:
            hook: Hook name to execute
            context: Context data to pass to handlers
        
        Returns:
            List of results from each handler
        """
        if context is None:
            context = {}
        
        results = []
        handlers = self._hooks.get(hook, [])
        
        for handler in handlers:
            try:
                result = handler(context)
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing hook '{hook}': {e}")
        
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get loaded plugin by name.
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            Plugin instance or None if not loaded
        """
        return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Get all loaded plugins.
        
        Returns:
            Dictionary of plugin_name -> plugin_instance
        """
        return self._plugins.copy()
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a plugin.
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            PluginMetadata or None if not found
        """
        return self._metadata_cache.get(plugin_name)
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if plugin is enabled (loaded).
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            True if plugin is loaded and initialized
        """
        plugin = self._plugins.get(plugin_name)
        return plugin is not None and plugin.is_initialized
    
    def load_enabled_plugins(self, enabled_list: List[str]) -> None:
        """Load a list of enabled plugins.
        
        Args:
            enabled_list: List of plugin names to load
        """
        for plugin_name in enabled_list:
            try:
                self.load_plugin(plugin_name)
            except PluginException as e:
                logger.error(f"Failed to load enabled plugin '{plugin_name}': {e}")
    
    # Private helper methods
    
    def _validate_plugin(self, plugin: BasePlugin, metadata: PluginMetadata) -> bool:
        """Validate plugin integrity.
        
        Args:
            plugin: Plugin instance to validate
            metadata: Plugin metadata
        
        Returns:
            True if valid
        """
        try:
            # Check metadata
            if plugin.get_metadata().name != metadata.name:
                logger.error("Plugin metadata mismatch")
                return False
            
            # Check dependencies
            if metadata.dependencies:
                try:
                    for dep in metadata.dependencies:
                        import_module(dep)
                except ImportError as e:
                    logger.error(f"Missing dependency: {e}")
                    return False
            
            # Run plugin validation
            if not plugin.validate():
                logger.error(f"Plugin validation failed: {metadata.name}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def _register_hook(self, plugin_name: str, hook: str, plugin: BasePlugin) -> None:
        """Register plugin handler for a hook.
        
        Args:
            plugin_name: Name of plugin
            hook: Hook name
            plugin: Plugin instance
        """
        if hook not in self._hooks:
            self._hooks[hook] = []
        
        # Create wrapper that includes plugin name
        def hook_handler(context):
            return plugin.execute(hook, context)
        
        # Attach plugin name for identification
        hook_handler._plugin_name = plugin_name
        self._hooks[hook].append(hook_handler)
    
    def _is_plugin_hook(self, handler: Callable, plugin_name: str) -> bool:
        """Check if handler belongs to plugin.
        
        Args:
            handler: Handler function
            plugin_name: Plugin name
        
        Returns:
            True if handler belongs to plugin
        """
        return getattr(handler, "_plugin_name", None) == plugin_name
    
    @staticmethod
    def _manifest_to_metadata(manifest: Dict[str, Any]) -> PluginMetadata:
        """Convert manifest dict to PluginMetadata.
        
        Args:
            manifest: Plugin manifest dictionary
        
        Returns:
            PluginMetadata instance
        """
        return PluginMetadata(
            name=manifest.get("name"),
            version=manifest.get("version"),
            author=manifest.get("author"),
            description=manifest.get("description"),
            entry_point=manifest.get("entry_point"),
            required_version=manifest.get("required_version", "1.0.0"),
            dependencies=manifest.get("dependencies", []),
            hooks=manifest.get("hooks", []),
        )    
    # Plugin state management
    
    def _load_plugin_state(self) -> Dict[str, bool]:
        """Load saved plugin enabled/disabled state.
        
        Returns:
            Dictionary of plugin_name -> is_enabled
        """
        try:
            if self._state_file.exists():
                with open(self._state_file) as f:
                    state = json.load(f)
                    logger.debug(f"Loaded plugin state: {state}")
                    return state
        except Exception as e:
            logger.warning(f"Failed to load plugin state: {e}")
        
        return {}
    
    def _save_plugin_state(self) -> None:
        """Save plugin enabled/disabled state to file."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w") as f:
                json.dump(self._enabled_plugins, f, indent=2)
            logger.debug(f"Saved plugin state: {self._enabled_plugins}")
        except Exception as e:
            logger.error(f"Failed to save plugin state: {e}")
    
    def set_plugin_enabled(self, plugin_name: str, enabled: bool) -> None:
        """Set plugin enabled/disabled state and persist to file.
        
        Args:
            plugin_name: Name of the plugin
            enabled: True to enable, False to disable
        """
        self._enabled_plugins[plugin_name] = enabled
        self._save_plugin_state()
        logger.info(f"Plugin '{plugin_name}' {'enabled' if enabled else 'disabled'}")
    
    def is_plugin_enabled_state(self, plugin_name: str) -> bool:
        """Check if plugin is enabled in saved state.
        
        Args:
            plugin_name: Name of the plugin
        
        Returns:
            True if plugin is enabled in saved state, False otherwise
        """
        # Default to True if not found in state (auto-enable new plugins)
        return self._enabled_plugins.get(plugin_name, True)
    
    def get_enabled_plugins_list(self) -> List[str]:
        """Get list of plugins that should be auto-loaded.
        
        Returns:
            List of plugin names to auto-load
        """
        discovered = self.discover_plugins()
        enabled = [p for p in discovered if self.is_plugin_enabled_state(p)]
        return enabled