"""Project/environment resolution for MCP tools.

Reuses the existing PES project registry and runtime mechanisms instead of
creating a second registry. Returns structured ambiguity errors instead of
guessing when detection is ambiguous.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .errors import (
    AMBIGUOUS_PROJECT,
    ENVIRONMENT_NOT_FOUND,
    PROJECT_NOT_FOUND,
    McpError,
)


def resolve_environment(environment_id):
    """Resolve an environment id to its public info dict via env_manager."""
    from py_env_studio.core import env_manager

    if not environment_id or not str(environment_id).strip():
        raise McpError("INVALID_INPUT", "environment_id is required.")
    info = env_manager.get_environment_info(str(environment_id).strip())
    if info is None:
        raise McpError(
            ENVIRONMENT_NOT_FOUND,
            "Environment '{}' was not found.".format(environment_id),
            {"environment_id": environment_id},
        )
    return info


def resolve_project(project_path=None):
    """Resolve project metadata using the existing runtime_toggle registry.

    Args:
        project_path: optional directory to resolve from (defaults to cwd).
    """
    from py_env_studio.core import runtime_toggle

    start = Path(project_path).resolve() if project_path else Path.cwd()
    if project_path and not start.exists():
        raise McpError(
            PROJECT_NOT_FOUND,
            "Project path does not exist: {}".format(project_path),
            {"project_path": str(project_path)},
        )
    root = runtime_toggle.get_project_root(start)
    if root is None:
        # No pes.config/pyproject.toml found: treat the given/cwd dir as
        # unregistered rather than guessing.
        raise McpError(
            PROJECT_NOT_FOUND,
            "No PES project found at or above '{}'.".format(start),
            {"project_path": str(start)},
        )
    metadata = runtime_toggle.load_project_metadata(root)
    if not metadata:
        raise McpError(
            PROJECT_NOT_FOUND,
            "No PES project metadata at '{}'.".format(root),
            {"project_path": str(root)},
        )
    result = dict(metadata)
    result["project_root"] = str(root)
    return result


def detect_ambiguity(candidate_roots):
    """Helper: raise AMBIGUOUS_PROJECT when several roots match."""
    if len(candidate_roots) > 1:
        raise McpError(
            AMBIGUOUS_PROJECT,
            "Multiple projects match; specify project_path explicitly.",
            {"candidates": [str(p) for p in candidate_roots]},
        )


def get_project_status_envelope(project_path=None):
    # type: (...) -> Dict[str, Any]
    """Read-only project status via runtime_toggle.get_project_status."""
    from py_env_studio.core import runtime_toggle

    start = Path(project_path).resolve() if project_path else None
    if project_path and not start.exists():
        raise McpError(
            PROJECT_NOT_FOUND,
            "Project path does not exist: {}".format(project_path),
            {"project_path": str(project_path)},
        )
    if start is not None:
        root = runtime_toggle.get_project_root(start)
        status = runtime_toggle.get_project_status(root)
    else:
        status = runtime_toggle.get_project_status()
    return status


def count_installed_packages(environment_id):
    # type: (str) -> Optional[int]
    """Best-effort installed-package count via package_manager (local)."""
    try:
        from py_env_studio.core import package_manager

        packages = package_manager.list_packages(environment_id)
        return len(list(packages))
    except Exception:
        return None


def environment_exists_on_disk(path):
    # type: (str) -> bool
    return bool(path) and os.path.isdir(str(path))
