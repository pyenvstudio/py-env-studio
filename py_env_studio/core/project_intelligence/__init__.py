"""Project intelligence service — consolidated read-only project analysis.

This package aggregates existing PES Core services (project registry,
environment manager, package manager, dependency preview, security cache)
into a single authoritative project report. It performs no mutations,
no network access of its own, and creates no new persistence.

Layering::

    MCP handler (thin: validate input, call service, wrap envelope)
          |
    ProjectIntelligenceService (this package: orchestration only)
          |
    PES Core services (runtime_toggle, env_manager, package_manager,
                       dependency_preview, handlers.DBHelper)
"""

from __future__ import annotations

from .service import ProjectIntelligenceService, analyze_project

__all__ = ["ProjectIntelligenceService", "analyze_project"]
