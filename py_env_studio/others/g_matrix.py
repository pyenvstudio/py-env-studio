
import requests
import json,os
from datetime import datetime
from cvss import CVSS3  # Requires `pip install cvss` for parsing CVSS vectors
ENV_PATH = r"C:\Users\Lenovo\.venvs\env_update2"

class Helpers:
    @staticmethod
    def get_env_path(env_name):
        """Get the full path to the virtual environment directory."""
        return f"{ENV_PATH}/{env_name}"

    @staticmethod
    def list_packages(env_name):
        """List installed packages in a virtual environment."""
        env_path = Helpers.get_env_path(env_name)
        if not os.path.exists(env_path):
            return []
        site_packages = os.path.join(env_path, "Lib", "site-packages")
        if not os.path.exists(site_packages):
            return []
        return [pkg for pkg in os.listdir(site_packages) if pkg.endswith('.dist-info')]
    

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
        """
        Fetch vulnerabilities for a package/version from OSV.dev.
        Returns a list of vulnerability dictionaries with enhanced details.
        """
        payload = {"package": {"name": package, "ecosystem": "PyPI"}, "version": version}
        response = requests.post(self.BASE_URL, json=payload)
        if response.status_code != 200:
            return []
        vulns = response.json().get("vulns", [])
        results = []
        for v in vulns:
            refs = [r["url"] for r in v.get("references", []) if r.get("url")]
            # Use the provided logic to get the fixed version
            fixed_version = (
                v.get("affected", [{}])[0]
                .get("ranges", [{}])[0]
                .get("events", [{}])[-1]
                .get("fixed")
            )
            fixed_versions = [fixed_version] if fixed_version else []

            severity = v.get("severity", [])
            severity_level = "Unknown"
            cvss_score = None
            for s in severity:
                if s.get("type") == "CVSS_V3":
                    try:
                        cvss = CVSS3(s.get("score"))
                        cvss_score = cvss.base_score
                        if cvss_score >= 9.0:
                            severity_level = "Critical"
                        elif cvss_score >= 7.0:
                            severity_level = "High"
                        elif cvss_score >= 4.0:
                            severity_level = "Medium"
                        else:
                            severity_level = "Low"
                    except:
                        pass
            results.append({
                "vulnerability_id": v["id"],
                "summary": v.get("summary", ""),
                "affected_components": [package],  # Placeholder, could be enhanced
                "severity": {
                    "type": "CVSS_V3" if severity else "Unknown",
                    "score": s.get("score") if severity else None,
                    "level": severity_level
                },
                "fixed_versions": fixed_versions,
                "impact": v.get("details", "").split(".")[0],  # First sentence as impact
                "remediation_steps": f"Upgrade to {fixed_versions[0]}" if fixed_versions else "No fix available",
                "references": [{"type": "advisory", "url": url} for url in refs],
                "reproduction_steps": "Not provided"  # Placeholder, requires manual input
            })
        return results

class NVDAPI:
    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def get_severity(self, cve_id):
        """
        Fetch severity details for a CVE from NVD.
        Returns CVSS v3 score and level if available.
        """
        url = f"{self.BASE_URL}?cveId={cve_id}"
        response = requests.get(url)
        if response.status_code != 200:
            return None, "Unknown"
        data = response.json()
        try:
            metrics = data["vulnerabilities"][0]["cve"]["metrics"]["cvssMetricV31"][0]["cvssData"]
            score = metrics["baseScore"]
            level = "Critical" if score >= 9.0 else "High" if score >= 7.0 else "Medium" if score >= 4.0 else "Low"
            return score, level
        except (KeyError, IndexError):
            return None, "Unknown"

class HackerNewsAPI:
    BASE_URL = "https://hn.algolia.com/api/v1/search"

    def get_discussions(self, query):
        """
        Fetch top Hacker News discussions for a given query.
        Returns a list of discussion dictionaries with title and URL.
        """
        url = f"{self.BASE_URL}?query={query}"
        response = requests.get(url)
        if response.status_code != 200:
            return []
        hits = response.json().get("hits", [])
        return [{"title": h.get("title"), "url": h.get("url")} for h in hits[:3]]

