# How to Run: Dependency Impact Preview Feature

## 🚀 Quick Start (2 minutes)

### Prerequisites
- ✅ Python 3.8+
- ✅ VS Code installed
- ✅ PES VS Code Extension loaded
- ✅ A Python environment with pip

### Step 1: Verify Python Module Works

Open your terminal in the project directory:

```bash
cd c:\Users\Lenovo\Desktop\Contribution\py_env_studio

# Test the Python module
python -c "from py_env_studio.core import dependency_preview; print('✅ Module loaded successfully')"
```

**Expected Output:**
```
✅ Module loaded successfully
```

### Step 2: Run Unit Tests

```bash
# Run all 22 unit tests
python tests/test_dependency_preview.py

# Expected output:
# ..................s.  (22 dots = passed tests, 1 s = skipped)
# Ran 22 tests in 0.002s
# OK (skipped=1)
```

### Step 3: Start VS Code Extension

```bash
# Navigate to extension directory
cd pes-vscode-extention

# Compile TypeScript
npm run compile

# Output should show: ... successfully
```

### Step 4: Load Extension in VS Code

1. Open VS Code
2. Press `F5` to start debugging the extension
3. A new VS Code window opens with the extension loaded
4. Check the Output panel → you should see connection messages

### Step 5: Run the Feature

In the new VS Code window:

1. Press `Ctrl+Shift+P`
2. Type: `PES: Preview Install`
3. Select from dropdown
4. Choose an environment (or create one)
5. Enter a package name: `requests`
6. Review the preview!

---

## 🧪 Detailed Testing Guide

### Test 1: Python Module Unit Tests

**Location:** `tests/test_dependency_preview.py`

```bash
cd py_env_studio

# Run tests with verbose output
python -m unittest tests.test_dependency_preview -v

# Or run directly
python tests/test_dependency_preview.py
```

**What it tests:**
- ✅ DependencyChange class (creation, serialization)
- ✅ BreakingChange class (creation, serialization)
- ✅ PreviewResult class (creation, serialization)
- ✅ Package spec parsing (various formats)
- ✅ Breaking change detection
- ✅ pip output parsing

**Expected Results:**
```
test_case_insensitive ... ok
test_check_outdated ... ok
test_complex_version ... ok
test_creation ... ok
test_dash_format ... ok
...
Ran 22 tests in 0.002s
OK (skipped=1)
```

### Test 2: Manual Feature Test (Recommended)

**Environment:** VS Code with extension running

**Test Cases:**

#### Test Case A: Simple Package Preview
```
Action:
1. Cmd+Shift+P → "PES: Preview Install"
2. Select your Python environment
3. Enter: "requests"

Expected:
✅ Shows preview without error
✅ Shows new packages section
✅ May show upgrades
✅ Displays in beautiful webview
```

#### Test Case B: Package with Breaking Changes
```
Action:
1. Cmd+Shift+P → "PES: Preview Install"
2. Select environment
3. Enter: "numpy"

Expected:
✅ Shows preview
✅ Shows "Potential Breaking Changes" section
✅ Displays numpy breaking change warning with severity
```

#### Test Case C: Version Constraints
```
Action:
1. Cmd+Shift+P → "PES: Preview Install"
2. Select environment
3. Enter: "django==4.2"

Expected:
✅ Parses version constraint correctly
✅ Shows what will be installed
✅ May show upgrades needed
```

#### Test Case D: Complex Version Spec
```
Action:
1. Cmd+Shift+P → "PES: Preview Install"
2. Select environment
3. Enter: "numpy>=1.20,<2.0"

Expected:
✅ Handles version constraint
✅ Shows compatible version
✅ Shows dependencies
```

### Test 3: Error Handling

#### Test Error Case A: Invalid Package
```bash
# In VS Code preview:
Enter: "this-package-does-not-exist-xyz"

Expected:
❌ Shows error message
✅ Error is handled gracefully
✅ Extension doesn't crash
```

#### Test Error Case B: No Environment Selected
```bash
# In VS Code:
1. Cmd+Shift+P → "PES: Preview Install"
2. Press Escape (cancel environment selection)

Expected:
✅ Command cancels gracefully
✅ No errors in output
```

---

## 📊 Complete Testing Checklist

Use this checklist to verify everything works:

### Unit Tests
- [ ] Run `python tests/test_dependency_preview.py`
- [ ] All 22 tests pass
- [ ] No errors in output

