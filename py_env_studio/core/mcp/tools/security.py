"""Security tools — cache-only reads of existing PES scan results.

Phase 1 never triggers a fresh network scan from MCP. The existing
SecurityMatrix/DBHelper stack owns network access; MCP only exposes the
SQLite-cached payload via DBHelper.get_vulnerability_info.
"""

from __future__ import annotations

from ..context import resolve_environment
from ..errors import McpError
from ..schemas.responses import failure, success


def _flatten_cached_payload(payload):
    # type: (object) -> list
    """Normalise both cache shapes into a flat vulnerability list."""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("vulnerability_insights")
    matrices = []
    if isinstance(raw, dict):
        matrices = [raw]
    elif isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            if "developer_view" in entry:
                matrices.append(entry)
            else:
                for inner in entry.values():
                    if isinstance(inner, dict) and "developer_view" in inner:
                        matrices.append(inner)
    findings = []
    for matrix in matrices:
        meta = matrix.get("metadata") if isinstance(matrix.get("metadata"), dict) else {}
        package = meta.get("package")
        version = meta.get("version")
        for vuln in matrix.get("developer_view") or []:
            if not isinstance(vuln, dict):
                continue
            affected = vuln.get("affected_components") or ([package] if package else [])
            severity = vuln.get("severity") if isinstance(vuln.get("severity"), dict) else {}
            findings.append(
                {
                    "package": (affected[0] if affected else package),
                    "installed_version": version,
                    "vulnerability_id": vuln.get("vulnerability_id"),
                    "severity": severity.get("level"),
                    "severity_score": severity.get("score"),
                    "fixed_versions": vuln.get("fixed_versions") or [],
                    "summary": vuln.get("summary"),
                    "remediation": vuln.get("remediation_steps"),
                    "status": vuln.get("status"),
                    "references": vuln.get("references") or [],
                }
            )
    return findings


def scan_vulnerabilities(arguments):
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
        from py_env_studio.utils.handlers import DBHelper
    except Exception as exc:
        return failure("SERVICE_UNAVAILABLE", "Security cache unavailable: {}".format(exc))
    try:
        cached = DBHelper.get_vulnerability_info(info["environment_id"])
    except Exception as exc:
        return failure(
            "SERVICE_UNAVAILABLE",
            "Could not read cached scan for '{}': {}".format(environment_id, exc),
            {"environment_id": environment_id},
        )
    findings = _flatten_cached_payload(cached)
    if not findings:
        return success(
            {
                "environment": info["environment_id"],
                "findings": [],
                "count": 0,
                "scan_available": False,
                "note": "No cached vulnerability scan found. Scans are performed "
                "by PES itself, not by MCP; no network lookup was attempted.",
            },
            cached=True,
        )
    return success(
        {
            "environment": info["environment_id"],
            "findings": findings,
            "count": len(findings),
            "scan_available": True,
        },
        cached=True,
    )
