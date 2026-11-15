# Py Env Studio UI State Fix Report

## Changed files

- `py_env_studio/ui/main_window.py`
- `tests/test_ui_state_consistency.py`
- `ui-state-fix-report.md`

## Root causes and changes

### Package request identity

Package loads already had a generation token, but callbacks did not verify that the captured environment was still selected. An in-flight load for A could therefore render after the user selected B if no newer package load had advanced the generation.

Each request now records its target in `_package_list_env_name`. Success and failure callbacks share `_package_request_is_current`, which validates generation, selected environment, displayed environment, and that the target still exists. A newly selected environment refreshes an open package pane. Package row click handlers also confirm that the selected and displayed environment still match the environment captured when those rows were built.

### Environment selection synchronization

Mouse click paths and keyboard Treeview selection previously updated different subsets of selection state. Refresh restoration selected the row without updating the directory field or dependent labels, and a missing row left the prior context in place.

`_select_environment` now synchronizes selected name, recent directory, activation state, package header, and package-pane invalidation/refresh. Mouse selection, keyboard selection, and `_restore_environment_selection` all use it. Missing or invalid selections clear the directory, disable activation, clear package content, and discard outstanding package callbacks. A missing recent-location marker (`-`) is normalized to an empty directory.

## Tests executed

Command:

```text
.\.venv\Scripts\python.exe -m pytest tests/test_ui_state_consistency.py tests/test_status_progress.py -q
```

Result: **23 passed in 0.79s**.

The new regression tests cover an A result arriving after selection changes to B, refreshing a visible package pane for B, keyboard selection updating the location, refresh restoration synchronizing location and controls, deleted environment cleanup, and stale success/failure callbacks leaving the current package view unchanged.

An exploratory run also included `tests/test_ui_backend.py`. Its two backend tests failed because `py_env_studio.ui.backend` cannot be imported in this checkout; the other seven tests in that run passed. The test-double failures seen in that initial run were corrected, and the final focused command above passed. No claim is made that `tests/test_ui_backend.py` passed.

## Scope

No database, filesystem, subprocess, package-management, or unrelated UI behavior was changed. Background package execution and Tk callback marshalling remain on the existing `run_in_background` path. The existing package-list generation check remains in place and is now combined with environment identity validation.
