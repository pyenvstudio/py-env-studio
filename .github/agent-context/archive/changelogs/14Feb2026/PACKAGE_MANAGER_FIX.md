# Fixed: Per-Environment Package Manager Support

## Issues Fixed

### Issue 1: VM Tool Column Shows Global Preference
**Problem**: VM Tool column was showing the current global package manager preference for ALL environments, changing whenever the sidebar dropdown was changed.

**Solution**: 
- Removed global package manager selector from sidebar
- Each environment now stores its package manager in `env_data.json`
- VM Tool column displays the actual manager used at creation time
- No longer changes when user changes selection in Create Environment section

### Issue 2: Package Manager Selector Location
**Problem**: Selector was in sidebar (global setting), misleading users

**Solution**:
- Moved Package Manager dropdown to "Create Environment" section
- Now positioned below "Python Path" field
- Only affects environments being created
- Clear intent: "which manager to use for this new environment"

### Issue 3: Package Operations Don't Use Environment's Manager
**Problem**: Package operations (install, uninstall, update) used global preference, not the manager that created the environment

**Solution**:
- Updated `package_manager.py` wrapper module
- New function: `get_env_package_manager(env_name)`
- Retrieves manager from environment's `env_data`
- All package operations route through this function
- If environment was created with uv, all operations use uv
- If environment was created with pip, all operations use pip

## Architecture Changes

### Data Flow (Before)
```
User selects "pip"/"uv" in sidebar
    ↓
Global preference set
    ↓
All envs show that preference
    ↓
All package ops use global preference
```

### Data Flow (After)
```
User selects "pip"/"uv" in Create Env section
    ↓
Create env with selected manager
    ↓
Store manager in env_data.json
    ↓
Each env shows its actual manager in table
    ↓
All package ops use that environment's manager
```

## Code Changes

### Files Modified

**`py_env_studio/core/package_manager.py`**
- Replaced `get_active_manager()` with `get_env_package_manager(env_name)`
- All functions now get manager from environment data, not global preference
- Automatic fallback: if uv unavailable, falls back to pip

**`py_env_studio/ui/main_window.py`**
- Removed global package manager dropdown from sidebar
- Added package manager dropdown to Create Environment section (row 3)
- Updated `create_env()` to use selected manager before creating
- Removed `change_package_manager_event()` callback
- VM Tool column still shows actual manager (now from env_data)

**`py_env_studio/core/env_manager.py`**
- No changes needed (already supports per-env storage)

## UI Changes

### Before
```
Sidebar:
├── Appearance Mode: [Light/Dark/System]
├── UI Scaling: [80%-120%]
└── Package Manager: [pip/uv] ← Global setting affecting all envs
```

### After
```
Sidebar:
├── Appearance Mode: [Light/Dark/System]
└── UI Scaling: [80%-120%]

Create Environment Section:
├── Environment Name: [_______]
├── Python Path: [_______] [Browse] or select: [▼]
├── ☑ Upgrade pip during creation
├── Package Manager: [pip/uv] ← Per-environment setting
└── [Create Environment]
```

## Behavior Examples

### Example 1: Multiple Environments with Different Managers
```
Environment   | Python Version | VM Tool  | ...
─────────────────────────────────────────────
myenv         | 3.10.5        | pip 24.0 | ...
uv_env        | 3.11.0        | uv 0.9   | ...
another_env   | 3.9.2         | pip 24.0 | ...

✓ Installing in uv_env uses uv
✓ Installing in myenv uses pip
✓ VM Tool column always shows the correct tool
✓ Changing Create Env dropdown doesn't affect existing envs
```

### Example 2: Creating Environment with UV
```
1. Select "uv" in Create Environment dropdown
2. Enter environment name "my_project"
3. Click "Create Environment"
4. Environment created with: uv venv
5. Stored as: package_manager = "uv"
6. VM Tool column shows: "uv 0.9"
7. Installing packages uses: uv pip install ...
```

## Benefits

✅ **Clarity**: Each environment explicitly shows what created it
✅ **Correctness**: Package ops use the right tool for each env
✅ **Consistency**: No more surprising tool switches
✅ **Flexibility**: Mix pip and uv environments in same setup
✅ **Predictability**: UI placement (Create Env section) matches functionality
✅ **Backward Compatible**: Old environments without `package_manager` field default to pip

## Testing

Run the test script to verify:
```bash
python test_env_managers.py
```

Output shows each environment's stored manager and resolved manager.

## Migration

Existing environments without `package_manager` field:
- Will default to `pip` when accessed
- Can be identified by "not set" in env_data
- Will use pip for all package operations
- No action needed - system handles gracefully
