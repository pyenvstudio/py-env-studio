"""Project-intelligence tool (thin adapter over ProjectIntelligenceService)."""

from __future__ import annotations

from ..errors import McpError
from ..schemas.responses import failure, success


def analyze_project(arguments):
    # type: (dict) -> dict
    from py_env_studio.core.project_intelligence import ProjectIntelligenceService

    arguments = arguments or {}
    try:
        analysis = ProjectIntelligenceService().analyze(arguments.get("project_path"))
    except McpError as exc:
        return failure(exc.code, exc.message, exc.details)
    except Exception as exc:
        return failure("SERVICE_UNAVAILABLE", "Project analysis failed: {}".format(exc))
    return success(analysis.to_dict(), cached=True)
