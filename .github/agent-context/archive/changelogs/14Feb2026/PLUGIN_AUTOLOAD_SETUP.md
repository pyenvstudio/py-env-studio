# Plugin Auto-Loading on PES Startup

## ✅ What Changed

### 1. **Auto-Load On Startup** (`_setup_plugins()` method)
When PyEnvStudio starts, it now:
- ✅ Initializes the PluginManager
- ✅ Discovers all available plugins in `~/.py_env_studio/plugins/`
- ✅ **Automatically loads all discovered plugins**
- ✅ Executes the `on_app_start` hook for each loaded plugin

### 2. **Shutdown Hook** (`on_closing()` method)
When PyEnvStudio closes, it now:
- ✅ Executes the `on_app_shutdown` hook for all loaded plugins
- ✅ Allows plugins to clean up resources
- ✅ Gracefully exits

---

## 📊 Startup Flow

```
PyEnvStudio Startup
    ↓
1. _setup_plugins() called
    ├─ Initialize PluginManager
    ├─ Set app context (app, config, logger)
    ├─ discover_plugins() → scan ~/.py_env_studio/plugins/
    ├─ Auto-load each discovered plugin
    │  ├─ Load plugin.json manifest
    │  ├─ Import plugin class
    │  ├─ Validate plugin
    │  ├─ Initialize plugin with app context
    │  └─ Register hooks
    └─ execute_hook("on_app_start") → All plugins notified
    ↓
2. App runs normally
    ├─ User interacts with UI
    ├─ Operations trigger hooks
    │  └─ Plugins respond to hooks
    └─ ...
    ↓
3. User closes app
    ├─ on_closing() called
    ├─ execute_hook("on_app_shutdown") → All plugins notified
    └─ Plugin cleanup handlers run
    ↓
App exits cleanly
```

---

## 🔍 Code Changes

### Changed: `_setup_plugins()` method
```python
def _setup_plugins(self):
    """Initialize plugin manager and auto-load plugins on startup."""
    self.plugin_manager = PluginManager()
    self.plugin_manager.set_app_context({
        "app": self,
        "config": self.app_config,
        "logger": logging.getLogger(__name__)
    })
    
    # Discover and auto-load all available plugins
    discovered = self.plugin_manager.discover_plugins()
    logging.info(f"Discovered {len(discovered)} plugins: {discovered}")
    
    # Auto-load all discovered plugins on startup
    for plugin_name in discovered:
        try:
            self.plugin_manager.load_plugin(plugin_name)
            logging.info(f"✓ Auto-loaded plugin: {plugin_name}")
        except Exception as e:
            logging.error(f"✗ Failed to auto-load plugin '{plugin_name}': {e}")
    
    # Execute on_app_start hook for all loaded plugins
    try:
        self.plugin_manager.execute_hook("on_app_start", {
            "app": self,
            "version": self.version
        })
        logging.info("✓ Executed on_app_start hook for all plugins")
    except Exception as e:
        logging.error(f"Error executing on_app_start hook: {e}")
```

### New: `on_closing()` method
```python
def on_closing(self):
    """Handle application shutdown - cleanup plugins."""
    try:
        # Execute on_app_shutdown hook for all loaded plugins
        self.plugin_manager.execute_hook("on_app_shutdown", {
            "version": self.version
        })
        logging.info("✓ Executed on_app_shutdown hook for all plugins")
    except Exception as e:
        logging.error(f"Error executing on_app_shutdown hook: {e}")
    
    self.destroy()
```

### Updated: Main loop
```python
if __name__ == "__main__":
    app = PyEnvStudio()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)  # ← Adds shutdown handler
    app.mainloop()
```

---

## 🧪 Testing

### 1. **Enable Sample Plugin**
```bash
# Copy sample plugin to plugins directory
mkdir -p ~/.py_env_studio/plugins/sample_plugin
cp examples/sample_plugin/* ~/.py_env_studio/plugins/sample_plugin/
```

### 2. **Start PES**
```bash
python -m py_env_studio
```

### 3. **Check Console Output**
Look for these messages:
```
INFO:py_env_studio.ui.main_window:Discovered 1 plugins: ['sample_plugin']
INFO:py_env_studio.ui.main_window:✓ Auto-loaded plugin: sample_plugin
INFO:py_env_studio.ui.main_window:✓ Executed on_app_start hook for all plugins
```

### 4. **Verify Plugin Events**
Check plugin event log:
```
~/.py_env_studio/plugins/sample_plugin/events.log
```

Should contain startup event:
```json
{"timestamp": "2024-02-14T...", "hook": "on_app_start", "status": "success", ...}
```

### 5. **Close PES**
Look for:
```
INFO:py_env_studio.ui.main_window:✓ Executed on_app_shutdown hook for all plugins
```

---

## 📋 Plugin Lifecycle

### Startup (on_app_start)
1. Plugin's `initialize()` method called with app context
2. Plugin's `validate()` method called
3. Plugin's `execute("on_app_start", context)` called
4. Plugin can initialize resources, log events, etc.

### Runtime
- Plugins listen for hooks:
  - `before_create_env`, `after_create_env`
  - `before_delete_env`, `after_delete_env`
  - `before_activate_env`, `after_activate_env`
  - `before_rename_env`, `after_rename_env`
  - `before_install_package`, `after_install_package`
  - `before_uninstall_package`, `after_uninstall_package`
  - `before_update_package`, `after_update_package`
  - `on_scan_complete`

### Shutdown (on_app_shutdown)
1. Plugin's `execute("on_app_shutdown", context)` called
2. Plugin's `cleanup()` method called
3. Plugin resources released
4. App exits

---

## ⚙️ Configuration

### Auto-load Plugins
Currently **ENABLED by default** - all discovered plugins auto-load.

To disable auto-loading in future:
```python
# Option 1: Comment out the auto-load loop in _setup_plugins()
# Option 2: Add config setting to control auto-load behavior
```

### Plugin Directory
Default: `~/.py_env_studio/plugins/`

Each plugin folder should contain:
```
~/.py_env_studio/plugins/my_plugin/
├── plugin.json           (required - manifest)
├── my_plugin.py          (required - plugin code)
├── config.json           (optional)
└── events.log            (optional - generated)
```

---

## 🐛 Troubleshooting

### Plugin doesn't auto-load?
1. Check `~/.py_env_studio/plugins/` exists
2. Verify plugin.json is valid JSON
3. Check console for error messages
4. Verify entry_point in plugin.json is correct

### Plugin loads but doesn't work?
1. Check plugin.py has correct class name
2. Verify hooks list in plugin.json is correct
3. Check console for execute() errors
4. Review plugin events.log

### App crashes on shutdown?
1. Plugin's cleanup() threw exception
2. Check console error messages
3. Plugin may need exception handling in cleanup()

---

## ✨ Benefits

✅ **Automatic Discovery** - No manual configuration needed  
✅ **Seamless Integration** - Plugins load transparently  
✅ **Resource Management** - Cleanup on shutdown  
✅ **Error Resilience** - One plugin failure doesn't crash app  
✅ **Observability** - Log messages show plugin status  

---

## 🚀 Next Steps

1. **Create plugins** in `~/.py_env_studio/plugins/`
2. **Plugins auto-load** on app startup
3. **Monitor plugins** via Tools > Plugins menu
4. **Check events** in plugin event logs

---

**Status**: ✅ ACTIVE - Plugins auto-load on startup!
