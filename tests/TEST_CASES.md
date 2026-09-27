# Py Env Studio — Test Case Catalog (Audit Baseline)

| Field | Value |
|---|---|
| Document ID | PES-TESTCASE-CATALOG |
| Version | 1.1.0 |
| Date | 2026-09-20 |
| Repository revision | `8d11de4` (`main`, "window icon fix") |
| Product version under test | 2.1.0 (`pyproject.toml`, `py_env_studio/config.ini`) |
| Verified platform | Windows 11, Python 3.13.7, pytest 9.1.1 |
| Scope | All documented features in `docs/reference/features.md`, `docs/getting-started/cli.md`, `.github/agent-context/feature-ledger.md`, `README.md` |
| Status | **v1.1.0 — two RED cases (TC-RT-016/TC-RT-017) resolved by realigning `tests/test_project_runtime.py` with the production `runtime_toggle` API. All other catalog cases remain unimplemented (deferred). No production code was modified.** |

## 0. How to use this catalog

This catalog is the audit baseline for the PES test suite. Each row is one test case with a stable ID,
so a reviewer can trace *feature → test case → automated test → result*.

- Cases marked `COVERED` already have an executing, assertion-bearing automated test.
- Cases marked `PARTIAL` have indirect or incomplete coverage.
- Cases marked `GAP` have **no** automated test today.
- Cases marked `RED` are covered by an automated test that currently **fails** (no case has this status
  after the v1.1.0 fix; the status is kept for future audit runs).
- Cases marked `MANUAL` only exist as script-style checks that pytest does not collect.

Implementation of the `GAP`/`MANUAL` cases is out of scope for this task and is tracked in
`TEST_AUDIT_REPORT.md` (section "Remediation backlog"). Recommended target files are named per area.

## 1. Case ID scheme, priority and type legend

ID format: `TC-<AREA>-<nnn>`.

| Area | Meaning |
|---|---|
| ENV | Environment lifecycle (create/search/rename/delete/activate/size/metadata) |
| PIP | pip package operations |
| UV | uv package operations and uv detection |
| PMGR | Package-manager routing + automatic fallback |
| AR | AutoResolver (dependency-resolution recovery) |
| DP | Dependency impact preview |
| SEC | Vulnerability scanning (`vulneribility_scanner`) |
| ST | Vulnerability status tracking (`db_status`, `version_utils`) |
| DASH | Vulnerability Insights dashboard (charts + remediation) |
| TPL | Template registry/models/validator/engine/workflow |
| TPLU | User template store + content filters |
| TPLG | GitHub import + Community templates |
| RT | Project runtime toggle + registry + `pes.config` |
| CLI | Command-line interface (`commands.py`, entry points) |
| CFG | Configuration service / preferences / runtime paths |
| PLG | Plugin system |
| DB | SQLite database + handlers |
| LRN | Py-Tonic learning support |
| STA | Setup state, bootstrap, Windows shortcut |
| UI | GUI behaviour (CustomTkinter, background tasks, dialogs) |
| UTIL | Shared utilities (icons, strategies, tool detection, version helpers) |
| NFR | Non-functional: determinism, security, cross-platform, performance |

| Priority | Meaning | Gate |
|---|---|---|
| P0 | Data loss, security, or a broken core workflow | Must pass before release |
| P1 | Primary user-facing feature | Must pass before release |
| P2 | Secondary feature / important edge case | Should pass before release |
| P3 | Cosmetic, rare edge case, resilience polish | Track as known gap |

| Type | Meaning |
|---|---|
| U | Unit test (pure logic, fully mocked) |
| I | Integration test (real filesystem/temp dirs, mocked externals) |
| E2E | End-to-end (real subprocess/venv/pip, opt-in marker) |
| GUI | GUI/manual verification (CustomTkinter window required) |
| SEC | Security / negative-input test |
| PERF | Performance or resource test |

**Determinism rule (master instructions §12):** every automated case must run without internet,
without the developer's IDEs, without the developer's real `~/.py_env_studio` data, and without
modifying a real virtual environment. Externals are mocked; `PES_*` data locations are redirected to
`tmp_path`.

## 2.1 Environment lifecycle — `py_env_studio/core/env_manager.py`

Target file for gaps: `tests/test_env_manager.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-ENV-001 | `search_envs("")` returns every environment known to the manager | All listed env names returned, order stable (sorted) | P1 | U | GAP |
| TC-ENV-002 | `search_envs("DSA")` matches case-insensitively as a substring | Only envs containing `dsa` in any case | P1 | U | GAP |
| TC-ENV-003 | `search_envs("no-such-env")` | Empty list, no exception | P2 | U | GAP |
| TC-ENV-004 | `_is_valid_env_name` accepts `my-env_1.2`; rejects `""`, `".."`, `"a/b"`, `"a\\b"`, `"bad name"`, `"CON"`, 300-char name | Only documented-safe names accepted; no path characters allowed | P0 | SEC | GAP |
| TC-ENV-005 | `create_env("demo")` with a valid Python path | `<venv_dir>/demo/pyvenv.cfg` exists, interpreter exists at the documented platform path, `pyvenv.cfg` records the requested interpreter | P0 | I | GAP |
| TC-ENV-006 | `create_env` with an existing env name | Clear error raised, existing environment untouched | P0 | I | GAP |
| TC-ENV-007 | `create_env` with an invalid name | Rejected before any filesystem write; no partial directory left behind | P0 | SEC | GAP |
| TC-ENV-008 | `create_env(..., upgrade_pip=True)` | pip upgrade invoked once through the existing process helper (mocked), failure surfaces as an error message | P1 | I | GAP |
| TC-ENV-009 | venv creation fails (mocked `subprocess` non-zero exit) | Error propagated with actionable message; no half-created env directory remains | P0 | I | GAP |
| TC-ENV-010 | `list_envs()` with a mix of valid envs, plain folders and stray files | Only directories containing `pyvenv.cfg` returned | P1 | I | GAP |
| TC-ENV-011 | `list_pythons()` and `_extract_python_version` on `py -0`/`which` output samples | Detected interpreters de-duplicated and parsed to a version string | P1 | U | GAP |
| TC-ENV-012 | `is_valid_python` / `is_valid_python_version_detected` with existing, missing and non-executable paths | `False` for missing/invalid, `True` for a real interpreter, no exception | P1 | U | GAP |
| TC-ENV-013 | `rename_env("a", "b")` | Directory renamed, metadata key migrated, recent-location and package-manager data preserved | P0 | I | GAP |
| TC-ENV-014 | `rename_env` to an existing name or invalid name | Rejected with clear error; nothing renamed | P0 | I | GAP |
| TC-ENV-015 | `delete_env("demo")` | Directory removed, metadata entry removed, no orphan rows in `env_data.json` | P0 | I | GAP |
| TC-ENV-016 | `delete_env("missing")` | Graceful failure message, no traceback leakage to CLI/GUI | P2 | U | GAP |
| TC-ENV-017 | `get_env_python` on existing env / missing env / broken `pyvenv.cfg` | Correct interpreter path; `None` (or documented error) when unavailable | P1 | U | GAP |
| TC-ENV-018 | `activate_env("demo", directory=..., open_with="vscode")` | Delegates to the registered `venv_injection` strategy with the env `Scripts`/`bin` on `PATH` and cwd = chosen directory (subprocess mocked) | P1 | I | GAP |
| TC-ENV-019 | `activate_env(..., open_in_venv_cwd=True)` | cwd is the environment root instead of the chosen directory | P2 | I | GAP |
| TC-ENV-020 | `set_env_data` / `get_env_data` round-trip incl. `recent_location`, `size`, `last_scanned`, `python_version`, `package_manager` | Values persisted atomically and returned unchanged; unknown env returns defaults | P1 | I | GAP |
| TC-ENV-021 | `calculate_env_size_mb` on empty dir, nested dir and missing dir | Recursive sum in MB; `0` for empty/missing; no crash on permission errors | P2 | U | GAP |
| TC-ENV-022 | `is_exact_env_active(python_exe_path)` | `True` only when the running interpreter matches the env exactly; `False` otherwise | P2 | U | GAP |
| TC-ENV-023 | `refresh_runtime_paths()` after a runtime-config change | Module-level `VENV_DIR`/`LOG_FILE`/`DB_FILE`/`MATRIX_FILE` reflect the new paths | P1 | U | GAP |
| TC-ENV-024 | `set_env_data` with a non-writable `env_data.json` (path mocked) | Fails safely, no corrupt/truncated JSON left on disk | P0 | I | GAP |
| TC-ENV-025 | `get_available_tools()` / `add_tool()` | Detected tools listed; duplicate tool name not added twice; new tool persisted | P2 | U | GAP |
| TC-ENV-026 | `get_preferred_package_manager` / `set_preferred_package_manager` / `get_package_manager_display` | Defaults to `pip`; invalid manager value rejected or normalised; display string mapped for `pip`/`uv` | P2 | U | GAP |

## 2.2 pip package operations — `py_env_studio/core/pip_tools.py`

Target file for gaps: `tests/test_pip_tools.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-PIP-001 | `list_packages(env)` parses `pip list --format=json` output | Ordered list of `(name, version)` pairs | P0 | U | GAP |
| TC-PIP-002 | `list_packages` when pip emits a warning line before JSON | Warning ignored, JSON still parsed (or documented empty result) | P1 | U | GAP |
| TC-PIP-003 | `list_packages` on an env with no interpreter / non-zero exit | Documented failure result, no partial/garbage data, error log emitted | P0 | U | GAP |
| TC-PIP-004 | `install_package(env, "requests")` success path (mocked process) | Called with argument-list `[python, -m, pip, install, requests]`, success returned, `log_callback` receives progress lines | P0 | U | GAP |
| TC-PIP-005 | `install_package` with a malicious spec (`"requests; rm -rf /"`, `"--evil"`, `"requests && whoami"`) | Rejected or passed as a single argv element — never interpreted by a shell (`shell=False` asserted) | P0 | SEC | GAP |
| TC-PIP-006 | `install_package` non-zero exit | Failure returned with stderr snippet, no exception escaping to the UI thread | P1 | U | GAP |
| TC-PIP-007 | `uninstall_package(env, "numpy")` success and `not installed` failure | Success flag and message per case; exit code mapped correctly | P1 | U | GAP |
| TC-PIP-008 | `update_package(env, "numpy")` | Uses `--upgrade`; success/failure mapped | P1 | U | GAP |
| TC-PIP-009 | `check_outdated_packages` parses `pip list --outdated --format=json` | Returns `(current, latest)` per package; empty list when all up to date | P1 | U | GAP |
| TC-PIP-010 | `export_requirements(env, path)` | File created with one `name==version` per line; parent directory created if missing | P1 | I | GAP |
| TC-PIP-011 | `export_requirements` to a non-writable path | Clear error, no partial file | P2 | I | GAP |
| TC-PIP-012 | `import_requirements(env, file)` success and missing-file failure | Requirements installed in order; missing file produces an actionable error and no subprocess run | P1 | U | GAP |
| TC-PIP-013 | `import_requirements` with a requirements file containing a bad line | Failure reported with the offending line; already-installed packages not rolled back silently | P2 | U | GAP |
| TC-PIP-014 | `get_pip_version()` | Version string returned for a valid interpreter, `"unknown"`-style value otherwise | P2 | U | GAP |

