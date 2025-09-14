import requests
import json

class DepsDevAPI:
    BASE_URL = "https://deps.dev/_/s/pypi/p/"

    def get_dependencies(self, package):
        """Fetch direct dependencies of a package from deps.dev"""
        url = f"{self.BASE_URL}{package}"
        response = requests.get(url)
        if response.status_code != 200:
            return []
        data = response.json()
        deps = set()
        for version in data.get("versions", []):
            for dep in version.get("dependencies", []):
                deps.add(dep.get("packageKey", {}).get("name"))
        return list(deps)


class OSVAPI:
    BASE_URL = "https://api.osv.dev/v1/query"

    def get_vulnerabilities(self, package, version):
        """Fetch vulnerabilities for a package/version from OSV.dev"""
        payload = {"package": {"name": package, "ecosystem": "PyPI"}, "version": version}
        response = requests.post(self.BASE_URL, json=payload)
        if response.status_code != 200:
            return []
        vulns = response.json().get("vulns", [])
        results = []
        for v in vulns:
            refs = [r["url"] for r in v.get("references", []) if r.get("url")]
            results.append({
                "id": v["id"],
                "summary": v.get("summary", ""),
                "fixed": v.get("affected", [{}])[0]
                         .get("ranges", [{}])[0]
                         .get("events", [{}])[-1]
                         .get("fixed"),
                "articles": refs  # Official articles and advisories
            })
        return results


class HackerNewsAPI:
    BASE_URL = "https://hn.algolia.com/api/v1/search"

    def get_discussions(self, query):
        """Fetch top Hacker News discussions for a given query"""
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
        self.hn_api = HackerNewsAPI()

    def build_matrix(self, package, version="latest"):
        """Build security matrix for a package and its dependencies"""
        matrix = []

        def package_info(pkg, ver):
            vulns = self.osv_api.get_vulnerabilities(pkg, ver)
            for v in vulns:
                v["discussions"] = self.hn_api.get_discussions(f"{pkg} {v['id']}")
            return {"package": pkg, "version": ver, "vulnerabilities": vulns}

        # Main package
        matrix.append(package_info(package, version))

        # Dependencies
        for dep in self.deps_api.get_dependencies(package):
            matrix.append(package_info(dep, "latest"))

        return matrix


# if __name__ == "__main__":
#     sm = SecurityMatrix()
#     result = sm.build_matrix("django", "3.2.15")
#     print(json.dumps(result, indent=2))
