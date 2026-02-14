"""Plugin exceptions module."""


class PluginException(Exception):
    """Base exception for plugin-related errors."""
    pass


class PluginLoadError(PluginException):
    """Raised when a plugin fails to load."""
    pass


class PluginValidationError(PluginException):
    """Raised when a plugin fails validation."""
    pass


class PluginExecutionError(PluginException):
    """Raised when a plugin fails during execution."""
    pass
