# Getting Started: Dependency Impact Preview

## 🎯 5-Minute Setup

### What You'll Do
1. Verify Python module works
2. Run unit tests
3. Test in VS Code
4. Celebrate! 🎉

### What You Need
- Python 3.8+ installed
- VS Code with PES extension
- 5 minutes of time

---

## Step 1️⃣: Verify Python Module (1 min)

### Option A: Windows PowerShell
```powershell
cd "C:\Users\Lenovo\Desktop\Contribution\py_env_studio"
python -c "from py_env_studio.core import dependency_preview; print('✅ SUCCESS: Module working!')"
```

### Option B: Windows Command Prompt
```cmd
cd C:\Users\Lenovo\Desktop\Contribution\py_env_studio
python -c "from py_env_studio.core import dependency_preview; print('✅ SUCCESS: Module working!')"
```

### Option C: Git Bash / WSL
```bash
cd /c/Users/Lenovo/Desktop/Contribution/py_env_studio
python -c "from py_env_studio.core import dependency_preview; print('✅ SUCCESS: Module working!')"
```

**Expected Output:**
```
✅ SUCCESS: Module working!
```

---

## Step 2️⃣: Run Unit Tests (1 min)

### In your terminal (same directory):

```bash
python tests/test_dependency_preview.py
```

### What You'll See
```
..................s.
Ran 22 tests in 0.002s

OK (skipped=1)
```

**What this means:**
- `.` = Test passed
- `s` = Test skipped (integration test, requires environment)
- `OK` = All tests passed! ✅

---

## Step 3️⃣: Open VS Code with Extension (1 min)

### Start the Extension Debugger

**In VS Code:**
1. Open the project root folder: `c:\Users\Lenovo\Desktop\Contribution\py_env_studio`
2. Navigate to `pes-vscode-extention` folder
3. Press **`F5`** (or Debug → Start Debugging)

**A NEW VS CODE WINDOW opens** with the extension loaded!

### Wait for Connection Message

In the new VS Code window, check the **Output** panel:
- Look for: `✅ PES Studio: Connected to Python server`
- If you see this → Everything is ready! ✅

---

## Step 4️⃣: Test the Feature (2 min)

### In the NEW VS Code window:

**Keyboard Shortcut:**
```
Ctrl + Shift + P
```

**Or use the menu:**
- Click `View` → `Command Palette`

**Search for:**
```
Preview Install
```

You should see: **`PES: Preview Package Install`**

### Select It

Click on `PES: Preview Package Install`

---

## Step 5️⃣: Try Your First Preview

### Environment Selection
1. You'll see a dropdown of Python environments
2. Select one (or create one if needed)
3. Examples: `default`, `test-env`, `my-project`

### Package Name
Enter a simple package to test:

**For First Test (Recommended):**
```
requests
```

**Click Enter** or press **`Enter` key**

---

## 🎯 What You Should See

A beautiful preview panel appears showing:

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
  └─ urllib3

✅ Ready to Install
Review the dependency changes above.
If everything looks good, you can 
proceed with installation.
```

### If You See This → Feature Works! ✅

---

## 🧪 Run a Few More Tests

### Test 1: Package with Dependencies
```
requests
```
Should show several new packages

### Test 2: Package with Upgrades
```
numpy
```
Should show breaking changes warning

### Test 3: Specific Version
```
django==4.2
```
Should show exact version constraint

### Test 4: Version Range
```
pandas>=1.5,<2.0
```
Should parse complex constraint

---

## ✅ Success Checklist

Mark these off as you go:

- [ ] ✅ Python module imports successfully
- [ ] ✅ All 22 tests pass
- [ ] ✅ VS Code extension loads (press F5)
- [ ] ✅ See "Connected to Python server" message
- [ ] ✅ Command appears in command palette
- [ ] ✅ Preview displays for "requests"
- [ ] ✅ Preview displays for "numpy"
- [ ] ✅ Preview displays for "django==4.2"

**All checked?** 🎉 **Your feature is working perfectly!**

---

## 🎨 Preview Panel Explained

The preview shows you everything that will change:

### 📥 New Packages
- Packages that WILL be installed
- Because they're dependencies of what you chose
- Example: `numpy` for `scipy`

### 📈 Upgrades  
- Packages that are ALREADY installed
- But will be updated to newer versions
- Shows: `old-version → new-version`

### 📤 Removals (if any)
- Packages that will be UNINSTALLED
- Because they're no longer needed
- Usually empty for most installs

### ⚠️ Potential Breaking Changes
- Known issues in these packages
- Might affect your code
- Shows severity: HIGH, MEDIUM, LOW

---

## 🔴 If Something Goes Wrong

### Problem: "Module not found"
```
ModuleNotFoundError: No module named 'py_env_studio'
```

**Solution:** Make sure you're in the right directory
```bash
# Should be:
c:\Users\Lenovo\Desktop\Contribution\py_env_studio