class SecurityMatrix:
    def __init__(self):
        self.deps_api = DepsDevAPI()
        self.osv_api = OSVAPI()
        self.nvd_api = NVDAPI()
        self.hn_api = HackerNewsAPI()
        self.pypi_api = PyPIAPI()  # Added PyPI insights

    def build_matrix(self, package, version="latest"):
        """
        Build security matrix for a package and its dependencies.
        Returns JSON in the specified format.
        """
        timestamp = datetime.now().astimezone().isoformat()
        matrix = {
            "vulnerability_insights": {
                "metadata": {
                    "timestamp": timestamp,
                    "package": package,
                    "version": version,
                    "ecosystem": "PyPI",
                    "index_insights": []  # will hold PyPI insights
                },
                "developer_view": [],
                "tech_leader_view": {
                    "total_vulnerabilities": 0,
                    "severity_breakdown": {
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    },
                    "trend_data": [],  # Placeholder, requires historical data
                    "fix_status": {
                        "open": 0,
                        "in_progress": 0,
                        "fixed": 0
                    },
                    "mean_time_to_remediate": 0.0,
                    "vulnerability_density": 0.0
                },
                "enterprise_view": {
                    "centralized_management": {
                        "tool": "Not specified",
                        "integration_status": "Not integrated",
                        "last_scan": timestamp
                    },
                    "compliance": [
                        {
                            "standard": "GDPR",
                            "status": "Not assessed",
                            "last_audit": "Unknown",
                            "documentation": "Not provided"
                        },
                        {
                            "standard": "PCI DSS",
                            "status": "Not assessed",
                            "last_audit": "Unknown",
                            "documentation": "Not provided"
                        }
                    ],
                    "training": {
                        "last_session": "Unknown",
                        "coverage": "0%",
                        "next_scheduled": "Unknown"
                    },
                    "incident_response": {
                        "plan_status": "Not defined",
                        "last_tested": "Unknown",
                        "stakeholder_communication": "Not established"
                    }
                }
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
            "classifiers": pypi_insights["classifiers"]
        })

        # 🔹 Main package vulnerabilities
        vulns = self.osv_api.get_vulnerabilities(package, version)
        for vuln in vulns:
            vuln["discussions"] = self.hn_api.get_discussions(f"{package} {vuln['vulnerability_id']}")
            if vuln["vulnerability_id"].startswith("CVE-"):
                nvd_score, nvd_level = self.nvd_api.get_severity(vuln["vulnerability_id"])
                if nvd_score and (not vuln["severity"]["score"] or nvd_level != vuln["severity"]["level"]):
                    vuln["severity"] = {
                        "type": "CVSS_V3",
                        "score": f"CVSS:3.1/{nvd_score}",
                        "level": nvd_level
                    }
            matrix["vulnerability_insights"]["developer_view"].append(vuln)

        # 🔹 Dependencies
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
                "classifiers": dep_pypi_insights["classifiers"]
            })

            # Vulnerabilities for dependency
            dep_vulns = self.osv_api.get_vulnerabilities(dep_name, dep_version)
            for vuln in dep_vulns:
                vuln["discussions"] = self.hn_api.get_discussions(f"{dep_name} {vuln['vulnerability_id']}")
                if vuln["vulnerability_id"].startswith("CVE-"):
                    nvd_score, nvd_level = self.nvd_api.get_severity(vuln["vulnerability_id"])
                    if nvd_score and (not vuln["severity"]["score"] or nvd_level != vuln["severity"]["level"]):
                        vuln["severity"] = {
                            "type": "CVSS_V3",
                            "score": f"CVSS:3.1/{nvd_score}",
                            "level": nvd_level
                        }
                vuln["affected_components"] = [dep_name]
                matrix["vulnerability_insights"]["developer_view"].append(vuln)

        # 🔹 Update tech_leader_view
        total_vulns = len(matrix["vulnerability_insights"]["developer_view"])
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in matrix["vulnerability_insights"]["developer_view"]:
            level = vuln["severity"]["level"].lower()
            if level in severity_counts:
                severity_counts[level] += 1
        matrix["vulnerability_insights"]["tech_leader_view"]["total_vulnerabilities"] = total_vulns
        matrix["vulnerability_insights"]["tech_leader_view"]["severity_breakdown"] = severity_counts
        matrix["vulnerability_insights"]["tech_leader_view"]["fix_status"]["open"] = total_vulns  # Simplified
        matrix["vulnerability_insights"]["tech_leader_view"]["trend_data"] = [
            {"timestamp": timestamp, "total_vulnerabilities": total_vulns, "fixed_vulnerabilities": 0}
        ]

        return matrix


# Example usage
if __name__ == "__main__":
    sm = SecurityMatrix()
    result = sm.build_matrix("tensorflow", "2.6.0")
    # print(json.dumps(result, indent=2))
    # export to JSON file
    with open("g_matricx_security_matrix.json", "w") as f:
        json.dump(result, f, indent=2)