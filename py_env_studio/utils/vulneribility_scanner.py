"""Explicitly triggered vulnerability scans and external API clients."""

from datetime import datetime
import requests
from cvss import CVSS3
from packaging.utils import canonicalize_name

from .handlers import DBHelper
from .version_utils import vuln_status
from py_env_studio.core.pip_tools import list_packages


class PyPIAPI:
    BASE_URL = "https://pypi.org/pypi/"

    def get_deprecation_eol(self, package, version=None):
        response = requests.get(f"{self.BASE_URL}{package}/json", timeout=15)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
            raise ValueError("Invalid PyPI response")
        info, releases = data["info"], data.get("releases", {})
        classifiers = info.get("classifiers", [])
        return {
            "deprecated": any(any(term in value for term in ("Deprecated", "Obsolete", "Unmaintained")) for value in classifiers),
            "yanked": bool(version and any(item.get("yanked", False) for item in releases.get(version, []))),
            "eol": any("End-of-life" in value or "EOL" in value for value in classifiers),
            "classifiers": classifiers,
        }


class DepsDevAPI:
    BASE_URL = "https://api.deps.dev/v3alpha/systems/"

    def get_dependencies(self, package, version):
        response = requests.get(f"{self.BASE_URL}pypi/packages/{package}/versions/{version}:dependencies", timeout=15)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid deps.dev response")
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("deps.dev response did not include a dependency graph root")
        paths = {0: [0]}
        for _ in range(len(nodes)):
            changed = False
            for edge in edges:
                source, target = edge.get("fromNode"), edge.get("toNode")
                if source in paths and isinstance(target, int) and target not in paths:
                    paths[target] = paths[source] + [target]
                    changed = True
            if not changed:
                break
        dependencies = []
        for index, node in enumerate(nodes[1:], 1):
            key = node.get("versionKey", {})
            if not key.get("name") or not key.get("version"):
                continue
            node_path = paths.get(index, [])
            path_names = [
                str(nodes[path_index].get("versionKey", {}).get("name"))
                for path_index in node_path
                if nodes[path_index].get("versionKey", {}).get("name")
            ]
            relation = str(node.get("relation", "")).upper()
            if relation not in {"DIRECT", "INDIRECT"}:
                relation = "UNKNOWN"
            dependencies.append({
                "name": key["name"], "version": key["version"],
                "relation": "direct" if relation == "DIRECT" else "transitive" if relation == "INDIRECT" else "unknown",
                "path": path_names,
                "parent_package": path_names[-2] if len(path_names) > 1 else None,
                "errors": node.get("errors", []) or [],
            })
        return {
            "dependencies": dependencies,
            "graph_error": data.get("error"),
            "node_errors": [error for node in nodes for error in (node.get("errors", []) or [])],
        }


