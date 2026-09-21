"""Project + dependency tools (thin adapters over runtime_toggle/dependency_preview)."""

from __future__ import annotations

from ..context import (
    count_installed_packages,
    get_project_status_envelope,
    resolve_environment,
)
from ..errors import McpError
from ..schemas.responses import failure, success


def get_project_context(arguments):
    # type: (dict) -> dict
    from py_env_studio.core import runtime_toggle

    arguments = arguments or {}
    project_path = arguments.get("project_path")
    try:
        status = get_project_status_envelope(project_path)
    except McpError as exc:
        return failure(exc.code, exc.message, exc.details)
    except Exception as exc:
        return failure("SERVICE_UNAVAILABLE", "Could not load project status: {}".format(exc))
    if not status.get("initialized"):
        return success(
            {
                "project": {
                    "path": status.get("project_root"),
                    "name": None,
                    "initialized": False,
                },
                "environment": None,
                "runtime": {
                    "managed": False,
                    "status": "off",
                    "runtime_enabled": False,
                },
                "packages": {"installed_count": None},
            },
            cached=True,
        )
    root = status.get("project_root")
    metadata = {}
    try:
        from pathlib import Path

        metadata = runtime_toggle.load_project_metadata(Path(root))
    except Exception:
        metadata = {}
    env_info = None
    env_id = status.get("environment_id") or metadata.get("environment_id")
    if env_id:
        try:
            env_info = resolve_environment(env_id)
        except McpError:
            env_info = None
    environment = None
    if env_info is not None:
        environment = {
            "id": env_info["environment_id"],
            "name": env_info["name"],
            "path": env_info["path"],
            "python_version": env_info.get("python_version"),
            "python_executable": env_info.get("python_executable"),
            "package_manager": env_info.get("package_manager"),
            "exists": status.get("environment_exists"),
        }
    elif env_id:
        environment = {
            "id": env_id,
            "name": env_id,
            "path": status.get("environment_path") or metadata.get("environment_path"),
            "python_version": status.get("python_version") or metadata.get("python_version"),
            "python_executable": None,
            "package_manager": metadata.get("package_manager"),
            "exists": status.get("environment_exists", False),
        }
    runtime_enabled = bool(status.get("runtime_enabled"))
    installed_count = count_installed_packages(env_id) if env_id else None
    return success(
        {
            "project": {
                "path": root,
                "name": status.get("project_name") or metadata.get("project_name"),
                "initialized": True,
            },
            "environment": environment,
            "runtime": {
                "managed": True,
                "status": "on" if runtime_enabled else "off",
                "runtime_enabled": runtime_enabled,
            },
            "packages": {"installed_count": installed_count},
        },
        cached=True,
    )


def get_dependency_information(arguments):
    # type: (dict) -> dict
    arguments = arguments or {}
    environment_id = arguments.get("environment_id")
    package_filter = arguments.get("package")
    if not environment_id:
        return failure("INVALID_INPUT", "environment_id is required.")
    try:
        info = resolve_environment(environment_id)
    except McpError as exc:
        return failure(exc.code, exc.message, exc.details)
    try:
        from py_env_studio.core import dependency_preview
        from py_env_studio.core import env_manager
    except Exception as exc:
        return failure("SERVICE_UNAVAILABLE", "Dependency service unavailable: {}".format(exc))
    try:
        installed = dependency_preview.get_installed_packages(info["environment_id"])
    except Exception as exc:
        return failure(
            "SERVICE_UNAVAILABLE",
            "Could not read installed packages for '{}': {}".format(environment_id, exc),
            {"environment_id": environment_id},
        )
    python_path = env_manager.get_env_python(info["environment_id"])
    names = sorted(installed)
    if package_filter:
        wanted = str(package_filter).strip().lower()
        names = [n for n in names if n == wanted]
        if not names:
            return failure(
                "INVALID_INPUT",
                "Package '{}' is not installed in '{}'.".format(package_filter, environment_id),
                {"environment_id": environment_id, "package": package_filter},
            )
    dependencies = []
    for name in names:
        try:
            deps = dependency_preview.get_package_dependencies(python_path, name)
        except Exception:
            deps = {}
        dependencies.append(
            {
                "package": name,
                "version": installed.get(name),
                "requires": sorted(deps) if isinstance(deps, dict) else [],
            }
        )
    return success(
        {
            "environment": info["environment_id"],
            "packages": dependencies,
            "count": len(dependencies),
        },
        cached=False,
    )
