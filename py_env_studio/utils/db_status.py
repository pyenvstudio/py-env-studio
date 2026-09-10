"""Vulnerability status (fixed / not fixed) persistence in the Py Env Studio DB.

Status is derived from installed vs. fixed versions and persisted back into the
stored ``env_vulnerability_info`` JSON blobs so the UI can lock further upgrade
actions once a package is fixed.
"""

import json

from .handlers import DBHelper
from .version_utils import vuln_status


def _latest_scan_rows(env_name, cur):
    """Fetch (vid, vulnerabilities) for every scan stored on the most recent
    scan day of an environment."""
    cur.execute(
        """
        SELECT evi.vid, evi.vulnerabilities
        FROM env_vulnerability_info evi
        JOIN environments e ON evi.env_id = e.env_id
        WHERE e.env_name=?
        AND DATE(evi.created_at) = (
            SELECT MAX(DATE(created_at))
            FROM env_vulnerability_info
            WHERE env_id = evi.env_id
        )
        ORDER BY evi.vid ASC
        """,
        (env_name,),
    )
    return cur.fetchall()


def _decode_payload(payload):
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return None
    return payload


def _matrices_of(decoded):
    """Return every vulnerability matrix stored in a payload.

    Supports the current ``{"vulnerability_insights": {matrix}}`` form as well
    as the legacy ``{"vulnerability_insights": [{scan_id: matrix}]}``
    list-of-buckets form.
    """
    if not isinstance(decoded, dict):
        return []
    raw = decoded.get("vulnerability_insights")
    matrices = []
    if isinstance(raw, dict):
        matrices.append(raw)
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
    return matrices


def _current_versions_of(matrix):
    """Map package name -> installed version from a matrix's metadata."""
    meta = matrix.get("metadata", {}) or {}
    versions = {}
    if meta.get("package"):
        versions[str(meta["package"]).split("[")[0].strip()] = str(meta.get("version", "?"))
    for entry in meta.get("index_insights", []) or []:
        name = str(entry.get("package", "")).split("[")[0].strip()
        ver = entry.get("version")
        if name and ver:
            versions[name] = str(ver)
    return versions


def _fill_statuses(matrix, force=False):
    """Set the 'status' (fixed/not fixed) field on every vulnerability in a
    matrix that does not already carry one (or all of them when ``force``).

    Returns True when any record was modified.
    """
    versions = _current_versions_of(matrix)
    changed = False
    for vuln in matrix.get("developer_view", []) or []:
        if not isinstance(vuln, dict):
            continue
        affected = vuln.get("affected_components") or []
        pkg = str(affected[0]).split("[")[0].strip() if affected else ""
        status = vuln_status(versions.get(pkg), vuln.get("fixed_versions", []) or [])
        if force or vuln.get("status") not in ("fixed", "not fixed"):
            vuln["status"] = status
            changed = True
    return changed


def ensure_vulnerability_statuses(env_name):
    """Backfill the 'status' (fixed/not fixed) field on every vulnerability in
    the latest scan of an environment when it is not already persisted."""
    with DBHelper._dbm.connect() as conn:
        cur = conn.cursor()
        rows = _latest_scan_rows(env_name, cur)
        for vid, payload in rows:
            decoded = _decode_payload(payload)
            if decoded is None:
                continue
            changed = False
            for matrix in _matrices_of(decoded):
                if _fill_statuses(matrix):
                    changed = True
            if changed:
                cur.execute(
                    "UPDATE env_vulnerability_info SET vulnerabilities=? WHERE vid=?",
                    (json.dumps(decoded), vid),
                )
        conn.commit()


def _bump_package_version(matrix, package, new_version):
    """Update the stored installed version for ``package`` inside a matrix's
    metadata. Returns True when anything changed."""
    meta = matrix.get("metadata", {}) or {}
    updated = False
    if str(meta.get("package", "")).split("[")[0].strip() == package:
        if meta.get("version") != new_version:
            meta["version"] = new_version
            updated = True
    for entry in meta.get("index_insights", []) or []:
        if str(entry.get("package", "")).split("[")[0].strip() == package:
            if entry.get("version") != new_version:
                entry["version"] = new_version
                updated = True
    return updated


def mark_package_fixed(env_name, package, new_version):
    """Persist a successful upgrade: bump the stored installed version of
    ``package`` in the latest scan and recompute statuses (fixed/not fixed),
    so the resolved state is recorded in the database."""
    with DBHelper._dbm.connect() as conn:
        cur = conn.cursor()
        rows = _latest_scan_rows(env_name, cur)
        for vid, payload in rows:
            decoded = _decode_payload(payload)
            if decoded is None:
                continue
            changed = False
            for matrix in _matrices_of(decoded):
                if _bump_package_version(matrix, package, new_version):
                    _fill_statuses(matrix, force=True)
                    changed = True
            if changed:
                cur.execute(
                    "UPDATE env_vulnerability_info SET vulnerabilities=? WHERE vid=?",
                    (json.dumps(decoded), vid),
                )
        conn.commit()