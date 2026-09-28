# Py Env Studio — Test Suite Audit Report

| Field | Value |
|---|---|
| Document ID | PES-TEST-AUDIT-2026-09-20 |
| Report version | 1.1.0 (v1.0.0 baseline audit → v1.1.0 after resolving the two RED cases) |
| Report date | 2026-09-20 |
| Repository | `pyenvstudio/py-env-studio` |
| Revision audited | `8d11de4` (`main`, "window icon fix") **plus uncommitted working-tree changes** |
| Product version | 2.1.2 |
| Platform audited | Windows (Python 3.13.7, pytest 9.1.1, customtkinter 5.2.2, tkinter-dash 0.1.5) |
| Companion document | `tests/TEST_CASES.md` (339-case catalog, IDs `TC-<AREA>-<nnn>`) |
| Audit type | Static + dynamic test-suite assessment |
| Remediation status | **F-02 resolved** (2 failing tests fixed). F-01, F-03…F-14 remain open by design. No production code was modified. |

---

## 1. Executive summary

| # | Item | Result |
|---|---|---|
| 1 | Pytest-collected tests at baseline | **80** (19 files in `tests/`) |
| 2 | Baseline run result | **79 passed, 1 skipped, 1 warning in 18.44 s** (exit code 0) — was `2 failed, 77 passed, 1 skipped` before the F-02 fix |
| 3 | Catalog cases defined | 339 — COVERED **39**, PARTIAL 10, MANUAL 12, RED **0**, GAP 272 |
| 4 | Automated coverage of cataloged acceptance criteria | **≈14 %** (49/339 fully or partially covered: 39 COVERED + 10 PARTIAL) |
| 5 | Files under `tests/` tracked in git | **0 of 19** — `tests/` is ignored by `.gitignore:218` |
| 6 | CI jobs that execute tests | **0** — the only workflow is `.github/workflows/publish.yml` (tag → PyPI publish) |
| 7 | Collected tests that assert nothing | **12** (`tests/test_all_features.py`, 0 `assert` statements) |
| 8 | Assertion-bearing checks that pytest never runs | **60** (`tests/test_window_icon.py` 26, `test_vulnerability_insights_update.py` 34) |

**Bottom line.** The repository has a small, partly high-quality pytest suite (templates, configuration,
dependency preview, insights charts, project openers) but the release gate is effectively absent: the suite
is untracked by git, never executed by CI, and the most safety-critical modules
(environment creation, pip/uv execution, auto-resolve, vulnerability scanning, CLI, plugins,
database) have **no automated tests at all**. Two "always green" mechanisms (`test_all_features.py` and
`run_all_tests.py`) create a false impression of comprehensive coverage.

The suite is now **green** (F-02 resolved in v1.1.0 by realigning `tests/test_project_runtime.py` with the
production `runtime_toggle` API). All other findings (F-01, F-03…F-14) remain open by design — the remediation
backlog in §7 lists them in recommended order, and `TEST_CASES.md` holds the 339-case inventory needed to close
the coverage gap.

---

## 2. Scope and method

**In scope**

- The whole `tests/` directory, the test runner, and the pytest configuration story.
- Coverage mapping of every feature documented in `docs/reference/features.md`, `docs/getting-started/cli.md`,
  `README.md` and `.github/agent-context/feature-ledger.md` against the existing tests.
- Determinism, isolation, security and negative-path testing practices.
- Actual execution evidence on Windows/Python 3.13.7.

**Out of scope**

- Fixing defects or writing the missing tests (explicitly deferred by the request).
- macOS/Linux runtime verification and frozen (PyInstaller) build verification.
- Live-network validation of PyPI / deps.dev / OSV / GitHub behaviour.

**Method**

1. Inventoried the repository (`git ls-files`, tree walk, `.gitignore` inspection).
2. Enumerated the public API surface from `api_inventory.txt` and the core/utils/UI modules.
3. Read every test file and classified it as pytest-style, unittest-style, or script-style.
4. Ran the suite twice with pytest (collection + execution) and captured exact output.
5. Cross-checked test targets against the real API (`search_codebase` for `initialize_project_runtime` etc.).
6. Derived the 339-case catalog in `tests/TEST_CASES.md` and mapped each area to a COVERED/PARTIAL/MANUAL/RED/GAP status.

## 3. Baseline execution evidence

### 3.1 Commands executed

```text
python -m pytest tests --collect-only -q
python -m pytest tests -q --no-header -rf
python -m pytest --version
python --version
git --no-pager log --oneline -5
git --no-pager ls-files tests
git check-ignore -v tests/test_configuration_service.py
```

### 3.2 Measured result

**v1.0.0 baseline (before the fix, executed 2026-09-20, Windows, Python 3.13.7)**

```text
tests/test_project_runtime.py::test_initialize_project_runtime_creates_and_reuses_env  FAILED
tests/test_project_runtime.py::test_disable_project_runtime_turns_banner_off           FAILED
tests/test_all_features.py:46  PytestCollectionWarning: cannot collect test class 'TestResult'
                               because it has a __init__ constructor
2 failed, 77 passed, 1 skipped, 1 warning in 23.09s
```