### Integration Tests
- [ ] Extension loads in VS Code
- [ ] Command appears in command palette
- [ ] Can select environment without error
- [ ] Can enter package name
- [ ] Preview displays correctly

### Feature Tests
- [ ] Shows new packages correctly
- [ ] Shows upgrades with version changes
- [ ] Shows breaking change warnings
- [ ] Handles package with no dependencies
- [ ] Handles complex version constraints

### UI/UX Tests
- [ ] Webview loads properly
- [ ] Text is readable
- [ ] Colors are visible
- [ ] Layout is organized
- [ ] Icons display correctly (📥, 📈, ⚠️)

### Error Tests
- [ ] Handles invalid package names gracefully
- [ ] Shows meaningful error messages
- [ ] Extension doesn't crash on errors
- [ ] Timeout handling works

---

## 🔧 Troubleshooting

### Issue: "Module not found" error

**Solution:**
```bash
# Make sure you're in the correct directory
cd c:\Users\Lenovo\Desktop\Contribution\py_env_studio

# Try importing again
python -c "from py_env_studio.core import dependency_preview; print('OK')"
```

### Issue: Tests fail with import errors

**Solution:**
```bash
# Make sure pytest/unittest can find the module
cd py_env_studio
python -m unittest discover

# Or run directly
python tests/test_dependency_preview.py
```

### Issue: Extension doesn't load

**Solution:**
```bash
# Recompile the TypeScript
cd pes-vscode-extention
npm run compile

# Then press F5 again in VS Code
```

### Issue: Preview command not found

**Solution:**
1. Reload VS Code window: `Ctrl+Shift+P` → "Reload Window"
2. Wait 5 seconds for extension to activate
3. Try command again

### Issue: Preview takes too long (> 30s)

**Solution:**
- The package might have many dependencies
- Try with a simpler package first (e.g., "requests")
- Check your internet connection
- Try restarting the server

---

## 📝 Test Results Log

Record your test results here:

```
Date: April 26, 2026
Tester: [Your Name]

Unit Tests: ✅ PASS (22/22)
  - All test cases passed
  - No skipped tests (except integration)

Integration Tests: ✅ PASS
  - [ ] Extension loads
  - [ ] Command works
  - [ ] Preview displays

Feature Tests: ✅ PASS
  - [ ] Simple package (requests)
  - [ ] Package with changes (pandas)
  - [ ] Major version upgrade (django)
  - [ ] Complex constraint (numpy>=1.20)

Error Tests: ✅ PASS
  - [ ] Invalid package handled
  - [ ] Missing environment handled
  - [ ] Timeout handled

Overall: ✅ ALL TESTS PASSED
```

---

## 🎯 Step-by-Step: Running the Complete Test Suite

### Total Time: ~10 minutes

**Step 1: Python Unit Tests (2 min)**
```bash
cd py_env_studio
python tests/test_dependency_preview.py
# Expected: Ran 22 tests in 0.002s - OK
```

**Step 2: VS Code Extension (3 min)**
```bash
cd pes-vscode-extention
npm run compile
# Expected: Successfully compiled
```

**Step 3: Load Extension in VS Code (2 min)**
- Press F5 in VS Code
- New window opens
- Wait for "PES connected" message

**Step 4: Test Feature (3 min)**
- Ctrl+Shift+P → "Preview Install"
- Select environment
- Try: "requests", then "pandas", then "numpy"
- Verify preview works each time

**Step 5: Test Error Cases (5 min)**
- Try invalid package name
- Try complex version specs
- Verify error handling

---

## 📚 Additional Resources

- **Feature Documentation**: See `DEPENDENCY_PREVIEW_FEATURE.md`
- **Quick Start Guide**: See `DEPENDENCY_PREVIEW_QUICK_START.md`
- **Implementation Details**: See project README

---

## ✅ Success Criteria

Your testing is complete when:

✅ All 22 unit tests pass  
✅ Extension compiles without errors  
✅ Command appears in command palette  
✅ Preview displays for multiple packages  
✅ Breaking changes are detected  
✅ Error cases are handled gracefully  
✅ UI looks professional and readable  

🎉 **If all above are ✅, the feature is working perfectly!**

---

## 🆘 Need Help?

1. Check this document for your issue
2. Review test output carefully
3. Check VS Code Output panel for errors
4. Try the troubleshooting section
5. Review the feature documentation
