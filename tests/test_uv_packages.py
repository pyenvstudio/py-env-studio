#!/usr/bin/env python
"""Test uv package operations."""

from py_env_studio.core.uv_tools import list_packages_uv, _get_venv_dir_from_python_path
from py_env_studio.core.env_manager import get_env_python, search_envs

# Find uv environment
envs = search_envs('')
print("Looking for uv-created environments...")

uv_envs = []
for env in envs:
    from py_env_studio.core.env_manager import get_env_data
    data = get_env_data(env)
    if data.get('package_manager') == 'uv':
        uv_envs.append(env)
        print(f"  Found: {env}")

if uv_envs:
    env_name = uv_envs[0]
    print(f"\nTesting package listing for: {env_name}")
    
    # Get python path
    python_path = get_env_python(env_name)
    print(f"Python path: {python_path}")
    
    # Convert to venv dir
    venv_dir = _get_venv_dir_from_python_path(python_path)
    print(f"Venv dir: {venv_dir}")
    
    # List packages
    print("\nListing packages...")
    packages = list_packages_uv(python_path)
    print(f"Found {len(packages)} packages:")
    for pkg in packages[:5]:
        print(f"  - {pkg['name']} {pkg['version']}")
    
    if len(packages) > 5:
        print(f"  ... and {len(packages) - 5} more")
else:
    print("No uv environments found. Create one first!")
    print("\nExisting environments:")
    for env in envs[:5]:
        from py_env_studio.core.env_manager import get_env_data
        data = get_env_data(env)
        mgr = data.get('package_manager', 'pip')
        print(f"  - {env} ({mgr})")
