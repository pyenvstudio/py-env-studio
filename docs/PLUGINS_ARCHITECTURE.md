# PyEnvStudio Plugin Architecture

## Overview

The PyEnvStudio plugin system provides a extensible, production-ready architecture for adding functionality without modifying core code. It implements industry-standard design patterns and follows SRE (Site Reliability Engineering) principles.

## Architecture Design

### Design Patterns

#### 1. Factory Pattern
The `PluginManager` acts as a factory, dynamically creating plugin instances:
```python
# Central factory method
def load_plugin(self, plugin_name: str) -> BasePlugin:
    # Dynamic module loading and instantiation
    module = import_module(module_path)
    plugin_class = getattr(module, class_name)
    return plugin_class()
```

**Benefits:**
- Decouples plugin creation from usage
- Enables runtime plugin discovery
- Simplifies plugin lifecycle management

#### 2. Observer Pattern
Hooks system implements the Observer pattern:
```python
# Plugins subscribe to hooks
plugin.execute("after_create_env", context)

# Application publishes events
plugin_manager.execute_hook("after_create_env", {"env_name": "my_env"})
```

**Benefits:**
- Loose coupling between app and plugins
- Multiple plugins can react to same event
- Event-driven architecture

#### 3. Strategy Pattern
Each plugin implements a strategy for extending functionality:
```python
class Plugin1Strategy(BasePlugin):
    def execute(self, hook, context):
        # Strategy 1 implementation
        
class Plugin2Strategy(BasePlugin):
    def execute(self, hook, context):
        # Strategy 2 implementation
```

**Benefits:**
- Different plugins provide different strategies
- Runtime strategy selection
- Easy to add/remove strategies

#### 4. Template Method Pattern
`BasePlugin` defines the plugin structure:
```python
class BasePlugin(ABC):
    def get_metadata(self) -> PluginMetadata: ...
    def initialize(self, app_context) -> None: ...
    def execute(self, hook, context) -> Any: ...
    def validate(self) -> bool: ...
    def cleanup(self) -> None: ...
```

**Benefits:**
- Consistent plugin interface
- Forces implementation of critical methods
- Defines extension points

## Directory Structure

```
PyEnvStudio/
├── py_env_studio/
│   ├── core/
│   │   └── plugins/              # Plugin system core
│   │       ├── __init__.py
│   │       ├── base.py           # BasePlugin, PluginMetadata, PluginHook
│   │       ├── manager.py        # PluginManager (Factory)
│   │       └── exceptions.py      # Plugin exceptions
│   └── ui/
│       └── main_window.py        # Plugin UI components
├── examples/
│   └── sample_plugin/            # Example plugin
│       ├── plugin.json
│       ├── sample_plugin.py
│       └── README.md
└── docs/
    ├── PLUGIN_DEVELOPMENT.md     # Developer guide
    └── PLUGINS_ARCHITECTURE.md   # This file
```

## Component Responsibilities

### BasePlugin (Abstract Interface)
**Responsibility:** Define plugin contract

```python
class BasePlugin(ABC):
    # Metadata retrieval
    @abstractmethod
    def get_metadata(self) -> PluginMetadata: ...
    
    # Initialization phase
    @abstractmethod
    def initialize(self, app_context: Dict[str, Any]) -> None: ...
    
    # Hook execution
    @abstractmethod
    def execute(self, hook: str, context: Dict[str, Any]) -> Any: ...
    
    # Validation
    def validate(self) -> bool: ...
    
    # Cleanup phase
    def cleanup(self) -> None: ...
```

### PluginManager (Factory + Orchestrator)
**Responsibility:** Manage plugin lifecycle

```python
class PluginManager:
    # Discovery
    def discover_plugins(self) -> List[str]: ...
    
    # Loading (Factory)
    def load_plugin(self, plugin_name: str) -> BasePlugin: ...
    
    # Unloading
    def unload_plugin(self, plugin_name: str) -> None: ...
    
    # Hook execution
    def execute_hook(self, hook: str, context: Dict[str, Any]) -> List[Any]: ...
    
    # Status
    def is_plugin_enabled(self, plugin_name: str) -> bool: ...
```