class OSVAPI:
    BASE_URL = "https://api.osv.dev/v1/query"

    def get_vulnerabilities(self, package, version):
        results = []
        payload = {"package": {"name": package, "ecosystem": "PyPI"}, "version": version}
        while True:
            response = requests.post(self.BASE_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or ("vulns" in data and not isinstance(data["vulns"], list)):
                raise ValueError("Invalid OSV response")
            for vuln in data.get("vulns", []):
                refs = [ref for ref in vuln.get("references", []) if ref.get("url")]
                fixed_versions, affected_versions, affected_ranges = set(), set(), []
                for affected in vuln.get("affected", []):
                    for item in affected.get("versions", []):
                        affected_versions.add(str(item))
                    for range_item in affected.get("ranges", []):
                        affected_ranges.append(range_item)
                        for event in range_item.get("events", []):
                            if event.get("fixed"):
                                fixed_versions.add(str(event["fixed"]))
                cvss_records = []
                for item in vuln.get("severity", []) or []:
                    vector = str(item.get("score") or "")
                    cvss_version = vector.split("/", 1)[0].split(":", 1)[1] if vector.startswith("CVSS:") and ":" in vector.split("/", 1)[0] else None
                    cvss_score = None
                    if item.get("type") == "CVSS_V3":
                        try:
                            cvss_score = float(CVSS3(vector).base_score)
                        except Exception:
                            pass
                    cvss_records.append({
                        "source": "OSV", "type": item.get("type"), "vector": vector,
                        "version": cvss_version, "base_score": cvss_score,
                    })
                scored = [item for item in cvss_records if item.get("base_score") is not None]
                base_score = max((item["base_score"] for item in scored), default=None)
                level = "Critical" if base_score is not None and base_score >= 9 else "High" if base_score is not None and base_score >= 7 else "Medium" if base_score is not None and base_score >= 4 else "Low" if base_score is not None else "Unknown"
                database_specific = vuln.get("database_specific", {}) or {}
                cwe_ids = database_specific.get("cwe_ids", []) or database_specific.get("cwe", []) or []
                if isinstance(cwe_ids, str):
                    cwe_ids = [cwe_ids]
                fixed_versions = sorted(fixed_versions)
                results.append({
                    "vulnerability_id": str(vuln["id"]), "summary": vuln.get("summary", ""),
                    "affected_components": [package], "affected_versions": sorted(affected_versions),
                    "affected_ranges": affected_ranges, "severity": {"type": scored[0].get("type") if scored else "Unknown", "score": base_score, "level": level},
                    "cvss_records": cvss_records, "aliases": list(vuln.get("aliases", []) or []),
                    "published": vuln.get("published"), "modified": vuln.get("modified"),
                    "withdrawn": vuln.get("withdrawn"), "advisory_status": "withdrawn" if vuln.get("withdrawn") else "active",
                    "cwe_ids": cwe_ids, "raw_advisory": vuln,
                    "fixed_versions": fixed_versions, "status": vuln_status(version, fixed_versions),
                    "impact": vuln.get("details", "").split(".")[0],
                    "remediation_steps": f"Upgrade to {fixed_versions[0]}" if fixed_versions else "No fix available",
                    "references": refs,
                })
            next_page = data.get("next_page_token")
            if not next_page:
                break
            payload["page_token"] = next_page
        return results


class SecurityMatrix:
    def __init__(self):
        self.deps_api, self.osv_api, self.pypi_api = DepsDevAPI(), OSVAPI(), PyPIAPI()
        self.log_callback = None
        self._scan_id = None
        self._query_cache = {}
        self._scan_errors = 0
        self._scan_successes = 0
        self._scan_warnings = 0
        self._observation_time = None

    def _query(self, source, package, version, function):
        identity = (source, canonicalize_name(str(package)), str(version))
        if identity in self._query_cache:
            return self._query_cache[identity]
        timestamp = datetime.now().astimezone().isoformat()
        try:
            result = function()
            if source == "OSV":
                unique = {}
                for item in result:
                    unique.setdefault(str(item.get("vulnerability_id", "")), item)
                result = list(unique.values())
            observations = result if source == "OSV" else []
            if self._scan_id is not None:
                count = len(result) if isinstance(result, list) else len(result.get("dependencies", [])) if isinstance(result, dict) and source == "deps.dev" else len(observations)
                DBHelper.record_intelligence_query(self._scan_id, package, identity[1], str(version), source, "success", count, None, timestamp, observations)
                self._scan_successes += 1
            self._query_cache[identity] = result
            return result
        except Exception as exc:
            if self._scan_id is not None:
                DBHelper.record_intelligence_query(self._scan_id, package, identity[1], str(version), source, "failed", None, str(exc)[:500], timestamp)
                self._scan_errors += 1
            self._query_cache[identity] = None
            return None

    def build_matrix(self, package, version="latest"):
        timestamp = datetime.now().astimezone().isoformat()
        matrix = {"vulnerability_insights": {"metadata": {"timestamp": timestamp, "package": package, "version": version, "ecosystem": "PyPI", "index_insights": [], "dependency_analysis": {"source": "deps.dev", "status": "unavailable", "dependencies": []}}, "developer_view": [], "tech_leader_view": {"total_vulnerabilities": 0, "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0}}}}
        insights = matrix["vulnerability_insights"]
        pypi = self._query("PyPI", package, version, lambda: self.pypi_api.get_deprecation_eol(package, version))
        if pypi is not None:
            insights["metadata"]["index_insights"].append({"source": "PyPI", "package": package, "version": version, **{key: pypi[key] for key in ("deprecated", "yanked", "eol")}})
        vulns = self._query("OSV", package, version, lambda: self.osv_api.get_vulnerabilities(package, version))
        if vulns:
            insights["developer_view"].extend(vulns)
        dependency_result = self._query("deps.dev", package, version, lambda: self.deps_api.get_dependencies(package, version))
        if isinstance(dependency_result, list):  # Older integrations may return direct name/version pairs.
            dependencies = [{"name": name, "version": dep_version, "relation": "direct", "path": [package, name], "parent_package": package, "errors": []} for name, dep_version in dependency_result]
            graph_error, node_errors = None, []
        elif isinstance(dependency_result, dict):
            dependencies = dependency_result.get("dependencies", [])
            graph_error = dependency_result.get("graph_error")
            node_errors = dependency_result.get("node_errors", [])
        else:
            dependencies, graph_error, node_errors = [], None, []
        if graph_error or node_errors:
            self._scan_warnings += 1
        insights["metadata"]["dependency_analysis"] = {
            "source": "deps.dev", "status": "unavailable" if dependency_result is None else "partial" if graph_error or node_errors else "success",
            "graph_error": graph_error, "node_errors": node_errors,
            "dependencies": dependencies,
            "limitation": "Parent paths reflect deps.dev's resolved graph for a generic platform and may differ from this environment's installed dependency graph.",
        }
        for dependency in dependencies:
            dep_name, dep_version = dependency["name"], dependency["version"]
            if self._scan_id is not None:
                DBHelper.record_intelligence_dependency(self._scan_id, package, version, dependency, timestamp)
            dep_pypi = self._query("PyPI", dep_name, dep_version, lambda n=dep_name, v=dep_version: self.pypi_api.get_deprecation_eol(n, v))
            if dep_pypi is not None:
                insights["metadata"]["index_insights"].append({"source": "PyPI", "package": dep_name, "version": dep_version, "relation": dependency["relation"], "parent_package": dependency.get("parent_package"), "dependency_path": dependency.get("path", []), **{key: dep_pypi[key] for key in ("deprecated", "yanked", "eol")}})
            dep_vulns = self._query("OSV", dep_name, dep_version, lambda n=dep_name, v=dep_version: self.osv_api.get_vulnerabilities(n, v))
            for vuln in dep_vulns or []:
                vuln["affected_components"] = [dep_name]
                vuln["current_version"] = dep_version
                vuln["dependency_relation"] = dependency["relation"]
                vuln["parent_package"] = dependency.get("parent_package")
                vuln["dependency_path"] = dependency.get("path", [])
                insights["developer_view"].append(vuln)
        for vuln in insights["developer_view"]:
            vuln.setdefault("current_version", version)
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in insights["developer_view"]:
            level = str(vuln.get("severity", {}).get("level", "Unknown")).lower()
            if level in counts:
                counts[level] += 1
        insights["tech_leader_view"].update(total_vulnerabilities=len(insights["developer_view"]), severity_breakdown=counts)
        return matrix

    def scan_pkg(self, pkg, version="latest", env_id=None):
        result = self.build_matrix(pkg, version)
        if env_id:
            DBHelper.save_vulnerability_info(env_id, result)
        return True

    def scan_env(self, env_name, log_callback):
        """Run an explicitly requested scan and retain every API outcome."""
        packages = list_packages(env_name)
        started = datetime.now().astimezone().isoformat()
        env_id = DBHelper.get_or_create_env(env_name)
        self._scan_id = DBHelper.begin_intelligence_scan(env_name, started, len(packages))
        self._query_cache, self._scan_errors, self._scan_successes = {}, 0, 0
        self._scan_warnings = 0
        completed, failed = 0, 0
        for package, version in packages:
            log_callback(f"Scanning package {package} (version: {version}) in environment {env_name}")
            prior_errors, prior_warnings = self._scan_errors, self._scan_warnings
            try:
                self.scan_pkg(package, version, env_id)
                if self._scan_errors == prior_errors and self._scan_warnings == prior_warnings:
                    completed += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                log_callback(f"Failed to scan package {package}: {exc}")
        status = "success" if self._scan_errors == 0 and self._scan_warnings == 0 and failed == 0 else "partial" if self._scan_successes else "failed"
        DBHelper.finish_intelligence_scan(self._scan_id, datetime.now().astimezone().isoformat(), status, len(packages), completed, failed)
        log_callback(f"Vulnerability scan {status}: {completed}/{len(packages)} packages queried successfully; {self._scan_errors} API failures.")
        return status != "failed"


if __name__ == "__main__":
    DBHelper.init_db()
