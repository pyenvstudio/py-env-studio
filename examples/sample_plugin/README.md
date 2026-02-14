# Sample Plugin

A complete example plugin for PyEnvStudio demonstrating best practices.

## Features

- **Hook-based architecture**: Subscribes to multiple application events
- **Handler pattern**: Uses DRY principle with dynamic handler routing
- **Error handling**: Comprehensive try-catch with logging
- **Event logging**: Logs all events to JSON file for auditing
- **Validation**: Checks plugin readiness during initialization

## Installation

Copy the sample_plugin directory to:
```
~/.py_env_studio/plugins/sample_plugin/
```

Then enable it in PyEnvStudio:
1. Open Tools > Plugins
2. Find "sample_plugin" in the list
3. Click "Enable"

## Configuration

No configuration needed - the plugin works out of the box.

Events are logged to:
```
~/.py_env_studio/plugins/sample_plugin/events.log
```

## What It Does

### Hooks Monitored

1. **on_app_start**: Logs when application starts
2. **after_create_env**: Logs when environments are created
3. **after_install_package**: Logs when packages are installed
4. **on_scan_complete**: Logs vulnerability scan results

### Event Log Format

Each event is logged as JSON:

```json
{
  "timestamp": "2024-02-14T10:30:45.123456",
  "hook": "after_create_env",
  "status": "success",
  "context": {
    "env_name": "myenv",
    "python_version": "3.11.0"
  },
  "error": null
}
```

## Learning Resources

Use this plugin as a reference for:
- ✅ Plugin structure and organization
- ✅ Handler pattern for DRY code
- ✅ Error handling best practices
- ✅ Logging integration
- ✅ File I/O operations
- ✅ Configuration management

See `docs/PLUGIN_DEVELOPMENT.md` for complete plugin development guide.
