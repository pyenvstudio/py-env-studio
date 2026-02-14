# Plugin System Quick Reference

## File Structure

```
~/.py_env_studio/plugins/
└── my_plugin/
    ├── plugin.json
    └── my_plugin.py
```

## Minimal Plugin Template

```python
from py_env_studio.core.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            author="Your Name",
            description="What it does",
            entry_point="my_plugin:MyPlugin",
            hooks=["after_create_env"]
        )
    
    def initialize(self, app_context):
        self.logger = app_context.get("logger")
    
    def execute(self, hook, context):
        if hook == "after_create_env":
            # Do something
            pass
        return context
```

## plugin.json Template

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Plugin description",
  "entry_point": "my_plugin:MyPlugin",
  "hooks": ["hook_name"]
}
```

## Available Hooks

### Environment
- `before_create_env` → `after_create_env`
- `before_delete_env` → `after_delete_env`
- `before_activate_env` → `after_activate_env`
- `before_rename_env` → `after_rename_env`

### Packages
- `before_install_package` → `after_install_package`
- `before_uninstall_package` → `after_uninstall_package`
- `before_update_package` → `after_update_package`

### Application
- `on_app_start`
- `on_app_shutdown`
- `on_scan_complete`

## Hook Context

```python
# Environment hooks
{
    "env_name": "my_env",
    "python_version": "3.11.0",
    "python_path": "/path/to/python"
}

# Package hooks
{
    "env_name": "my_env",
    "package_name": "requests",
    "version": "2.31.0"
}

# Scan complete
{
    "env_name": "my_env",
    "vulnerabilities": [...],
    "severity_counts": {...}
}
```

## BasePlugin Methods

| Method | Required | Purpose |
|--------|----------|---------|
| `get_metadata()` | Yes | Return plugin metadata |
| `initialize(app_context)` | Yes | Setup plugin |
| `execute(hook, context)` | Yes | Handle hook events |
| `validate()` | No | Check plugin readiness |
| `cleanup()` | No | Cleanup resources |

## Common Patterns

### Handler Pattern (DRY)
```python
def execute(self, hook, context):
    handler = getattr(self, f"_handle_{hook}", None)
    if handler:
        return handler(context)
    return context

def _handle_after_create_env(self, context):
    # logic
    return context
```

### Error Handling
```python
def execute(self, hook, context):
    try:
        # plugin logic
        return context
    except Exception as e:
        self.logger.error(f"Error: {e}", exc_info=True)
        return context
```

### Configuration
```python
from pathlib import Path
import json

def initialize(self, app_context):
    config_file = Path.home() / ".py_env_studio" / "plugins" / "my_plugin" / "config.json"
    self.config = json.loads(config_file.read_text()) if config_file.exists() else {}
```

## Testing

```python
import pytest
from my_plugin import MyPlugin

def test_plugin_loads():
    plugin = MyPlugin()
    metadata = plugin.get_metadata()
    assert metadata.name == "my_plugin"

def test_plugin_executes():
    plugin = MyPlugin()
    plugin.initialize({"logger": create_logger()})
    context = {"env_name": "test"}
    result = plugin.execute("after_create_env", context)
    assert result == context
```

## Installation Steps

1. Create directory: `~/.py_env_studio/plugins/my_plugin/`
2. Create `plugin.json` manifest
3. Create `my_plugin.py` with plugin class
4. Open PyEnvStudio → Tools → Plugins
5. Click "Enable" next to your plugin
6. Check console logs for messages

## Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check if plugin loads
plugin = PluginManager().load_plugin("my_plugin")

# Verify metadata
metadata = plugin.get_metadata()
print(metadata)

# Test execution
result = plugin.execute("after_create_env", {"env_name": "test"})
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Plugin not discovered | Check `plugin.json` exists in correct directory |
| Import error | Verify `entry_point` format is `module:ClassName` |
| Validation fails | Check all dependencies are installed |
| Hook not called | Verify hook name is in `hooks` list |
| Can't access app | Get from `app_context` in `initialize()` |

## Resources

- **Developer Guide**: `docs/PLUGIN_DEVELOPMENT.md`
- **Architecture**: `docs/PLUGINS_ARCHITECTURE.md`
- **Example Plugin**: `examples/sample_plugin/`
- **API Reference**: `py_env_studio.core.plugins`

## Support

For issues or questions:
1. Check logs in console
2. Review example plugin
3. Read developer guide
4. Check plugin architecture document
