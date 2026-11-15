from __future__ import annotations

from datetime import datetime
import json
import os
from packaging.utils import canonicalize_name

from py_env_studio.core.database import DatabaseManager
from py_env_studio.core.env_manager import DB_FILE, MATRIX_FILE, VENV_DIR
from py_env_studio.core import schema as sql
from .vulnerability_intelligence import build_package_profile


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
                sql.get("vulnerability", "latest_scan_rows"),
                (env_name,),
            )
            rows = cur.fetchall()

        if not rows:
            return {"vulnerability_insights": []}

        buckets = {}
        for vid, payload in rows:
            try:
                decoded = json.loads(payload) if isinstance(payload, str) else payload
            except Exception:
                continue

            raw_matrix = decoded.get("vulnerability_insights", decoded)
            package_meta = raw_matrix.get("metadata", {}) if isinstance(raw_matrix, dict) else {}
            package_key = canonicalize_name(str(package_meta.get("package") or "")) if isinstance(package_meta, dict) else ""
            buckets[package_key or str(vid)] = raw_matrix

        # External intelligence trends are based only on explicit scan query
        # outcomes. Legacy/local scan rows remain the source of local history.
        intelligence = DBHelper.intelligence_history(env_name)
        dependency_history = DBHelper.successful_intelligence_dependency_history(env_name)
        by_package = {}
        by_identity = {}
        records_by_package = {}
        successful_scans_by_package = {}
        source_attempts = {}
        for row in intelligence:
            (query_id, scan_id, package, normalized, version, source, status,
             result_count, error, observed_at, observation_id, vuln_id,
             affected_versions, affected_ranges, fixed_versions, severity,
             vuln_status_value, details_json, scan_status, aliases_json,
             published_at, modified_at, withdrawn_at, cvss_json, cwe_ids_json,
             advisory_status, affected_release_count) = row
            source_key = (normalized, version, source)
            source_attempt = {"status": status, "error": error, "timestamp": observed_at, "scan_id": scan_id}
            if source_key not in source_attempts or (observed_at or "") >= (source_attempts[source_key]["timestamp"] or ""):
                source_attempts[source_key] = source_attempt
            if source != "OSV":
                continue
            entry = by_identity.setdefault((normalized, version), {"attempt": None, "success": None, "observations": {}})
            attempt = {"query_id": query_id, "scan_id": scan_id, "status": status, "error": error, "timestamp": observed_at, "result_count": result_count, "scan_status": scan_status}
            if status == "success":
                successful_scans_by_package.setdefault(normalized, {})[scan_id] = observed_at
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
                def decode_list(value):
                    try:
                        return json.loads(value) if isinstance(value, str) else value or []
                    except (TypeError, json.JSONDecodeError):
                        return []
                severity_details = details.get("severity")
                if not isinstance(severity_details, dict):
                    severity_details = {}
                severity_details.setdefault("level", severity)
                details.update({
                    "vulnerability_id": vuln_id,
                    "package_name": package,
                    "normalized_package": normalized,
                    "scan_id": scan_id,
                    "source": source,
                    "aliases": decode_list(aliases_json),
                    "published": published_at,
                    "modified": modified_at,
                    "withdrawn": withdrawn_at,
                    "cvss_records": decode_list(cvss_json),
                    "cwe_ids": decode_list(cwe_ids_json),
                    "advisory_status": advisory_status,
                    "affected_versions": decode_list(affected_versions),
                    "affected_ranges": decode_list(affected_ranges),
                    "fixed_versions": decode_list(fixed_versions),
                    "status": vuln_status_value,
                    "severity": severity_details,
                    "package_version": version,
                    "observed_at": observed_at,
                    "affected_release_count": affected_release_count,
                })
                entry["observations"].setdefault(query_id, []).append(details)
                records_by_package.setdefault(normalized, []).append(details)
                if status == "success":
                    point["fixed_vulnerabilities"] += int(vuln_status_value == "fixed")

        dependencies_by_root = {}
        for row in dependency_history:
            (scan_id, root_package, root_normalized, root_version, package_name,
             normalized_package, package_version, relation, parent_package,
             dependency_path, observed_at, scan_status) = row
            root_key = (root_normalized, root_version)
            context = dependencies_by_root.setdefault(root_key, {"scan_id": 0, "observed_at": None, "scan_status": None, "dependencies": []})
            if scan_id > context["scan_id"]:
                context.update(scan_id=scan_id, observed_at=observed_at, scan_status=scan_status, dependencies=[])
            if scan_id == context["scan_id"]:
                try:
                    path = json.loads(dependency_path)
                except (TypeError, json.JSONDecodeError):
                    path = []
                context["dependencies"].append({
                    "name": package_name, "version": package_version, "relation": relation,
                    "parent_package": parent_package, "path": path,
                })

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
            else:
                metadata["intelligence_status"] = "not_scanned"
                metadata["intelligence_scan_status"] = "not_scanned"
            dependency_analysis = metadata.setdefault("dependency_analysis", {})
            dependency_attempt = source_attempts.get((normalized, version, "deps.dev"))
            if dependency_attempt:
                dependency_analysis["latest_api_status"] = dependency_attempt["status"]
                dependency_analysis["latest_api_error"] = dependency_attempt["error"]
            previous_graph = dependencies_by_root.get((normalized, version))
            if dependency_analysis.get("status", "unavailable") == "unavailable" and previous_graph:
                dependency_analysis.update({
                    "source": "deps.dev", "status": "stale",
                    "dependencies": previous_graph["dependencies"],
                    "last_successful_scan_id": previous_graph["scan_id"],
                    "last_successful_collected_at": previous_graph["observed_at"],
                    "limitation": "Showing the last successfully resolved deps.dev graph; its generic-platform graph may differ from the installed environment.",
                })
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
            dependency_metadata = metadata.get("dependency_analysis", {}) or {}
            for dependency in dependency_metadata.get("dependencies", []) or []:
                if dependency.get("name") and dependency.get("version"):
                    identities.append((canonicalize_name(str(dependency["name"])), str(dependency["version"])))
            for identity in identities:
                package_entry = by_identity.get(identity)
                if package_entry and package_entry["success"]:
                    has_successful_observation_query = True
                    for item in package_entry["observations"].get(package_entry["success"]["query_id"], []):
                        current_item = dict(item)
                        dependency = next((dep for dep in dependency_metadata.get("dependencies", []) or []
                                           if canonicalize_name(str(dep.get("name", ""))) == identity[0]
                                           and str(dep.get("version", "")) == identity[1]), None)
                        if dependency:
                            current_item["affected_components"] = [dependency["name"]]
                            current_item["dependency_relation"] = dependency.get("relation", "unknown")
                            current_item["parent_package"] = dependency.get("parent_package")
                            current_item["dependency_path"] = dependency.get("path", [])
                        current_observations.append(current_item)
            if has_successful_observation_query:
                local_status_by_id = {}
                for local_item in package_data.get("developer_view", []) or []:
                    if not isinstance(local_item, dict) or local_item.get("status") not in {"fixed", "not fixed"}:
                        continue
                    for identifier in [local_item.get("vulnerability_id"), *(local_item.get("aliases") or [])]:
                        if identifier:
                            local_status_by_id[str(identifier)] = local_item["status"]
                for current_item in current_observations:
                    identifiers = [current_item.get("vulnerability_id"), *(current_item.get("aliases") or [])]
                    stored_status = next((local_status_by_id.get(str(identifier)) for identifier in identifiers if identifier and str(identifier) in local_status_by_id), None)
                    if stored_status:
                        current_item["status"] = stored_status
                package_data["developer_view"] = current_observations
            current_root_observations = (
                entry["observations"].get(entry["success"]["query_id"], [])
                if entry and entry["success"] else []
            )
            current_scan_id = entry["success"]["scan_id"] if entry and entry["success"] else None
            previous_scan_id = max(
                (scan_id for scan_id in successful_scans_by_package.get(normalized, {})
                 if current_scan_id is not None and scan_id < current_scan_id),
                default=None,
            )
            package_data["intelligence_profile"] = build_package_profile(
                records_by_package.get(normalized, []),
                current_root_observations,
                successful_scans_by_package.get(normalized, {}).get(previous_scan_id),
                entry["success"]["timestamp"] if entry and entry["success"] else None,
                current_version=version,
            )

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
                affected_versions = item.get("affected_versions", []) or []
                aliases = item.get("aliases", []) or []
                advisory_status = "withdrawn" if item.get("withdrawn") else "active"
                conn.execute(sql.get("vulnerability_intelligence", "insert_vulnerability_intelligence_observation"), (
                    query_id, scan_id, package, normalized_package, version, item["vulnerability_id"], source,
                    json.dumps(affected_versions), json.dumps(item.get("affected_ranges", [])),
                    json.dumps(item.get("fixed_versions", [])), severity, item.get("status", "not fixed"),
                    json.dumps(aliases), item.get("published"), item.get("modified"), item.get("withdrawn"),
                    json.dumps(item.get("cvss_records", []), sort_keys=True), json.dumps(item.get("cwe_ids", [])),
                    advisory_status, len(set(affected_versions)) if affected_versions else None,
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

    @staticmethod
    def successful_intelligence_dependency_history(env_name):
        with DBHelper._dbm.connect() as conn:
            return conn.execute(sql.get("vulnerability_intelligence", "successful_vulnerability_intelligence_dependency_history"), (env_name,)).fetchall()

    @staticmethod
    def record_intelligence_dependency(scan_id, root_package, root_version, dependency, observed_at):
        with DBHelper._dbm.connect() as conn:
            conn.execute(sql.get("vulnerability_intelligence", "insert_vulnerability_intelligence_dependency_link"), (
                scan_id, root_package, canonicalize_name(str(root_package)), str(root_version),
                dependency["name"], canonicalize_name(str(dependency["name"])), str(dependency["version"]),
                dependency["relation"], dependency.get("parent_package"),
                json.dumps(dependency.get("path", [])), observed_at,
            ))
