# Testing Verification Guide: Dependency Impact Preview

## ✅ Expected Test Output Reference

Use this guide to verify that your tests produce the correct output.

---

## Test 1: Python Module Import

### Command
```bash
python -c "from py_env_studio.core import dependency_preview; print('✅ Module loaded successfully')"
```

### ✅ EXPECTED OUTPUT
```
✅ Module loaded successfully
```

### ❌ If You See This Instead
```
ModuleNotFoundError: No module named 'py_env_studio'
```

**Fix:** Make sure you're in the correct directory
```bash
cd c:\Users\Lenovo\Desktop\Contribution\py_env_studio
```

---

## Test 2: Unit Tests - Complete Output

### Command
```bash
python tests/test_dependency_preview.py
```

### ✅ EXPECTED OUTPUT

```
..................s.
Ran 22 tests in 0.002s

OK (skipped=1)
```

### Explanation
- `..................s.` = Test results
  - `.` = Test passed ✅ (shows 20 times)
  - `s` = Test skipped ⏭️ (integration test requires live environment)
- `Ran 22 tests in 0.002s` = Ran all 22 tests in 2 milliseconds
- `OK (skipped=1)` = All passed, 1 was skipped

### ❌ If You See Failures

Example of FAILED test:
```
FAIL: test_case_insensitive
----------------------------------------------------------------------
AssertionError: 'numpy' != 'NUMPY'
----------------------------------------------------------------------

Ran 22 tests in 0.003s

FAILED (failures=1)
```

**What to check:**
1. Are you in the correct directory?
2. Have you modified the core module?
3. Try running again
4. Check Python version is 3.8+

---

## Test 3: Detailed Unit Test Results

### Command
```bash
python -m unittest tests.test_dependency_preview -v
```

### ✅ EXPECTED OUTPUT

```
test_case_insensitive (test_dependency_preview.TestParsePackageSpec) ... ok
test_check_breaking_changes (test_dependency_preview.TestCheckBreakingChanges) ... ok
test_check_unknown_package (test_dependency_preview.TestCheckBreakingChanges) ... ok
test_complex_version (test_dependency_preview.TestParsePackageSpec) ... ok
test_creation (test_dependency_preview.TestDependencyChange) ... ok
test_creation (test_dependency_preview.TestBreakingChange) ... ok
test_creation (test_dependency_preview.TestPreviewResult) ... ok
test_dash_format (test_dependency_preview.TestExtractNameAndVersion) ... ok
test_equals_format (test_dependency_preview.TestExtractNameAndVersion) ... ok
test_exact_version (test_dependency_preview.TestParsePackageSpec) ... ok
test_get_installed_packages (test_dependency_preview.TestGetInstalledPackages) ... ok
test_minimum_version (test_dependency_preview.TestParsePackageSpec) ... ok
test_parentheses_format (test_dependency_preview.TestExtractNameAndVersion) ... ok
test_simple_name (test_dependency_preview.TestParsePackageSpec) ... ok
test_to_dict (test_dependency_preview.TestDependencyChange) ... ok
test_to_dict (test_dependency_preview.TestBreakingChange) ... ok
test_to_dict (test_dependency_preview.TestPreviewResult) ... ok
test_to_dict_empty (test_dependency_preview.TestPreviewResult) ... ok
test_to_dict_with_changes (test_dependency_preview.TestPreviewResult) ... ok
test_with_old_version (test_dependency_preview.TestDependencyChange) ... ok
test_case_insensitive (test_dependency_preview.TestGetInstalledPackages) ... ok
test_preview_install_requests (test_dependency_preview.TestIntegration) ... skipped 'Requires actual environment'

----------------------------------------------------------------------
Ran 22 tests in 0.003s

OK (skipped=1)
```

---

## Test 4: VS Code Extension Load

### Where to Check
1. Start extension: Press **F5** in VS Code (pes-vscode-extention folder)
2. New window opens with extension
3. Check the **Output** panel

### ✅ EXPECTED OUTPUT (in Output panel)

```
PES Studio extension is now active
Looking for Python server at: [path]
Using Python: python
Running: python -m python_server
Server started successfully
✅ PES Studio: Connected to Python server
```

### ❌ Problems

