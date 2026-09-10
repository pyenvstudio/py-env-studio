# Plugin System Documentation Index

## 📚 Documentation Map

This index helps you navigate the PyEnvStudio Plugin System documentation and code.

### Quick Navigation

| Need | Document | Time |
|------|----------|------|
| **Just want to use plugins?** | [Plugin Quick Reference](quick-reference.md) | 5 min |
| **Creating your first plugin?** | [Plugin Development Guide](development.md) | 30 min |
| **Understanding the system?** | [Architecture Document](architecture.md) | 20 min |
| **Seeing an example?** | [Sample Plugin Code](https://github.com/pyenvstudio/py-env-studio/tree/main/examples/sample_plugin) | 10 min |
| **Quick lookup?** | [This Index](#documentation-map) | 2 min |

---

## 📖 Complete Documentation Guide

### 1. For Plugin Users
**Goal**: Enable and use existing plugins

#### Start Here
- [Plugin Quick Reference](quick-reference.md)
  - How to enable plugins
  - Available hooks
  - Common issues

#### Then Read
- [Main Feature Guide](../reference/features.md) (mentions plugin system)
- [Installation Guide](../getting-started/install.md)

### 2. For Plugin Developers
**Goal**: Create new plugins

#### Phase 1: Understand
1. [Plugin Development Guide](development.md) - START HERE
   - What are plugins
   - Architecture overview
   - Creating your first plugin
   
2. [Architecture Deep Dive](architecture.md)
   - Design patterns explained
   - Lifecycle details
   - Performance characteristics

#### Phase 2: Learn by Example
- [Sample Plugin](https://github.com/pyenvstudio/py-env-studio/blob/main/examples/sample_plugin/sample_plugin.py)
  - Working, documented code
  - Handler pattern
  - Error handling
  - Event logging

#### Phase 3: Create
1. Copy sample plugin template
2. Follow [Plugin Development Guide](development.md) step-by-step
3. Test with included examples

#### Phase 4: Reference
- [Quick Reference](quick-reference.md) - Templates and patterns
- [API Reference](#api-reference-section) below

### 3. For System Maintainers
**Goal**: Understand and extend the plugin system

#### Core Understanding
1. [Architecture Document](architecture.md)
   - Component responsibilities
   - Design patterns
   - Lifecycle management

2. [Core Code](https://github.com/pyenvstudio/py-env-studio/tree/main/py_env_studio/core/plugins)
   - `base.py` - Plugin interface
   - `manager.py` - Factory and orchestration
   - `exceptions.py` - Error types

#### Adding Features
- [How Hooks Work](#hook-system-section)
- [Plugin Lifecycle](#plugin-lifecycle-section)
- [Adding New Hooks](#extending-the-system)

---

## 📂 File Structure Reference

### Documentation Files
```
docs/
├── development.md       # ⭐ Start here for plugin creation
├── architecture.md     # Technical deep-dive
├── quick-reference.md   # Quick lookup tables
├── PLUGIN_SYSTEM_SUMMARY.md    # Implementation overview
└── index.md (this file)

examples/
└── sample_plugin/
    ├── plugin.json             # Example manifest
    ├── sample_plugin.py        # Working plugin code
    └── README.md               # How to use example
```

### Code Files
```
py_env_studio/core/plugins/
├── __init__.py                 # Public API exports
├── base.py                     # BasePlugin class
├── manager.py                  # PluginManager class
└── exceptions.py               # Exception types

py_env_studio/ui/
└── main_window.py              # Plugin UI (see show_plugins_dialog)
```

### Configuration
```
~/.py_env_studio/plugins/
├── sample_plugin/
│   ├── plugin.json             # Manifest
│   └── sample_plugin.py        # Code
├── my_plugin/
│   ├── plugin.json
│   ├── my_plugin.py
│   └── config.json             # Optional
└── ...
```

---

## 🎯 Common Tasks

### I want to... Enable a plugin
→ [Quick Reference - Installation Steps](quick-reference.md#installation-steps)

### I want to... Create a plugin
→ [Development Guide - Creating a Plugin](development.md#step-3-implement-plugin-class)

### I want to... Understand hooks
→ [Architecture - Hook System](architecture.md#hook-system)

### I want to... Debug a plugin
→ [Quick Reference - Debugging](quick-reference.md#debugging)

### I want to... See working code
→ [Sample Plugin - sample_plugin.py](https://github.com/pyenvstudio/py-env-studio/blob/main/examples/sample_plugin/sample_plugin.py)

### I want to... Understand design patterns
→ [Architecture - Design Patterns](architecture.md#design-patterns)

---

## 🔑 Key Concepts

### Plugin
Self-contained module that extends PyEnvStudio functionality

### Hook
Event that plugins can subscribe to and react to

### PluginManager
Factory pattern class managing plugin lifecycle

### Plugin Metadata
JSON manifest describing plugin (name, version, hooks, etc.)

### Plugin Context
Application references passed to plugins at initialization

---

## 📋 API Reference Section

### BasePlugin Interface
**File**: `py_env_studio/core/plugins/base.py`

```python
class BasePlugin(ABC):
    @abstractmethod
    def get_metadata(self) -> PluginMetadata: ...
    
    @abstractmethod
    def initialize(self, app_context: Dict[str, Any]) -> None: ...
    
    @abstractmethod
    def execute(self, hook: str, context: Dict[str, Any]) -> Any: ...
    
    def validate(self) -> bool: ...
    def cleanup(self) -> None: ...
```

### PluginManager API
**File**: `py_env_studio/core/plugins/manager.py`

```python
class PluginManager:
    def discover_plugins(self) -> List[str]: ...
    def load_plugin(self, plugin_name: str) -> BasePlugin: ...
    def unload_plugin(self, plugin_name: str) -> None: ...
    def execute_hook(self, hook: str, context: Dict[str, Any]) -> List[Any]: ...
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]: ...
    def is_plugin_enabled(self, plugin_name: str) -> bool: ...
```

---

## 🔗 Hook System Section

### Environment Hooks
- `before_create_env` / `after_create_env`
- `before_delete_env` / `after_delete_env`
- `before_activate_env` / `after_activate_env`
- `before_rename_env` / `after_rename_env`

### Package Hooks
- `before_install_package` / `after_install_package`
- `before_uninstall_package` / `after_uninstall_package`
- `before_update_package` / `after_update_package`

### Application Hooks
- `on_app_start`
- `on_app_shutdown`
- `on_scan_complete`

**See**: [Architecture - Hook System](architecture.md#hook-system)

---

## 🔄 Plugin Lifecycle Section

1. **Discovery** - PluginManager finds plugins in `~/.py_env_studio/plugins/`
2. **Loading** - User enables plugin via UI
3. **Initialization** - Plugin's `initialize()` method called with app context
4. **Execution** - Plugin's `execute()` called when hooks fire
5. **Unloading** - User disables or app shuts down
6. **Cleanup** - Plugin's `cleanup()` method called

**See**: [Architecture - Plugin Lifecycle](architecture.md#plugin-lifecycle)

---

## 🛠️ Extending the System

### Adding a New Hook

1. Add hook to `PluginHook` enum:
   ```python
   # py_env_studio/core/plugins/base.py
   class PluginHook(str, Enum):
       MY_NEW_HOOK = "my_new_hook"
   ```

2. Fire hook from application:
   ```python
   # py_env_studio/ui/main_window.py
   self.plugin_manager.execute_hook("my_new_hook", {
       "data": "value"
   })
   ```

3. Plugin can subscribe:
   ```json
   {
     "hooks": ["my_new_hook"]
   }
   ```

### Adding Plugin Features

See [Architecture - Future Enhancements](architecture.md#future-enhancements)

---

## 📝 Documentation Checklist

- [x] Plugin Development Guide (30 min read)
- [x] Architecture Document (20 min read)
- [x] Quick Reference (5 min lookup)
- [x] Sample Plugin Code (working example)
- [x] API Reference (inline)
- [x] Hook Documentation (complete)
- [x] Lifecycle Diagrams (clear)
- [x] Design Patterns Explained (detailed)
- [x] DRY Principles Applied (documented)
- [x] SRE Principles (covered)
- [x] Security Considerations (noted)
- [x] Performance Characteristics (analyzed)
- [x] Testing Guide (included)
- [x] Troubleshooting (comprehensive)

---

## 🚀 Getting Started Path

### Path 1: Just Use Plugins (5 min)
1. Read: [Quick Reference](quick-reference.md)
2. Do: Enable sample plugin via Tools > Plugins
3. Done!

### Path 2: Create First Plugin (45 min)
1. Read: [Development Guide](development.md) introduction
2. Study: [Sample Plugin](https://github.com/pyenvstudio/py-env-studio/blob/main/examples/sample_plugin/sample_plugin.py)
3. Copy: Sample plugin to new directory
4. Modify: For your use case
5. Test: Via plugin manager
6. Done!

### Path 3: Understand System (60 min)
1. Read: [Architecture Document](architecture.md)
2. Study: [Core Plugin Code](https://github.com/pyenvstudio/py-env-studio/tree/main/py_env_studio/core/plugins)
3. Review: [Design Patterns](architecture.md#design-patterns)
4. Understand: [Plugin Lifecycle](architecture.md#plugin-lifecycle)
5. Done!

---

## ❓ FAQ

**Q: Where do I put my plugin?**
A: `~/.py_env_studio/plugins/my_plugin/`

**Q: What's required in plugin.json?**
A: name, version, author, description, entry_point, hooks

**Q: Can plugins access the UI?**
A: Yes, via `app_context.get("app")`

**Q: Do plugins need dependencies?**
A: No, but list them in `dependencies` field

**Q: Can plugins communicate?**
A: Not directly (future enhancement)

**Q: Are plugins sandboxed?**
A: No, they run in main process (security consideration)

---

## 📞 Support

- **Questions?** Check [Quick Reference FAQ](quick-reference.md)
- **Stuck?** Review [Development Guide - Troubleshooting](development.md#troubleshooting)
- **Code Issue?** See [Architecture - Troubleshooting](architecture.md#troubleshooting)
- **Example?** Study [Sample Plugin](https://github.com/pyenvstudio/py-env-studio/blob/main/examples/sample_plugin/sample_plugin.py)

---

## 📌 Summary

The PyEnvStudio Plugin System provides:

✅ **Complete Framework** - Base classes, manager, exceptions  
✅ **User Interface** - Tools > Plugins menu for management  
✅ **17 Hooks** - Cover all major operations  
✅ **Example Plugin** - Working code to learn from  
✅ **Comprehensive Docs** - 3 documents + quick reference  
✅ **Design Patterns** - Factory, Observer, Strategy, Template Method  
✅ **DRY Principles** - Handler pattern, metadata reuse  
✅ **SRE Ready** - Reliability, observability, scalability, simplicity, automation  

**Get started**: Read [Plugin Quick Reference](quick-reference.md) or [Plugin Development Guide](development.md)

---

**Version**: 1.0.0  
**Last Updated**: February 14, 2026  
**Status**: Production Ready ✅