# Check current directory:
pwd  (or cd on Windows)

# If wrong, navigate:
cd c:\Users\Lenovo\Desktop\Contribution\py_env_studio
```

### Problem: Tests fail
```
FAILED ... TestCase ...
```

**Solution:** Run tests from the project root:
```bash
# Must be in this directory:
c:\Users\Lenovo\Desktop\Contribution\py_env_studio

# Then run:
python tests/test_dependency_preview.py
```

### Problem: Extension doesn't load
```
Error: Extension activation failed
```

**Solution:** Recompile TypeScript
```bash
cd pes-vscode-extention
npm run compile
```

Then press F5 again.

### Problem: Preview command not found
```
No matching command 'pes.previewInstall'
```

**Solution:** Reload the VS Code window
- Press Ctrl+Shift+P
- Type: "Reload Window"
- Press Enter
- Wait 5 seconds
- Try again

### Problem: Preview takes forever
```
Analyzing dependencies...
(waiting for 2+ minutes)
```

**Solution:** Some packages have large dependency trees
- This is normal! Wait up to 30 seconds
- Try a simpler package first
- Check your internet connection

---

## 🚀 Next Steps

Once everything is working:

1. **Explore More Packages**
   - Try: `pandas`, `tensorflow`, `flask`, etc.
   - See how many dependencies they have
   - Compare different versions

2. **Review Breaking Changes**
   - Try packages like `numpy`, `django`
   - See the warning messages
   - Learn about version compatibility

3. **Test Complex Scenarios**
   - Try: `package>=1.0,<2.0`
   - Try: `package==specific-version`
   - See how it handles constraints

4. **Read the Documentation**
   - Check: `DEPENDENCY_PREVIEW_FEATURE.md` for full guide
   - Check: `HOW_TO_RUN.md` for detailed testing
   - Review implementation details

---

## 📞 Quick Reference

| Task | Command/Action |
|------|---|
| Test Python | `python tests/test_dependency_preview.py` |
| Load extension | Press `F5` in VS Code |
| Open command | `Ctrl+Shift+P` → "Preview Install" |
| Preview requests | Enter: `requests` |
| Preview numpy | Enter: `numpy` |
| Preview django | Enter: `django==4.2` |

---

## 🎓 Learning Path

**Beginner** (What you just did)
- ✅ Verified module works
- ✅ Ran tests
- ✅ Tested basic feature

**Intermediate** (What's next)
- [ ] Try different packages
- [ ] Review breaking changes
- [ ] Test error cases

**Advanced** (Deep dive)
- [ ] Read implementation code
- [ ] Understand data flow
- [ ] Modify for custom needs
- [ ] Contribute improvements

---

## 🎉 Congratulations!

You've successfully set up and tested the **Dependency Impact Preview** feature!

### What You Can Do Now:
✅ See what will change before installing packages  
✅ Identify potential breaking changes  
✅ Make informed decisions about dependencies  
✅ Avoid surprise issues after installation  

### Share the Joy:
- Tell teammates about this feature
- Use it for all Python package installs
- Help spot dependency issues early
- Improve project stability

---

## 📚 Where to Go From Here

- **Full Documentation**: `DEPENDENCY_PREVIEW_FEATURE.md`
- **Advanced Testing**: `HOW_TO_RUN.md`
- **Implementation Details**: See project root files
- **Report Issues**: Open a GitHub issue

---

**Enjoy the safer, smarter way to install Python packages!** 🚀
