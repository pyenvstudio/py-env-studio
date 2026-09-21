"""MCP error codes and helpers (Phase 1: read-only)."""

from __future__ import annotations


class McpError(Exception):
    """Structured failure raised by MCP tool adapters."""

    def __init__(self, code, message, details=None):
        super(McpError, self).__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


ENVIRONMENT_NOT_FOUND = "ENVIRONMENT_NOT_FOUND"
PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
AMBIGUOUS_PROJECT = "AMBIGUOUS_PROJECT"
INVALID_INPUT = "INVALID_INPUT"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
SCAN_UNAVAILABLE = "SCAN_UNAVAILABLE"