## 2.3 uv package operations — `py_env_studio/core/uv_tools.py`

Target file for gaps: `tests/test_uv_tools.py` (new; `tests/test_uv_packages.py` is script-style and pytest collects **0** tests from it).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-UV-001 | `is_uv_installed()` when `shutil.which("uv")` returns a path / `None` | `True` / `False` (monkeypatched, no real uv required) | P0 | U | GAP |
| TC-UV-002 | `get_uv_version()` success and non-zero exit | Version string or `None`; exception contained | P2 | U | GAP |
| TC-UV-003 | `_get_venv_dir_from_python_path` on Windows (`Scripts\python.exe`), POSIX (`bin/python`) and odd inputs | Correct venv root for both layouts; `None`/documented fallback for unusable input | P1 | U | GAP |
| TC-UV-004 | `list_packages_uv(venv_path)` parses `uv pip list --format=json` | Normalised `[{name, version}]`, matching the pip contract consumed by the GUI | P0 | U | GAP |
| TC-UV-005 | `list_packages_uv` on malformed JSON output | Documented failure (`(False, ...)`), no exception escaping | P1 | U | GAP |
| TC-UV-006 | `install_package_uv` success, non-zero exit, and uv binary missing | `(True, output)` / `(False, stderr)` / `(False, msg)`; argument-list invocation only | P0 | U | GAP |
| TC-UV-007 | `uninstall_package_uv`, `update_package_uv`, `check_outdated_packages_uv`, `get_package_info_uv` | Correct uv subcommands used; results normalised to the pip-equivalent shapes | P1 | U | GAP |
| TC-UV-008 | `import_requirements_uv` / `export_requirements_uv` | Correct `-r` import and export file content; failures surfaced as `(False, msg)` | P1 | I | GAP |
| TC-UV-009 | `UVManager` facade methods delegate to the module functions with the stored venv path | Identical results; `is_available()` short-circuits when uv is absent | P2 | U | GAP |
| TC-UV-010 | Install requires `uv` not installed → caller falls back to pip instead of failing the user action | Routed through `package_manager` fallback (see TC-PMGR-002) | P0 | I | GAP |

## 2.4 Package-manager routing and fallback — `py_env_studio/core/package_manager.py`

Target file for gaps: `tests/test_package_manager.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-PMGR-001 | `get_env_package_manager(env)` for unset, `pip`, `uv`, and unknown values | `pip` default; valid values returned; unknown value falls back to `pip` | P1 | U | GAP |
| TC-PMGR-002 | Install/uninstall/update/list for an env configured as `uv` while uv is unavailable | Operation transparently re-routed to pip and succeeds; a warning is logged | P0 | I | GAP |
| TC-PMGR-003 | `uv` operation fails at runtime (mocked non-zero exit) | Automatic pip fallback once, then success; user is not asked to retry manually | P0 | I | GAP |
| TC-PMGR-004 | Both uv and pip fail | Failure returned once with the pip error; no infinite retry loop, bounded attempts | P0 | U | GAP |
| TC-PMGR-005 | `list_packages` / `check_outdated_packages` for pip and uv envs | Identical normalised return shape for both managers (GUI-safe) | P1 | U | GAP |
| TC-PMGR-006 | `export_requirements` / `import_requirements` routed per env manager | Correct backend used; file-on-disk result verified | P1 | I | GAP |

## 2.5 AutoResolver — `py_env_studio/core/auto_resolve.py`

Target file for gaps: `tests/test_auto_resolve.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-AR-001 | `extract_package_name` for `numpy`, `numpy==1.26.4`, `numpy>=1.2,<2`, `pkg[extra]>=1.0`, `Pkg.Name`, invalid/empty string | Canonical lower-case distribution name; empty/invalid input handled without exception | P1 | U | GAP |
| TC-AR-002 | `strip_version_constraints` for `==`, `>=`, `~=`, `!=`, extras, and plain names | Only the bare package name remains; extras preserved if required by design | P1 | U | GAP |
| TC-AR-003 | `is_resolution_error` on real pip resolver messages (`ResolutionImpossible`, `conflicting dependencies`, `Could not find a version`) | `True` for genuine resolver conflicts | P0 | U | GAP |
| TC-AR-004 | `is_resolution_error` on unrelated failures (network timeout, bad interpreter, permission denied, disk full) | `False` — AutoResolver must not mask non-resolution failures | P0 | U | GAP |
| TC-AR-005 | `parse_conflicting_packages` on a pip conflict dump | Exact conflicting package names extracted, de-duplicated, no transitive noise | P1 | U | GAP |
| TC-AR-006 | `AutoResolver.should_retry` across attempts | Retry allowed while under the documented bound, denied afterwards (no infinite loop) | P0 | U | GAP |
| TC-AR-007 | `prepare_retry_package(spec, attempt)` per attempt | Attempt sequence strips constraints as documented (e.g. `==` → unconstrained), never returns an empty/unsafe spec | P1 | U | GAP |
| TC-AR-008 | `resolve` where the first attempt succeeds | Single install call, `(True, output)` returned, no retry | P1 | U | GAP |
| TC-AR-009 | `resolve` where attempt 1 conflicts and attempt 2 succeeds | Two calls with progressively relaxed specs; success returned; each retry logged via `log_callback` | P0 | U | GAP |
| TC-AR-010 | `resolve` where all attempts fail | `(False, <last error>)`, attempt count bounded, original error preserved for the user | P0 | U | GAP |
| TC-AR-011 | `auto_resolve_install` module-level helper with `log_callback=None` | Works without a callback; no `None`-call crash | P1 | U | GAP |
| TC-AR-012 | Auto-resolve never modifies the user's requirements file on disk | Source file hash identical before/after a resolution retry | P0 | I | GAP |
| TC-AR-013 | Auto-resolve with a package already installed at a conflicting version | Documented behaviour (upgrade/downgrade message), no duplicate install calls | P2 | U | GAP |

## 2.6 Dependency impact preview — `py_env_studio/core/dependency_preview.py`

Existing coverage: `tests/test_dependency_preview.py` (22 collected cases, 1 skipped).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-DP-001 | `parse_package_spec` for plain, `==`, `>=`, `<`, `~=`, extras, case variants | `(name, spec)` split correctly; name lower-cased | P1 | U | COVERED |
| TC-DP-002 | `DependencyChange` / `BreakingChange` construction and `to_dict` | Field values and dictionary keys stable (GUI/JSON contract) | P1 | U | COVERED |
| TC-DP-003 | `PreviewResult.to_dict()` empty and populated | Summary counts (`will_add`, `will_upgrade`, `will_remove`) match list lengths | P1 | U | COVERED |
| TC-DP-004 | `_extract_name_and_version` for `name==1.0`, `name-1.0`, `name (1.0)` | Correct split for all three pip output formats | P2 | U | COVERED |
| TC-DP-005 | `get_installed_packages` is case-insensitive and handles empty envs | Lower-cased mapping; `{}` for empty env | P1 | U | COVERED |
| TC-DP-006 | `_check_breaking_changes` for a known package (numpy) and an unknown package | Known package yields a `high` severity entry; unknown yields none | P2 | U | PARTIAL (only numpy is asserted) |
| TC-DP-007 | `_parse_pip_dry_run_output` additions vs upgrades vs removals, incl. "Would install/Uninstall" lines | Each change classified exactly once, no duplicates | P0 | U | PARTIAL (single happy-path case) |
| TC-DP-008 | `simulate_dependency_resolution` when the pip dry-run is unavailable/fails | Falls back to `_analyze_dependencies_manually` and still returns a usable `PreviewResult` | P1 | U | GAP |
| TC-DP-009 | `get_package_dependencies` on network failure | Documented empty/partial result, no exception to the caller | P1 | U | GAP |
| TC-DP-010 | `preview_install(env, spec)` end-to-end against a temp venv | Additions/upgrades/conflicts reported without installing anything (`--dry-run` only) | P1 | E2E | MANUAL (skipped in suite: `Requires actual environment`) |
| TC-DP-011 | Preview is read-only: installed package set and `requirements.txt` unchanged after preview | No mutations on disk | P0 | I | GAP |

