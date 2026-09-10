# Auto-Resolve Feature - Testing Guide

## Manual Testing Instructions

### Prerequisites
- PyEnvStudio running
- At least 2 Python environments created (one with pip, one with uv)
- Internet connection (to reach PyPI)

---

## Test Case 1: Pip - Successful Auto-Resolve

### Setup
1. Create an environment named `test_pip` with pip
2. Note the Python version

### Steps
1. Go to **Packages** tab
2. Ensure `test_pip` is selected
3. In "Package Name" field, enter: `django==4.2`
4. Click **Install Package**

### Expected Behavior
- Console shows: `Installing django==4.2 in test_pip`
- If conflict occurs:
  - Console shows: `ERROR: ResolutionImpossible: ...`
  - Console shows: `[Auto-Resolve] Detected dependency conflict...`
  - Console shows: `[Auto-Resolve] Attempt 1: Installing 'django' without...`
  - Installation succeeds with compatible version (e.g., django==3.2.x)
  - Console shows: `[Auto-Resolve] ✓ Successfully installed 'django'`

### Possible Outcomes
- **A**: Success immediately (no conflict)
  - ✅ Package installs without auto-resolve
- **B**: Conflict occurs, auto-resolves
  - ✅ Package installs after auto-resolve (MAIN TEST)
- **C**: Conflict occurs, auto-resolve fails
  - ⚠️ Error shown after max retries
  - Check console for `[Auto-Resolve] Max retry attempts`

---

## Test Case 2: UV - Successful Auto-Resolve

### Setup
1. Create an environment named `test_uv` with UV
2. Note the Python version

### Steps
1. Go to **Packages** tab
2. Ensure `test_uv` is selected
3. In "Package Name" field, enter: `flask==2.0.0`
4. Click **Install Package**

### Expected Behavior
- Console shows: `[UV] Installing flask==2.0.0...`
- If conflict occurs:
  - Console shows: `[Auto-Resolve] Detected dependency conflict...`
  - Console shows: `[Auto-Resolve] Attempt 1: Installing 'flask'...`
  - Installation succeeds with compatible version
  - Console shows: `[Auto-Resolve] ✓ Successfully installed 'flask'`

### Possible Outcomes
- **A**: Success immediately (no conflict)
  - ✅ Package installs without auto-resolve
- **B**: Conflict occurs, auto-resolves
  - ✅ Package installs after auto-resolve (MAIN TEST)
- **C**: Conflict occurs, auto-resolve fails
  - ⚠️ Error shown after max retries

---

## Test Case 3: Console Logging Verification

### Steps
1. Install any package with version constraint
2. Watch the console output carefully

### Expected Console Output
```
Installing <package>==<version> in <env>
...
[Auto-Resolve] Detected dependency conflict, attempting auto-resolve...
[Auto-Resolve] Attempt 1: Installing '<package>' without version constraints
Installing <package>...
[Auto-Resolve] ✓ Successfully installed '<package>'
Installed <package> successfully
```

### Verification Points
- [ ] `[Auto-Resolve]` prefix appears
- [ ] Attempt number shown
- [ ] Package name without version shown
- [ ] Success message shown (✓ symbol)
- [ ] No error messages after resolution

---

## Test Case 4: Multi-Attempt Retry

### Steps (Hypothetical - may not trigger)
1. Try installing a package with multiple constraints
2. If auto-resolve needs to retry multiple times:

### Expected Behavior
- See Attempt 1, 2, 3 in console
- Package installs on one of the attempts
- Or fails with: `[Auto-Resolve] Max retry attempts (3) reached`

### Verification Points
- [ ] Attempts numbered correctly (1, 2, 3)
- [ ] Max 3 attempts shown (prevents infinite loops)
- [ ] Clear error message if all fail

---

## Test Case 5: Non-Conflicting Package

### Setup
1. Select any environment
2. Install a package with no dependencies or simple dependencies

### Steps
1. Enter package name: `requests` (or similar simple package)
2. Click **Install Package**

### Expected Behavior
- Console shows: `Installing requests in <env>`
- NO `[Auto-Resolve]` messages (no conflict)
- Package installs normally
- Success message shown

### Verification Points
- [ ] Auto-resolve NOT triggered
- [ ] Installation succeeds immediately
- [ ] No error messages

---

## Test Case 6: Invalid Package

### Setup
1. Select any environment

### Steps
1. Enter package name: `nonexistent-package-12345`
2. Click **Install Package**

### Expected Behavior
- Installation fails (package not found)
- NO auto-resolve attempt (not a resolution error)
- Error shown: Package not found (from pip/uv)

### Verification Points
- [ ] Auto-resolve NOT triggered (correct behavior)
- [ ] Proper error message shown
- [ ] Console shows pip/uv error