**v1.1.0 after resolving F-02 (same platform, re-run 2026-09-20)**

```text
tests/test_project_runtime.py::test_init_project_creates_environment_once_and_reuses_it           PASSED
tests/test_project_runtime.py::test_disable_runtime_turns_runtime_off_and_keeps_environment       PASSED
79 passed, 1 skipped, 1 warning in 18.44s
```

Collected total: **80 tests** (see §4 for per-file detail). Skipped: `TestIntegration::test_preview_install_requests`
(`@unittest.skip("Requires actual environment")` in `tests/test_dependency_preview.py:228`). The remaining warning
is the pre-existing `PytestCollectionWarning` for the non-asserting `TestResult` helper class (F-04).

### 3.3 Failure evidence (F-02 — historical, resolved in v1.1.0)

```text
E   AttributeError: module 'py_env_studio.core.env_manager' has no attribute 'initialize_project_runtime'
    tests/test_project_runtime.py:26   (test_initialize_project_runtime_creates_and_reuses_env)
E   AttributeError: module 'py_env_studio.core.env_manager' has no attribute 'initialize_project_runtime'
    tests/test_project_runtime.py:52   (test_disable_project_runtime_turns_banner_off)
```

`initialize_project_runtime`, `disable_project_runtime` and `load_project_runtime_state` exist **only** in
`tests/test_project_runtime.py`; the production API lives in `py_env_studio/core/runtime_toggle.py`
(`init_project`, `enable_runtime`, `disable_runtime`, `is_runtime_enabled`). The tests were stale relative to the
implementation and had been failing before this audit — `.pytest_cache/v/cache/lastfailed` already recorded
exactly these two node IDs.

**Resolution:** the stale tests were replaced (not merely deleted) by two tests against the production API —
`test_init_project_creates_environment_once_and_reuses_it` and
`test_disable_runtime_turns_runtime_off_and_keeps_environment` — which assert create-once/reuse, `pes.config`
creation, registry registration and the enable/disable round trip while keeping the managed environment intact.
Virtual-environment creation is stubbed and runtime paths are redirected into `tmp_path`, so the two tests run in
**0.24 s** and write nothing outside the temporary directory. The unused `import types` was removed at the same time.

The same test module imports `types` (line 2) and never uses it — a small sign of drift.

### 3.4 Working-tree state at audit time

```text
 M .github/agent-context/feature-ledger.md
 M py_env_studio/requirements.txt
 M py_env_studio/utils/vulneribility_insights.py
 M pyproject.toml
?? api_inventory.txt
```

The `matplotlib → tkinter-dash` migration is present in the working tree (`pyproject.toml`, `requirements.txt`,
`vulneribility_insights.py`, feature ledger) but is **not committed**, and the generated
`py_env_studio.egg-info/requires.txt` still lists `matplotlib>=3.10.5`. This audit therefore describes the
**working tree**, not a reproducible revision; see F-11.

## 4. Automated test inventory

| File | Style | Collected by pytest | Assertions | Notes |
|---|---|---|---|---|
| `test_all_features.py` | script-style functions | 12 | **0** | 100 `results.add_*` calls, 41 `except Exception` blocks; recorded failures only print — tests cannot fail. Performs real network scans/env lookups. |
| `test_community_templates.py` | pytest | 4 | 16 | Good pattern: fake session, static-inspection checks, cleanup check. |
| `test_configuration_service.py` | pytest | 4 | 11 | Uses `tmp_path` + `monkeypatch`; no real user config touched. |
| `test_dependency_preview.py` | unittest | 22 (1 skipped) | unittest assertions | Integration case permanently skipped ("Requires actual environment"). |
| `test_github_template_import.py` | pytest | 6 | 6 | `tmp_path` + `monkeypatch`; git/subprocess mocked. |
| `test_plugin_events.py` | script (module-level) | 0 | 0 | Prints only; depends on `~/.py_env_studio/plugins/sample_plugin`. |
| `test_plugin_import.py` | script (module-level) | 0 | 0 | Prints only; inserts the real plugin dir on `sys.path`. |
| `test_plugin_load.py` | script (module-level) | 0 | 0 | Prints only; loads the developer's real plugin. |
| `test_project_openers.py` | pytest | 5 | 7 | Mocks `Popen`; no shell usage asserted. |
| `test_project_runtime.py` | pytest | 2 | 16 | Green in v1.1.0 — realigned to the production `runtime_toggle` API (F-02). Stubs venv creation; paths redirected to `tmp_path`; runs in 0.24 s. |
| `test_template_engine.py` | pytest | 8 | 12 | Strong: placeholders, overwrite refusal, venv/dependency integration. |
| `test_template_registry.py` | pytest | 4 | 8 | Resets the module-level default registry; no leak detected. |
| `test_template_workflow.py` | pytest | 2 | 4 | SUCCESS/FAILED workflow states. |
| `test_user_template_store.py` | pytest | 4 | 10 | Save/load/delete, reserved ids, `.git`/`.env` handling. |
| `test_uv_packages.py` | script (module-level) | 0 | 0 | Prints only; requires a real uv-created environment. |
| `test_vulnerability_insights_charts.py` | pytest (+GUI) | 7 | 30 | Opens a real Tk root; skips automatically when no display is available. |
| `test_vulnerability_insights_update.py` | script (module-level) | 0 | 34 `check()` calls | Manual only; remediation/report-button checks never run in the suite. |
| `test_window_icon.py` | script (module-level) | 0 | 26 `check()` calls | Manual only; depends on the real UI + Windows icon API. |
| `run_all_tests.py` | runner | n/a | n/a | Executes each `test_*.py` as a script and trusts the exit code → false PASS (F-08). |
| `tests/setup/{state.py, db.py, test_window.py}` | helper copies | 0 (no test functions) | 0 | Duplicates production `setup_state`/`database` logic with no assertions (F-10); `test_window.py` builds a Tk wizard UI. |
| `tests/myproject/pes`, `tests/test-app/**` | artifacts | — | — | Generated project/CLI scratch data, incl. 4-level nested `tmp-cli-check` directories (F-13). |

