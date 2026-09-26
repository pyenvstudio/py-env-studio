# 🤝 Contributing

We welcome contributions!  

- Fork the repo
- Open an issue / discussion
- Submit pull requests

Join our [Telegram Community](https://t.me/pyenvstudio) for collaboration.

---

## Development setup

```bash
git clone https://github.com/pyenvstudio/py-env-studio.git
cd py-env-studio

python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

Python **3.12+** is required. `pip install -e ".[dev]"` installs the package in
editable mode together with `pytest`, `black`, and `isort`.

## Running the test suite

```bash
pytest                      # full suite
pytest tests/test_mcp_server.py -q   # one module
python tests/run_all_tests.py        # the repository test runner
```

Tests must be deterministic and must not require network access or a display.
Add tests for success, failure, and edge cases with every behavioural change.
GUI-only modules (Tkinter/CustomTkinter) are skipped automatically in headless
environments.

## Code style

```bash
black py_env_studio tests
isort py_env_studio tests
```

Keep GUI concerns in `py_env_studio/ui`, business logic in
`py_env_studio/core`, and shared helpers in `py_env_studio/utils`. Reuse the
existing environment, package, configuration, logging, and template services
rather than adding parallel implementations, and record user-visible changes in
`.github/agent-context/feature-ledger.md`.

---

## Building the documentation locally

The documentation site is built from the Markdown files in `docs/` with
**Sphinx** and **MyST-Parser**, and published by Read the Docs using
`.readthedocs.yaml` (`docs/conf.py` is the Sphinx configuration).

1. Install the documentation dependencies (once):

   ```bash
   pip install -r docs/requirements.txt
   ```

   This installs `sphinx`, the `furo` theme, and `myst-parser`.

2. Build the HTML site into `docs/_build/html`:

   ```bash
   sphinx-build -b html docs docs/_build/html
   ```

3. Preview it by opening `docs/_build/html/index.html`, or serve it while you
   edit (the `sphinx-autobuild` package is not installed by
   `docs/requirements.txt`; add it to your environment first):

   ```bash
   pip install sphinx-autobuild
   sphinx-autobuild docs docs/_build/html
   ```

4. Fix every warning the build prints - broken `{toctree}` entries, missing
   cross-references, and bad code fences are treated as defects.

Notes for writing docs:

- Add every new page to a `{toctree}` block in `docs/index.md`, otherwise it is
  not published.
- Internal links use relative Markdown paths such as `../reference/mcp.md`;
  Sphinx resolves them into the built pages.
- Feature behaviour belongs in `docs/reference/current-implementation.md`, page
  structure in `docs/reference/architecture.md`, and user-facing steps in
  `docs/getting-started/`.
- Read the Docs builds `latest` from `main`; no extra step is required after a
  merge.

---

## Release checklist

1. Update the version in all three places so the installed package, fallback
    package config, and docs agree:
   - `pyproject.toml` → `[project] version`
    - `py_env_studio/config.ini` → `[project] version` (fallback for source-tree
       runs without installed distribution metadata, and used by the MCP handshake)
   - `docs/conf.py` → the `_project_version` default
2. Add `docs/releases/v<version>.md` and link it from the `Releases` toctree in
   `docs/index.md`; mark the previous release as superseded.
3. Update `.github/agent-context/feature-ledger.md`, the GitHub `README.md`
   highlights, and `PYPI_README.md` — the separate PyPI description
   (`pyproject.toml` maps it via `readme = "PYPI_README.md"`).
4. Run the full test suite and the documentation build from above.
5. Tag and push the release. The `publish.yml` workflow runs on any `v*` tag:
   it re-derives `pyproject.toml`/`config.ini` versions from the tag, verifies
   `PYPI_README.md` exists and is the configured project readme, builds the
   package, confirms the built wheel description and sdist contents match
   `PYPI_README.md`, publishes to PyPI, and creates the GitHub release with
   generated notes:

   ```bash
   git tag v2.1.0
   git push origin v2.1.0
   ```

