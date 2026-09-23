# Release / deployment

1. Bump the version in all three places so code, package metadata, and docs agree:

   - `pyproject.toml` → `[project] version`
   - `py_env_studio/config.ini` → `[project] version`
   - `docs/conf.py` → `_project_version` default

2. Add `docs/releases/v<version>.md` and list it in the `Releases` toctree in
   `docs/index.md` (mark the previous note as superseded).

3. Verify locally:

   ```bash
   pytest
   python -m sphinx -b html docs docs/_build/html
   ```

4. Commit, tag, and push. `publish.yml` re-derives the version from the tag,
   builds the distribution, publishes to PyPI, and creates the GitHub release:

   ```bash
   git tag v2.1.0
   git push origin main
   git push origin v2.1.0
   ```

5. Read the Docs rebuilds `latest` from `main` automatically
   (`.readthedocs.yaml` + `docs/conf.py`); no manual documentation deploy step
   is required.

