"""Environment tools (thin adapters over env_manager)."""

from __future__ import annotations

from ..context import resolve_environment
from ..errors import McpError
from ..schemas.responses import failure, success


def list_environments(arguments):
    # type: (dict) -> dict
    from py_env_studio.core import env_manager

    try:
        names = env_manager.list_envs()
    except Exception as exc:
        return failure("SERVICE_UNAVAILABLE", "Could not list environments: {}".format(exc))
    items = []
    for name in names:
        info = env_manager.get_environment_info(name)
        if info is None:
            continue
        items.append(
            {
                "environment_id": info["environment_id"],
                "name": info["name"],
                "path": info["path"],
                "python_version": info.get("python_version"),
                "python_executable": info.get("python_executable"),
                "package_manager": info.get("package_manager"),
                "status": info.get("status"),
                "metadata": info.get("metadata") or {},
            }
        )
    return success({"environments": items, "count": len(items)}, cached=True)


def get_environment(arguments):
    # type: (dict) -> dict
    arguments = arguments or {}
    environment_id = arguments.get("environment_id")
    if not environment_id:
        return failure("INVALID_INPUT", "environment_id is required.")
    try:
        info = resolve_environment(environment_id)
    except McpError as exc:
        return failure(exc.code, exc.message, exc.details)
    return success({"environment": info}, cached=True)


def get_environment_status(arguments):
    # type: (dict) -> dict
    import os

    arguments = arguments or {}
    environment_id = arguments.get("environment_id")
    if not environment_id:
        return failure("INVALID_INPUT", "environment_id is required.")
    try:
        info = resolve_environment(environment_id)
    except McpError as exc:
        return failure(exc.code, exc.message, exc.details)
    env_path = info.get("path")
    exists = bool(env_path) and os.path.isdir(env_path)
    python_exe = info.get("python_executable")
    python_available = bool(python_exe) and os.path.exists(python_exe)
    package_count = None
    try:
        from py_env_studio.core import package_manager

        package_count = len(list(package_manager.list_packages(info["environment_id"])))
    except Exception:
        package_count = None
    runtime_status = None
    try:
        from py_env_studio.core import runtime_toggle

        registry = runtime_toggle.load_registry()
        for _name, entry in registry.items():
            if entry.get("environment_id") == info["environment_id"] or entry.get(
                "environment_path"
            ) == env_path:
                runtime_status = "on" if entry.get("runtime_enabled") else "off"
                break
    except Exception:
        runtime_status = None
    return success(
        {
            "environment": info["environment_id"],
            "exists": exists,
            "python_available": python_available,
            "runtime_status": runtime_status,
            "package_manager": info.get("package_manager"),
            "package_count": package_count,
        },
        cached=True,
    )