**Totals:** 80 collected tests; 60 assertion-bearing manual checks never executed by pytest; 4 test files with
no assertions of any kind.

## 5. Coverage matrix (catalog areas → source → status)

| Area (catalog prefix) | Primary source modules | Existing tests | Coverage | Risk |
|---|---|---|---|---|
| Environment lifecycle (ENV) | `core/env_manager.py` | none (the green `test_project_runtime.py` covers `core/runtime_toggle.py` — project runtime toggle/registry — not env create/rename/delete) | ❌ 0 % | **High** — create/rename/delete can lose data |
| pip ops (PIP) | `core/pip_tools.py` | none | ❌ 0 % | **High** — process execution, argv safety |
| uv ops (UV) | `core/uv_tools.py` | `test_uv_packages.py` (script, unasserted) | ❌ ~0 % | High |
| Manager routing/fallback (PMGR) | `core/package_manager.py` | none | ❌ 0 % | **High** — silent fallback behaviour |
| AutoResolver (AR) | `core/auto_resolve.py` | none | ❌ 0 % | **High** — relaxes version pinning |
| Dependency preview (DP) | `core/dependency_preview.py` | `test_dependency_preview.py` | 🟡 ~50 % | Medium — preview path partially asserted |
| Scanning (SEC) | `utils/vulneribility_scanner.py` | none (script-only checks inside `test_all_features.py`) | ❌ ~0 % | **High** — core security claim |
| Status tracking (ST) | `utils/db_status.py`, `utils/version_utils.py` | none | ❌ 0 % | **High** — fixed/open status drives remediation |
| Insights dashboard (DASH) | `utils/vulneribility_insights.py` | `test_vulnerability_insights_charts.py`; manual `_update` script | 🟡 ~40 % | Medium — remediation actions manual-only |
| Templates (TPL) | `core/templates/{engine,registry,validator,models,workflow}.py` | `test_template_engine/registry/workflow` | 🟢 ~65 % | Medium — validator security cases missing |
| User templates/filters (TPLU) | `core/templates/user_template_store.py`, `content_filters.py` | `test_user_template_store.py` | 🟡 ~45 % | Medium-High — sensitive-file coverage thin |
| GitHub/community (TPLG) | `core/templates/github_import.py`, `community.py` | `test_github_template_import.py`, `test_community_templates.py` | 🟡 ~55 % | Medium — URL hardening, temp cleanup |
| Runtime + registry (RT) | `core/runtime_toggle.py` | `test_project_runtime.py` (2 green tests, realigned v1.1.0) | 🟡 ~25 % | **High** — `pes run` / interceptor / registry listing still untested |
| CLI (CLI) | `commands.py`, `__main__.py` | none | ❌ 0 % | **High** — power-user entry point |
| Configuration (CFG) | `core/configuration.py`, `core/runtime.py` | `test_configuration_service.py` | 🟢 ~55 % | Medium |
| Plugins (PLG) | `core/plugins/*` | `test_plugin_import/load/events.py` (unasserted scripts) | ❌ ~5 % | **High** — loads third-party code |
| Database (DB) | `core/database.py`, `utils/handlers.py` | none | ❌ 0 % | **High** — migration/persistence |
| Py-Tonic (LRN) | `core/py_tonic.py` | script-only checks | ❌ ~5 % | Low-Medium |
| Setup/bootstrap (STA) | `core/setup_state.py`, `core/bootstrap.py`, `core/windows_apps.py` | `tests/setup/*` (duplicate code, unasserted) | ❌ ~0 % | **High** — install/repair lifecycle |
| GUI (UI) | `ui/main_window.py` | none (script-style icon checks only) | ❌ ~2 % | Medium — manual acceptance required |
| Utilities (UTIL) | `utils/app_icon.py`, `core/{strategies,integration,project_launcher,tools}.py` | `test_project_openers.py`, manual icon script | 🟡 ~35 % | Medium |
| NFR/security guards (NFR) | repository-wide | none | ❌ 0 % | **High** — no shell/secrets/determinism guards |

