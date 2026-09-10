# PyEnvStudio Plugin Development Guide

## Overview

PyEnvStudio uses a plugin system that allows extending functionality without modifying the core codebase. Plugins follow **SRE principles**, **software design patterns** (Factory, Observer, Strategy), and **DRY (Don't Repeat Yourself)**.

## Architecture

### Design Patterns Used

1. **Factory Pattern**: `PluginManager` creates plugin instances dynamically
2. **Observer Pattern**: Hook system for event-driven plugin execution
3. **Strategy Pattern**: Plugins implement different strategies for the same operation
4. **Template Method Pattern**: `BasePlugin` defines the plugin structure

### Core Components

- **`BasePlugin`**: Abstract base class all plugins must inherit from
- **`PluginMetadata`**: Dataclass describing plugin information
- **`PluginHook`**: Enum of available hooks in the application
- **`PluginManager`**: Factory and manager for plugin lifecycle
- **Plugin Directory**: `~/.py_env_studio/plugins/`

## Creating a Plugin

### Step 1: Create Plugin Directory Structure

```
~/.py_env_studio/plugins/
└── my_plugin/
    ├── plugin.json          # Plugin manifest
    ├── my_plugin.py         # Main plugin code
    └── requirements.txt     # Optional: Plugin dependencies
```

### Step 2: Create plugin.json Manifest

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Brief description of what your plugin does",
  "entry_point": "my_plugin:MyPlugin",
  "required_version": "1.0.0",
  "dependencies": [],
  "hooks": ["after_create_env", "on_app_start"]
}
```

**Manifest Fields:**
- `name`: Unique plugin identifier (lowercase, no spaces)
- `version`: Semantic versioning (MAJOR.MINOR.PATCH)
- `author`: Plugin author
- `description`: What the plugin does
- `entry_point`: Format `module:ClassName` pointing to plugin class
- `required_version`: Minimum PyEnvStudio version (default: "1.0.0")
- `dependencies`: List of required Python packages to install
- `hooks`: List of hooks this plugin subscribes to

### Step 3: Implement Plugin Class

Minimal example:

```python
from py_env_studio.core.plugins import BasePlugin, PluginMetadata, PluginHook
from typing import Dict, Any


class MyPlugin(BasePlugin):
    """My custom plugin for PyEnvStudio."""
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            author="Your Name",
            description="My plugin does something useful",
            entry_point="my_plugin:MyPlugin",
            hooks=["after_create_env"]
        )
    
    def initialize(self, app_context: Dict[str, Any]) -> None:
        """Initialize plugin with app context."""
        self.app = app_context.get("app")
        self.logger = app_context.get("logger")
        self.logger.info("MyPlugin initialized")
    
    def execute(self, hook: str, context: Dict[str, Any]) -> Any:
        """Execute plugin logic for a hook."""
        if hook == "after_create_env":
            env_name = context.get("env_name")
            self.logger.info(f"Environment created: {env_name}")
            # Perform custom logic here
        return context
    
    def cleanup(self) -> None:
        """Clean up resources on shutdown."""
        self.logger.info("MyPlugin cleanup")
```

## Available Hooks

Plugins can subscribe to the following hooks:

### Environment Hooks
- `before_create_env`: Before environment creation
- `after_create_env`: After environment creation
- `before_delete_env`: Before environment deletion
- `after_delete_env`: After environment deletion
- `before_activate_env`: Before activating environment
- `after_activate_env`: After activating environment
- `before_rename_env`: Before renaming environment
- `after_rename_env`: After renaming environment

### Package Hooks
- `before_install_package`: Before installing package
- `after_install_package`: After installing package
- `before_uninstall_package`: Before uninstalling package
- `after_uninstall_package`: After uninstalling package
- `before_update_package`: Before updating package
- `after_update_package`: After updating package

### Application Hooks
- `on_app_start`: On application startup
- `on_app_shutdown`: On application shutdown
- `on_scan_complete`: After vulnerability scan completes

## Hook Context

Each hook receives a `context` dictionary with relevant data:

```python
# after_create_env context
{
    "env_name": "my_env",
    "python_version": "3.11.0",
    "python_path": "/path/to/python"
}

