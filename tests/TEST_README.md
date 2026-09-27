# Py Env Studio - Test Suite Documentation

> **Audit status (2026-09-20):** this document describes the *intended* suite and overstates the current automated
> coverage (see `TEST_AUDIT_REPORT.md`, finding F-12). Measured baseline on revision `8d11de4`:
> **80 pytest-collected tests → 2 failed, 77 passed, 1 skipped (23.09 s)**.
> Read the two audit documents below before relying on anything in this file.

## Related audit documents

| Document | Purpose |
|---|---|
| [`TEST_CASES.md`](TEST_CASES.md) | 339-case test catalog for every documented feature, with ID, steps, expected result, priority, type and current coverage status (COVERED / PARTIAL / MANUAL / RED / GAP), plus the fixture/mocking strategy needed to implement the gaps. |
| [`TEST_AUDIT_REPORT.md`](TEST_AUDIT_REPORT.md) | Audit report: baseline execution evidence, automated test inventory, per-area coverage matrix, 14 findings (F-01…F-14) with file/line evidence and recommendations, and a prioritized remediation backlog. No fixes were applied. |

## Overview

The test suite for Py Env Studio is a comprehensive collection of tests that verify all features and functionality of the application. It covers:

- ✅ Environment Management
- ✅ Package Management (pip & uv)
- ✅ Vulnerability Scanning
- ✅ Configuration Management
- ✅ Database Operations
- ✅ Plugin System
- ✅ Auto-Resolution
- ✅ Integration Features
- ✅ PyTonic Learning System
- ✅ Setup State & Runtime

## Test Files

### Existing Tests

1. **test_plugin_events.py** - Plugin event system tests
2. **test_plugin_import.py** - Plugin import and loading tests
3. **test_plugin_load.py** - Plugin discovery and loading tests
4. **test_uv_packages.py** - UV package manager functionality tests

### New Tests

1. **test_all_features.py** - Comprehensive feature test suite
   - 12 test categories covering all major features
   - 50+ individual test cases
   - Detailed error reporting
   - Color-coded output

2. **run_all_tests.py** - Test suite runner
   - Executes all test files
   - Aggregates results
   - Generates summary report

## Running Tests

### Run All Tests at Once

```bash
cd py_env_studio
python tests/run_all_tests.py
```

### Run Specific Test Suite

```bash
# Comprehensive feature tests
python tests/test_all_features.py

# Plugin tests
python tests/test_plugin_import.py
python tests/test_plugin_load.py
python tests/test_plugin_events.py

# UV package manager tests
python tests/test_uv_packages.py
```

### Run with pytest (Optional)

```bash
# Install pytest if not already installed
pip install pytest pytest-cov

# Run all tests with coverage
pytest tests/ -v --cov=py_env_studio

# Run specific test
pytest tests/test_all_features.py -v
```

## Test Coverage

### 1. Environment Management Tests
- List available Python versions
- Search existing environments
- Get environment data
- Validate environment integrity

### 2. Package Management Tests
- List installed packages
- Check for outdated packages
- Parse package information correctly
- Handle JSON format consistency

### 3. UV Package Manager Tests
- List packages with UV
- Check outdated packages with UV
- Verify UV command execution
- Handle UV-specific output format

### 4. Vulnerability Scanning Tests
- Initialize vulnerability database
- Load security matrix
- Scan for known vulnerabilities
- Generate vulnerability reports

### 5. Configuration Management Tests
- Load application configuration
- Get configuration values
- Set configuration values
- Handle configuration file operations

### 6. Database Operations Tests
- Initialize database
- Get database connection
- Retrieve all environments
- Verify data persistence

### 7. Plugin System Tests
- Initialize PluginManager
- Load plugins from disk
- Get loaded plugins list
- Retrieve available hooks
- Verify plugin metadata

### 8. Auto-Resolution Tests
- Initialize AutoResolver
- Detect resolution errors
- Test fallback mechanisms
- Verify resolution strategies