Legend: 🟢 good · 🟡 partial · ❌ none · 🔴 red.

## 6. Findings

Severity: **Critical** (release blocker) · **High** · **Medium** · **Low**.
No finding below has been fixed; each lists the evidence and the recommendation for a follow-up task.

### F-01 — Critical — The entire test suite is untracked (`tests/` is git-ignored)

**Evidence**

- `.gitignore:215-220`:
  ```text
  changelogs/
  notes/
  prompts/
  tests/
  !.github/agent-context/
  !.github/agent-context/**
  ```
- `git ls-files tests` → **0 files**.
- `git check-ignore -v tests/test_configuration_service.py` → `.gitignore:218:tests/	tests/test_configuration_service.py`.
- `git status --porcelain --untracked-files=all tests` → empty (the directory is ignored, so nothing is reported either).

**Impact**

19 Python files (2 888 lines at the `tests/` top level, plus 429 lines under `tests/setup/`, incl. the only
automated coverage of templates, configuration, dependency preview and insights charts) exist **only on this
machine**. A fresh clone has no tests, contributors cannot see them,
and CI can never run them. The two previously failing tests are now green (F-02, resolved in v1.1.0), but the
loses the suite permanently. This also means the repository's own contribution rules (`.github/copilot-instructions.md`
"Add deterministic tests…") cannot be satisfied from a clean clone.

**Recommendation (not applied)**

Narrow the ignore rule to the intended agent scratch directories (e.g. ignore `.github/agent-context/*/tests/`
or rename the scratch folder) and commit the suite, adding `tests/**` explicitly if needed. Afterwards the
baseline becomes reproducible and CI can gate releases.

### F-02 — High — The suite was red on the audited revision — **RESOLVED in v1.1.0**

**Evidence (historical, v1.0.0 baseline)**

- `python -m pytest tests -q --no-header -rf` → `2 failed, 77 passed, 1 skipped, 1 warning in 23.09s` (exit code 1).
- `tests/test_project_runtime.py:26` and `:52` called `env_manager.initialize_project_runtime`, which does not exist;
  `.pytest_cache/v/cache/lastfailed` already recorded both node IDs before this audit.

**Impact (historical)**

There was no green baseline, so any regression introduced by future work would have been indistinguishable from
the known failures. The runtime/project feature appeared tested but was in fact unverified (catalog
`TC-RT-016`, `TC-RT-017` were marked **RED**).

**Resolution (applied 2026-09-20, v1.1.0)**

`tests/test_project_runtime.py` was realigned from the non-existent `env_manager.*` runtime helpers to the
production API in `core/runtime_toggle.py`. The two stale functions were **replaced, not deleted**, keeping the
original intent and asserting more than before:

| Old (failing) test | New (green) test | Asserts |
|---|---|---|
| `test_initialize_project_runtime_creates_and_reuses_env` | `test_init_project_creates_environment_once_and_reuses_it` | `init_project` succeeds twice; managed environment created exactly once; stable environment id; `pes.config` written; runtime enabled; registry records the environment id |
| `test_disable_project_runtime_turns_banner_off` | `test_disable_runtime_turns_runtime_off_and_keeps_environment` | `disable_runtime` succeeds; runtime flag `False` in `pes.config` **and** registry; environment id preserved; managed environment **not** deleted; `enable_runtime` turns it back on |

Verification (measured): `python -m pytest tests/test_project_runtime.py -v` → **2 passed in 0.24 s**;
`python -m pytest tests -q` → **79 passed, 1 skipped, 1 warning in 18.44 s**.

Design constraints honored (no over-engineering): no production code changed, no new test file added, one
module of 89 lines, virtual-environment creation stubbed, runtime paths redirected to `tmp_path` so the tests
are deterministic and write nothing outside the temporary directory. Catalog counts updated: RED 2 → **0**,
COVERED 37 → 39 (TC-RT-016, TC-RT-017 now covered). TC-RT-003 and TC-RT-005 were already COVERED before this
fix; TC-RT-002 was already PARTIAL before this fix; their status annotations flag "v1.1.0" because the
replaced tests assert slightly more than the originals, but the net PARTIAL count did not change (10).

**Still open from the original recommendation:** the remaining RT cases (`TC-RT-001`, `TC-RT-004`,
`TC-RT-006`…`TC-RT-015` — `pes run` execution, interceptor, registry listing, corruption handling) are still
GAP and are tracked in the backlog as R-06.

### F-03 — High — No CI job ever executes the tests

**Evidence**

- `.github/workflows/publish.yml` is the only workflow: it triggers on `v*` tags and runs
  `sed`-version-bump → `python -m build` → GitHub Release → PyPI publish. There is no install step for the
  project, no `pytest` invocation, and no test job.
- No `pytest` configuration exists: no `[tool.pytest.ini_options]` in `pyproject.toml`, no `pytest.ini`,
  `setup.cfg` or `tox.ini`, and no `conftest.py` anywhere in the repository.

**Impact**