### PluginMetadata (Data Object)
**Responsibility:** Store plugin information

```python
@dataclass
class PluginMetadata:
    name: str
    version: str
    author: str
    description: str
    entry_point: str
    required_version: str
    dependencies: List[str]
    hooks: List[str]
```

## Plugin Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│                    Plugin Lifecycle                      │
└─────────────────────────────────────────────────────────┘

1. DISCOVERY
   └─> PluginManager scans ~/.py_env_studio/plugins/
       └─> Finds plugin.json manifests
       └─> Returns list of discovered plugins

2. LOADING
   └─> User selects plugin in UI
   └─> PluginManager.load_plugin()
       ├─> Parse plugin.json manifest
       ├─> Import module dynamically
       ├─> Instantiate plugin class
       ├─> Call plugin.validate()
       └─> Call plugin.initialize(app_context)

3. EXECUTION
   └─> Application event occurs
   └─> PluginManager.execute_hook()
       ├─> Find all subscribed plugins
       ├─> Call plugin.execute(hook, context)
       └─> Collect results

4. UNLOADING
   └─> User disables plugin in UI
   └─> PluginManager.unload_plugin()
       ├─> Call plugin.cleanup()
       ├─> Remove hook subscriptions
       └─> Release plugin reference

5. SHUTDOWN
   └─> Application closing
   └─> PluginManager cleanup
       └─> Unload all plugins
```

## Hook System

### Hook Categories

#### Environment Hooks
- `before_create_env` → `after_create_env`
- `before_delete_env` → `after_delete_env`
- `before_activate_env` → `after_activate_env`
- `before_rename_env` → `after_rename_env`

#### Package Hooks
- `before_install_package` → `after_install_package`
- `before_uninstall_package` → `after_uninstall_package`
- `before_update_package` → `after_update_package`

#### Application Hooks
- `on_app_start`
- `on_app_shutdown`
- `on_scan_complete`

### Hook Context

Each hook provides context-specific data:

```python
# before_create_env / after_create_env
{
    "env_name": "my_env",
    "python_version": "3.11.0",
    "python_path": "/path/to/python"
}

# after_install_package
{
    "env_name": "my_env",
    "package_name": "requests",
    "version": "2.31.0"
}

# on_scan_complete
{
    "env_name": "my_env",
    "vulnerabilities": [...],
    "severity_counts": {
        "critical": 0,
        "high": 1,
        "medium": 3,
        "low": 5
    }
}
```

## DRY (Don't Repeat Yourself) Principles

### 1. Handler Pattern for Hook Execution

**Bad (repeated if-elif):**
```python
def execute(self, hook, context):
    if hook == "after_create_env":
        # 10 lines of logic
    elif hook == "after_install_package":
        # 10 lines of logic
    elif hook == "on_scan_complete":
        # 10 lines of logic
```

**Good (DRY with dynamic dispatch):**
```python
def execute(self, hook, context):
    handler = getattr(self, f"_handle_{hook}", None)
    if handler:
        return handler(context)
    return context

def _handle_after_create_env(self, context):
    # logic
    
def _handle_after_install_package(self, context):
    # logic
    
def _handle_on_scan_complete(self, context):
    # logic
```

### 2. Metadata Reuse

Plugin metadata is defined once in `plugin.json` and reused:
- Plugin discovery
- Validation (version, dependencies)
- UI display
- Hook registration

```python
# Load once
metadata = self._manifest_to_metadata(manifest)

# Used multiple times
self._validate_plugin(plugin, metadata)
self._register_hooks(plugin, metadata)
self.plugin_metadata[plugin_name] = metadata
```

### 3. Common Exception Handling

Centralized exception types prevent code duplication:

```python
# core/plugins/exceptions.py - defined once
class PluginException(Exception): ...
class PluginLoadError(PluginException): ...
class PluginValidationError(PluginException): ...

# Used everywhere
try:
    load_plugin()
except PluginException as e:
    logger.error(f"Plugin error: {e}")
