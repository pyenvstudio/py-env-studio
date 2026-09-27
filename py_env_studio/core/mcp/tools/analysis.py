"""Project-intelligence tools (thin adapters over ProjectIntelligenceService).

Both tools are strictly read-only and reuse the same service. The consistency
tool is a stub: it reports what the existing analysis already knows and never
computes a verdict.
"""

from __future__ import annotations

from ..errors import McpError
from ..schemas.responses import failure, success

# Probe stub: the tool does not read manifests or lockfiles yet, so these
# blocks are reported as unavailable instead of being guessed.
DECLARED_UNAVAILABLE_REASON = (
    "Declared dependency manifests are not read by this tool."
)
RESOLVED_UNAVAILABLE_REASON = (
    "Lockfile / resolved dependency state is not read by this tool."
)


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


def check_consistency(arguments):
    # type: (dict) -> dict
    """Report project/environment context for a Python project (stub).

    Same project-path semantics as :func:`analyze_project` (``path``, or the
    ``project_path`` spelling used by the other project tools; both optional).
    The response reuses the existing ``ProjectAnalysis`` payload and adds
    ``declared``/``resolved``/``installed`` blocks plus ``consistent``. The
    verdict is always ``"unknown"`` because this tool does not evaluate
    consistency (no manifest/lockfile reading, no new algorithms) — ``unknown``
    does not mean consistent.
    """
    arguments = arguments or {}
    path = arguments.get("path")
    if path is None:
        path = arguments.get("project_path")
    try:
        from py_env_studio.core.project_intelligence import ProjectIntelligenceService

        analysis = ProjectIntelligenceService().analyze(path)
    except McpError as exc:
        return failure(exc.code, exc.message, exc.details)
    except Exception as exc:
        return failure("SERVICE_UNAVAILABLE", "Project analysis failed: {}".format(exc))
    return success(_consistency_report(analysis.to_dict()), cached=True)


def _consistency_report(data):
    # type: (dict) -> dict
    """Map the existing analysis payload onto the consistency response shape.

    Nothing is recalculated: ``declared`` and ``resolved`` are unavailable
    (this tool reads neither), and ``installed`` re-exposes the
    installed-package fact the analysis already produced.
    """
    dependencies = data.get("dependencies") or {}
    environment = data.get("environment") or {}
    installed = {"available": False}
    if dependencies.get("analysis_available"):
        installed = {
            "available": True,
            "environment_id": environment.get("id"),
            "count": dependencies.get("installed"),
        }
    return {
        "project": data,
        "declared": {"available": False, "reason": DECLARED_UNAVAILABLE_REASON},
        "resolved": {"available": False, "reason": RESOLVED_UNAVAILABLE_REASON},
        "installed": installed,
        "consistent": "unknown",
    }