A release can be published from a revision whose suite is red (as it is today). Test results are invisible to
maintainers and contributors, and the "Publish to PyPI" job is the de-facto quality gate — it has none.

**Recommendation**

Add a `test` job (matrix: Windows + Ubuntu, Python 3.9–3.13) that installs the package with the `dev` extra,
runs `python -m pytest tests -q`, and is required before the publish job.

### F-04 — High — 12 collected tests cannot fail and perform real I/O

**Evidence**

- `tests/test_all_features.py`: 12 functions named `test_*`, **0 `assert` statements**, 100 `results.add_pass/add_fail/add_skip`
  calls, and 41 `except Exception` blocks. Failures are recorded in a `TestResult` object and only printed from
  `main()`; pytest treats each function as passed.
- `results.print_summary()` (line 66) and `main()` (line 539) are never called by pytest (`main` is not a test name).
- The same functions call the live application: `env_manager.list_pythons()`, `search_envs("")`, package listing,
  vulnerability scanning helpers and Py-Tonic profile loading — i.e. developer-machine state.
- Measured: the whole 80-test run takes 23.09 s, dominated by these network/OS-bound checks.

**Impact**

`12 passed` in the report is meaningless for `[1]–[12]` categories (Environment, Package, UV, Vulnerability,
Configuration, Database, Plugin, Auto-Resolve, Integration, Py-Tonic, Setup State, Runtime), while the run is
slow, network-dependent and mutates the developer's real environment metadata. This is the single largest
source of false confidence in the suite.

**Recommendation**

Retire the file as a test artefact: convert each numbered category into real pytest cases per `TEST_CASES.md`
(ENV/PIP/UV/SEC/CFG/DB/PLG/AR/UTIL/LRN/STA/RT), keep the console runner only as a local smoke script (or delete it),
and never let a "test" swallow exceptions to report success.

### F-05 — High — 85 % of cataloged acceptance criteria have no automated test

**Evidence**

- Catalog totals: 277 GAP + 13 MANUAL = 290 of 339 cases without an executing automated assertion.
- Modules with **zero** test references: `core/pip_tools.py`, `core/package_manager.py`, `core/uv_tools.py`,
  `core/auto_resolve.py`, `core/database.py`, `core/runtime_toggle.py`, `core/bootstrap.py`, `core/runtime.py`,
  `core/strategies.py`, `core/integration.py`, `core/windows_apps.py`, `utils/vulneribility_scanner.py`,
  `utils/db_status.py`, `utils/version_utils.py`, `utils/handlers.py`, `commands.py`, `ui/main_window.py`,
  `core/templates/validator.py`, `core/templates/content_filters.py`, `core/plugins/manager.py`.

**Impact**

Every release-critical flow (create/delete environment, pip/uv install with argv safety, AutoResolver relaxing
version pins, vulnerability scanning + status tracking, plugin execution, CLI parsing, DB migration) can break
without a single test failing. Security-relevant behaviour (command construction, path traversal, sensitive-file
filtering, secrets in logs) is entirely unguarded.

**Recommendation**

Implement the catalog in the listed priority order (see §7), starting with the P0 rows.

### F-06 — Medium — 60 assertion-bearing manual checks are never executed by pytest

**Evidence**

- `tests/test_window_icon.py` — 297 lines, 26 `check(...)` calls, 0 `def test_*`; module-level code plus a
  `main`-style block. Pytest collects **0** tests from it.
- `tests/test_vulnerability_insights_update.py` — 387 lines, 34 `check(...)` calls, 0 `def test_*`; covers
  `_parse_target_version`, `_version_key`, `Update Now` and `Upgrade all Packages` remediation.
- `tests/test_plugin_import.py`, `test_plugin_load.py`, `test_plugin_events.py`, `test_uv_packages.py` — 0
  assertions of any kind; they only `print()` results and rely on uncaught exceptions.
- All four plugin/uv scripts insert the developer's real path `Path.home()/".py_env_studio"/"plugins"` on
  `sys.path` and load `sample_plugin` from it, so they cannot run in a clean environment or CI.

**Impact**

The window-icon fix and both vulnerability-remediation actions (documented in the feature ledger for 2026-09-18)
have **no executed regression coverage**; the plugin hooks and uv paths have none at all. The 60 checks give a
misleading impression that these features are tested.

**Recommendation**

Convert the `check()` scripts into pytest functions with `assert` (the two files already compute exact expected
values, e.g. severity counts, dedup labels, `_parse_target_version` results) and move the plugin/uv scripts to
`tmp_path`-based fixtures; mark genuinely interactive checks with a `gui`/`e2e` marker.

### F-07 — Medium — No test isolation: no `conftest.py`, no pytest config, real user directories

**Evidence**

- No `conftest.py` and no pytest configuration anywhere (also F-03).
- `tests/setup/db.py:18-21` and `tests/setup/state.py:22-28` construct `PlatformDirs(APP_NAME)` and write to the
  real per-user data directory; `tests/setup/db.py:115-117` even initialises the real database when run directly.
- `tests/test_window_icon.py` and `test_vulnerability_insights_update.py` create real `ctk.CTk()` windows
  (requires a display) and read the user profile icon path.