# after_install_package context
{
    "env_name": "my_env",
    "package_name": "requests",
    "version": "2.31.0"
}

# on_scan_complete context
{
    "env_name": "my_env",
    "vulnerabilities": [...],
    "severity_counts": {"critical": 0, "high": 1, ...}
}
```

## Best Practices

### 1. Follow DRY Principle

**Bad:**
```python
def execute(self, hook, context):
    if hook == "after_create_env":
        self.logger.info("Creating env")
        # logic
    elif hook == "before_delete_env":
        self.logger.info("Deleting env")
        # logic
```

**Good:**
```python
def execute(self, hook, context):
    handler = getattr(self, f"_handle_{hook}", None)
    if handler:
        return handler(context)
    return context

def _handle_after_create_env(self, context):
    """Handle environment creation."""
    self.logger.info(f"Created: {context.get('env_name')}")
    return context
```

### 2. Error Handling

Always catch exceptions and log them:

```python
def execute(self, hook, context):
    try:
        # plugin logic
        return context
    except Exception as e:
        self.logger.error(f"Plugin error in {hook}: {e}", exc_info=True)
        return context  # Return context unchanged to not break flow
```

### 3. Resource Management

Use cleanup() to release resources:

```python
def initialize(self, app_context):
    self.db_connection = create_connection()

def cleanup(self):
    if self.db_connection:
        self.db_connection.close()
```

### 4. Configuration Storage

Store plugin settings in `~/.py_env_studio/plugins/my_plugin/config.json`:

```python
from pathlib import Path
import json

def initialize(self, app_context):
    self.config_file = Path.home() / ".py_env_studio" / "plugins" / "my_plugin" / "config.json"
    self.config = self._load_config()

def _load_config(self):
    if self.config_file.exists():
        return json.loads(self.config_file.read_text())
    return {"option1": "default"}

def _save_config(self):
    self.config_file.parent.mkdir(parents=True, exist_ok=True)
    self.config_file.write_text(json.dumps(self.config, indent=2))
```

### 5. Logging

Use the logger from app_context:

```python
def execute(self, hook, context):
    self.logger.debug(f"Hook {hook} executed")
    self.logger.info("Important operation completed")
    self.logger.warning("Something unusual happened")
    self.logger.error("An error occurred")
```

### 6. Validation

Implement validate() to check dependencies and setup:

```python
def validate(self) -> bool:
    try:
        import required_module  # Check if optional dependency available
        return True
    except ImportError:
        self.logger.warning("Optional dependency missing")
        return False
```

## Example: Email Notification Plugin

Here's a complete example plugin that sends email notifications:

```python
# my_plugin.py
from py_env_studio.core.plugins import BasePlugin, PluginMetadata
from pathlib import Path
import json
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any