## 2.7 Vulnerability scanning — `py_env_studio/utils/vulneribility_scanner.py`

Target file for gaps: `tests/test_vulnerability_scanner.py` (new). All HTTP must be mocked (no live PyPI/deps.dev/OSV calls in CI).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-SEC-001 | `PyPIAPI.get_deprecation_eol("pkg")` parses a normal PyPI JSON payload | Deprecation/EOL (and yanked) flags extracted per documented contract | P1 | U | GAP |
| TC-SEC-002 | `PyPIAPI.get_deprecation_eol` on 404 / 5xx / timeout / invalid JSON | Documented fallback (`None`/empty), no exception escape, warning logged | P0 | U | GAP |
| TC-SEC-003 | `DepsDevAPI.get_dependencies(pkg, version)` parses a deps.dev response | Normalised dependency list (name + requirement + scope) | P1 | U | GAP |
| TC-SEC-004 | `DepsDevAPI.get_dependencies` "package not found" and malformed payload | Empty result + warning; scan continues for the remaining packages | P0 | U | GAP |
| TC-SEC-005 | `OSVAPI.get_vulnerabilities(pkg, version)` maps a known OSV record to `developer_view` fields | `vulnerability_id`, `summary`, `severity.level`, `affected_components`, `fixed_versions`, `impact`, `remediation_steps`, `references` all populated | P0 | U | GAP |
| TC-SEC-006 | OSV severity normalisation: CVSS vector, numeric score, `MODERATE` vs `Unknown` | Mapped to the fixed vocabulary `Critical/High/Medium/Low/Unknown` used by charts | P0 | U | GAP |
| TC-SEC-007 | OSV record without `fixed_versions` | Remediation reports "no fix available"; action flags disabled downstream | P0 | U | GAP |
| TC-SEC-008 | `SecurityMatrix.build_matrix(pkg, version)` aggregates PyPI + deps.dev + OSV data | Single matrix object with `metadata`, `developer_view`, `tech_leader_view`, `enterprise_view` keys | P0 | U | GAP |
| TC-SEC-009 | `SecurityMatrix.scan_pkg(..., env_id=...)` | Result is written for the correct `env_id`; scan timestamp recorded | P0 | I | GAP |
| TC-SEC-010 | `SecurityMatrix.scan_env(env_name, log_callback)` iterates all installed packages | Every package visited exactly once; per-package failures do not abort the whole scan; `log_callback` receives progress | P0 | I | GAP |
| TC-SEC-011 | Scan of an environment with zero installed packages | Empty-but-valid report; UI shows "no vulnerabilities", not an error | P1 | I | GAP |
| TC-SEC-012 | Full scan with the network fully offline | Scan completes with a clear offline/partial warning; no hang, no traceback into the GUI thread | P0 | U | GAP |
| TC-SEC-013 | Rate-limited (HTTP 429) or 403 response from a public API | Backoff/report path exercised; no crash; message names the failing service | P1 | U | GAP |
| TC-SEC-014 | Scan history is retained across scans for the same package | Previous scan rows preserved (trend data availability), newest row wins for "latest" | P1 | I | GAP |
| TC-SEC-015 | Corrupted stored vulnerability payload in the DB | Decoded defensively (`_decode_payload`), treated as "no data", no crash | P0 | I | GAP |
| TC-SEC-016 | Package version pinned vs `latest` for the same package | Matrix reflects the queried version; no stale previous-version data | P1 | U | GAP |

## 2.8 Vulnerability status tracking — `py_env_studio/utils/db_status.py`, `utils/version_utils.py`

Target file for gaps: `tests/test_vulnerability_status.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-ST-001 | `version_key` ordering: `2.11.1` < `26.2.0`, `1.0` < `1.0.1`, pre-release vs release | Numeric (not lexicographic) ordering; `_MISSING` sentinels sort last | P0 | U | GAP |
| TC-ST-002 | `is_known_version` for `""`, `"?"`, `"—"`, `"None"`, `"Unknown"`, `"n/a"`, real versions | `False` for all sentinels, `True` for real versions | P1 | U | GAP |
| TC-ST-003 | `vuln_status(current, fixed)` when current >= highest fix | `"fixed"`/up-to-date status; remediation disabled | P0 | U | GAP |
| TC-ST-004 | `vuln_status` when current < fix | Actionable status, target = highest recommended fixed version | P0 | U | GAP |
| TC-ST-005 | `vuln_status` with an empty/`None` fixed-version list | "No fix available" status; no upgrade recommended | P0 | U | GAP |
| TC-ST-006 | `ensure_vulnerability_statuses(env)` back-fills missing statuses | Every stored vulnerability gains a status; already-populated rows untouched unless `force=True` | P1 | I | GAP |
| TC-ST-007 | `ensure_vulnerability_statuses` with `force=True` after a package upgrade | Statuses re-derived from the new installed version | P1 | I | GAP |
| TC-ST-008 | `mark_package_fixed(env, pkg, new_version)` | Matrix current version bumped, affected entries marked resolved, other packages untouched | P0 | I | GAP |
| TC-ST-009 | `mark_package_fixed` for an unknown env/package | No-op with a warning, DB unchanged | P2 | I | GAP |
| TC-ST-010 | Status tracking is idempotent (running twice yields identical JSON) | Byte-identical payload after the second run | P2 | I | GAP |

## 2.9 Vulnerability Insights dashboard — `py_env_studio/utils/vulneribility_insights.py`

Existing coverage: `tests/test_vulnerability_insights_charts.py` (7 collected cases). `tests/test_vulnerability_insights_update.py` is script-style: pytest collects **0** tests from it.

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-DASH-001 | Severity breakdown chart uses `tkinter_dash.BarChart`, counts match the selected package, order is `CHART_SEVERITY_ORDER` | Exact counts, fixed order, no matplotlib objects on the app | P0 | GUI | COVERED |
| TC-DASH-002 | Trend chart renders `tech_leader_view.trend_data` as `LineChart`; duplicate timestamps get unique labels | `Total Vulnerabilities` / `Fixed Vulnerabilities` series with de-duplicated x labels | P1 | GUI | COVERED |
| TC-DASH-003 | Package without scan history | Trend chart is hidden and `TREND_EMPTY_MESSAGE` placeholder shown | P1 | GUI | COVERED |
| TC-DASH-004 | `_clear_ui()` resets both charts and the details panes | Zeroed severity chart, placeholder trend chart, empty detail tabs | P1 | GUI | COVERED |
| TC-DASH-005 | Chart data helpers `_to_count` (string `"8"` → `8`), `_format_trend_label`, `_unique_labels` | Numeric coercion and label de-duplication exactly as documented | P2 | U | PARTIAL (helpers asserted indirectly via chart tests) |
| TC-DASH-006 | `_parse_target_version` variants: plain, `upgrade to`, `Upgrade to the latest patched release` + `fixed_versions` list, `No fix available`, `None` input | Correct version or `None` for every variant | P0 | U | MANUAL (script `test_vulnerability_insights_update.py`) |
| TC-DASH-007 | `_version_key` ordering (`26.2.0` > `2.11.1`) | Numeric ordering | P0 | U | MANUAL |
| TC-DASH-008 | `_is_vuln_up_to_date(vuln)` when the installed version already satisfies the fix | `True`; "Update Now" hidden/disabled | P1 | U | MANUAL |
| TC-DASH-009 | `_collect_upgrade_plan()` across multiple vulnerable packages | One entry per package at the **highest** recommended fixed version; packages with no fix excluded | P0 | U | MANUAL |
| TC-DASH-010 | `update_now()` success path | Package upgraded once, `mark_package_fixed` called, report refreshed, button shows success state | P0 | GUI | MANUAL |
| TC-DASH-011 | `update_now()` failure path (pip error, network down) | Error surfaced on the button/dialog, no fixed-status write, package remains actionable | P0 | GUI | MANUAL |
| TC-DASH-012 | `upgrade_all_packages()` with partial failures | Successful packages marked fixed; failed packages reported by name; report refreshed | P0 | GUI | MANUAL |
| TC-DASH-013 | `upgrade_all_packages()` with zero actionable packages | Button disabled/no-op with an explanatory message | P1 | GUI | GAP |
| TC-DASH-014 | Remediation runs without blocking the GUI thread (`run_async`/polling) | Window stays responsive; result collected via polling | P1 | GUI | GAP |
| TC-DASH-015 | `format_enterprise_details` / `format_index_details` for empty, partial and full payloads | Readable text for every case, no `KeyError`/`NoneType` | P1 | U | GAP |
| TC-DASH-016 | `sort_column` on every sortable column, ascending/descending, numeric columns | Numeric columns sorted numerically (not lexicographically); direction toggles | P2 | U | GAP |
| TC-DASH-017 | Dashboard window title and PES icon applied | Title `Vulnerability Insights Dashboard`, icon set on the window | P2 | GUI | PARTIAL (covered by `tests/test_window_icon.py`, not collected by pytest) |
| TC-DASH-018 | `_refresh_from_db()` re-reads data after an external fix | Displayed data matches the DB after refresh | P2 | GUI | GAP |
| TC-DASH-019 | Reference links are clickable (`_make_links_clickable`) and comments are never rendered as links | Safe link handling; no `webbrowser` call for non-URL text | P3 | GUI | GAP |
| TC-DASH-020 | Dark/light theme switch updates chart colours | Charts follow the active appearance mode without a restart | P3 | GUI | GAP |

## 2.10 Template registry, models, validator and engine — `py_env_studio/core/templates/`

Existing coverage: `tests/test_template_engine.py` (8), `tests/test_template_registry.py` (4), `tests/test_template_workflow.py` (2). Target file for gaps: `tests/test_template_validator.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-TPL-001 | `TemplateRegistry.register` / `get` / `contains` for a built-in template | Registration and lookup by id; `name` and metadata preserved | P1 | U | COVERED |
| TC-TPL-002 | Duplicate registration of the same template id | `ValueError` containing "already registered"; existing entry unchanged | P1 | U | COVERED |
| TC-TPL-003 | `registry.get("does-not-exist")` | `KeyError` containing "Unknown template id" | P2 | U | COVERED |
| TC-TPL-004 | Default registry discovers user templates alongside built-ins | Both `python-script` and the user template present | P1 | U | COVERED |
| TC-TPL-005 | Generating `python-script`, `python-cli`, `python-package` projects | Expected file trees created; every generated `.py` file compiles; no unrendered `{placeholder}` tokens remain | P0 | I | COVERED |
| TC-TPL-006 | Placeholder substitution incl. spaces in the project name (`alpha project`) | README/module names rendered correctly; `{project_name}` gone | P1 | I | COVERED |
| TC-TPL-007 | Generating into an existing non-empty target directory | `TemplateValidationError`; existing files **not** overwritten | P0 | I | COVERED |
| TC-TPL-008 | Invalid project name (`*`) | `TemplateValidationError`, nothing written | P0 | SEC | COVERED |
| TC-TPL-009 | `create_virtual_environment=True` | Environment created with the requested Python version and dev dependencies installed (`pytest>=8.0`, `mypy>=1.10`) | P0 | I | COVERED |
| TC-TPL-010 | User template with `{{ double_brace }}` style and a module-name variable | Files rendered, `src/<module_name>` directory created | P1 | I | COVERED |
| TC-TPL-011 | Validator name rules: empty, leading/trailing space, dot-only, 200-char name, reserved Windows device names (`CON`, `NUL`, `AUX`), non-ASCII name | Documented accept/reject decision per case, no crash | P0 | SEC | GAP |
| TC-TPL-012 | Validator path-traversal input: project name `../evil`, `..\\evil`, `/etc/passwd`, absolute Windows path, name containing `:` or `%` | Rejected before any filesystem write; generated path stays inside `project_location` | P0 | SEC | GAP |
| TC-TPL-013 | Validator module/package/distribution names derived from the project name | Syntactically valid Python identifiers/distribution names; fallback applied for names starting with a digit | P0 | U | GAP |
| TC-TPL-014 | Unsupported `python_version` for a template with a `min_python` constraint | Rejected with an actionable message listing supported versions | P1 | U | GAP |
| TC-TPL-015 | `project_location` that does not exist / is not a directory / is read-only | Clear error before generation, no partial output | P1 | I | GAP |
| TC-TPL-016 | Template payload whose file path escapes the target (e.g. `../../x.py` in `TemplateFile.path`) | Rejected by the engine/validator (path traversal protection) | P0 | SEC | GAP |
| TC-TPL-017 | Creation failure mid-generation (mocked write error on the 2nd file) | Failure surfaced; no half-generated project silently left in a "successful" state | P0 | I | GAP |
| TC-TPL-018 | Engine `log_callback` receives progress and completion messages | Ordered, non-empty messages; `None` callback tolerated | P2 | U | GAP |
| TC-TPL-019 | `initialize_git=True` in a created project | `git init` invoked via argument list (no shell), failure reported without deleting the project | P1 | I | GAP |
| TC-TPL-020 | Project metadata persisted through `runtime_toggle.save_project_metadata` after creation | `pes.config` written with project name/environment id | P1 | I | GAP |
| TC-TPL-021 | `TemplateCreationWorkflow` state transitions `PENDING → SUCCESS` and `PENDING → FAILED` | Status enum and `error_message` set exactly as documented | P1 | U | COVERED |
| TC-TPL-022 | Workflow called twice / re-entrancy | No stale state leaking from the previous run | P2 | U | GAP |
| TC-TPL-023 | Workflow invokes the `after_template_created` plugin hook on success only | Hook called once with project + template context; hook errors logged, never break creation | P1 | U | GAP |
| TC-TPL-024 | Built-in template inventory is stable (ids, names, min Python, tooling lists) | Snapshot matches the documented catalog (guards accidental template changes) | P2 | U | GAP |

