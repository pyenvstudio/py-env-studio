# Community Templates

Community Templates lets you discover public Python project repositories from GitHub and import a selected repository as a reusable Py Env Studio template.

Community repositories are untrusted third-party sources. A result's star count, activity, or license is metadata only; it does not mean Py Env Studio has verified the repository, its security, or its production readiness.

## Discover a template

1. Open **Templates -> Community Templates**.
2. Enter an optional search term such as `FastAPI`, `Django`, `CLI`, or `Machine Learning`.
3. Select a category and sort order, then choose **Search**.
4. Review the candidate's repository name, description, stars, update date, language, license, and topics.
5. Use **Load More** to retrieve another page of results.

GitHub search returns candidate repositories, not pre-validated PES templates. Community Templates prioritizes Python repositories and uses GitHub topics when a category is selected.

## Preview safely

Select **Preview** before importing. Py Env Studio downloads a temporary clone only at this point and performs static inspection. The preview can show:

- README excerpt and project structure
- Python project markers such as `pyproject.toml`, `setup.py`, and `setup.cfg`
- Dependency and tooling files such as `requirements.txt`, `tox.ini`, and `Dockerfile`
- Test directories, environment files, and GitHub workflows
- Sensitive files that will be excluded from import

Py Env Studio does not execute repository code, install dependencies, run build hooks, invoke Docker, run workflows, or create an environment during discovery, preview, or import.

## Import and use

1. From a preview, select **Import as Template**.
2. Choose a custom template name and ID. The repository name is only a suggested default.
3. Review the import preview and save the template.
4. Select **Use Template** from Community Templates or **My Templates** to open the existing project creation wizard.

Imported templates use the same storage, registry, rendering engine, configuration defaults, environment creation, package manager, and editor-opening workflow as other user templates.

If the same repository has already been imported, Py Env Studio offers to use the existing template, import a separately named copy, or cancel. Imported templates continue to work offline.

## Network and privacy

Community Templates uses GitHub's public repository-search API without requiring GitHub sign-in. Search results are cached in memory briefly to avoid unnecessary requests. Network failures, invalid API responses, unavailable repositories, and GitHub rate limits are shown in the dialog without affecting built-in or previously imported templates.

Py Env Studio does not store GitHub credentials or access tokens for this feature. Source provenance is retained with the imported template as its GitHub repository URL.
