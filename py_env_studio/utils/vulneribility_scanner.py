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
        dependencies = []
        for node in data.get("nodes", []):
            key = node.get("versionKey", {})
            if node.get("relation") == "DIRECT" and key.get("name") and key.get("version"):
                dependencies.append((key["name"], key["version"]))
        return dependencies


class OSVAPI:
    BASE_URL = "https://api.osv.dev/v1/query"

    def get_vulnerabilities(self, package, version):
        response = requests.post(self.BASE_URL, json={"package": {"name": package, "ecosystem": "PyPI"}, "version": version}, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or ("vulns" in data and not isinstance(data["vulns"], list)):
            raise ValueError("Invalid OSV response")
        results = []
        for vuln in data.get("vulns", []):
            refs = [ref["url"] for ref in vuln.get("references", []) if ref.get("url")]
            fixed_versions, affected_versions, affected_ranges = set(), set(), []
            for affected in vuln.get("affected", []):
                for item in affected.get("versions", []):
                    affected_versions.add(str(item))
                for range_item in affected.get("ranges", []):
                    affected_ranges.append(range_item)
                    for event in range_item.get("events", []):
                        if event.get("fixed"):
                            fixed_versions.add(str(event["fixed"]))
            severity = vuln.get("severity", [])
            level, score = "Unknown", None
            for value in severity:
                if value.get("type") == "CVSS_V3":
                    score = value.get("score")
                    try:
                        base_score = CVSS3(score).base_score
                        level = "Critical" if base_score >= 9 else "High" if base_score >= 7 else "Medium" if base_score >= 4 else "Low"
                    except Exception:
                        pass
                    break
            fixed_versions = sorted(fixed_versions)
            results.append({
                "vulnerability_id": str(vuln["id"]), "summary": vuln.get("summary", ""),
                "affected_components": [package], "affected_versions": sorted(affected_versions),
                "affected_ranges": affected_ranges, "severity": {"type": "CVSS_V3" if score else "Unknown", "score": score, "level": level},
                "fixed_versions": fixed_versions, "status": vuln_status(version, fixed_versions),
                "impact": vuln.get("details", "").split(".")[0],
                "remediation_steps": f"Upgrade to {fixed_versions[0]}" if fixed_versions else "No fix available",
                "references": [{"type": "advisory", "url": url} for url in refs],
            })
        return results


class SecurityMatrix:
    def __init__(self):
        self.deps_api, self.osv_api, self.pypi_api = DepsDevAPI(), OSVAPI(), PyPIAPI()
        self.log_callback = None
        self._scan_id = None
        self._query_cache = {}
        self._scan_errors = 0
        self._scan_successes = 0
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
                DBHelper.record_intelligence_query(self._scan_id, package, identity[1], str(version), source, "success", len(result) if isinstance(result, list) else len(observations), None, timestamp, observations)
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
        matrix = {"vulnerability_insights": {"metadata": {"timestamp": timestamp, "package": package, "version": version, "ecosystem": "PyPI", "index_insights": []}, "developer_view": [], "tech_leader_view": {"total_vulnerabilities": 0, "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0}}}}
        insights = matrix["vulnerability_insights"]
        pypi = self._query("PyPI", package, version, lambda: self.pypi_api.get_deprecation_eol(package, version))
        if pypi is not None:
            insights["metadata"]["index_insights"].append({"source": "PyPI", "package": package, "version": version, **{key: pypi[key] for key in ("deprecated", "yanked", "eol")}})
        vulns = self._query("OSV", package, version, lambda: self.osv_api.get_vulnerabilities(package, version))
        if vulns:
            insights["developer_view"].extend(vulns)
        deps = self._query("deps.dev", package, version, lambda: self.deps_api.get_dependencies(package, version)) or []
        for dep_name, dep_version in deps:
            dep_pypi = self._query("PyPI", dep_name, dep_version, lambda n=dep_name, v=dep_version: self.pypi_api.get_deprecation_eol(n, v))
            if dep_pypi is not None:
                insights["metadata"]["index_insights"].append({"source": "PyPI", "package": dep_name, "version": dep_version, **{key: dep_pypi[key] for key in ("deprecated", "yanked", "eol")}})
            dep_vulns = self._query("OSV", dep_name, dep_version, lambda n=dep_name, v=dep_version: self.osv_api.get_vulnerabilities(n, v))
            for vuln in dep_vulns or []:
                vuln["affected_components"] = [dep_name]
                vuln["current_version"] = dep_version
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
        completed, failed = 0, 0
        for package, version in packages:
            log_callback(f"Scanning package {package} (version: {version}) in environment {env_name}")
            prior_errors = self._scan_errors
            try:
                self.scan_pkg(package, version, env_id)
                if self._scan_errors == prior_errors:
                    completed += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                log_callback(f"Failed to scan package {package}: {exc}")
        status = "success" if self._scan_errors == 0 and failed == 0 else "partial" if self._scan_successes else "failed"
        DBHelper.finish_intelligence_scan(self._scan_id, datetime.now().astimezone().isoformat(), status, len(packages), completed, failed)
        log_callback(f"Vulnerability scan {status}: {completed}/{len(packages)} packages queried successfully; {self._scan_errors} API failures.")
        return status != "failed"


if __name__ == "__main__":
    DBHelper.init_db()
