import os
import requests
from datetime import datetime
from cvss import CVSS3
from .handlers import DBHelper
from py_env_studio.core.env_manager import VENV_DIR, DB_FILE
from py_env_studio.core.pip_tools import list_packages

# ===================== Helpers =====================
class Helpers:
    pass
# ===================== API Clients =====================
class PyPIAPI:
    BASE_URL = "https://pypi.org/pypi/"

    def get_deprecation_eol(self, package, version=None):
        """
        Fetch deprecation and EOL insights for a package (and optionally a version) from PyPI.
        Returns a dict with 'deprecated', 'yanked', 'eol', and 'classifiers' info.
        """
        url = f"{self.BASE_URL}{package}/json"
        response = requests.get(url)
        if response.status_code != 200:
            return {"deprecated": False, "yanked": False, "eol": False, "classifiers": []}
        data = response.json()
        info = data.get("info", {})
        releases = data.get("releases", {})
        deprecated = False
        yanked = False
        eol = False
        classifiers = info.get("classifiers", [])
        # Check for deprecation/EOL in classifiers
        for c in classifiers:
            if "Deprecated" in c or "Obsolete" in c or "Unmaintained" in c:
                deprecated = True
            if "End-of-life" in c or "EOL" in c:
                eol = True
        # Check if the version is yanked
        if version and version in releases:
            for file in releases[version]:
                if file.get("yanked", False):
                    yanked = True
        return {
            "deprecated": deprecated,
            "yanked": yanked,
            "eol": eol,
            "classifiers": classifiers
        }

class DepsDevAPI:
    BASE_URL = "https://api.deps.dev/v3alpha/systems/"

    def get_dependencies(self, package, version):
        """
        Fetch direct dependencies for a specific package and version from deps.dev.
        Returns a list of (dep_name, dep_version) tuples.
        """

        url = f"{self.BASE_URL}pypi/packages/{package}/versions/{version}:dependencies"
        response = requests.get(url)
        
        if response.status_code != 200:
            return []
        
        data = response.json()

        deps = []
        for node in data.get("nodes", []):
            if node.get("relation") == "DIRECT":
                dep_key = node["versionKey"].get("name")
                dep_version = node["versionKey"].get("version")
                if dep_key and dep_version:
                    deps.append((dep_key, dep_version))
        return deps

class OSVAPI:
    BASE_URL = "https://api.osv.dev/v1/query"
    def get_vulnerabilities(self, package, version):
        payload = {"package": {"name": package, "ecosystem": "PyPI"}, "version": version}
        r = requests.post(self.BASE_URL, json=payload)
        if r.status_code != 200:
            return []
        vulns = r.json().get("vulns", [])
        results = []
        for v in vulns:
            refs = [r["url"] for r in v.get("references", []) if r.get("url")]
            fixed_version = (
                v.get("affected", [{}])[0]
                .get("ranges", [{}])[0]
                .get("events", [{}])[-1]
                .get("fixed")
            )
            fixed_versions = [fixed_version] if fixed_version else []
            severity = v.get("severity", [])
            severity_level = "Unknown"
            for s in severity:
                if s.get("type") == "CVSS_V3":
                    try:
                        cvss = CVSS3(s.get("score"))
                        score = cvss.base_score
                        if score >= 9.0:
                            severity_level = "Critical"
                        elif score >= 7.0:
                            severity_level = "High"
                        elif score >= 4.0:
                            severity_level = "Medium"
                        else:
                            severity_level = "Low"
                    except:
                        pass
            results.append({
                "vulnerability_id": v["id"],
                "summary": v.get("summary", ""),
                "affected_components": [package],
                "severity": {
                    "type": "CVSS_V3" if severity else "Unknown",
                    "score": severity[0].get("score") if severity else None,
                    "level": severity_level
                },
                "fixed_versions": fixed_versions,
                "impact": v.get("details", "").split(".")[0],
                "remediation_steps": f"Upgrade to {fixed_versions[0]}" if fixed_versions else "No fix available",
                "references": [{"type": "advisory", "url": url} for url in refs]
            })
        return results
