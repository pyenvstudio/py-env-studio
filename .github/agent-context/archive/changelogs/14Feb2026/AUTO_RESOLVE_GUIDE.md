# Auto-Resolve Dependency Conflicts

## Overview

The auto-resolve feature automatically handles dependency conflicts during package installation by intelligently retrying with relaxed version constraints. This feature works with both **pip** and **uv** package managers.

## Problem It Solves

When installing packages, you might encounter errors like:

```
ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts
```

This happens when:
- A package requires a specific version of a dependency
- An already-installed package requires a different version of the same dependency
- The package manager cannot find a compatible version set

## How It Works

### Strategy

1. **Initial Install**: Attempts to install the package with the exact version constraints specified
2. **Error Detection**: If a resolution error occurs, detects the dependency conflict
3. **Retry with Relaxed Constraints**: Strips version constraints and retries the installation
4. **Fallback**: Allows the package manager to find a compatible version set

### Examples

#### Example 1: Django with conflicting dependency
```
Initial attempt: django==4.2
Error: ResolutionImpossible - some dependency requires django<4.0

Auto-resolve retry: django (no version constraint)
Result: Installs django 3.2.x (latest compatible version)
```

#### Example 2: Package with specific version
```
Initial attempt: requests==2.28.0
Error: Some package requires requests>=3.0.0

Auto-resolve retry: requests
Result: Installs requests 3.1.0 (or other compatible version)
```

## Configuration

The auto-resolve feature is enabled by default. To disable it, edit `config.ini`:

```ini
[settings]
auto_resolve_dependencies = false
```

## Usage

### Via PyEnvStudio UI

When installing a package through the UI:
1. Enter the package name (with or without version constraints)
2. Click "Install Package"
3. If a dependency conflict occurs, auto-resolve automatically retries

The console will show messages like:
```
[Auto-Resolve] Detected dependency conflict, attempting auto-resolve...
[Auto-Resolve] Attempt 1: Installing 'package-name' without version constraints
[Auto-Resolve] ✓ Successfully installed 'package-name'
```

### Via Command Line (if available)

```python
from py_env_studio.core.package_manager import install_package

# This automatically uses auto-resolve
install_package('my_env', 'django==4.2', log_callback=print)
```

## Logging

Auto-resolve operations are logged with `[Auto-Resolve]` prefix for easy identification:

- `[Auto-Resolve] Detected dependency conflict...` - Conflict detected
- `[Auto-Resolve] Attempt N: Installing...` - Retry attempt
- `[Auto-Resolve] ✓ Successfully installed...` - Success after retry
- `[Auto-Resolve] Max retry attempts (3) reached` - Failed after all retries

## Supported Package Managers

- **pip**: Full support with ResolutionImpossible error handling
- **uv**: Full support with dependency resolution errors

## Limitations

- **Maximum Retries**: Limited to 3 retry attempts to avoid infinite loops
- **Version Constraints**: Only removes version constraints as a fallback; doesn't force incompatible versions
- **Network Errors**: Doesn't retry on network-related errors
- **Invalid Packages**: Doesn't retry for packages that don't exist in PyPI

## How to Handle Common Scenarios

### When Auto-Resolve Can Help

✓ Version conflict between dependencies  
✓ Strict version requirements that have newer compatible versions  
✓ Environmental differences affecting dependency resolution  

### When Auto-Resolve Cannot Help

✗ Package doesn't exist in the repository  
✗ Fundamental incompatibility (no compatible version exists)  
✗ Network connectivity issues  
✗ Corrupted package files  

## Future Enhancements

- Configurable retry attempts
- Pre-resolution compatibility checking
- Detailed dependency graph visualization
- Interactive conflict resolution dialog
- Automatic downgrade suggestions

## See Also

- [Pip Dependency Resolution](https://pip.pypa.io/en/latest/topics/dependency-resolution/)
- [UV Documentation](https://docs.astral.sh/uv/)
