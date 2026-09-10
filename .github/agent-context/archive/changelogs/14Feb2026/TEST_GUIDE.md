# Quick Test Guide: Per-Environment Package Manager Support

## What to Test

### 1. Create Environment with UV
**Steps:**
1. Open PyEnvStudio
2. In "Create Environment" section, select "uv" from Package Manager dropdown
3. Enter environment name (e.g., "uv_test")
4. Click "Create Environment"

**Expected Results:**
- Console shows: "Creating virtual environment ... using uv"
- Environment is created with `uv venv` (if uv is installed)
- VM Tool column shows "uv X.X.X"
- Stored in env_data as: `"package_manager": "uv"`

### 2. Create Environment with PIP
**Steps:**
1. In "Create Environment" section, select "pip" from Package Manager dropdown
2. Enter environment name (e.g., "pip_test")
3. Click "Create Environment"

**Expected Results:**
- Console shows: "Creating virtual environment ... using venv"
- Environment is created with `python -m venv`
- VM Tool column shows "pip X.X.X"
- Stored in env_data as: `"package_manager": "pip"`

### 3. Package Manager Selector Is Per-Environment
**Steps:**
1. Create "env1" with "pip"
2. Change dropdown to "uv"
3. Create "env2" with "uv"
4. Look at VM Tool column

**Expected Results:**
- env1 still shows "pip X.X.X"
- env2 shows "uv X.X.X"
- Changing dropdown doesn't affect already-created environments

### 4. Package Operations Use Environment's Manager
**Steps:**
1. Select "env2" (created with uv)
2. Install a package (e.g., "requests")
3. Select "env1" (created with pip)
4. Install same package

**Expected Results:**
- env2 installation uses `uv pip install requests`
- env1 installation uses `pip install requests`
- Check logs to see which command was used

### 5. Verify No Global Sidebar Setting
**Visual Check:**
- Sidebar should NOT have "Package Manager" option
- Only "Appearance Mode" and "UI Scaling" in sidebar
- Package Manager dropdown only in "Create Environment" section

## Verification Commands

### Check Environment Data
```bash
# View env_data.json to see package_manager field
cat ~/.py_env_studio/venvs/env_data.json
```

Should show:
```json
{
  "uv_test": {
    "python_version": "3.10.5",
    "package_manager": "uv",
    ...
  },
  "pip_test": {
    "python_version": "3.11.0",
    "package_manager": "pip",
    ...
  }
}
```

### Check Package Manager Resolution
```bash
python test_env_managers.py
```

Should show correct manager for each environment.

## Success Criteria

✅ Package Manager dropdown only in Create Environment section
✅ VM Tool column shows actual tool used (not global preference)
✅ Different environments can have different managers
✅ Package operations use environment's specific manager
✅ Console logs show correct tool being used
✅ env_data.json contains package_manager field

## Troubleshooting

**Issue**: VM Tool column still shows global preference
- **Fix**: Clear env_data.json and recreate environments

**Issue**: Package operations use wrong manager
- **Fix**: Check if environment has package_manager in env_data

**Issue**: Sidebar still shows Package Manager dropdown
- **Fix**: Verify main_window.py doesn't have the sidebar code

**Issue**: "uv" selected but creates with pip
- **Fix**: Check if uv is installed (`uv --version`)