**If you see:**
```
[PES Server Error] No module named 'grpc'
```
**Solution:** Install gRPC
```bash
pip install grpcio grpcio-tools protobuf
```

**If you see:**
```
⚠ PES Studio: Python server not responding. Some features may be limited.
```
**Solution:** Wait 5 seconds for server to start, or reload window

---

## Test 5: Command Palette Command

### Step 1: Press Ctrl+Shift+P
The command palette opens

### Step 2: Search for "Preview Install"

### ✅ EXPECTED RESULT
You should see in the dropdown:
```
> PES: Preview Package Install
  Preview installation impact before installing a package
```

### ❌ If You Don't See It

**Solution:** Reload VS Code window
1. Ctrl+Shift+P
2. Type: "Reload Window"
3. Press Enter
4. Wait 5 seconds
5. Try Ctrl+Shift+P again

---

## Test 6: Feature Functionality - "requests" Package

### Steps
1. Ctrl+Shift+P → "Preview Install"
2. Select your Python environment
3. Enter: `requests`

### ✅ EXPECTED OUTPUT (Webview Preview)

```
📦 Dependency Impact Preview

Installing: requests
Environment: [your-env]

Summary:
+ 2      NEW PACKAGES
↑ 0      UPGRADES
- 0      REMOVALS

📥 New Packages (2)
  ├─ requests
  │  Version: v[version]
  │
  └─ urllib3
     Version: v[version]

✅ Ready to Install
Review the dependency changes above. 
If everything looks good, you can proceed with installation.
```

### Key Indicators of Success
- ✅ Webview displays without errors
- ✅ Summary badges show numbers
- ✅ Package list displays
- ✅ Beautiful formatting with colors
- ✅ "Ready to Install" message appears

---

## Test 7: Feature Functionality - "numpy" Package

### Steps
1. Ctrl+Shift+P → "Preview Install"
2. Select your Python environment
3. Enter: `numpy`

### ✅ EXPECTED OUTPUT

```
📦 Dependency Impact Preview

Installing: numpy
Environment: [your-env]

Summary:
+ 1      NEW PACKAGES
↑ X      UPGRADES
- 0      REMOVALS

📥 New Packages (1)
  └─ numpy
     Version: v[latest]

📈 Upgrades (X)
  ├─ [package1]  [old] → [new]
  └─ [package2]  [old] → [new]

⚠️ Potential Breaking Changes (1)
  └─ numpy: May break code using deprecated numpy.dtype constructors
     Severity: high

✅ Ready to Install
```

### Key Indicators
- ✅ Shows new packages section
- ✅ Shows upgrades with version changes
- ✅ **Shows breaking changes warning** ⚠️
- ✅ Breaking change severity is shown

---

## Test 8: Feature Functionality - Specific Version

### Steps
1. Ctrl+Shift+P → "Preview Install"
2. Select environment
3. Enter: `django==4.2`

### ✅ EXPECTED OUTPUT

```
📦 Dependency Impact Preview

Installing: django==4.2
Environment: [your-env]

Summary:
+ X      NEW PACKAGES
↑ 1      UPGRADES
- 0      REMOVALS

[... packages shown ...]

📈 Upgrades (1)
  └─ django  [current] → 4.2

⚠️ Potential Breaking Changes
[... if upgrading from major version ...]

✅ Ready to Install
```

### Key Indicators
- ✅ Parses version constraint `==4.2` correctly
- ✅ Shows upgrade if already installed
- ✅ Shows exact version in upgrade section

---

## Test 9: Error Case - Invalid Package

### Steps
1. Ctrl+Shift+P → "Preview Install"
2. Select environment
3. Enter: `this-package-definitely-does-not-exist-xyz123`

### ✅ EXPECTED BEHAVIOR

**Option A:** Shows error in preview
```
Error: Package not found
Please verify the package name and try again.
```

**Option B:** Shows empty/basic result
```
📦 Dependency Impact Preview

Installing: this-package-definitely-does-not-exist-xyz123
Environment: [your-env]

Summary:
+ 0      NEW PACKAGES
↑ 0      UPGRADES
- 0      REMOVALS

✅ Ready to Install
```

### Key Indicators
- ✅ Error is handled gracefully
- ✅ No extension crash
- ✅ User gets feedback

---