- `tests/test_plugin_*.py` depend on `~/.py_env_studio/plugins/sample_plugin` existing.
- `tests/test_all_features.py` calls live environment/scan helpers.

**Impact**

Results depend on the machine (`HOME`/`APPDATA` state, installed IDEs, plugin directory, display availability),
so the suite is non-deterministic and unsafe to run in CI or on a developer's machine with real environments.
It also means "passing locally" cannot be trusted.

**Recommendation**

Add `tests/conftest.py` with the fixtures listed in `TEST_CASES.md` §3 (a `pes_home` fixture that redirects the
platform user-data location to `tmp_path`, fake process/HTTP sessions, a GUI root fixture) and a
`[tool.pytest.ini_options]` block registering the `gui`/`e2e` markers with a non-GUI default selection.

### F-08 — Medium — `run_all_tests.py` reports false PASS results

**Evidence**

- `tests/run_all_tests.py:52-55` globs `test_*.py` and `:27-33` executes each file with `subprocess.run([sys.executable, str(test_file)])`,
  treating a zero exit code as PASS.
- pytest-style files (`test_template_engine.py`, `test_configuration_service.py`, `test_project_openers.py`, …)
  define functions but execute nothing when run as a script — the interpreter exits `0`, so the runner prints
  `PASS` for a file that ran zero tests.
- Script-style files with broad `except` blocks (plugin/uv scripts) likewise report `PASS` when they fail
  internally, because they print instead of raising.

**Impact**

`python tests/run_all_tests.py` — the command documented in `tests/TEST_README.md` — can report a fully green
run while nothing was verified. This is the second false-confidence mechanism in the suite (with F-04).

**Recommendation**

Replace the runner with `python -m pytest tests` (optionally `-p no:cacheprovider`), or make it invoke
`sys.exit(pytest.main([...]))`; delete the per-file subprocess approach. Recount results from pytest's summary
instead of exit codes.

### F-09 — Medium — CLI input validation is effectively untested and has a dead error branch

**Evidence** (`py_env_studio/commands.py`)

```python
25  def _split_two_values(raw_value: str, usage: str) -> Tuple[str, str]:
26      try:
27          return raw_value.split(",", 1)
28      except ValueError:
29          print(f"Error: Invalid value. Usage: {usage}")
30          sys.exit(1)
...
50  def handle_install(args: argparse.Namespace) -> None:
51      env_name, package = _split_two_values(
52          args.install, "py-env-studio --install env_name,package"
53      )
```

`str.split(",", 1)` never raises `ValueError`; it returns a 1-element list when no comma is present. The
`ValueError` is raised later, at the caller's tuple unpacking (line 51), **outside** the `try` block — so
`pes --install onlyone` produces a traceback instead of the documented `Usage: ...` message plus exit code 1.
The same pattern applies to `--uninstall`, `--export` and `--import-reqs` (lines 58-79).

**Impact**

User-visible rough edge on the documented CLI (master instructions §15 require clear failure for invalid
arguments). It is invisible because **no CLI test exists** (catalog CLI area is 0 % covered). Also note
`--export` is documented as `env_name,file_path` while `docs/getting-started/cli.md` shows
`--export <<env_name>>,requirements.txt` — behavior, help text and docs differ (catalog TC-CLI-015).

**Recommendation**

Validate the split result (or catch the unpack error at the call site) and add catalog case `TC-CLI-008`
plus the remaining CLI cases; do not change behaviour without a test asserting the intended contract.

### F-10 — Medium — `tests/setup/` duplicates production modules and asserts nothing

**Evidence**

- `tests/setup/state.py` (129 lines) re-implements `SetupStateManager` with the same constants and logic as
  `py_env_studio/core/setup_state.py`; `tests/setup/db.py` (118 lines) re-implements `DatabaseManager` from
  `py_env_studio/core/database.py` (including a legacy schema without the production migration path).
- Neither module contains an assertion or a `def test_*`; `tests/setup/test_window.py` builds a Tk setup wizard
  (GUI) and is collected but contributes **0** tests.
- `tests/setup/test_window.py:4-5` imports `from setup.state import ...`, which only resolves because pytest
  inserts `tests/` into `sys.path` (there is no `tests/__init__.py`, but `tests/setup/__init__.py` exists).

**Impact**

The STA coverage claimed for setup/bootstrap is illusory: changing `core/setup_state.py` or `core/database.py`
cannot fail any test in this directory. It also duplicates maintenance (two divergent health-check
implementations) and hides the absence of the real migration test (`TC-DB-003`).

**Recommendation**

Delete the duplicated helpers and write `tests/test_setup_state.py` / `tests/test_database.py` against the
production modules using a `tmp_path`-based state directory (catalog STA/DB cases), keeping any genuinely
interactive wizard check as a marked `gui` test.

### F-11 — Low — Dependency and metadata drift around the `tkinter-dash` migration

**Evidence**

- `pyproject.toml` (working tree) declares `tkinter-dash>=0.1.5`; `py_env_studio/requirements.txt` pins
  `tkinter-dash==0.1.5`; both replaced `matplotlib` (migration is **uncommitted**).
