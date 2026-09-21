"""PES MCP server — Python Environment Control Plane for AI coding agents.

Phase 1 is strictly read-only. MCP handlers here are thin adapters over
existing PES Core services; no business logic lives in the tool layer.

Layout::

    Copilot / AI agent (reasoning)
                |
               MCP (this package)
                |
            PES Core services
"""

from __future__ import annotations

from .server import READ_ONLY_TOOL_NAMES, PesMcpServer, create_server

__all__ = ["PesMcpServer", "create_server", "READ_ONLY_TOOL_NAMES"]
