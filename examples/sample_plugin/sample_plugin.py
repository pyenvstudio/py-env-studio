"""Sample Plugin - Demonstrates PyEnvStudio Plugin System.

This is a complete example plugin showing best practices including:
- Proper initialization and cleanup
- Multiple hook implementations
- Error handling
- Logging
- Configuration management
- DRY principles with handler pattern
"""

from py_env_studio.core.plugins import BasePlugin, PluginMetadata
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class SamplePlugin(BasePlugin):
    """Sample plugin that logs environment events to a file."""
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="sample_plugin",
            version="1.0.0",
            author="PyEnvStudio Team",
            description="Logs environment events to demonstrate plugin capabilities",
            entry_point="sample_plugin:SamplePlugin",
            hooks=[
                "on_app_start",
                "after_create_env",
                "after_install_package",
                "on_scan_complete"
            ]
        )
    
    def initialize(self, app_context: Dict[str, Any]) -> None:
        """Initialize plugin.
        
        Sets up logger and event log file.
        """
        self.app = app_context.get("app")
        self.logger = app_context.get("logger")
        self.log_file = self._get_log_file()
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        if self.logger:
            self.logger.info(f"SamplePlugin initialized - logging to {self.log_file}")
        else:
            print(f"SamplePlugin initialized - logging to {self.log_file}")
    
    def execute(self, hook: str, context: Dict[str, Any]) -> Any:
        """Execute plugin logic for hooks.
        
        Uses handler pattern to avoid long if-elif chains (DRY principle).
        """
        try:
            # Dynamically route to handler method
            handler_name = f"_handle_{hook}"
            handler = getattr(self, handler_name, None)
            
            if handler:
                if self.logger:
                    self.logger.debug(f"Executing handler for hook: {hook}")
                result = handler(context)
                self._log_event(hook, context, status="success")
                return result
            else:
                if self.logger:
                    self.logger.debug(f"No handler for hook: {hook}")
                return context
        
        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Error executing hook '{hook}': {e}",
                    exc_info=True
                )
            self._log_event(hook, context, status="error", error=str(e))
            return context
    
    def validate(self) -> bool:
        """Validate plugin is ready to run.
        
        Returns:
            True if all checks pass
        """
        try:
            # Verify log file is writable
            self.log_file = self._get_log_file()
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Validation failed: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up plugin resources on shutdown."""
        if self.logger:
            self.logger.info("SamplePlugin cleanup - goodbye!")
        self._log_event("on_app_shutdown", {}, status="success")
    
    # Hook handlers - using DRY pattern
    
    def _handle_on_app_start(self, context: Dict[str, Any]) -> Any:
        """Handle application startup."""
        if self.logger:
            self.logger.info("Application started")
        return context
    
    def _handle_after_create_env(self, context: Dict[str, Any]) -> Any:
        """Handle environment creation.
        
        Args:
            context: Contains env_name, python_version, python_path
        """
        env_name = context.get("env_name", "unknown")
        python_version = context.get("python_version", "unknown")
        
        if self.logger:
            self.logger.info(
                f"Environment created: {env_name} "
                f"(Python {python_version})"
            )
        
        return context
    
    def _handle_after_install_package(self, context: Dict[str, Any]) -> Any:
        """Handle package installation.
        
        Args:
            context: Contains env_name, package_name, version
        """
        env_name = context.get("env_name", "unknown")
        package = context.get("package_name", "unknown")
        version = context.get("version", "unknown")
        
        if self.logger:
            self.logger.info(
                f"Package installed in {env_name}: "
                f"{package}=={version}"
            )
        
        return context
    
    def _handle_on_scan_complete(self, context: Dict[str, Any]) -> Any:
        """Handle vulnerability scan completion.
        
        Args:
            context: Contains env_name, vulnerabilities, severity_counts
        """
        env_name = context.get("env_name", "unknown")
        vulnerabilities = context.get("vulnerabilities", [])
        severity_counts = context.get("severity_counts", {})
        
        if self.logger:
            self.logger.info(
                f"Scan completed for {env_name}: "
                f"{len(vulnerabilities)} vulnerabilities found"
            )
            
            if severity_counts:
                critical = severity_counts.get("critical", 0)
                high = severity_counts.get("high", 0)
                self.logger.warning(
                    f"Severity breakdown: {critical} critical, {high} high"
                )
        
        return context
    
    # Private helper methods
    
    def _get_log_file(self) -> Path:
        """Get path to plugin event log file."""
        return (
            Path.home() / 
            ".py_env_studio" / 
            "plugins" / 
            "sample_plugin" / 
            "events.log"
        )
    
    def _log_event(
        self,
        hook: str,
        context: Dict[str, Any],
        status: str = "info",
        error: str = None
    ) -> None:
        """Log event to file.
        
        Args:
            hook: Hook name
            context: Hook context data
            status: Event status (success, error, info)
            error: Optional error message
        """
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "hook": hook,
                "status": status,
                "context": context,
                "error": error
            }
            
            # Append to log file
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        
        except Exception as e:
            self.logger.error(f"Failed to write event log: {e}")