# ===================== Security Scanner =====================
class SecurityMatrix:
    def __init__(self):
        self.deps_api = DepsDevAPI()
        self.osv_api = OSVAPI()
        self.pypi_api = PyPIAPI()  # Added PyPI insights
        # log callback from parent
        self.log_callback = None

    def build_matrix(self, package, version="latest"):
        timestamp = datetime.now().astimezone().isoformat()
        matrix = {
            "vulnerability_insights": {
                "metadata": {"timestamp": timestamp, "package": package, "version": version, "ecosystem": "PyPI",
                            "index_insights": []  # will hold PyPI insights
                            },
                "developer_view": [],
                "tech_leader_view": {"total_vulnerabilities": 0, "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0}}
            }
        }

        # 🔹 PyPI insights for main package
        pypi_insights = self.pypi_api.get_deprecation_eol(package, version)
        matrix["vulnerability_insights"]["metadata"]["index_insights"].append({
            "source": "PyPI",
            "package": package,
            "version": version,
            "deprecated": pypi_insights["deprecated"],
            "yanked": pypi_insights["yanked"],
            "eol": pypi_insights["eol"],
            # "classifiers": pypi_insights["classifiers"]
        })

        # Main package
        vulns = self.osv_api.get_vulnerabilities(package, version)
        matrix["vulnerability_insights"]["developer_view"].extend(vulns)
        # Dependencies
        deps = self.deps_api.get_dependencies(package, version)
        for dep_name, dep_version in deps:
            # PyPI insights for dependency
            dep_pypi_insights = self.pypi_api.get_deprecation_eol(dep_name, dep_version)
            matrix["vulnerability_insights"]["metadata"]["index_insights"].append({
                "source": "PyPI",
                "package": dep_name,
                "version": dep_version,
                "deprecated": dep_pypi_insights["deprecated"],
                "yanked": dep_pypi_insights["yanked"],
                "eol": dep_pypi_insights["eol"],
                # "classifiers": dep_pypi_insights["classifiers"]
            })

            dep_vulns = self.osv_api.get_vulnerabilities(dep_name, dep_version)
            for dv in dep_vulns:
                dv["affected_components"] = [dep_name]
                matrix["vulnerability_insights"]["developer_view"].append(dv)
        # Summary counts
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in matrix["vulnerability_insights"]["developer_view"]:
            lvl = v["severity"]["level"].lower()
            if lvl in severity_counts:
                severity_counts[lvl] += 1
        matrix["vulnerability_insights"]["tech_leader_view"]["total_vulnerabilities"] = len(matrix["vulnerability_insights"]["developer_view"])
        matrix["vulnerability_insights"]["tech_leader_view"]["severity_breakdown"] = severity_counts
        return matrix

    def scan_pkg(self,pkg, version="latest", env_id=None):
        """Scan a single package and save to DB."""
        result = self.build_matrix(pkg, version)
        if env_id:
            DBHelper.save_vulnerability_info(env_id, result)
        return True

    def scan_env(self, env_name, log_callback):

        """Scan all packages in an environment and save results."""
        env_id = DBHelper.get_or_create_env(env_name)
        packages = list_packages(env_name)
        pkg_scan_flag = {pkg: False for pkg in packages}
        for i, (pkg, version) in enumerate(packages):
            log_callback(f"Scanning package {pkg} (version: {version}) in environment {env_name}")
            is_scanned = self.scan_pkg(pkg, version, env_id)
            if is_scanned:
                pkg_scan_flag[pkg] = True
            else:
                log_callback(f"Failed to scan package {pkg} in environment {env_name}")
                continue
        # Check if all packages were scanned
        if all(pkg_scan_flag.values()):
            log_callback(f"All packages in environment '{env_name}' scanned successfully.")
        else:
            log_callback(f"Some packages in environment '{env_name}' failed to scan.")
        return True

# # ===================== Main =====================
if __name__ == "__main__":
    DBHelper.init_db()
    sm = SecurityMatrix()

    # # Example: Scan single package
    # sm.scan_pkg("django", "2.1.0", env_id=DBHelper.get_or_create_env("test_env"))

    # Example: Scan entire environment
    # sm.scan_env("env_update2")


