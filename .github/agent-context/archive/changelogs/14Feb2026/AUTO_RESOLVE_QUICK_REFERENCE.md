# Auto-Resolve Feature - Quick Reference

## What It Does

Automatically resolves dependency conflicts when installing packages by:
1. Detecting `ResolutionImpossible` errors
2. Removing version constraints (e.g., `django==4.2` → `django`)
3. Retrying the installation (up to 3 attempts)
4. Allowing the package manager to find a compatible version

## When It Activates

Auto-resolve triggers when:
- A package has strict version requirements
- Those requirements conflict with already-installed packages
- The package manager cannot find a compatible version set

## Supported Managers

- **pip** ✓ Full support
- **uv** ✓ Full support

## Example Scenarios

### Scenario 1: Django Version Conflict
```
User tries: pip install django==4.2
Error: ResolutionImpossible - conflict with dependency X

Auto-resolve strips version:
Retries: pip install django
Result: Installs django 3.2.x (latest compatible)
```

### Scenario 2: UV with Strict Requirements
```
User tries: uv pip install package==1.0.0
Error: Dependency conflict detected

Auto-resolve retries: uv pip install package
Result: Installs compatible version
```

## Console Messages

Look for these in the PyEnvStudio console:

| Message | Meaning |
|---------|---------|
| `[Auto-Resolve] Detected dependency conflict...` | Conflict found, attempting resolution |
| `[Auto-Resolve] Attempt N: Installing...` | Retry N in progress |
| `[Auto-Resolve] ✓ Successfully installed...` | Resolution successful |
| `[Auto-Resolve] Max retry attempts (3) reached` | Failed after all retries |

## Configuration

### Enable (Default)
```ini
[settings]
auto_resolve_dependencies = true
```

### Disable
```ini
[settings]
auto_resolve_dependencies = false
```

## How It Differs From Manual Solutions

### Manual Approach (Old Way)
```
1. Try: pip install django==4.2
2. Get error
3. Read error message
4. Manually try: pip install django
5. Installs different version
```

### Auto-Resolve (New Way)
```
1. Try: pip install django==4.2
2. Get error
3. Automatically retries: pip install django
4. Installs compatible version
5. All transparent to user
```

## Error Patterns Detected

Auto-resolve recognizes:
- `ResolutionImpossible`
- `dependency-resolution` errors
- `dependency conflict` messages
- `conflicting dependencies`
- `No matching distribution`
- Version mismatch errors (`has requirement` vs `but you have`)

## Limitations

- ❌ Cannot create compatible version if none exists
- ❌ Doesn't force install incompatible versions
- ❌ Limited to 3 retry attempts
- ❌ Doesn't help with network errors
- ❌ Cannot install non-existent packages

## When Auto-Resolve Helps

✓ Strict version pins with new compatible releases  
✓ Environmental dependency differences  
✓ Dependency resolver bugs/timeouts  
✓ Legacy package compatibility  

## When It Won't Help

✗ Fundamentally incompatible versions  
✗ Non-existent packages  
✗ Network issues  
✗ Corrupted installations  
✗ Python version incompatibilities  

## Implementation Details

- **Module**: `py_env_studio/core/auto_resolve.py`
- **Classes**: `AutoResolver`
- **Functions**: 
  - `is_resolution_error()`
  - `strip_version_constraints()`
  - `parse_conflicting_packages()`
  - `auto_resolve_install()`

## For Developers

### Using Auto-Resolve in Code

```python
from py_env_studio.core.auto_resolve import AutoResolver

resolver = AutoResolver(log_callback=my_logger)
success, message = resolver.resolve(
    package_spec='django==4.2',
    install_func=my_install_function,
    env_name='my_env'
)
```

### Adding Support to New Functions

```python
from py_env_studio.core import auto_resolve

def custom_install(env, package, log_callback=None):
    # Your installation logic here
    pass

# Use auto-resolve wrapper
success, msg = auto_resolve.auto_resolve_install(
    package,
    custom_install,
    log_callback=log_callback,
    env=env
)
```

## Debugging

Enable logging to see auto-resolve in action:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from py_env_studio.core.package_manager import install_package
install_package('env', 'package==1.0.0', log_callback=print)
```

Look for `[Auto-Resolve]` prefixed messages in the output.

## Related Documentation

- See `AUTO_RESOLVE_GUIDE.md` for detailed user guide
- See `AUTO_RESOLVE_IMPLEMENTATION.md` for technical details
- See config.ini for configuration options
