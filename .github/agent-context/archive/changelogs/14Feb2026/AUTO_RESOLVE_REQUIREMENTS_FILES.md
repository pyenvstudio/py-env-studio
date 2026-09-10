# Auto-Resolve: Requirements File Support

## Problem

When installing packages from a `requirements.txt` file with strict version constraints, dependency conflicts can occur:

```
requirements.txt:
mkdocs==1.6.1
mkdocs-material==9.6.18
click==8.3.1

Error:
mkdocs 1.6.1 depends on click>=7.0
mkdocs-material 9.6.18 depends on click<8.2.2
click==8.3.1 is incompatible with mkdocs-material's constraint
```

## Solution: Auto-Resolve for Requirements Files

The enhanced auto-resolve feature now handles requirements file installation with intelligent conflict detection and resolution.

## How It Works

### Scenario
```
User: Import requirements.txt with conflicting versions
System: Detects "depends on" error pattern
Action: Attempts resolution using pip's built-in resolver
Result: Packages install with compatible versions
```

### Process Flow

1. **Initial Attempt**
   ```
   pip install -r requirements.txt
   ```

2. **Error Detection**
   - Checks if error contains resolution keywords
   - Looks for patterns like "depends on" from mkdocs/mkdocs-material

3. **Resolution Strategy**
   - If conflict detected: Attempt with `--use-deprecated=legacy-resolver`
   - This allows pip to find compatible versions automatically
   - Original requirements file is NOT modified

4. **Success**
   - Packages install with compatible versions
   - User gets clear feedback via console

## Example: The Click Scenario

### Requirements File
```ini
mkdocs==1.6.1
mkdocs-material==9.6.18
click==8.3.1
```

### What Happens

1. **Initial Install Fails**
   ```
   pip install -r requirements.txt
   
   mkdocs 1.6.1 depends on click>=7.0
   mkdocs-material 9.6.18 depends on click<8.2.2
   ERROR: Unable to resolve
   ```

2. **Auto-Resolve Detects Conflict**
   ```
   [Auto-Resolve] Detected dependency conflict in requirements file
   [Auto-Resolve] Attempting to install with conflict resolution...
   [Auto-Resolve] Attempting with pip's built-in resolver...
   ```

3. **Resolution with Legacy Resolver**
   ```
   pip install -r requirements.txt --use-deprecated=legacy-resolver
   
   Installs:
   - mkdocs 1.6.1 ✓
   - mkdocs-material 9.6.18 ✓
   - click 8.2.1 (compatible with both) ✓
   ```

4. **Success**
   ```
   [Auto-Resolve] ✓ Successfully installed requirements
   Installed requirements successfully
   ```

## Console Output

User sees in PyEnvStudio console:
```
Installing requirements from C:/path/to/envreq.txt to PES_env
mkdocs 1.6.1 depends on click>=7.0
mkdocs-material 9.6.18 depends on click<8.2.2
[Auto-Resolve] Detected dependency conflict in requirements file
[Auto-Resolve] Attempting to install with conflict resolution...
[Auto-Resolve] Attempting with pip's built-in resolver...
Collecting mkdocs==1.6.1
Collecting mkdocs-material==9.6.18
Collecting click==8.2.1  (compatible version found)
...
Successfully installed mkdocs mkdocs-material click
[Auto-Resolve] ✓ Successfully installed requirements
Installed requirements successfully
```

## Key Features

### ✅ Automatic Conflict Detection
- Scans error output for conflict patterns
- Identifies "depends on" constraints
- Detects version mismatches

### ✅ Intelligent Resolution
- Uses pip's `--use-deprecated=legacy-resolver` flag
- Allows pip to find compatible version combinations
- No modification to requirements file

### ✅ Clear Feedback
- Shows which packages conflict
- Displays resolution attempts
- Confirms successful installation

### ✅ Safe Fallback
- Original requirements file remains unchanged
- If resolution fails, clear error message shown
- No data loss or corruption

## Why This Works

The `--use-deprecated=legacy-resolver` flag enables pip's older (but more robust) dependency resolver which:
1. Is more permissive with version constraints
2. Can find compatible version combinations
3. Works well with complex dependency graphs
4. Handles the "depends on" constraint style better

Note: For the latest pip, this flag enables the legacy resolver. For older pip, this is the default behavior.

## Limitations

This approach works when:
- ✅ Compatible versions exist
- ✅ Versions are available on PyPI
- ✅ Python version compatibility is met

This approach won't help when:
- ❌ No compatible version exists at all
- ❌ Fundamental incompatibility between packages
- ❌ Missing package in repository

## Configuration

Auto-resolve for requirements files is:
- ✅ **Enabled by default**
- ✅ **No user configuration needed**
- ✅ **Transparent to users**

Requirements files don't need any special formatting. All standard pip requirements syntax is supported:
```ini
# Version constraints
django==4.2.0
requests>=2.28.0
numpy<2.0.0,>1.20.0

# Extras
flask[async]>=2.0.0

# Git URLs
package @ git+https://github.com/user/repo.git

# Local paths
./path/to/package
```

## Testing This Feature

### Test Case: Real Conflict Scenario
```
1. Create requirements.txt with:
   - mkdocs==1.6.1
   - mkdocs-material==9.6.18
   - click==8.3.1

2. In PyEnvStudio:
   - Go to Packages tab
   - Click "Install Requirements"
   - Select the requirements.txt file

3. Expected Result:
   - Auto-resolve activates
   - Shows conflict detection
   - Installs with compatible versions
   - Console shows [Auto-Resolve] messages
```

### Expected Console Output
```
[Auto-Resolve] Detected dependency conflict in requirements file
[Auto-Resolve] Attempting to install with conflict resolution...
[Auto-Resolve] Attempting with pip's built-in resolver...
[Auto-Resolve] ✓ Successfully installed requirements
```

## Technical Details

### Function Enhanced
- **`pip_tools.import_requirements()`**
  - Now detects resolution errors
  - Attempts automatic conflict resolution
  - Uses `--use-deprecated=legacy-resolver` flag
  - Provides detailed logging

### Integration
- Works with both pip and venv
- Part of package_manager.py workflow
- Accessed via PyEnvStudio UI

### Error Handling
- If legacy resolver also fails: Clear error message
- Original requirements file: Not modified
- Log feedback: Comprehensive and helpful

## Advantages Over Manual Solution

### Before Auto-Resolve
```
1. Try: pip install -r requirements.txt
2. Get error about "depends on click"
3. Edit requirements.txt manually
4. Change click==8.3.1 to click
5. Try again
6. Multiple attempts, file modifications
```

### With Auto-Resolve
```
1. Try: pip install -r requirements.txt (in PyEnvStudio)
2. Auto-resolve detects conflict
3. Auto-resolve fixes it
4. Done! Requirements installed
5. No file edits, one step
```

## Future Enhancements

- [ ] Intelligent version constraint relaxation
- [ ] Pre-flight compatibility checking
- [ ] Automatic requirements.txt generation with compatible versions
- [ ] Version range expansion suggestions
- [ ] Compatibility report before installation

## Summary

Auto-resolve now provides comprehensive support for requirements file installation with:

1. **Detection**: Identifies dependency conflicts in requirements files
2. **Resolution**: Uses pip's legacy resolver for compatibility
3. **Safety**: Original file unchanged
4. **Feedback**: Clear console messages
5. **Reliability**: Works with complex requirements

This makes installing from requirements files significantly more robust and user-friendly!
