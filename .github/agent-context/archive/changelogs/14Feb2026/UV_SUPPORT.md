# UV Package Manager Support for PyEnvStudio

## Overview
PyEnvStudio now supports creating and managing Python virtual environments using both **pip** (traditional) and **uv** (modern, 10-100x faster package manager).

## Features Implemented

### 1. **Package Manager Selection UI**
- New dropdown in sidebar under "Package Manager" setting
- Choose between "pip" and "uv"
- Selection is saved to config file and persists across sessions

### 2. **Smart Virtual Environment Creation**
- When creating a new environment, PyEnvStudio uses the selected package manager
- If uv is selected but not installed, automatically falls back to pip
- Creates environments with `uv venv` when uv is available
- Creates environments with `python -m venv` as fallback

### 3. **Per-Environment Package Manager Tracking**
- Each environment stores which package manager was used at creation time
- "VM Tool" column in environment table shows actual tool (not just global preference)
- Display format: "pip v24.0" or "uv 0.9.0"

### 4. **Unified Package Operations**
- `package_manager.py` wrapper module intelligently routes to pip or uv
- All operations (install, uninstall, update, import/export requirements) work with both managers
- Automatic fallback: if uv fails, falls back to pip gracefully

### 5. **UV Tools Module**
- New `core/uv_tools.py` implements uv-based package operations
- Functions: install, uninstall, update, import/export requirements, check outdated packages
- Version detection and availability checking
- Proper error handling and logging

## Files Created/Modified

### New Files
- `py_env_studio/core/uv_tools.py` - UV package manager implementation (380+ lines)
- `py_env_studio/core/package_manager.py` - Wrapper layer for dual manager support (210+ lines)

### Modified Files
- `py_env_studio/core/env_manager.py`
  - Added `get_preferred_package_manager()` - Get user's manager preference
  - Added `set_preferred_package_manager()` - Set user's manager preference
  - Added `get_package_manager_display()` - Get display string with version
  - Updated `create_env()` - Now uses selected package manager
  - Updated `set_env_data()` - Stores package_manager per environment

- `py_env_studio/core/pip_tools.py`
  - Added `get_pip_version()` - Get pip version with regex parsing

- `py_env_studio/ui/main_window.py`
  - Updated imports to use `package_manager` wrapper instead of direct `pip_tools`
  - Added "VM Tool" column to environment table (shows actual manager used)
  - Added package manager dropdown in sidebar
  - Added `change_package_manager_event()` callback
  - Per-environment display of package manager in table

## Usage

### Creating an Environment with UV
1. In the sidebar, select "UV" from the "Package Manager" dropdown
2. Create a new environment as usual
3. The environment will be created using `uv venv` (if uv is installed)
4. The "VM Tool" column will show "uv X.X.X"

### Installing Packages
- Package operations automatically use the manager that created the environment
- If uv is unavailable, falls back to pip
- All operations (install, uninstall, update, requirements) work transparently

### Managing Preference
- Dropdown selection saves to `config.ini` under `[settings]` section
- Key: `preferred_package_manager` (value: "pip" or "uv")
- Can be changed anytime from sidebar UI

## Technical Details

### Strategy Pattern Implementation
- Base interface: `package_manager.py` wrapper functions
- Concrete implementations: `pip_tools.py` and `uv_tools.py`
- Routes based on `get_preferred_package_manager()`

### Error Handling & Fallback
- If uv not installed: uses pip automatically
- If uv command fails: falls back to pip
- Logging for all failures
- User-friendly error messages

### Code Ethics Applied
✅ Backward compatible - existing pip workflows unaffected
✅ Optional feature - uv not required
✅ Fail gracefully - automatic fallback
✅ DRY principle - shared interface layer
✅ Clean separation - separate modules for each manager
✅ Per-environment storage - accurate tool tracking
✅ User choice - explicit selection mechanism
✅ Performance - leverages uv's 10-100x speed advantage

## Performance Benefits

UV is 10-100x faster than pip for:
- Creating virtual environments
- Installing packages
- Resolving dependencies
- Locking versions

**Note**: For compatibility, pip is still installed in all environments created via uv, ensuring broader package support.

## Bug Fixes Applied

### Fix 1: Per-Environment Package Manager Display
**Issue**: VM Tool column showed global preference for all environments
**Solution**: Store `package_manager` in env_data when creating each environment, display that value

### Fix 2: Environment Creation with UV
**Issue**: Creating environment with uv selected still used pip
**Solution**: Updated `create_env()` to check preferred manager and use `uv venv` when available

## Configuration

### Default Config Location
`~/.py_env_studio/config.ini`

### Config Example
```ini
[settings]
preferred_package_manager = pip
# or
preferred_package_manager = uv
```

## Future Enhancements

Potential additions:
- Per-environment manager override
- UV project management features
- Automatic uv installation
- Migration helper (convert pip envs to uv)
- Performance metrics dashboard