## Test 10: Preview Panel UI Verification

### Checklist
Check that the preview panel has:

- [ ] ✅ Header with title "📦 Dependency Impact Preview"
- [ ] ✅ Package name and environment shown
- [ ] ✅ Summary badges with numbers (+ X, ↑ X, - X)
- [ ] ✅ Color-coded sections (green, yellow, red if applicable)
- [ ] ✅ Package lists with names and versions
- [ ] ✅ Icons/emojis display correctly
- [ ] ✅ Text is readable with good contrast
- [ ] ✅ Layout is organized and professional
- [ ] ✅ "Ready to Install" message at bottom
- [ ] ✅ No JavaScript errors in console

---

## Test 11: Performance Benchmark

### Simple Package (requests)
- **Expected time:** 1-3 seconds
- **Max acceptable:** 5 seconds

### Medium Package (pandas)
- **Expected time:** 5-10 seconds
- **Max acceptable:** 15 seconds

### Complex Package (tensorflow)
- **Expected time:** 10-30 seconds
- **Max acceptable:** 60 seconds

---

## Test 12: Stress Test

### Try Multiple Preview in Sequence

```
1. Preview "requests" → Should work
2. Preview "numpy" → Should work
3. Preview "pandas" → Should work
4. Preview "django==4.2" → Should work
5. Preview "flask" → Should work
```

### ✅ EXPECTED RESULT
- All 5 previews work without error
- No memory leaks
- Extension remains responsive
- Each preview shows quickly (after first one)

---

## ✅ Complete Test Verification Checklist

Mark these off as you complete each test:

### Python Module Tests
- [ ] ✅ Module imports successfully
- [ ] ✅ All 22 unit tests pass
- [ ] ✅ Verbose test output shows all tests

### VS Code Extension Tests
- [ ] ✅ Extension loads (F5)
- [ ] ✅ Connected to Python server
- [ ] ✅ Command appears in palette

### Feature Functionality Tests
- [ ] ✅ "requests" preview works
- [ ] ✅ "numpy" preview works with breaking changes
- [ ] ✅ "django==4.2" preview works with version
- [ ] ✅ Complex versions work (pandas>=1.5,<2.0)

### UI/UX Tests
- [ ] ✅ Preview panel displays properly
- [ ] ✅ Text is readable
- [ ] ✅ Colors are appropriate
- [ ] ✅ Layout is organized
- [ ] ✅ Icons display correctly

### Error Handling Tests
- [ ] ✅ Invalid package handled gracefully
- [ ] ✅ No extension crashes
- [ ] ✅ Error messages are clear

### Performance Tests
- [ ] ✅ Simple packages < 5 seconds
- [ ] ✅ Medium packages < 15 seconds
- [ ] ✅ Multiple previews work sequentially

### Stress Tests
- [ ] ✅ 5+ previews work without errors
- [ ] ✅ Extension remains responsive
- [ ] ✅ No memory issues

---

## 🎉 Success Criteria

Your feature is working correctly when:

✅ **ALL** tests pass (22/22)  
✅ **ALL** UI elements display correctly  
✅ **MULTIPLE** packages preview successfully  
✅ **ERROR** cases are handled gracefully  
✅ **PERFORMANCE** is acceptable (<5s for simple packages)  

---

## 📝 Test Report Template

Use this to document your testing:

```
TEST REPORT: Dependency Impact Preview
========================================

Date: [Today's date]
Tester: [Your Name]
Environment: [Your System, e.g., Windows 10, Python 3.10]

UNIT TESTS
  Result: ✅ PASS / ❌ FAIL
  Tests Passed: 22/22
  Time: 0.002s

EXTENSION LOAD
  Result: ✅ PASS / ❌ FAIL
  Message: Connected to Python server

COMMAND PALETTE
  Result: ✅ PASS / ❌ FAIL
  Command Found: Yes

FEATURE TESTS
  requests:     ✅ PASS / ❌ FAIL
  numpy:        ✅ PASS / ❌ FAIL
  django==4.2:  ✅ PASS / ❌ FAIL
  Version range: ✅ PASS / ❌ FAIL

OVERALL: ✅ PASS / ❌ FAIL

NOTES: [Any issues or observations]
```

---

**Use this guide to verify every test passes correctly!** ✅