## 2.11 User template store and content filters — `core/templates/user_template_store.py`, `content_filters.py`

Existing coverage: `tests/test_user_template_store.py` (4). Target file for gaps: `tests/test_content_filters.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-TPLU-001 | `generate_template_id("My FastAPI Starter")` | `my-fastapi-starter` | P1 | U | COVERED |
| TC-TPLU-002 | `validate_template_id` for valid id, `../bad`, `BadID`, empty, reserved ids | Only safe lower-case ids accepted; traversal/reserved rejected with `UserTemplateError` | P0 | SEC | COVERED |
| TC-TPLU-003 | `save_template` then `load_user_templates` | Template discoverable, `source="user"`, `variable_style="double_brace"`, project-name token replaced | P1 | I | COVERED |
| TC-TPLU-004 | `save_template` with a reserved built-in id | `UserTemplateError`, nothing written | P1 | SEC | COVERED |
| TC-TPLU-005 | `delete_template` / `template_exists` | Template removed from disk and from subsequent loads; `template_exists` `False` | P2 | I | COVERED |
| TC-TPLU-006 | `inspect_source` exclusions: `.git`, `__pycache__`, `*.pyc`, `.venv`, `node_modules`, `dist`, `build` | All excluded from `included_files`, listed in `excluded_files` | P1 | SEC | PARTIAL (`.git`/`__pycache__` only) |
| TC-TPLU-007 | `inspect_source` sensitive detection: `.env`, `*.pem`, `id_rsa`, `credentials.json`, `*.key`, `*.pfx`, `.aws/credentials` | Every sensitive file reported in `sensitive_files`, never silently imported | P0 | SEC | PARTIAL (`.env` only) |
| TC-TPLU-008 | `inspect_source` on a symlinked file/dir pointing outside the source tree | Symlink target not copied into the template (no data exfiltration) | P0 | SEC | GAP |
| TC-TPLU-009 | `inspect_source` on an empty directory / a single file instead of a directory | Documented error or empty inspection, no crash | P2 | I | GAP |
| TC-TPLU-010 | Binary files (PNG, `.pyc`, `.so`) and very large text files during inspection | Binary skipped/flagged; oversized files handled without loading everything into memory | P1 | I | GAP |
| TC-TPLU-011 | Unicode and space-containing file names inside an imported template | Preserved and re-rendered correctly | P2 | I | GAP |
| TC-TPLU-012 | Saving a template whose project-name token appears in a binary file | Token replacement limited to text files; binary content unchanged | P2 | I | GAP |
| TC-TPLU-013 | Repeated `save_template` with the same id (overwrite policy) | Documented behaviour (overwrite or explicit error) and no orphaned files | P2 | I | GAP |
| TC-TPLU-014 | `inspect_source` never executes code from the inspected project (no `subprocess`, no import) | No process is started and no project module is imported during inspection | P0 | SEC | GAP |

## 2.12 GitHub import and Community templates — `core/templates/github_import.py`, `community.py`

Existing coverage: `tests/test_github_template_import.py` (6), `tests/test_community_templates.py` (4).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-TPLG-001 | `validate_github_repository_url` for `https://github.com/u/p`, `.git`, ssh form, `http://`, extra path segments, query strings, `github.com.evil.com` | Only genuine `github.com` HTTPS repositories normalised to `.git`; everything else rejected | P0 | SEC | PARTIAL (2 positive, 1 negative case) |
| TC-TPLG-002 | `extract_github_repository_name` incl. `.git` suffix and invalid host | Repository slug returned; invalid host raises | P1 | U | COVERED |
| TC-TPLG-003 | `clone_github_repository` when `git` is missing, when clone fails, on success | `GitHubImportError` with an actionable message; success returns the resolved destination | P1 | U | COVERED |
| TC-TPLG-004 | Clone failure leaves no temporary directory behind | Temp clone dir removed on every failure path | P0 | I | GAP |
| TC-TPLG-005 | Clone timeout (hanging git) | Bounded by a timeout, no GUI freeze, temp dir cleaned | P0 | I | GAP |
| TC-TPLG-006 | `CommunityTemplateService.search` builds the documented query/sort and caches identical queries | One HTTP call for repeated identical search; `q` includes `language:Python topic:<category>`; cache key includes all params | P1 | U | COVERED |
| TC-TPLG-007 | Search cache TTL/eviction and invalidation for a different query | Cached result reused only within the TTL; different params hit the network | P2 | U | GAP |
| TC-TPLG-008 | Search: network error, 403 rate limit, 500, malformed JSON, empty items | `CommunityTemplateError` / `CommunityTemplateRateLimitError` with the documented messages; empty list for empty items | P1 | U | COVERED |
| TC-TPLG-009 | `inspect(candidate)` static signals: python project, tests, workflows, environment files, README excerpt | All four flags and the excerpt populated from file inspection only | P1 | I | COVERED |
| TC-TPLG-010 | `inspect` never executes repository content (no `setup.py`/hook execution) | No `subprocess`, no `exec`, no import of repository code during inspection | P0 | SEC | GAP (only asserted indirectly) |
| TC-TPLG-011 | `inspect` on a repository with no README / no Python files | Flags all `False`, excerpt empty, no error | P2 | I | GAP |
| TC-TPLG-012 | `cleanup_inspection(inspection)` | Temporary clone directory removed; a second cleanup is a no-op | P1 | I | COVERED |
| TC-TPLG-013 | `find_existing_import(url)` duplicate-origin detection incl. `.git` and trailing-slash variants | Existing template id returned for equivalent origins; `None` for a new origin | P1 | U | PARTIAL (`.git` variant only) |
| TC-TPLG-014 | Community candidate → user template import end-to-end (mocked clone) | Template saved with source metadata (`source_type="github"`, origin URL), then usable in the creation wizard | P1 | I | GAP |
| TC-TPLG-015 | Import of a repository whose project-name token appears in paths | Token replaced in file names and contents; no unrendered tokens remain | P2 | I | GAP |
| TC-TPLG-016 | Pagination: page 2 request carries the documented `page`/`per_page` params and results do not duplicate page 1 | Pagination params correct, no duplicates | P2 | U | GAP |

