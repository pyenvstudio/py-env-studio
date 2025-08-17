import os
import json
import sqlite3
import requests
from datetime import datetime
from cvss import CVSS3

# configuration
DB_PATH = "py_env_studio.db"
ENV_PATH = r"C:\Users\Lenovo\/.venvs"  # adjust as needed
JSON_PATH = "py_env_studio_matrix.json"


# ===================== Data Helper =====================

class DataHelper:
    """Operations in JSON file (acts like DBHelper but with JSON)."""

    @staticmethod
    def _load_data():
        """Load JSON data from file (or return default structure)."""
        if not os.path.exists(JSON_PATH):
            return {"environments": [], "env_vulnerability_info": []}

        with open(JSON_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"environments": [], "env_vulnerability_info": []}

    @staticmethod
    def _save_data(data):
        """Save data back to JSON file."""
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # ===================== Environment Methods =====================

    @staticmethod
    def get_or_create_env(env_name, env_path):
        """Return env_id for env_name, create if not exists."""
        data = DataHelper._load_data()

        for env in data["environments"]:
            if env["env_name"] == env_name:
                return env["env_id"]

        # assign new id
        new_id = len(data["environments"]) + 1
        new_env = {
            "env_id": new_id,
            "env_name": env_name,
            "env_path": env_path,
        }
        data["environments"].append(new_env)
        DataHelper._save_data(data)

        return new_id

    # ===================== Vulnerability Methods =====================

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        """Save vulnerabilities for an environment."""
        data = DataHelper._load_data()

        new_vid = len(data["env_vulnerability_info"]) + 1
        record = {
            "vid": new_vid,
            "env_id": env_id,
            "vulnerabilities": vulnerabilities_json,
        }

        data["env_vulnerability_info"].append(record)
        DataHelper._save_data(data)

    @staticmethod
    def get_vulnerability_info(env_id):
        """Retrieve vulnerabilities for a given env_id."""
        data = DataHelper._load_data()

        results = [
            rec for rec in data["env_vulnerability_info"] if rec["env_id"] == env_id
        ]

        return results if results else None

# ===================== Database Helper =====================
class DBHelper:
    @staticmethod
    def init_db():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS environments (
                env_id INTEGER PRIMARY KEY AUTOINCREMENT,
                env_name TEXT UNIQUE,
                env_path TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_vulneribility_info (
                vid INTEGER PRIMARY KEY AUTOINCREMENT,
                env_id INTEGER,
                vulneribilities TEXT,
                FOREIGN KEY (env_id) REFERENCES environments(env_id)
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def get_or_create_env(env_name):
        """Return env_id for env_name, create if not exists."""
        env_path = Helpers.get_env_path(env_name)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT env_id FROM environments WHERE env_name=?", (env_name,))
        row = cur.fetchone()
        if row:
            env_id = row[0]
        else:
            cur.execute("INSERT INTO environments (env_name, env_path) VALUES (?, ?)", (env_name, env_path))
            env_id = cur.lastrowid
            conn.commit()
        conn.close()
        return env_id

    @staticmethod
    def save_vulnerability_info(env_id, vulnerabilities_json):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO env_vulneribility_info (env_id, vulneribilities) VALUES (?, ?)",
            (env_id, json.dumps(vulnerabilities_json))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_vulnerability_info(env_id):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM env_vulneribility_info WHERE env_id=?", (env_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            print(f"Retrieved vulnerability info for env_id {row}")
            return json.loads(row[0])
        return None


# ===================== Helpers =====================
class Helpers:
    @staticmethod
    def get_env_path(env_name):
        return os.path.join(ENV_PATH, env_name)

    @staticmethod
    def list_packages(env_name):
        """List installed packages in a virtual environment."""
        env_path = Helpers.get_env_path(env_name)
        site_packages = os.path.join(env_path, "Lib", "site-packages")
        if not os.path.exists(site_packages):
            return []
        pkgs = []
        for pkg in os.listdir(site_packages):
            if pkg.endswith('.dist-info'):
                pkg_name = pkg.split("-")[0]
                pkgs.append(pkg_name)
        return pkgs
# ===================== API Clients =====================
class DepsDevAPI:
    BASE_URL = "https://deps.dev/_/s/pypi/p/"
    def get_dependencies(self, package, version):
        url = f"{self.BASE_URL}{package}/v/{version}"
        r = requests.get(url)
        if r.status_code != 200:
            return []
        data = r.json()
        deps = []
        for dep in data.get("version", {}).get("dependencies", []):
            dep_key = dep.get("packageKey", {}).get("name")
            dep_version = dep.get("constraint", "latest")
            if dep_key:
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

    def build_matrix(self, package, version="latest"):
        timestamp = datetime.now().astimezone().isoformat()
        matrix = {
            "vulnerability_insights": {
                "metadata": {"timestamp": timestamp, "package": package, "version": version, "ecosystem": "PyPI"},
                "developer_view": [],
                "tech_leader_view": {"total_vulnerabilities": 0, "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0}}
            }
        }
        # Main package
        vulns = self.osv_api.get_vulnerabilities(package, version)
        matrix["vulnerability_insights"]["developer_view"].extend(vulns)
        # Dependencies
        deps = self.deps_api.get_dependencies(package, version)
        for dep_name, dep_version in deps:
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

    def scan_pkg(self, index,pkg, version="latest", env_id=None):
        """Scan a single package and save to DB."""
        result = self.build_matrix(pkg, version)
        if env_id:
            DBHelper.save_vulnerability_info(env_id, result)
        return True

    def scan_env(self, env_name):
        
        """Scan all packages in an environment and save results."""
        env_id = DBHelper.get_or_create_env(env_name)
        packages = Helpers.list_packages(env_name)
        pkg_scan_flag = {pkg: False for pkg in packages}
        for i, pkg in enumerate(packages):
            is_scanned = self.scan_pkg(i,pkg, "latest", env_id)
            if is_scanned:
                pkg_scan_flag[pkg] = True
            else:
                print(f"Failed to scan package {pkg} in environment {env_name}")
                continue
        # Check if all packages were scanned
        if all(pkg_scan_flag.values()):
            print(f"All packages in environment '{env_name}' scanned successfully.")
        else:
            print(f"Some packages in environment '{env_name}' failed to scan.")
        return True

# # ===================== Main =====================
if __name__ == "__main__":
    DBHelper.init_db()
    sm = SecurityMatrix()

    # # Example: Scan single package
    # sm.scan_pkg("django", "2.1.0", env_id=DBHelper.get_or_create_env("test_env"))

    # Example: Scan entire environment
    sm.scan_env("env_update2")