### 9. Integration Features Tests
- Get available tools (IDE, terminal, etc.)
- Add new tools
- Launch integrated environments
- Handle tool configuration

### 10. PyTonic Learning System Tests
- Get available topics
- Retrieve learning modes
- Generate random challenges
- Load user profiles
- Track learning progress

### 11. Setup State Tests
- Get setup state
- Check first-run status
- Verify initialization state

### 12. Runtime Operations Tests
- Get runtime configuration
- Verify runtime environment
- Check runtime dependencies

## Test Output

### Success Output
```
✓ List available Python versions
✓ Search environments (found 5 envs)
✓ List packages in 'myenv' (found 42 packages)
✓ Check outdated packages (found 3 outdated)
✓ Initialize PluginManager
✓ Load plugins from disk
✓ Get loaded plugins (found 1 plugins)
```

### Skip Output
```
⊘ UV package manager tests: No UV environments found
⊘ Get random challenge: No challenges available
```

### Failure Output
```
✗ Get configuration value: [error message]
✗ Load PyTonic user profile: [error message]
```

## Test Summary Report

After running the complete test suite, you'll see:

```
============================================================
Test Summary
============================================================
Passed: 42
Failed: 2
Skipped: 8
Total: 52

Failed Tests:
  - Get configuration value: [error details]
  - Load PyTonic user profile: [error details]
```

## Understanding Test Results

| Status | Symbol | Meaning |
|--------|--------|---------|
| ✓ PASS | ✓ | Test passed successfully |
| ✗ FAIL | ✗ | Test failed with error |
| ⊘ SKIP | ⊘ | Test skipped (not applicable) |

### Passing Tests
All green checkmarks indicate the feature is working correctly. These are required for the application to function properly.

### Failing Tests
Red X marks indicate a problem that needs to be addressed. Check the error message for details on what went wrong.

### Skipped Tests
Yellow signs indicate tests that were skipped, usually because:
- Required components aren't installed (e.g., UV)
- Required environment setup (e.g., specific Python version)
- Optional features not configured

## Common Issues & Troubleshooting

### Issue: "No environments available"
**Solution:** Create a test environment first:
```bash
python -m py_env_studio
# Create a new environment in the GUI
```

### Issue: "UV tools import failed"
**Solution:** Install UV if you want to test UV features:
```bash
pip install uv
```

### Issue: "PluginManager initialization failed"
**Solution:** Ensure plugins directory exists and is writable:
```bash
mkdir -p ~/.py_env_studio/plugins
chmod 755 ~/.py_env_studio/plugins
```

### Issue: "Test timeout"
**Solution:** Some tests may take longer on slower machines. You can increase the timeout in `run_all_tests.py` by modifying the `timeout` parameter.

## Adding New Tests

To add new test cases:

1. **Create new test method in `test_all_features.py`**:
```python
def test_new_feature():
    """Test description."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}[N] New Feature Tests{Colors.RESET}")
    
    try:
        # Your test code here
        results.add_pass("Test case name")
    except Exception as e:
        results.add_fail("Test case name", str(e))
```

2. **Call the test method in `main()`**:
```python
def main():
    # ... existing code ...
    test_new_feature()  # Add this line
    # ... summary code ...
```

3. **Run the test suite to verify**:
```bash
python tests/test_all_features.py
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Test Suite
  run: python tests/run_all_tests.py
```

## Performance Notes

- Complete test suite runs in **30-60 seconds** (varies by machine)
- Each test category completes in **5-10 seconds**
- Parallel execution not recommended (shared state)

## Logging

Test logs are printed to the console with timestamps. For detailed logging during test execution:

```bash
# Enable debug logging
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('tests/test_all_features.py').read())
"
```

## Support

For issues with tests:
1. Check the error message output
2. Verify environment setup (see troubleshooting section)
3. Review application logs in `~/.py_env_studio/logs/`
4. Open an issue on GitHub with test output