---

## Test Case 7: Version Constraint Removal Verification

### Steps
1. Install package with complex version spec:
   - Example: `numpy>=1.20.0,<2.0.0`

### Expected Behavior
If conflict occurs:
- Console shows: `Attempt 1: Installing 'numpy' without version constraints`
- Installs `numpy` without the >= and < constraints
- Package installs with compatible version

### Verification Points
- [ ] Version constraints shown as removed
- [ ] Package name extracted correctly
- [ ] Installation succeeds with any compatible version

---

## Test Case 8: Config Setting (Optional)

### If Disabling Auto-Resolve (Future Feature)
1. Edit `config.ini`
2. Change: `auto_resolve_dependencies = false`
3. Restart PyEnvStudio
4. Try installing package with conflict

### Expected Behavior
- On conflict: Direct error shown
- NO auto-resolve messages
- NO retry attempts
- User must handle error manually

### Verification Points
- [ ] Setting respected
- [ ] No auto-resolve when disabled
- [ ] Original error shown to user

---

## Logging Checklist

During any installation attempt, verify these log patterns:

```
✓ [Auto-Resolve] Detected dependency conflict...
✓ [Auto-Resolve] Attempt N: Installing '<pkg>' without...
✓ [Auto-Resolve] ✓ Successfully installed...
✓ [Auto-Resolve] Max retry attempts (3) reached (if failure)
```

---

## What to Look For

### Success Indicators ✅
- [x] `[Auto-Resolve]` prefix in console
- [x] Attempt number shown
- [x] Package name extracted correctly
- [x] Version constraints removed
- [x] Package installs with compatible version
- [x] Success message shown

### Error Indicators ⚠️
- [x] Max retries reached message
- [x] Error output from pip/uv
- [x] No auto-resolve for non-resolution errors

### Normal Behavior (No Auto-Resolve Needed)
- [x] No `[Auto-Resolve]` messages
- [x] Direct success or failure
- [x] Appropriate error messages

---

## Common Test Packages with Known Issues

### django==4.2
- Often has dependency conflicts
- Good test case for auto-resolve

### flask==2.0.0
- May conflict with newer werkzeug
- Good test case for auto-resolve

### numpy>=1.20.0,<2.0.0
- Complex version constraints
- Good test case for version removal

### requests (no version)
- Should install without issues
- Good test case for non-conflict scenario

---

## Troubleshooting During Testing

### If Auto-Resolve Doesn't Trigger
1. Check package actually has conflicts
2. Try: `pip install <package>==<specific-version>` manually
3. See if pip shows ResolutionImpossible error
4. If no error, package has no conflicts (normal)

### If Console Shows No [Auto-Resolve] Messages
1. Check if error is resolution-related
2. Verify package name is correct
3. Check PyPI is accessible
4. Verify config setting is enabled

### If Package Fails to Install After Auto-Resolve
1. Verify python version supports package
2. Check system has required development tools
3. Check disk space available
4. Try manual `pip install <package>` (no version)

---

## Success Criteria

### Minimum Required ✅
- [x] No errors on import
- [x] Code runs without crashes
- [x] Logging appears when expected
- [x] Package installs successfully

### Recommended ✅
- [x] Multiple test packages work
- [x] Both pip and uv environments tested
- [x] Console messages are clear
- [x] No false positives

### Ideal ✅
- [x] All test cases pass
- [x] Conflict scenario tested and works
- [x] Logs are detailed and helpful
- [x] Performance is acceptable

---

## Test Report Template

```
Date: _______________
Tester: _______________

Test Environment:
- PyEnvStudio Version: _______________
- Python Version: _______________
- OS: _______________

Test Case 1 (Pip): [PASS / FAIL / N/A]
Test Case 2 (UV): [PASS / FAIL / N/A]
Test Case 3 (Logging): [PASS / FAIL / N/A]
Test Case 4 (Multi-Attempt): [PASS / FAIL / N/A]
Test Case 5 (No-Conflict): [PASS / FAIL / N/A]
Test Case 6 (Invalid Package): [PASS / FAIL / N/A]
Test Case 7 (Version Removal): [PASS / FAIL / N/A]
Test Case 8 (Config): [PASS / FAIL / N/A]

Issues Found:
1. _______________
2. _______________
3. _______________

Overall Status: [PASS / FAIL]

Notes:
_______________
_______________
_______________
```

---

## Next Steps After Testing

1. **If All Pass**: Feature is ready
2. **If Some Fail**: Check specific error, consult documentation
3. **If Issues Found**: Create issue report with:
   - Test case number
   - Error message
   - Console output
   - Environment details

---

**Happy Testing!** 🚀

