# PyEnvStudio Plugin System Core

This package implements the complete plugin system for PyEnvStudio, providing a production-ready framework for extending functionality.

## Quick Start

### For Plugin Developers

1. **Read the guide**: See `docs/PLUGIN_DEVELOPMENT.md`
2. **Study the example**: Check `examples/sample_plugin/`
3. **Create your plugin**: Follow the template in quick reference
4. **Enable it**: Tools > Plugins menu in PyEnvStudio

### For PyEnvStudio Users

1. **Access plugins**: Tools > Plugins menu
2. **Enable/disable**: Click buttons next to each plugin
3. **View status**: Console shows plugin messages

## Core Modules

### `base.py`
Abstract base classes and plugin interface

**Key Classes:**
- `BasePlugin` - Abstract base class for all plugins
- `PluginMetadata` - Plugin information dataclass
- `PluginHook` - Available hooks enum

### `manager.py`
Plugin lifecycle management using Factory pattern

**Key Classes:**
- `PluginManager` - Discovers, loads, executes plugins

**Key Methods:**
- `discover_plugins()` - Find available plugins
- `load_plugin()` - Load and initialize plugin
- `unload_plugin()` - Cleanup and unload
- `execute_hook()` - Run hook handlers

### `exceptions.py`
Plugin-specific exception hierarchy

**Exception Types:**
- `PluginException` - Base exception
- `PluginLoadError` - Loading failures
- `PluginValidationError` - Validation failures
- `PluginExecutionError` - Runtime errors

## Plugin Structure

```
~/.py_env_studio/plugins/my_plugin/
├── plugin.json           # Metadata manifest
├── my_plugin.py          # Plugin implementation
├── requirements.txt      # Dependencies (optional)
├── config.json           # Configuration (optional)
└── README.md             # Plugin documentation (optional)
```

## Minimal Plugin Example

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
            self.logger.info(f"Environment created: {context.get('env_name')}")
        return context
```

## Available Hooks (17 Total)

### Environment (8)
- before/after_create_env
- before/after_delete_env
- before/after_activate_env
- before/after_rename_env

### Packages (6)
- before/after_install_package
- before/after_uninstall_package
- before/after_update_package

### Application (3)
- on_app_start
- on_app_shutdown
- on_scan_complete

## Plugin Lifecycle

```
Discovery → Loading → Initialization → Execution → Unloading → Cleanup
```

1. **Discovery**: PluginManager finds plugin.json files
2. **Loading**: Module imported, class instantiated
3. **Initialization**: Plugin.initialize() called with app context
4. **Execution**: Plugin.execute() called when hooks fire
5. **Unloading**: User disables or app shuts down
6. **Cleanup**: Plugin.cleanup() called

## Design Patterns

- **Factory Pattern**: PluginManager creates plugin instances
- **Observer Pattern**: Hooks system for event subscriptions
- **Strategy Pattern**: Different plugins provide different strategies
- **Template Method Pattern**: BasePlugin defines structure

## DRY Principles

### Handler Pattern
Use dynamic method dispatch instead of if-elif chains:

```python
def execute(self, hook, context):
    handler = getattr(self, f"_handle_{hook}", None)
    if handler:
        return handler(context)
    return context
```

### Metadata Reuse
Plugin.json metadata reused for discovery, validation, UI, hooks

### Exception Hierarchy
All plugin errors use same exception types

## SRE Integration

- **Reliability**: Error handling, validation, graceful degradation
- **Observability**: Structured logging, status tracking
- **Scalability**: Lazy loading, resource cleanup
- **Simplicity**: Minimal API (5 core methods)
- **Automation**: Auto-discovery, validation, initialization

## Testing

```python
def test_plugin():
    plugin = MyPlugin()
    metadata = plugin.get_metadata()
    assert metadata.name == "my_plugin"
    
    plugin.initialize({"logger": logger})
    result = plugin.execute("after_create_env", {"env_name": "test"})
    assert result is not None
