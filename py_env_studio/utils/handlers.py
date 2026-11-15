from __future__ import annotations

from datetime import datetime
import json
import os
from packaging.utils import canonicalize_name

from py_env_studio.core.database import DatabaseManager
from py_env_studio.core.env_manager import DB_FILE, MATRIX_FILE, VENV_DIR
from py_env_studio.core import schema as sql
from .version_utils import vuln_status


class DataHelper:
    """Operations in JSON file (acts like DBHelper but with JSON)."""

    @staticmethod
    def _load_data():
        if not os.path.exists(MATRIX_FILE):
            return {"environments": [], "env_vulnerability_info": []}

        with open(MATRIX_FILE, "r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                return {"environments": [], "env_vulnerability_info": []}

    @staticmethod
    def _save_data(data):
        with open(MATRIX_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)

    @staticmethod
    def get_or_create_env(env_name, env_path):
        data = DataHelper._load_data()

        for env in data["environments"]:
            if env["env_name"] == env_name:
                return env["env_id"]

        new_id = len(data["environments"]) + 1
        data["environments"].append(
            {
                "env_id": new_id,
                "env_name": env_name,
                "env_path": env_path,
            }
        )
        DataHelper._save_data(data)
        return new_id

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        data = DataHelper._load_data()

        new_vid = len(data["env_vulnerability_info"]) + 1
        data["env_vulnerability_info"].append(
            {
                "vid": new_vid,
                "env_id": env_id,
                "vulnerabilities": vulnerabilities_json,
            }
        )
        DataHelper._save_data(data)

    @staticmethod
    def get_vulnerability_info(env_id):
        data = DataHelper._load_data()
        results = [record for record in data["env_vulnerability_info"] if record["env_id"] == env_id]
        return results if results else None


class DBHelper:
    _dbm = DatabaseManager()

    @staticmethod
    def init_db():
        DBHelper._dbm.initialize_database()

    @staticmethod
    def get_or_create_env(env_name):
        env_path = os.path.join(VENV_DIR, env_name)
        with DBHelper._dbm.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql.get("environments", "get_env_id"), (env_name,))
            row = cur.fetchone()
            if row:
                return row[0]

            cur.execute(
                sql.get("environments", "create_environment"),
                (env_name, env_path, datetime.now()),
            )
            conn.commit()
            return cur.lastrowid

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        with DBHelper._dbm.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                sql.get("vulnerability", "insert_scan"),
                (env_id, json.dumps(vulnerabilities_json), datetime.now()),
            )
            conn.commit()

    @staticmethod
    def get_vulnerability_info(env_name):
        with DBHelper._dbm.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                sql.get("vulnerability", "scan_history_rows"),
                (env_name,),
            )
            rows = cur.fetchall()

        if not rows:
            return {"vulnerability_insights": []}

        latest_scan_date = max((row[3] for row in rows if row[3]), default=None)
        buckets = {}
        history = {}
        for vid, payload, created_at, scan_date in rows:
            try:
                decoded = json.loads(payload) if isinstance(payload, str) else payload
            except Exception:
                continue

            raw_matrix = decoded.get("vulnerability_insights", decoded)
            if latest_scan_date is not None and scan_date == latest_scan_date:
                buckets[str(vid)] = raw_matrix

            if not isinstance(raw_matrix, dict) or "metadata" not in raw_matrix:
                continue
            metadata = raw_matrix.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            package_name = str(metadata.get("package") or "").strip()
            if not package_name or not scan_date:
                continue

            developer_view = raw_matrix.get("developer_view") or []
            tech_view = raw_matrix.get("tech_leader_view") or {}
            if not isinstance(developer_view, list):
                developer_view = []
            if not isinstance(tech_view, dict):
                tech_view = {}
            try:
                total = max(0, int(tech_view.get("total_vulnerabilities")))
            except (TypeError, ValueError):
                total = len(developer_view)
            versions = {package_name.split("[")[0].strip(): str(metadata.get("version") or "?")}
            for insight in metadata.get("index_insights", []) or []:
                if not isinstance(insight, dict):
                    continue
                dependency = str(insight.get("package") or "").split("[")[0].strip()
                if dependency and insight.get("version"):
                    versions[dependency] = str(insight["version"])

            def is_fixed(vulnerability):
                if not isinstance(vulnerability, dict):
                    return False
                status = str(vulnerability.get("status", "")).lower()
                if status in {"fixed", "not fixed"}:
                    return status == "fixed"
                affected = vulnerability.get("affected_components") or []
                affected_package = str(affected[0]).split("[")[0].strip() if affected else package_name
                return vuln_status(
                    versions.get(affected_package),
                    vulnerability.get("fixed_versions", []) or [],
                ) == "fixed"

            fixed = sum(
                1 for vulnerability in developer_view if is_fixed(vulnerability)
            )
            history.setdefault(package_name.casefold(), []).append(
                {
                    "timestamp": str(created_at or scan_date),
                    "total_vulnerabilities": total,
                    "fixed_vulnerabilities": fixed,
                }
            )

        for package_data in buckets.values():
            if not isinstance(package_data, dict) or "metadata" not in package_data:
                continue
            metadata = package_data.get("metadata") or {}
            if not isinstance(metadata, dict):
                continue
            package_name = str(metadata.get("package") or "").strip()
            if not package_name:
                continue
            tech_view = package_data.setdefault("tech_leader_view", {})
            if not isinstance(tech_view, dict):
                tech_view = {}
                package_data["tech_leader_view"] = tech_view
            tech_view["trend_data"] = history.get(package_name.casefold(), [])

        for trend in history.values():
            trend.sort(key=lambda point: point["timestamp"])

        # External intelligence trends are based only on explicit scan query
        # outcomes. Legacy/local scan rows remain the source of local history.
        intelligence = DBHelper.intelligence_history(env_name)
        by_package = {}
        by_identity = {}
        for row in intelligence:
            (query_id, scan_id, package, normalized, version, source, status,
             result_count, error, observed_at, observation_id, vuln_id,
             affected_versions, affected_ranges, fixed_versions, severity,
             vuln_status_value, details_json, scan_status) = row
            if source != "OSV":
                continue
            entry = by_identity.setdefault((normalized, version), {"attempt": None, "success": None, "observations": {}})
            attempt = {"query_id": query_id, "status": status, "error": error, "timestamp": observed_at, "result_count": result_count, "scan_status": scan_status}
            if entry["attempt"] is None or (observed_at or "") >= (entry["attempt"]["timestamp"] or ""):
                entry["attempt"] = attempt
            if status == "success":
                if entry["success"] is None or (observed_at or "") >= (entry["success"]["timestamp"] or ""):
                    entry["success"] = attempt
                point = by_package.setdefault(normalized, {}).setdefault(query_id, {
                    "timestamp": observed_at,
                    "total_vulnerabilities": int(result_count or 0),
                    "fixed_vulnerabilities": 0,
                })
            if observation_id is not None:
                try:
                    details = json.loads(details_json)
                except (TypeError, json.JSONDecodeError):
                    details = {}
                entry["observations"].setdefault(query_id, []).append(details)
                if status == "success":
                    point["fixed_vulnerabilities"] += int(vuln_status_value == "fixed")

        for package_data in buckets.values():
            if not isinstance(package_data, dict):
                continue
            metadata = package_data.setdefault("metadata", {})
            name = str(metadata.get("package") or "").strip()
            version = str(metadata.get("version") or "")
            normalized = canonicalize_name(name)
            entry = by_identity.get((normalized, version))
            tech_view = package_data.setdefault("tech_leader_view", {})
            tech_view["trend_data"] = sorted(by_package.get(normalized, {}).values(), key=lambda p: p["timestamp"] or "")
            if entry:
                metadata["intelligence_status"] = (entry["attempt"] or {}).get("status", "not_scanned")
                metadata["intelligence_error"] = (entry["attempt"] or {}).get("error")
                metadata["intelligence_observed_at"] = (entry["success"] or {}).get("timestamp")
                metadata["intelligence_result_count"] = (entry["attempt"] or {}).get("result_count")
                metadata["intelligence_scan_status"] = (entry["attempt"] or {}).get("scan_status")
                metadata["intelligence_last_success_count"] = (entry["success"] or {}).get("result_count")
            current_observations = []
            has_successful_observation_query = False
            identities = [(normalized, version)]
            for vuln in package_data.get("developer_view", []) or []:
                components = vuln.get("affected_components", []) if isinstance(vuln, dict) else []
                for component in components:
                    identities.append((canonicalize_name(str(component)), str(vuln.get("current_version") or "")))
            for insight in metadata.get("index_insights", []) or []:
                if isinstance(insight, dict) and insight.get("package") and insight.get("version"):
                    identities.append((canonicalize_name(str(insight["package"])), str(insight["version"])))
            for identity in identities:
                package_entry = by_identity.get(identity)
                if package_entry and package_entry["success"]:
                    has_successful_observation_query = True
                    current_observations.extend(package_entry["observations"].get(package_entry["success"]["query_id"], []))
            if has_successful_observation_query:
                package_data["developer_view"] = current_observations
            elif entry is None:
                metadata["intelligence_status"] = "not_scanned"
                metadata["intelligence_scan_status"] = "not_scanned"

        return {"vulnerability_insights": [buckets]}

    @staticmethod
    def begin_intelligence_scan(env_name, started_at, package_count):
        with DBHelper._dbm.connect() as conn:
            cur = conn.execute(sql.get("vulnerability_intelligence", "begin_vulnerability_intelligence_scan"), (env_name, started_at))
            scan_id = cur.lastrowid
            conn.execute(sql.get("vulnerability_intelligence", "set_vulnerability_intelligence_scan_counts"), (package_count, 0, 0, scan_id))
            return scan_id

    @staticmethod
    def record_intelligence_query(scan_id, package, normalized_package, version, source, status, result_count, error, observed_at, observations=()):
        with DBHelper._dbm.connect() as conn:
            conn.execute(sql.get("vulnerability_intelligence", "insert_vulnerability_intelligence_query"), (scan_id, package, normalized_package, version, source, status, result_count, error, observed_at))
            row = conn.execute(sql.get("vulnerability_intelligence", "get_vulnerability_intelligence_query_id"), (scan_id, normalized_package, version, source)).fetchone()
            query_id = row[0]
            for item in observations:
                severity = item.get("severity", "Unknown")
                if isinstance(severity, dict):
                    severity = severity.get("level", "Unknown")
                conn.execute(sql.get("vulnerability_intelligence", "insert_vulnerability_intelligence_observation"), (
                    query_id, scan_id, package, normalized_package, version, item["vulnerability_id"], source,
                    json.dumps(item.get("affected_versions", [])), json.dumps(item.get("affected_ranges", [])),
                    json.dumps(item.get("fixed_versions", [])), severity, item.get("status", "not fixed"),
                    observed_at, json.dumps(item.get("details", item), sort_keys=True),
                ))

    @staticmethod
    def finish_intelligence_scan(scan_id, completed_at, status, package_count, completed_packages, failed_packages):
        with DBHelper._dbm.connect() as conn:
            conn.execute(sql.get("vulnerability_intelligence", "finish_vulnerability_intelligence_scan"), (completed_at, status, package_count, completed_packages, failed_packages, scan_id))

    @staticmethod
    def intelligence_history(env_name):
        with DBHelper._dbm.connect() as conn:
            return conn.execute(sql.get("vulnerability_intelligence", "vulnerability_intelligence_history"), (env_name,)).fetchall()