## 2.13 Project runtime toggle and registry — `py_env_studio/core/runtime_toggle.py`

Existing coverage: `tests/test_project_runtime.py` (2 cases, **green**). The module was realigned on 2026-09-20
from the non-existent `env_manager.initialize_project_runtime` / `disable_project_runtime` /
`load_project_runtime_state` API to the production API in `py_env_studio/core/runtime_toggle.py`
(`init_project`, `enable_runtime`, `disable_runtime`, `is_runtime_enabled`). Both tests stub virtual-environment
creation and redirect the envs/registry paths into `tmp_path`, so they run in ~0.2 s without touching the real
machine. Target file for the remaining gaps: `tests/test_runtime_toggle.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-RT-001 | `get_project_root()` from a nested directory containing `pes.config` above it | Nearest ancestor holding `pes.config` returned; `None` when absent | P1 | I | GAP |
| TC-RT-002 | `init_project(project_root, python_version)` | `pes.config` created with project name, environment id, path, Python version, package manager; registry updated | P0 | I | PARTIAL (v1.1.0: `pes.config` existence + registry `environment_id` asserted; remaining fields not asserted) |
| TC-RT-003 | `init_project` when already initialised | Idempotent: existing metadata and environment reused, not recreated | P0 | I | COVERED (v1.1.0) |
| TC-RT-004 | `generate_environment_id(project_name)` | Stable, unique, filesystem-safe id (documented pattern, e.g. `<name>-<hash>`) | P2 | U | GAP |
| TC-RT-005 | `enable_runtime` / `disable_runtime` / `is_runtime_enabled` | `runtime_enabled` toggles and persists in `pes.config`; no other metadata lost | P0 | I | COVERED (v1.1.0) |
| TC-RT-006 | `create_managed_environment(env_id, version)` | venv created under `get_envs_dir()`; `get_environment_python` resolves to it on Windows and POSIX | P1 | I | GAP |
| TC-RT-007 | `get_environment_executable(env_path, name)` for `python`/`pip` | Correct `Scripts/*.exe` vs `bin/*` resolution; `None` for a missing executable | P1 | U | GAP |
| TC-RT-008 | `execute_in_managed_env(project_root, ["script.py", "arg1"])` | Runs with the managed interpreter via argument list, returns the child exit code, args passed verbatim | P0 | I | GAP |
| TC-RT-009 | `execute_in_managed_env` when the environment is missing | Documented failure (message + non-zero code) instead of an unhandled exception | P0 | I | GAP |
| TC-RT-010 | `get_project_environment_python(root, auto_init=True)` with no metadata | Environment auto-created and returned; `auto_init=False` returns `None` | P1 | I | GAP |
| TC-RT-011 | `create_runtime_interceptor(project_root)` | Interceptor artefact written under the project; running it twice is safe | P2 | I | GAP |
| TC-RT-012 | `get_project_status()` inside vs outside an initialised project | Documented field set (`initialized`, `project_name`, `project_root`, `runtime_enabled`, `environment_id`, `environment_exists`, `environment_path`, `python_version`) with correct values | P1 | U | GAP |
| TC-RT-013 | `list_registered_projects()` with 0, 1 and many entries + stale (deleted) project paths | All live projects listed with correct status; stale entries flagged/dropped without crash | P1 | I | GAP |
| TC-RT-014 | Corrupted `registry.json` or `pes.config` (invalid TOML/JSON) | Recovered to defaults or reported clearly; no data loss for other projects | P0 | I | GAP |
| TC-RT-015 | Writes to `pes.config` / `registry.json` are atomic | No truncated file when the process is interrupted mid-write (temp file + replace) | P0 | I | GAP |
| TC-RT-016 | *(resolved v1.1.0)* `tests/test_project_runtime.py::test_init_project_creates_environment_once_and_reuses_it` | **Passes:** `init_project` succeeds twice, the managed environment is created exactly once, the environment id is stable, `pes.config` exists, runtime is enabled and the registry records the environment id | P0 | I | **COVERED** |
| TC-RT-017 | *(resolved v1.1.0)* `tests/test_project_runtime.py::test_disable_runtime_turns_runtime_off_and_keeps_environment` | **Passes:** `disable_runtime` reports success, runtime flag is `False` in both `pes.config` and the registry, the environment id is preserved, the managed environment directory still exists, and `enable_runtime` turns the runtime back on | P0 | I | **COVERED** |

## 2.14 Command-line interface — `py_env_studio/commands.py`

Target file for gaps: `tests/test_commands.py` (new). Currently **no** CLI test exists in the suite.

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-CLI-001 | `build_parser()` exposes flags `--create --delete --list --activate --install --uninstall --export --import-reqs --gui --upgrade-pip` and subcommands `init on off status list-projects run` | All options/subcommands present with documented help text | P1 | U | GAP |
| TC-CLI-002 | `dispatch_command` prefers the flag command when both a flag and a subcommand are supplied | Flag handler called exactly once; subcommand ignored | P2 | U | GAP |
| TC-CLI-003 | `main([])` with no arguments | GUI launched (mocked `PyEnvStudio`) — never a traceback | P1 | U | GAP |
| TC-CLI-004 | `main(["script.py", "--flag"])` (bare script path) | Routed to `handle_run` with args preserved | P1 | U | GAP |
| TC-CLI-005 | `handle_list` with zero and several environments | One env name per line, exit code 0 | P1 | U | GAP |
| TC-CLI-006 | `--create demo --upgrade-pip` | `create_env("demo", upgrade_pip=True)` called once | P1 | U | GAP |
| TC-CLI-007 | `--install demo,numpy`, `--uninstall`, `--export`, `--import-reqs` comma parsing | `(env, value)` split on the first comma only (values containing extra commas preserved) | P1 | U | GAP |
| TC-CLI-008 | `_split_two_values("onlyone")` (no comma present) | **Current behaviour:** the documented friendly error path never runs because `str.split()` cannot raise `ValueError`; the unpack error escapes as a traceback. Expected per usage text: clear `Usage: ...` message and exit code 1 | P0 | U | GAP (defect candidate — see audit F-06) |
| TC-CLI-009 | Runtime subcommands `init`, `on`, `off` on success and failure | `result["message"]` printed; exit code `1` when `success` is `False` | P1 | U | GAP |
| TC-CLI-010 | `status` for an initialised vs a non-initialised project | Documented field lines printed; only `Initialized: False` outside a project | P1 | U | GAP |
| TC-CLI-011 | `list-projects` with zero and several registered projects | Readable one-per-line listing | P2 | U | GAP |
| TC-CLI-012 | Unknown option / invalid subcommand | `argparse` usage error, exit code 2, no stack trace | P2 | U | GAP |
| TC-CLI-013 | Entry points `py-env-studio`, `pyenvstudio`, `pes` all map to `py_env_studio.commands:main` | `pyproject.toml` `[project.scripts]` unchanged (contract test) | P2 | U | GAP |
| TC-CLI-014 | `main()` calls `initialize_app_runtime()` exactly once before dispatch | Runtime/bootstrap initialised before any handler runs | P1 | U | GAP |
| TC-CLI-015 | `--export demo,requirements.txt` documented as `env_name,file_path` | CLI help, `docs/getting-started/cli.md` and behaviour agree (documentation consistency check) | P3 | U | GAP |

## 2.15 Configuration, preferences and runtime paths — `core/configuration.py`, `core/runtime.py`

Existing coverage: `tests/test_configuration_service.py` (4 cases).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-CFG-001 | `load_preferences()` with no user config file | Bootstrapped from packaged `config.ini` defaults (`venv_dir`, `preferred_package_manager=pip`, template defaults `True`) | P0 | U | COVERED |
| TC-CFG-002 | `save_preferences` + `load_preferences` round-trip for every field | All fields (venv path, python, manager, project tool, open-with list, template flags, appearance, scaling) preserved | P0 | I | COVERED |
| TC-CFG-003 | `validate_preferences` with `default_package_manager="uv"` while uv is unavailable | `ConfigurationError` raised, preferences not saved | P0 | U | COVERED |
| TC-CFG-004 | `reset_to_defaults()` | Default package manager `pip`, template flags back to `True` | P1 | I | COVERED |
| TC-CFG-005 | `validate_preferences` with an unsupported `ui_scaling` (`"abc"`, `"0%"`, `"500%"`) | Rejected with an actionable message | P1 | U | GAP |
| TC-CFG-006 | `validate_preferences` with a non-existent `default_venv_path` / a path that is a file | Documented behaviour (created or rejected) and consistent GUI feedback | P1 | I | GAP |
| TC-CFG-007 | `validate_preferences` with `default_project_tool` absent from `available_project_tools` | Rejected | P1 | U | GAP |
| TC-CFG-008 | `_normalize_open_with_entries` for `"CMD"`, `"CMD, VSCode"`, `""`, duplicates, whitespace-only | Deterministic list, de-duplicated and ordered, blank entries dropped | P1 | U | GAP |
| TC-CFG-009 | `_parse_bool` for `true/True/1/yes/on`, `false/False/0/no/off`, junk, `None` | Documented coercion; invalid values fall back to the supplied default | P1 | U | GAP |
| TC-CFG-010 | User config file containing invalid INI syntax or unknown keys | Known keys preserved, unknown keys ignored, corrupt file does not crash startup | P0 | I | GAP |
| TC-CFG-011 | `_write_atomic_text` when the target directory is read-only | `ConfigurationError` (or documented error) and the previous config file remains intact | P0 | I | GAP |
| TC-CFG-012 | `AppConfig.get_param` / `set_param` incl. `fallback` for unknown section/option | Value returned/persisted in `config.ini`; fallback returned when missing | P2 | I | GAP |
| TC-CFG-013 | Packaged `config.ini` and `pyproject.toml` declare the same version | Single-source-of-truth consistency assertion | P2 | U | GAP |
| TC-CFG-014 | `runtime.get_runtime_config()` path resolution: relative, absolute, `~`-expanded, missing → default | Data/log/DB/matrix paths resolved per documented precedence | P1 | U | GAP |
| TC-CFG-015 | `refresh_runtime_config()` after the user config changes `venv_dir` | New value returned and consumed by `env_manager.refresh_runtime_paths()` | P1 | I | GAP |
| TC-CFG-016 | Runtime config precedence: user config overrides packaged defaults | Precedence verified with conflicting values in both files | P1 | U | GAP |

## 2.16 Plugin system — `py_env_studio/core/plugins/`

Existing coverage: `tests/test_plugin_import.py`, `test_plugin_load.py`, `test_plugin_events.py` are script-style (pytest collects **0** tests; they print and only exit non-zero when an exception escapes). Target file for gaps: `tests/test_plugin_manager.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-PLG-001 | `PluginManager(plugins_dir=tmp_path)` + `discover_plugins()` with 0/1/many valid plugins | Discovered names returned; ordering stable; no writes outside the directory | P1 | I | GAP |
| TC-PLG-002 | `load_plugin(name)` for a valid plugin | Plugin instance returned, metadata readable, `is_initialized()` `True` after `initialize(app_context)` | P1 | I | GAP |
| TC-PLG-003 | Plugin manifest missing required metadata (name/version/entry point) | `PluginValidationError`, plugin not loaded, other plugins unaffected | P0 | U | GAP |
| TC-PLG-004 | Plugin module with a syntax/import error | `PluginLoadError`, application does not crash, error logged once | P0 | I | GAP |
| TC-PLG-005 | Plugin that does not subclass `BasePlugin` | `PluginValidationError` | P1 | U | GAP |
| TC-PLG-006 | `execute_hook("on_env_create", ctx)` with subscribers | Every subscribed plugin invoked once with the context dict | P0 | U | GAP |
| TC-PLG-007 | One plugin raises inside a hook | Exception contained/logged, remaining plugins still execute, app continues | P0 | U | GAP |
| TC-PLG-008 | `execute_hook` for a hook with no subscribers | No-op, no error | P2 | U | GAP |
| TC-PLG-009 | Hook coverage: `on_env_create`, `on_env_delete`, `on_env_rename`, `on_env_activate`, `on_package_install`, `on_package_uninstall`, `on_package_update`, `on_scan_complete`, `on_template_created`, `on_app_start`, `on_app_shutdown` | Each documented hook is dispatched from its core call site | P1 | I | GAP |
| TC-PLG-010 | `set_plugin_enabled` / `is_plugin_enabled_state` / `get_enabled_plugins_list` across manager instances | State survives a new `PluginManager` (state file) | P0 | I | GAP |
| TC-PLG-011 | Corrupted plugin state JSON file | Manager falls back to defaults without crashing | P0 | I | GAP |
| TC-PLG-012 | `load_enabled_plugins(list)` containing one failing plugin | Other enabled plugins still load; failures reported | P1 | I | GAP |
| TC-PLG-013 | `unload_plugin(name)` | Hooks unregistered, `get_plugin` returns `None`, later dispatch skips it | P1 | U | GAP |
| TC-PLG-014 | `get_all_plugins` / `get_plugin_metadata` / `is_plugin_enabled` for known and unknown names | Documented results, no `KeyError` | P2 | U | GAP |
| TC-PLG-015 | Plugin `cleanup()` during `on_app_shutdown` | Called exactly once per loaded plugin | P2 | U | GAP |
| TC-PLG-016 | `examples/sample_plugin` satisfies the documented plugin contract | Sample plugin loads, exposes metadata, documented example hooks run | P2 | I | GAP |
| TC-PLG-017 | Discovery ignores stray files/folders and never imports from outside `plugins_dir` | Only valid plugin packages considered; no path escape | P0 | SEC | GAP |

## 2.17 Database and data helpers — `core/database.py`, `utils/handlers.py`

Target file for gaps: `tests/test_database.py` (new). Every case must use a `db_path` inside `tmp_path` (never the real `PlatformDirs` location).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-DB-001 | `DatabaseManager(db_path=tmp_path/"x.db").initialize_database()` | Tables `environments` and `env_vulnerability_info` created with the documented columns/FK | P0 | I | GAP |
| TC-DB-002 | `initialize_database()` called twice | Idempotent, existing data preserved | P0 | I | GAP |
| TC-DB-003 | `_migrate_legacy_schema` on a legacy DB fixture | Missing columns/status fields added, existing rows preserved, no destructive loss | P0 | I | GAP |
| TC-DB-004 | `connect()` when the directory is read-only/locked | `DatabaseError` with an actionable message; no partial schema | P0 | I | GAP |
| TC-DB-005 | `db_exists()` / `get_db_path()` before and after initialisation | `False`/`True` and the resolved path | P2 | U | GAP |
| TC-DB-006 | Parameterised write/read round-trip incl. a value containing quotes/SQL text | Value stored verbatim (no injection, no syntax error) | P0 | SEC | GAP |
| TC-DB-007 | `DataHelper.get_or_create_env` called twice for the same env | Single record reused, no duplicate rows | P1 | I | GAP |
| TC-DB-008 | `DataHelper.save_vulnerability_info` / `get_vulnerability_info` round-trip, incl. non-ASCII content | JSON payload returned unchanged | P1 | I | GAP |
| TC-DB-009 | `DBHelper` and `DataHelper` for the same env | Documented precedence (DB vs JSON fallback) with no duplicated source of truth drifting | P1 | I | GAP |
| TC-DB-010 | Reading vulnerability info for an unknown env | Empty/"no data" result, no exception | P2 | U | GAP |

## 2.18 Py-Tonic learning support — `py_env_studio/core/py_tonic.py`

Existing coverage: script-style check inside `tests/test_all_features.py` (non-asserting). Target file for gaps: `tests/test_py_tonic.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-LRN-001 | `default_py_tonic_profile()` | Documented keys: topics, notification mode, learning mode, notified timestamps, completed challenges | P1 | U | GAP |
| TC-LRN-002 | `load_py_tonic_profile()` when the profile file does not exist | Defaults returned and no file written as a side effect of a read | P1 | I | GAP |
| TC-LRN-003 | `load_py_tonic_profile()` for a corrupt/partial JSON profile | Sanitised defaults, unreadable keys replaced, no crash | P0 | I | GAP |
| TC-LRN-004 | `sanitize_py_tonic_profile` with invalid topic, notification mode, learning mode, score types | Only documented values retained; invalid ones reset to defaults | P1 | U | GAP |
| TC-LRN-005 | `save_py_tonic_profile` + reload round-trip | Profile persisted in the platform user-data location; values identical | P1 | I | GAP |
| TC-LRN-006 | `should_notify` for `daily`, `weekly`, `manual` and for just-notified profiles | `daily` once per day, `weekly` once per 7 days, `manual` never auto-notifies; boundary timestamps respected | P1 | U | GAP |
| TC-LRN-007 | `mark_notified(profile)` | Timestamp updated and persisted; does not clear completed challenges | P2 | U | GAP |
| TC-LRN-008 | `get_random_challenge(profile)` with only `core_python` or only `python_django` enabled | Only challenges from enabled topics returned (deterministic with a seeded RNG) | P1 | U | GAP |
| TC-LRN-009 | `evaluate_challenge_answer(challenge, answer)` for correct, incorrect, differently-cased and whitespace-padded answers | Correct/incorrect verdict per documented comparison rules | P1 | U | GAP |
| TC-LRN-010 | `get_py_tonic_advice(action)` for every documented action (`general`, install, uninstall, update, scan, template) | Non-empty topic-specific advice, no `KeyError` for unknown action (falls back to general) | P2 | U | GAP |
| TC-LRN-011 | Strict learning mode enforcement callback | Blocking action returns the expected signal and surfaces the challenge dialog path (GUI) | P2 | GUI | GAP |
| TC-LRN-012 | `_parse_iso` for valid ISO strings, `None`, empty and malformed values | `None` or a timezone-aware datetime per documented contract, never an exception | P2 | U | GAP |

## 2.19 Setup state, bootstrap and platform integration — `core/setup_state.py`, `core/bootstrap.py`, `core/windows_apps.py`

Target file for gaps: `tests/test_setup_state.py` (new). `tests/setup/state.py` is a duplicate implementation used by an uncollected GUI script — it must not be treated as the test target.

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-STA-001 | `SetupStateManager()` state directory resolution (mocked `PlatformDirs`) | Uses `PlatformDirs(APP_NAME).user_data_dir/state`, created on demand | P1 | U | GAP |
| TC-STA-002 | `create_installing_marker()` → `check_installation_health()` | `"installing"` while the marker is fresh | P1 | I | GAP |
| TC-STA-003 | Fresh marker older than `INSTALL_TIMEOUT` (mtime back-dated) | `"recover"` | P1 | I | GAP |
| TC-STA-004 | `mark_setup_complete()` | Sentinel written, installing marker removed, health `"complete"` | P0 | I | GAP |
| TC-STA-005 | `mark_setup_failed("reason")` | Failure marker written with the reason, installing marker removed, health `"failed"` | P0 | I | GAP |
| TC-STA-006 | Health for missing sentinel / version drift (`CURRENT_VERSION` bumped) | `"missing"` / `"migrate"` respectively | P1 | I | GAP |
| TC-STA-007 | `is_complete()` / `needs_migration()` with schema newer than `CURRENT_SCHEMA` and older `appVersion` | `True`/`False` per documented schema/version rules | P1 | U | GAP |
| TC-STA-008 | `_read_json` on a truncated/corrupt state file | `None` returned, no exception, next write succeeds | P0 | I | GAP |
| TC-STA-009 | `_write_atomic` interrupted (simulated write failure) | Target file unchanged or absent, temp file cleaned up | P0 | I | GAP |
| TC-STA-010 | `bootstrap.initialize_app_runtime()` on a clean environment (temp dirs mocked) | Required directories, database and setup state initialised; documented value returned | P0 | I | GAP |
| TC-STA-011 | `initialize_app_runtime()` called twice | Idempotent, no duplicate/overwritten data | P1 | I | GAP |
| TC-STA-012 | `windows_apps.ensure_windows_apps_shortcut()` on Windows (shortcut creation mocked) | Shortcut created with the PES icon; no exception when already present | P2 | U | GAP |
| TC-STA-013 | `ensure_windows_apps_shortcut()` on non-Windows | Documented no-op, no exception | P2 | U | GAP |
| TC-STA-014 | `_resolve_python_gui_executable()` / `_resolve_icon_path()` for frozen (PyInstaller) vs source execution | Correct executable/icon resolution in both modes; `None` when the icon is genuinely missing | P2 | U | GAP |

## 2.20 GUI layer — `py_env_studio/ui/main_window.py`

Target file for gaps: `tests/test_main_window_smoke.py` (new, GUI-marked; skipped when no display). These cases are the GUI acceptance checklist for the Windows desktop build.

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-UI-001 | Application starts (`PyEnvStudio()`) with a temp config/venv dir | Window builds, Environment tab active, no exception, no modal error dialog | P0 | GUI | GAP |
| TC-UI-002 | Environment table refresh after create/delete/rename | Table reflects the current environment list; empty state handled without error | P0 | GUI | GAP |
| TC-UI-003 | Search box filters the environment table live; clearing restores all rows | Case-insensitive filtering; no crash on regex-special characters | P1 | GUI | GAP |
| TC-UI-004 | Double-click on an environment row | Activation workflow triggered for that env only | P1 | GUI | GAP |
| TC-UI-005 | "Copy recent location" action | Clipboard contains the recent location and the working-directory field is pre-filled | P2 | GUI | GAP |
| TC-UI-006 | Create-environment flow with detected and manually browsed Python | Environment created, log streamed to the console, UI not blocked | P0 | GUI | GAP |
| TC-UI-007 | "Show detected version" after selecting a Python path | Reported version matches the interpreter; invalid path shows a clear warning | P2 | GUI | GAP |
| TC-UI-008 | Install / update / uninstall a package from the package tab | Correct operation executed, console logs streamed, list refreshed on completion | P0 | GUI | GAP |
| TC-UI-009 | Install with a dependency conflict (AutoResolver path) | Retry messages visible in the console; final success/failure reported accurately | P1 | GUI | GAP |
| TC-UI-010 | Bulk "check for updates" + batch update of several packages | All selected packages updated, per-package result reported, no UI freeze | P1 | GUI | GAP |
| TC-UI-011 | Import requirements / export packages | Dialogs default correctly, missing paths handled, cancellation is a clean no-op | P1 | GUI | GAP |
| TC-UI-012 | A long-running task while a second action is requested | UI stays responsive; unsupported re-entrancy is prevented or queued | P1 | GUI | GAP |
| TC-UI-013 | Console log queues are drained and never grow unbounded | Drained per tab; no `Tcl` callback error after window close | P2 | GUI | GAP |
| TC-UI-014 | Appearance mode switch (Light/Dark/System) + UI scaling change | Applied immediately and persisted; tables/charts follow the theme | P2 | GUI | GAP |
| TC-UI-015 | Preferences dialog: apply / save / cancel / reset | Apply updates the running app, cancel discards changes, reset restores documented defaults | P1 | GUI | GAP |
| TC-UI-016 | Open-With tools management (`add_open_with_tool`) | Tool added/removed from the dropdown and persisted to config | P2 | GUI | GAP |
| TC-UI-017 | Plugins dialog: enable / disable / reload a plugin | Plugin loads/unloads, state persisted, errors shown as a dialog not a traceback | P1 | GUI | GAP |
| TC-UI-018 | Templates menu: preview + wizard + "project created" prompt + failed-open recovery | Wizard creates the project, prompt offers open-in-editor, failures offer retry/choose-another | P1 | GUI | GAP |
| TC-UI-019 | Manage Templates: add from local project, add from GitHub, delete user template | Import shows a metadata preview before saving; deletion requires confirmation | P1 | GUI | GAP |
| TC-UI-020 | Community Templates dialog: search, category filter, sort, pagination, error states | Results paginate; rate-limit/network errors are user-friendly; no repository code executed | P1 | GUI | GAP |
| TC-UI-021 | Vulnerability report + scan now + insights dashboard for a selected env | Report/dashboard open for the correct env; scan progress shown; failures clear | P1 | GUI | GAP |
| TC-UI-022 | Every window/dialog shows the PES icon (`tests/test_window_icon.py` checks) | Icon applied to main window, CTkToplevel dialogs, plugin windows and the dashboard | P2 | GUI | MANUAL (script not collected by pytest) |
| TC-UI-023 | Closing the app (`on_closing`) | Prompt if work is running, plugins shut down, resources released, no lingering process | P1 | GUI | GAP |
| TC-UI-024 | GUI callbacks never run long tasks on the Tk thread (`run_async` used) | No blocking call in a button callback path (static review + instrumented smoke test) | P1 | GUI | GAP |

## 2.21 Shared utilities — `utils/app_icon.py`, `core/strategies.py`, `core/integration.py`, `core/project_launcher.py`, `core/tools.py`

Existing coverage: `tests/test_project_openers.py` (5), `tests/test_window_icon.py` (script, not collected). Target file for gaps: `tests/test_utilities.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-UTIL-001 | `get_app_icon_path()` | Returns the packaged `pes-transparrent-icon-default.ico`; filesystem fallback when not frozen | P1 | U | MANUAL |
| TC-UTIL-002 | `apply_window_icon(window)` with `None`, a destroyed window, a missing icon file | `False` without raising; genuine success returns `True` | P1 | U | MANUAL |
| TC-UTIL-003 | `install_window_icon_hook()` called twice | Hook installed once (marker attribute), no duplicate patching | P2 | U | MANUAL |
| TC-UTIL-004 | `schedule_window_icon(window)` delayed re-apply survives the CustomTkinter icon update | `_pes_window_icon_photo` still present after the delay elapses | P2 | GUI | MANUAL |
| TC-UTIL-005 | `discover_project_open_tools(open_with_names, include_default)` | Reuses configured open-with tools, appends detected tools, adds `default` last, de-duplicates by `tool_id` | P1 | U | COVERED |
| TC-UTIL-006 | `find_tool_by_id` and `open_project_with_tool` for available vs unavailable tool | Project path passed as the second argv element; unavailable tool raises `RuntimeError`; `OSError` propagates for recovery UX | P1 | U | COVERED |
| TC-UTIL-007 | `open_project_with_tool` uses an argument list (no `shell=True`) | `shell` never enabled; paths with spaces handled | P0 | SEC | PARTIAL |
| TC-UTIL-008 | `strategies.run_strategy("venv_injection", ...)` injects the env `Scripts`/`bin` into `PATH` and sets cwd | Environment variables and cwd match the strategy contract | P1 | U | GAP |
| TC-UTIL-009 | `strategies.run_strategy("shell_activation", ...)` | Shell activation command built as documented (no user input concatenated into a shell string) | P1 | SEC | GAP |
| TC-UTIL-010 | `run_strategy` with an unregistered strategy name | Documented error, no silent no-op | P2 | U | GAP |
| TC-UTIL-011 | `integration.detect_tools()` / `_which` with mocked `shutil.which` | Detected tools mapped to the documented `strategy` per tool; missing tools skipped | P1 | U | GAP |
| TC-UTIL-012 | `integration.detect_tools()` when nothing is installed | Empty list, no exception | P2 | U | GAP |
| TC-UTIL-013 | `version_utils` unit cases (TC-ST-001, TC-ST-002) are reused by dashboard table sorting | Shared helper reused, no duplicated comparison logic | P2 | U | GAP |
| TC-UTIL-014 | `tools.py` helper surface is importable and side-effect free | Import performs no filesystem/network work | P3 | U | GAP |
| TC-UTIL-015 | Version consistency: `pyproject.toml`, `py_env_studio/config.ini` and `docs/releases` | All declare the same version | P2 | U | GAP |
| TC-UTIL-016 | Dependency consistency: `pyproject.toml` `dependencies` vs `py_env_studio/requirements.txt` (and the stale `py_env_studio.egg-info/requires.txt`) | Declared third-party packages agree; stale generated metadata does not contradict the runtime dependency set | P2 | U | GAP |
| TC-UTIL-017 | PyInstaller specs (`py_env_studio/main.spec`, `PyEnvStudio.spec`) bundle `tkinter_dash` and icon resources, and reference no removed dependency | Specs stay in sync with `pyproject.toml` | P2 | U | GAP |
| TC-UTIL-018 | `docs/reference/features.md` feature list is fully covered by catalog IDs | Every documented feature maps to at least one test case ID (traceability check) | P3 | U | GAP |

## 2.22 Non-functional requirements — determinism, security, cross-platform, performance

Target file for gaps: `tests/test_nfr_guards.py` (new).

| ID | Test case | Expected result | Pri | Type | Status |
|---|---|---|---|---|---|
| TC-NFR-001 | Static guard: no module under `py_env_studio/` calls `subprocess.*` with `shell=True` | Zero hits (argument-list process execution only) | P0 | SEC | GAP |
| TC-NFR-002 | Static guard: no `os.system` / `eval` / `exec` on untrusted input in core modules | Zero hits | P0 | SEC | GAP |
| TC-NFR-003 | Static guard: no `matplotlib` import anywhere in `py_env_studio/` (migration to `tkinter-dash`) | Zero hits; `tkinter_dash` declared in both dependency files | P1 | U | PARTIAL (asserted for the insights module only) |
| TC-NFR-004 | Independent test run: `pytest tests/` with networking blocked | Suite passes without internet (all HTTP mocked) | P0 | U | GAP |
| TC-NFR-005 | Independent test run: `pytest tests/` with `HOME`/`APPDATA`/`LOCALAPPDATA` redirected to a temp dir | Suite passes and writes nothing to the real user profile | P0 | U | GAP |
| TC-NFR-006 | Independent test run: `pytest tests/` twice in a row | Identical results (no order dependence, no leftover state) | P0 | U | GAP |
| TC-NFR-007 | Randomised test order shows no inter-test coupling | Suite passes in at least two different orders | P1 | U | GAP |
| TC-NFR-008 | Path handling: every public API accepts `pathlib.Path` and `str` and uses `Path` internally | Identical behaviour for both input types; Windows/POSIX separators handled | P1 | U | GAP |
| TC-NFR-009 | Unicode paths and env names (e.g. `проект`, `环境`, `münchen`) through env create / template / export flows | Works on Windows and POSIX; no `UnicodeEncodeError` | P2 | I | GAP |
| TC-NFR-010 | Environment listing performance with 200+ env directories | `list_envs()` + size calculation stay within a documented budget (sizes stubbed) | P2 | PERF | GAP |
| TC-NFR-011 | Scanning 100 packages issues sequential API calls with no unbounded concurrency | Request count equals package count; no thread explosion | P2 | PERF | GAP |
| TC-NFR-012 | Secrets are never logged: `.env`/token values absent from logs and console during import/scan/install flows | Log-capture assertion finds no secret values | P0 | SEC | GAP |
| TC-NFR-013 | Every user-supplied name (env, project, template, package, GitHub URL) is validated at the entry point | Boundary validation matrix passes for all entry points | P0 | SEC | GAP |
| TC-NFR-014 | Every external-process call has a timeout or is guaranteed non-hanging | `git clone` and pip/uv calls bounded; review list attached to the audit | P1 | SEC | GAP |
| TC-NFR-015 | Failure of an external service (PyPI/deps.dev/OSV/GitHub) never leaves the app broken | Clear user message, retry works, no partial DB writes | P0 | I | GAP |
| TC-NFR-016 | Tests are deterministic: no sleep-based racing, no real network, no real profile writes, no real venv mutation | Static/measured guard across the suite | P1 | U | GAP |

## 3. Fixture and mocking strategy (needed before implementing the gaps)

The following shared fixtures are required so that the gap cases above can be implemented deterministically
(master instructions §12: no internet, no developer machine state, no user-specific paths).

| Fixture (new `tests/conftest.py`) | Purpose | Used by |
|---|---|---|
| `pes_home(tmp_path, monkeypatch)` | Redirect `PlatformDirs`-based user data/log/db/venv locations into `tmp_path`; also set `VENV_DIR`/`DATA` env overrides used by `runtime.py`. Asserts nothing outside `tmp_path` is written. | All I/E2E cases (CFG, STA, RT, DB, LRN, SEC, ENV) |
| `fake_python_env(tmp_path)` | Creates a fake venv layout (`pyvenv.cfg`, `Scripts|bin/python`) so env-dependent code runs without a real interpreter. | ENV, PIP, PMGR, UV |
| `run_result(returncode, stdout, stderr)` | Factory returning a `subprocess.CompletedProcess`-like object for mocked process calls. | PIP, UV, AR, TPL (git), TPLG (git) |
| `fake_process(monkeypatch)` | Patches the single process-execution entry point(s) and records argv/kwargs (asserts `shell` never `True`). | PIP, UV, AR, TPL, TPLG, UTIL, NFR |
| `fake_session(*responses)` | Fake HTTP session for PyPI / deps.dev / OSV / GitHub (extends the existing `FakeSession` pattern in `tests/test_community_templates.py`). | SEC, TPLG |
| `sqlite_manager(tmp_path)` | `DatabaseManager(db_path=tmp_path/"pes.db")` with schema initialised. | DB, SEC, ST, DASH |
| `sample_matrix()` / `sample_scan_payload()` | Reusable vulnerability payloads (with/without fix, all severities, string counts) — the payload shape already used by `test_vulnerability_insights_charts.py`. | SEC, ST, DASH |
| `plugin_dir(tmp_path)` | Temporary plugins directory with a valid, an invalid and a broken plugin. | PLG |
| `gui_root` (GUI marker) | Creates/destroys a hidden `ctk.CTk()` root and pumps events; skipped when no display is available. | UI, DASH, UTIL |
| `pytest.ini`/`pyproject` markers | Register `gui` and `e2e` markers; default run excludes them (`-m "not gui and not e2e"`). | Whole suite |

Recommended supporting changes (tracked, not implemented here):
`tests/conftest.py` (new), `[tool.pytest.ini_options]` in `pyproject.toml` with `testpaths = ["tests"]`,
`addopts = "-m 'not gui and not e2e'"`, `markers = ["gui", "e2e"]`, plus a GitHub Actions workflow that runs
`pytest tests` on the supported Python versions (Windows + Ubuntu). Today the only workflow is `.github/workflows/publish.yml`,
which never runs tests.

## 4. Catalog summary and traceability

### 4.1 Case counts by status (baseline, revision `8d11de4`)

| Status | Count | Interpretation |
|---|---|---|
| COVERED | 39 | Executing automated test with assertions, currently passing |
| PARTIAL | 10 | Only part of the acceptance criteria is asserted |
| MANUAL | 12 | Script-style checks that pytest does not collect (run only by hand) |
| **RED** | **0** | No failing automated test remains (was 2 before the v1.1.0 fix) |
| GAP | 272 | No automated test at all |
| **Total** | **339** | |

### 4.2 Case counts by area

| Area | Cases | Area | Cases |
|---|---|---|---|
| ENV | 26 | TPL | 24 |
| PIP | 14 | TPLU | 14 |
| UV | 10 | TPLG | 16 |
| PMGR | 6 | RT | 17 (4 COVERED, 1 PARTIAL) |
| AR | 13 | CLI | 15 |
| DP | 11 | CFG | 16 |
| SEC | 16 | PLG | 17 |
| ST | 10 | DB | 10 |
| DASH | 20 | LRN | 12 |
| STA | 14 | UI | 24 |
| UTIL | 18 | NFR | 16 |

### 4.3 Feature → catalog traceability (`docs/reference/features.md`)

| Documented feature group | Catalog areas |
|---|---|
| Environment management | ENV, RT |
| Package and dependency management | PIP, UV, PMGR, AR, DP |
| Security insights (scan, dashboard, remediation) | SEC, ST, DASH |
| Project templates (built-in, user, GitHub, community) | TPL, TPLU, TPLG |
| Runtime-managed projects and CLI | RT, CLI |
| Configuration and personalization | CFG, UI |
| Plugins and learning support | PLG, LRN |
| Platform support and installation resilience | STA, UTIL, NFR |

## 5. Out of scope for this baseline

- No production code was changed and **no bug found by this audit was fixed** (per the request to not resolve issues now).
- One existing test file was realigned in v1.1.0 to resolve the two RED cases
  (`tests/test_project_runtime.py` → production `runtime_toggle` API). No other test was added, and the
  remaining GAP/PARTIAL/MANUAL cases in §2 are still to be implemented.
- Load/stress testing at production scale, packaging/installer verification (PyInstaller frozen build),
  and macOS/Linux desktop verification are not covered at this stage; macOS/Linux cases are limited to
  platform-branching logic (TC-STA-013, TC-NFR-008, TC-NFR-009).

## 6. Revision history

| Version | Date | Change |
|---|---|---|
| 1.1.0 | 2026-09-20 | Resolved the two RED cases (TC-RT-016, TC-RT-017) by realigning `tests/test_project_runtime.py` with `core/runtime_toggle.py`. Measured suite result: 79 passed, 1 skipped, 1 warning (18.44 s), exit 0. Catalog: RED 2 → 0, COVERED 37 → 39 (TC-RT-016, TC-RT-017). TC-RT-003 and TC-RT-005 were already COVERED before this fix; TC-RT-002 was already PARTIAL; net PARTIAL unchanged at 10. Counts updated in §4. |
| 1.0.0 | 2026-09-20 | Initial audit baseline catalog: 339 cases across 22 areas derived from `docs/reference/features.md`, `docs/getting-started/cli.md`, `README.md`, `.github/agent-context/feature-ledger.md` and the public API inventory of `py_env_studio/`. |
