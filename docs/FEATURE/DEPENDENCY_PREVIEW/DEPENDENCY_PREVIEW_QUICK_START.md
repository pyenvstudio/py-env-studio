# Quick Start: Dependency Impact Preview

## Installation

The feature is built into the PES VS Code Extension. No additional installation needed.

## Basic Usage

### Step 1: Open Command Palette
Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)

### Step 2: Search for Preview Command
Type: `PES: Preview Install`

### Step 3: Select Your Environment
Choose the Python environment where you want to install the package.

Examples:
- `my-project` 
- `data-science`
- `default`

### Step 4: Enter Package Specification
Type the package you want to install:

- Simple: `requests`
- With version: `django==4.2`
- With constraint: `numpy>=1.20,<2.0`
- Complex: `opencv-python[headless]>=4.8`

### Step 5: Review the Preview
The preview shows you:

1. **Summary at the top**:
   ```
   + 12  New packages
   ↑ 3   Upgrades
   - 0   Removals
   ```

2. **New packages** that will be installed
3. **Package upgrades** with old → new version
4. **Breaking changes** warnings with severity

### Step 6: Proceed or Cancel
- If satisfied: Install normally with `pip install <package>`
- If concerned: Cancel and adjust your version constraints

## Real-World Examples

### Example 1: Installing Data Science Stack

**You type:** `pandas`

**Preview shows:**
```
+ 12 New packages
  📥 numpy         1.26.4
  📥 scipy         1.11.0
  📥 pytz          2023.3
  ... (9 more)

↑ 3 Upgrades
  📈 setuptools    65.5.0 → 69.0.0
  📈 pip           24.0 → 24.1

⚠️ Breaking Changes (1)
  ⚠️ numpy: May break deprecated numpy.dtype constructors
     Severity: high
```

**Action:** Review numpy warning, consider if your code uses deprecated APIs

---

### Example 2: Major Version Upgrade

**You type:** `django==5.0`  
(currently have django 4.2)

**Preview shows:**
```
+ 0 New packages

↑ 1 Upgrade
  📈 django  4.2.8 → 5.0.0

⚠️ Breaking Changes (1)
  ⚠️ django: ORM query API changes between major versions
     Severity: high
```

**Action:** Read django 5.0 migration guide before upgrading

---

### Example 3: Security Update

**You type:** `requests>=2.32`  
(currently have 2.28)

**Preview shows:**
```
+ 0 New packages

↑ 1 Upgrade
  📈 requests  2.28.0 → 2.32.1

✅ No breaking changes
```

**Action:** Safe to install

---

### Example 4: Installing with Dependencies

**You type:** `scikit-learn`

**Preview shows:**
```
+ 8 New packages
  📥 scikit-learn   1.3.2
  📥 joblib        1.3.2
  📥 threadpoolctl 3.2.0
  📥 threadpoolctl 3.2.0
  ... (4 more)

↑ 2 Upgrades
  📈 numpy        1.24.0 → 1.26.4
  📈 scipy        1.10.0 → 1.11.0

⚠️ Breaking Changes (1)
  ⚠️ numpy: May break deprecated numpy.dtype constructors
     Severity: high
```

**Action:** Review if your code uses numpy deprecated APIs

## Tips & Tricks

### 💡 Check Before Installing Popular Packages
Always preview major packages like:
- `pandas` - Large dependency tree
- `django` - Can have breaking changes
- `tensorflow` - Heavy dependencies
- `pytorch` - Multiple options (cpu/gpu)

### 💡 Use Version Constraints
Instead of just `pandas`, be specific:
- `pandas>=1.5,<2.0` - More predictable
- `django>=4.2,<5.0` - Avoid major versions
- `numpy==1.26.4` - Exact version lock

### 💡 Review Breaking Changes
Even if there are breaking changes, you can still install. Just review:
1. The reason
2. The severity (high/medium/low)
3. Whether your code uses affected features

### 💡 Check Multiple Packages
Want to compare installations?
1. Preview package A
2. Note the changes
3. Preview package B
4. Compare before installing

## Understanding the Output

### Summary Badges

| Badge | Meaning |
|-------|---------|
| `+ 5` | 5 new packages will be installed |
| `↑ 2` | 2 currently installed packages will be upgraded |
| `- 1` | 1 package may be removed |

### Package Items

**New Package:**
```
📥 numpy
   Version: v1.26.4
```

**Upgrade:**
```
📈 pandas
   2.0.0 → 2.1.0
```

**Removal:**
```
📤 deprecated-lib
   Version: v1.0.0
```

### Breaking Changes

**High Severity** (Red) - Critical, may break your code:
```
⚠️ numpy: May break deprecated numpy.dtype constructors
   Severity: high
```

**Medium Severity** (Orange) - May affect some code:
```
⚠️ pandas: Index behavior changed
   Severity: medium
```

**Low Severity** (Yellow) - Unlikely to affect code:
```
⚠️ requests: Minor API changes
   Severity: low
```

## Common Questions

### Q: What if preview takes too long?
**A:** Some packages have many dependencies. Wait up to 30 seconds. If it times out, try a simpler package first to test.

### Q: Can I install a specific version?
**A:** Yes! Use `package==1.2.3` for exact version or `package>=1.2` for minimum version.

### Q: What if I see conflicts?
**A:** The preview will show conflicting requirements. You may need to:
1. Install an older version of the package
2. Uninstall conflicting packages first
3. Use a different package manager (uv)

### Q: Are breaking changes guaranteed to break my code?
**A:** No! They're potential issues. Review your code to see if you use the affected features. Many projects handle breaking changes gracefully.

### Q: Can I preview without installing?
**A:** Yes! The preview doesn't install anything. You review it first, then decide to install manually or cancel.

### Q: Does preview work offline?
**A:** Mostly yes, but fetching detailed package metadata requires PyPI access. Local metadata works from your environment's installed packages.

## Troubleshooting

### Preview says "Package not found"
- Check spelling of package name
- Verify it exists on PyPI (https://pypi.org/)
- Try updating pip: `pip install --upgrade pip`

### Preview takes forever (> 2 minutes)
- This might indicate a large dependency tree
- Try canceling and installing a different package
- Check your internet connection
- Try adjusting the timeout in settings

### Preview shows no changes
- The package may have no dependencies
- Or all dependencies are already installed
- This is fine! It's safe to install

### "Server not responding" error
- The gRPC server might not have started
- Reload VS Code window: `Ctrl+R`
- Check the Output panel for errors
- Restart VS Code completely

## Next Steps

- 📖 Read full documentation: `docs/DEPENDENCY_PREVIEW_FEATURE.md`
- 🔧 See technical details: `docs/DEPENDENCY_IMPACT_PREVIEW_IMPLEMENTATION.md`
- 🧪 Run tests: `python tests/test_dependency_preview.py`
- 💬 Report issues on GitHub

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open Command Palette | `Ctrl+Shift+P` |
| Search "Preview Install" | (in command palette) |

## Need Help?

1. Check this guide
2. Read the full documentation
3. Look at test cases for usage examples
4. Check VS Code output panel for errors
5. Open an issue on GitHub

---

**Happy dependency previewing! 🚀**