- `py_env_studio.egg-info/requires.txt` — generated metadata present in the working tree — still lists
  `matplotlib>=3.10.5` and no `tkinter-dash`, i.e. stale build metadata contradicting the declared dependencies.
- `api_inventory.txt` (29 KB) is untracked at the repository root.
- `py_env_studio/main.spec` / `PyEnvStudio.spec` correctly bundle `tkinter_dash`, so packaging is consistent;
  only the generated metadata drifted.

**Impact**

Stale egg-info can mislead tooling/audits about runtime dependencies and would be shipped if the tree is built
as-is; an uncommitted dependency migration makes the "revision" in any test report ambiguous (§3.4).

**Recommendation**

Commit the migration, regenerate (or remove) `py_env_studio.egg-info`, and add catalog case `TC-UTIL-016`
(dependency parity) plus `TC-NFR-003` (no `matplotlib` import anywhere) as guards.

### F-12 — Low — Test documentation overstates the current coverage

**Evidence** `tests/TEST_README.md`

- Claims a "comprehensive collection of tests that verify all features" and "50+ individual test cases" in
  `test_all_features.py` covering Environment, Package, Vulnerability, Database, Plugin, Auto-Resolution,
  Py-Tonic and Runtime — exactly the categories that today have no executing assertions (F-04, F-05).
- Documents `pytest tests/ -v --cov=py_env_studio`, but `pytest-cov` is neither installed nor declared
  (`pyproject.toml` `[project.optional-dependencies].dev = ["pytest", "black", "isort"]`).
- Presents `run_all_tests.py` output as authoritative (including its F-08 false-PASS behaviour) and states the
  suite runs in "30-60 seconds" (measured: 23 s for the collected tests only).

**Impact**

A reviewer or contributor reading the docs would conclude the suite is far stronger than it is, and the
documented workflow cannot be reproduced as written.

**Recommendation**

Rewrite `tests/TEST_README.md` from measured facts (real test counts, what each file actually asserts, how to run
GUI/E2E cases) and link it to `tests/TEST_CASES.md` and this report.

### F-13 — Low — Repository pollution from manual test runs

**Evidence**

- `tests/myproject/pes` (file) and `tests/test-app/tmp-project-check/main.py`.
- `tests/test-app/tmp-cli-check/tmp-cli-check/tmp-cli-check/tmp-cli-check/` — four nested levels of leftover CLI
  scratch directories.
- These live inside the git-ignored `tests/` folder, so they were never cleaned up or reviewed.

**Impact**

Noisy working tree, risk of being copied into future branches/archives, and unclear provenance of the artefacts.

**Recommendation**

Delete the generated scratch trees and ensure CLI/template manual checks run inside `tmp_path` (catalog
`TC-CLI-*`, `TC-TPL-*`).

### F-14 — Low — No coverage measurement or test reporting

**Evidence**

- No `pytest-cov`/`coverage` configuration, no `--cov` option, no `.coveragerc`, no coverage threshold, and no
  mention of coverage in `docs/development/contributing.md`.
- Test artefacts (`.pytest_cache/`, `build/`, `dist/`, `site/`) sit in the working tree with no reporting step.

**Impact**

Coverage cannot be tracked over time, so the gap in F-05 will silently persist and regressions in covered
modules cannot be quantified.

**Recommendation**

Add coverage reporting (`pytest-cov`) with a threshold for the core modules and publish the report from CI once
F-01/F-03 are resolved.

## 7. Remediation backlog (recommended order — not implemented)

| Order | Task | Addresses | Type | Catalog reference |
|---|---|---|---|---|
| R-01 | Narrow the `.gitignore` rule and commit the test suite | F-01 | Repo hygiene | — |
| R-02 | ✅ **DONE (v1.1.0)** — baseline made green by realigning `tests/test_project_runtime.py` with `core/runtime_toggle.py` (F-02 resolved; 79 passed, 1 skipped, 1 warning) | F-02 | Test fix | TC-RT-016/017 |
| R-03 | Remove the false-confidence paths: convert `test_all_features.py` into real assertions (or delete it), replace `run_all_tests.py` with `pytest` | F-04, F-08 | Test architecture | all areas |
| R-04 | Add test infrastructure: `tests/conftest.py`, `[tool.pytest.ini_options]` (`testpaths`, `gui`/`e2e` markers, default deselection), `pytest-cov` in the `dev` extra | F-03, F-07, F-14 | Infra | `TEST_CASES.md` §3 |
| R-05 | Add a CI workflow that installs the package and runs `pytest tests` on Windows + Ubuntu (Py 3.9–3.13) before publishing | F-03 | CI | — |
| R-06 | Implement the P0 catalog cases: environment lifecycle, pip/uv argv safety, manager fallback, AutoResolver bounds, scanning + status tracking, runtime `pes run`, plugin isolation, DB migration | F-05 | New tests | ENV, PIP, UV, PMGR, AR, SEC, ST, RT, PLG, DB |
| R-07 | Convert `test_window_icon.py` (26 checks) and `test_vulnerability_insights_update.py` (34 checks) into collected pytest cases | F-06 | Test conversion | DASH, UTIL |
| R-08 | Implement the P1/P2 cases for templates/validator security, CLI contract, configuration edge cases, Py-Tonic, setup state, GUI smoke | F-05 | New tests | TPL, TPLU, TPLG, CLI, CFG, LRN, STA, UI |
| R-09 | Implement the NFR guards (`shell=True`, secrets in logs, determinism, dependency parity, no matplotlib) | F-05, F-11 | New tests | NFR, UTIL |
| R-10 | Fix the CLI split helper only after `TC-CLI-008` exists as a failing-then-passing test | F-09 | Product fix | CLI |
| R-11 | Remove `tests/setup/*` duplication, regenerate metadata, clean scratch artefacts, rewrite `tests/TEST_README.md` from measured facts | F-10, F-11, F-12, F-13 | Cleanup | STA, DB, UTIL |

