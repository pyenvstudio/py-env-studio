"""Reusable MCP response envelopes."""

from __future__ import annotations

from datetime import datetime, timezone


def _utc_now():
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:  # pragma: no cover - defensive
        return datetime.utcnow().isoformat() + "Z"


def success(data, cached=False, extra_metadata=None):
    """Build a success envelope: {success, data, metadata}."""
    metadata = {"source": "pes", "cached": bool(cached), "timestamp": _utc_now()}
    if extra_metadata:
        metadata.update(extra_metadata)
    return {"success": True, "data": data, "metadata": metadata}


def failure(code, message, details=None):
    """Build a failure envelope: {success, error{code,message,details}}."""
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details or {}},
    }
