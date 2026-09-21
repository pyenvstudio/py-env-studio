"""Package tools (thin adapters over package_manager)."""

from __future__ import annotations

from ..context import resolve_environment
from ..errors import McpError
from ..schemas.responses import failure, success


def list_packages(arguments):
    # type: (dict) -> dict
    arguments = arguments or {}
    environment_id = arguments.get("environment_id")
    if not environment_id:
        return failure("INVALID_INPUT", "environment_id is required.")
    try:
        info = resolve_environment(environment_id)
    except McpError as exc:
        return failure(exc.code, exc.message, exc.details)
    try:
        from py_env_studio.core import package_manager

        raw = package_manager.list_packages(info["environment_id"])
    except Exception as exc:
        return failure(
            "SERVICE_UNAVAILABLE",
            "Could not list packages for '{}': {}".format(environment_id, exc),
            {"environment_id": environment_id},
        )
    items = [{"name": name, "version": version} for name, version in (raw or [])]
    try:
        manager = package_manager.get_env_package_manager(info["environment_id"])
    except Exception:
        manager = info.get("package_manager")
    return success(
        {
            "environment": info["environment_id"],
            "package_manager": manager,
            "packages": items,
            "count": len(items),
        },
        cached=False,
    )