Suggested effort split (relative): R-01–R-05 = small (repo/CI hygiene); R-06–R-07 = large (the bulk of the
339-case catalog); R-08–R-11 = medium. Implementing R-06/R-07 would take automated coverage from ≈14 % to
roughly 60 % of the catalog; reaching 100 % also requires the GUI (`TC-UI-*`) manual acceptance runs.

## 8. Verification notes and limitations

**Verified in this audit**

- Full pytest execution on Windows 11 / Python 3.13.7 (80 collected; 2 failed, 77 passed, 1 skipped, 23.09 s).
- `--collect-only` node-ID inventory per file, used to build §4.
- Static verification that the failing tests target a non-existent API (`search_codebase` found
  `initialize_project_runtime` only inside `tests/test_project_runtime.py` and `.pytest_cache`).
- Static verification of git tracking status (`git ls-files`, `git check-ignore`), workflow inventory,
  `.gitignore` content, assertion counts per file, and the CLI helper defect (code reading).
- Existing dependency/packaging facts: `pyproject.toml`, `py_env_studio/requirements.txt`,
  `py_env_studio.egg-info/requires.txt`, `py_env_studio/main.spec`, `py_env_studio/PyEnvStudio.spec`.

**Not verified (stated honestly, per master instructions §27)**

- **Not tested because:** GUI cases (`TC-UI-*`, `TC-DASH-*` remediation flows) require interactive verification;
  no GUI acceptance run was performed.
- **Not tested because:** macOS and Linux behaviour could not be executed in this environment; the platform
  branch logic is covered only by static reading.
- **Not tested because:** live calls to PyPI / deps.dev / OSV / GitHub were deliberately not made during this
  audit (offline, deterministic conditions), so scanner behaviour against real APIs is unmeasured.
- **Not tested because:** the frozen PyInstaller build and the Windows Start Menu shortcut were not exercised.
- Coverage percentages in §5 are computed from the catalog mapping (§ categorical estimates), not from a
  coverage tool — no coverage tooling is configured (F-14). The exact numbers are the case counts in
  `TEST_CASES.md` §4.1.

## 9. Appendix — commands and key paths

```text
# Baseline execution
python -m pytest tests -q --no-header -rf          # 79 passed, 1 skipped, 1 warning, 18.44s
python -m pytest tests --collect-only -q           # 80 tests collected

# Governance checks
git --no-pager ls-files tests                      # 0 tracked files  (F-01)
git check-ignore -v tests/TEST_README.md           # .gitignore:218:tests/
Get-ChildItem .github/workflows                    # only publish.yml   (F-03)

# Evidence paths
tests/TEST_CASES.md                                # 339-case catalog (companion document)
tests/TEST_AUDIT_REPORT.md                         # this report
tests/test_project_runtime.py                      # realigned to runtime_toggle (F-02 resolved, 2 green)
tests/test_all_features.py                        # 0 asserts, 100 add_*   (F-04)
tests/test_window_icon.py                         # 26 manual checks       (F-06)
tests/test_vulnerability_insights_update.py        # 34 manual checks       (F-06)
tests/run_all_tests.py:27-33,52-55                 # exit-code PASS logic   (F-08)
py_env_studio/commands.py:25-30                    # dead error branch      (F-09)
tests/setup/{state.py,db.py}                       # duplicated production code (F-10)
py_env_studio.egg-info/requires.txt                # stale matplotlib pin   (F-11)
tests/TEST_README.md                               # overstated coverage    (F-12)
.github/copilot-instructions.md                    # mandated test policy the suite does not yet meet
```

## 10. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 1.1.0 | 2026-09-20 | Test/QA audit (agent) | Resolved RED cases F-02: realigned `tests/test_project_runtime.py` from the non-existent `env_manager.*` helpers to the production `core/runtime_toggle.py` API. Suite went from 2 failed / 77 passed to 79 passed, 1 skipped, 1 warning (18.44 s), exit 0. Catalog: RED 2 → 0, COVERED 37 → 39 (TC-RT-016, TC-RT-017), PARTIAL unchanged at 10. Documentation updated to match measured evidence. No production code changed. |
