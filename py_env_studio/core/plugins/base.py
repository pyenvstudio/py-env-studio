"""Base plugin classes and interfaces for PyEnvStudio plugins.

Plugins should inherit from BasePlugin and implement required methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class PluginHook(str, Enum):
    """Available plugin hooks in PyEnvStudio.
    
    Hooks are events that plugins can subscribe to and extend functionality.
    """
    
    # Environment hooks
    BEFORE_CREATE_ENV = "before_create_env"
    AFTER_CREATE_ENV = "after_create_env"
    BEFORE_DELETE_ENV = "before_delete_env"
    AFTER_DELETE_ENV = "after_delete_env"
    BEFORE_ACTIVATE_ENV = "before_activate_env"
    AFTER_ACTIVATE_ENV = "after_activate_env"
    BEFORE_RENAME_ENV = "before_rename_env"
    AFTER_RENAME_ENV = "after_rename_env"
    
    # Package hooks
    BEFORE_INSTALL_PACKAGE = "before_install_package"
    AFTER_INSTALL_PACKAGE = "after_install_package"
    BEFORE_UNINSTALL_PACKAGE = "before_uninstall_package"
    AFTER_UNINSTALL_PACKAGE = "after_uninstall_package"
    BEFORE_UPDATE_PACKAGE = "before_update_package"
    AFTER_UPDATE_PACKAGE = "after_update_package"
    
    # Application hooks
    ON_APP_START = "on_app_start"
    ON_APP_SHUTDOWN = "on_app_shutdown"
    ON_SCAN_COMPLETE = "on_scan_complete"


@dataclass
class PluginMetadata:
    """Metadata describing a plugin.
    
    Attributes:
        name: Unique identifier for the plugin
        version: Semantic version (e.g., "1.0.0")
        author: Plugin author name
        description: Brief description of plugin functionality
        entry_point: Module path to plugin class (e.g., "my_plugin:MyPluginClass")
        required_version: Minimum PyEnvStudio version required (e.g., "1.0.0")
        dependencies: List of required Python packages
        hooks: List of PluginHook names this plugin subscribes to
    """
    
    name: str
    version: str
    author: str
    description: str
    entry_point: str
    required_version: str = "1.0.0"
    dependencies: List[str] = None
    hooks: List[str] = None
    
    def __post_init__(self):
        """Validate metadata after initialization."""
        if not self.name or not self.version or not self.author:
            raise ValueError("name, version, and author are required")
        if not self.entry_point or ":" not in self.entry_point:
            raise ValueError("entry_point must be in format 'module:ClassName'")
        if self.dependencies is None:
            self.dependencies = []
        if self.hooks is None:
            self.hooks = []


class BasePlugin(ABC):
    """Abstract base class for PyEnvStudio plugins.
    
    All plugins must inherit from this class and implement required methods.
    
    Example:
        >>> class MyPlugin(BasePlugin):
        ...     def get_metadata(self):
        ...         return PluginMetadata(
        ...             name="my_plugin",
        ...             version="1.0.0",
        ...             author="Your Name",
        ...             description="My plugin description",
        ...             entry_point="my_plugin:MyPlugin",
        ...             hooks=["after_create_env"]
        ...         )
        ...
        ...     def initialize(self, app_context):
        ...         # Setup plugin
        ...         pass
        ...
        ...     def execute(self, hook, context):
        ...         if hook == "after_create_env":
        ...             env_name = context.get("env_name")
        ...             # Do something with environment
    """
    
    def __init__(self):
        """Initialize the plugin."""
        self._initialized = False
        self._app_context = None
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata.
        
        Returns:
            PluginMetadata: Plugin information
        """
        pass
    
    @abstractmethod
    def initialize(self, app_context: Dict[str, Any]) -> None:
        """Initialize the plugin with app context.
        
        Called once when plugin is loaded. Use this to setup resources,
        register hooks, or perform initialization tasks.
        
        Args:
            app_context: Dictionary containing app references and configuration
                - "app": Main PyEnvStudio application instance
                - "config": Application configuration
                - "logger": Logger instance
        
        Raises:
            Exception: If initialization fails
        """
        pass
    
    @abstractmethod
    def execute(self, hook: str, context: Dict[str, Any]) -> Any:
        """Execute plugin logic for a hook.
        
        Called when a hook event occurs. Implement hook-specific logic here.
        
        Args:
            hook: The hook name that triggered execution
            context: Hook-specific context data
        
        Returns:
            Result data or modified context (hook-dependent)
        
        Raises:
            Exception: If execution fails
        """
        pass
    
    def validate(self) -> bool:
        """Validate plugin integrity and dependencies.
        
        Called after loading to ensure plugin is valid and all
        dependencies are satisfied.
        
        Returns:
            bool: True if valid, False otherwise
        """
        return True
    
    def cleanup(self) -> None:
        """Clean up plugin resources on shutdown.
        
        Called when plugin is unloaded or application shuts down.
        Use this to release resources, close connections, etc.
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if plugin has been initialized."""
        return self._initialized
    
    @property
    def app_context(self) -> Optional[Dict[str, Any]]:
        """Get the app context (read-only)."""
        return self._app_context