class EmailNotifierPlugin(BasePlugin):
    """Send email notifications on important events."""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="email_notifier",
            version="1.0.0",
            author="Your Name",
            description="Sends email notifications on environment events",
            entry_point="my_plugin:EmailNotifierPlugin",
            dependencies=["python-dotenv"],
            hooks=["after_create_env", "on_scan_complete"]
        )
    
    def initialize(self, app_context: Dict[str, Any]) -> None:
        self.app = app_context.get("app")
        self.logger = app_context.get("logger")
        self.config_file = self._get_config_path()
        self.config = self._load_config()
    
    def execute(self, hook: str, context: Dict[str, Any]) -> Any:
        try:
            if hook == "after_create_env":
                self._handle_env_created(context)
            elif hook == "on_scan_complete":
                self._handle_scan_complete(context)
        except Exception as e:
            self.logger.error(f"Email notifier error: {e}", exc_info=True)
        
        return context
    
    def validate(self) -> bool:
        # Check if SMTP credentials are configured
        if not self.config.get("smtp_host"):
            self.logger.warning("Email notifier not configured")
            return False
        return True
    
    def cleanup(self) -> None:
        self.logger.info("Email notifier plugin cleaned up")
    
    def _handle_env_created(self, context):
        """Send email when environment is created."""
        env_name = context.get("env_name")
        recipient = self.config.get("recipient_email")
        
        subject = f"Environment Created: {env_name}"
        body = f"Python environment '{env_name}' has been created."
        
        self._send_email(subject, body, recipient)
    
    def _handle_scan_complete(self, context):
        """Send email with scan results."""
        env_name = context.get("env_name")
        vulns = context.get("vulnerabilities", [])
        
        subject = f"Scan Complete: {env_name} ({len(vulns)} issues)"
        body = f"Vulnerability scan completed for {env_name}.\nFound {len(vulns)} vulnerabilities."
        
        recipient = self.config.get("recipient_email")
        self._send_email(subject, body, recipient)
    
    def _send_email(self, subject: str, body: str, recipient: str) -> None:
        """Send email using SMTP."""
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.config.get("from_email")
            msg["To"] = recipient
            
            with smtplib.SMTP(self.config.get("smtp_host"), 
                            self.config.get("smtp_port")) as server:
                if self.config.get("use_tls"):
                    server.starttls()
                server.login(self.config.get("smtp_user"), 
                           self.config.get("smtp_password"))
                server.send_message(msg)
            
            self.logger.info(f"Email sent to {recipient}")
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
    
    def _get_config_path(self) -> Path:
        """Get plugin config file path."""
        return Path.home() / ".py_env_studio" / "plugins" / "email_notifier" / "config.json"
    
    def _load_config(self) -> Dict[str, Any]:
        """Load plugin configuration."""
        if self.config_file.exists():
            return json.loads(self.config_file.read_text())
        return {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "smtp_user": "",
            "smtp_password": "",
            "from_email": "",
            "recipient_email": ""
        }
```

## Installing Plugin Dependencies

If your plugin requires additional packages, list them in `plugin.json`:

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  ...
  "dependencies": ["requests>=2.28.0", "numpy>=1.20"]
}
```

PluginManager will validate these are installed during plugin loading.

## Testing Your Plugin

```python
# test_my_plugin.py
import pytest
from my_plugin import MyPlugin
from py_env_studio.core.plugins import PluginMetadata


def test_plugin_metadata():
    """Test plugin metadata is valid."""
    plugin = MyPlugin()
    metadata = plugin.get_metadata()
    
    assert metadata.name == "my_plugin"
    assert metadata.version == "1.0.0"
    assert isinstance(metadata.hooks, list)


def test_plugin_initialization():
    """Test plugin initializes correctly."""
    plugin = MyPlugin()
    app_context = {
        "app": None,
        "logger": create_test_logger()
    }
    
    plugin.initialize(app_context)
    assert plugin.is_initialized


def test_plugin_execute():
    """Test plugin executes hooks."""
    plugin = MyPlugin()
    context = {"env_name": "test_env"}
    
    result = plugin.execute("after_create_env", context)
    assert result == context
```

## Troubleshooting

### Plugin won't load
1. Check `plugin.json` is valid JSON
2. Verify `entry_point` module exists and class is importable
3. Check `required_version` matches PyEnvStudio version
4. Review application logs for specific error

### Plugin crashes during execution
1. Add try-except in execute() method
2. Ensure logger is initialized in initialize()
3. Check context data matches expected keys

### Performance issues
1. Offload heavy operations to background threads
2. Cache expensive computations
3. Minimize log output in hot paths

## SRE Principles Applied

1. **Reliability**: Plugins use error handling and validation
2. **Observability**: Logging at all levels (debug, info, warning, error)
3. **Scalability**: Plugin system handles multiple concurrent plugins
4. **Automation**: PluginManager automates discovery and loading
5. **Simplicity**: Minimal API, clear interfaces