```

## SRE Principles

### 1. Reliability
- **Error Handling**: Try-catch blocks at all boundaries
- **Validation**: Plugins validated before loading
- **Graceful Degradation**: Failed plugins don't crash app
- **Logging**: All operations logged at appropriate levels

### 2. Observability
- **Structured Logging**: Clear, contextual log messages
- **Plugin Status**: Track loaded/unloaded/failed states
- **Hook Tracing**: Monitor which hooks execute
- **Error Details**: Include stack traces and context

### 3. Scalability
- **Lazy Loading**: Plugins loaded on-demand
- **Memory Management**: Cleanup releases resources
- **Concurrent Hooks**: Multiple plugins can handle same hook
- **Performance**: No blocking on plugin operations

### 4. Simplicity
- **Minimal API**: Just 5 methods in BasePlugin
- **Clear Naming**: Intent is obvious
- **Documentation**: Extensive guides and examples
- **Consistency**: All plugins follow same pattern

### 5. Automation
- **Auto-discovery**: Find plugins automatically
- **Auto-validation**: Check dependencies automatically
- **Auto-initialization**: Setup plugins automatically
- **Auto-cleanup**: Release resources automatically

## Security Considerations

### 1. Plugin Isolation
Plugins share same process - malicious plugins can harm app:
- Validate plugin sources
- Review plugin code before installing
- Run from trusted repositories

### 2. Dependency Management
Always validate plugin dependencies:
```python
# In PluginManager._validate_plugin()
for dep in metadata.dependencies:
    import_module(dep)  # Raises ImportError if missing
```

### 3. Context Limitations
Plugin `app_context` provides read-only references:
```python
@property
def app_context(self) -> Optional[Dict[str, Any]]:
    """Get the app context (read-only)."""
    return self._app_context
```

## Performance Characteristics

### Load Time
- **Discovery**: O(n) - scan plugin directory
- **Loading**: O(1) - single module import + instantiation
- **Validation**: O(d) - d dependencies

### Execution Time
- **Hook dispatch**: O(1) - direct method call
- **Plugin execution**: O(p) - p plugins subscribed to hook
- **Context creation**: O(1) - minimal copying

### Memory Usage
- **Per Plugin**: ~500KB base + plugin-specific
- **Hooks Registry**: O(p) - p plugins
- **Metadata Cache**: O(1) - constant size

## Testing Plugins

### Unit Testing
```python
def test_plugin_metadata():
    plugin = MyPlugin()
    metadata = plugin.get_metadata()
    assert metadata.name == "my_plugin"
```

### Integration Testing
```python
def test_plugin_with_app():
    manager = PluginManager()
    manager.load_plugin("my_plugin")
    manager.execute_hook("after_create_env", {...})
```

### End-to-End Testing
```python
def test_plugin_ui():
    app = PyEnvStudio()
    app.show_plugins_dialog()
    # Verify plugin appears in dialog
```

## Troubleshooting

### Plugin Discovery Issues
1. Check plugin directory: `~/.py_env_studio/plugins/`
2. Verify `plugin.json` exists and is valid JSON
3. Check plugin directory name matches discovery pattern

### Plugin Loading Errors
1. Verify `entry_point` is correct format: `module:Class`
2. Check module can be imported: `python -c "from module import Class"`
3. Verify all dependencies are installed
4. Check Python version compatibility

### Hook Execution Issues
1. Verify hook name in `plugin.json`
2. Check context keys match hook expectations
3. Enable debug logging: `logging.getLogger().setLevel(logging.DEBUG)`
4. Review plugin error handling

## Future Enhancements

1. **Plugin Configuration UI**: Visual settings editor
2. **Plugin Marketplace**: Share and discover plugins
3. **Plugin Versioning**: Version conflicts and updates
4. **Plugin Sandboxing**: Isolated execution environment
5. **Plugin Communication**: Plugin-to-plugin messaging
6. **Plugin Events**: Custom plugin-defined events

## References

- **Design Patterns**: Gang of Four
- **Python Packaging**: PEP 427
- **Plugin Architecture**: https://docs.python-guide.org/en/latest/scenarios/cli/
- **SRE Handbook**: Google Cloud SRE