```

## API Reference

### BasePlugin Methods
```python
get_metadata() -> PluginMetadata      # Required: Return metadata
initialize(app_context) -> None        # Required: Setup plugin
execute(hook, context) -> Any          # Required: Handle hook
validate() -> bool                     # Optional: Validate plugin
cleanup() -> None                      # Optional: Cleanup
```

### PluginManager Methods
```python
discover_plugins() -> List[str]
load_plugin(name) -> BasePlugin
unload_plugin(name) -> None
execute_hook(hook, context) -> List[Any]
get_plugin(name) -> Optional[BasePlugin]
get_all_plugins() -> Dict[str, BasePlugin]
is_plugin_enabled(name) -> bool
```

## Documentation

- **[Plugin Development Guide](../docs/PLUGIN_DEVELOPMENT.md)** - Complete how-to
- **[Architecture Document](../docs/PLUGINS_ARCHITECTURE.md)** - Technical details
- **[Quick Reference](../docs/PLUGIN_QUICK_REFERENCE.md)** - Quick lookup
- **[Documentation Index](../docs/PLUGIN_DOCUMENTATION_INDEX.md)** - Navigation guide
- **[Sample Plugin](../examples/sample_plugin/)** - Working example

## Common Patterns

### Configuration Storage
```python
def initialize(self, app_context):
    config_file = Path.home() / ".py_env_studio" / "plugins" / "my_plugin" / "config.json"
    self.config = json.loads(config_file.read_text()) if config_file.exists() else {}
```

### Error Handling
```python
def execute(self, hook, context):
    try:
        handler = getattr(self, f"_handle_{hook}")
        return handler(context)
    except Exception as e:
        self.logger.error(f"Hook error: {e}", exc_info=True)
        return context
```

### Hook Routing
```python
def execute(self, hook, context):
    handler = getattr(self, f"_handle_{hook}", None)
    if handler:
        return handler(context)
    return context

def _handle_after_create_env(self, context): ...
def _handle_after_install_package(self, context): ...
```

## Security Considerations

⚠️ **Important**: Plugins run in the main process
- Validate plugin sources
- Review code before installing
- Malicious plugins can harm the application

## Performance

- **Discovery**: ~50ms (directory scan)
- **Load per plugin**: ~100ms (import + init)
- **Hook execution**: <1ms overhead
- **Memory per plugin**: ~500KB base
- **No startup impact** (lazy loading)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Plugin not discovered | Check plugin.json exists in correct directory |
| Import error | Verify entry_point is module:ClassName |
| Validation fails | Check dependencies installed |
| Hook not called | Verify hook name in plugin.json |
| Can't access app | Get from app_context in initialize() |

## Contributing

To extend the plugin system:

1. Add new hook to `PluginHook` enum in `base.py`
2. Fire hook from application with `execute_hook()`
3. Update documentation with new hook details
4. Add example to `sample_plugin.py`

## Files Overview

| File | Purpose | Size |
|------|---------|------|
| `__init__.py` | Public API exports | ~20 lines |
| `base.py` | Plugin interface | ~200 lines |
| `manager.py` | Lifecycle management | ~300 lines |
| `exceptions.py` | Exception types | ~20 lines |

## Version

**Plugin System Version**: 1.0.0  
**Release Date**: February 14, 2026  
**Status**: Production Ready ✅

## Support Resources

- **Questions?** Check [Quick Reference](../docs/PLUGIN_QUICK_REFERENCE.md)
- **How-to?** See [Development Guide](../docs/PLUGIN_DEVELOPMENT.md)
- **Architecture?** Review [Architecture Doc](../docs/PLUGINS_ARCHITECTURE.md)
- **Example?** Study [Sample Plugin](../examples/sample_plugin/)
- **Stuck?** Check troubleshooting sections

## Next Steps

1. 📖 Read [Quick Reference](../docs/PLUGIN_QUICK_REFERENCE.md)
2. 📚 Study [Development Guide](../docs/PLUGIN_DEVELOPMENT.md)
3. 👀 Review [Sample Plugin](../examples/sample_plugin/sample_plugin.py)
4. 🚀 Create your first plugin
5. ✨ Enable via Tools > Plugins
