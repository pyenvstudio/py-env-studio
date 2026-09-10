# Auto-Resolve Architecture & Flow Diagrams

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PyEnvStudio UI                              │
│                   (main_window.py)                              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ install_package()
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Package Manager Interface                           │
│                (package_manager.py)                             │
│                                                                 │
│  • Detects environment's package manager (pip or uv)           │
│  • Routes to appropriate tool (pip_tools or uv_tools)          │
│  • Passes log_callback for console output                      │
└──────────────┬──────────────────────────────────┬───────────────┘
               │                                  │
               │ pip branch                       │ uv branch
               ▼                                  ▼
    ┌──────────────────────┐          ┌──────────────────────┐
    │   pip_tools.py       │          │   uv_tools.py        │
    │                      │          │                      │
    │  install_package()   │          │install_package_uv()  │
    └──────────┬───────────┘          └──────────┬───────────┘
               │                                  │
               └─────────────────┬────────────────┘
                                 │
                                 │ Calls auto_resolve_install()
                                 ▼
            ┌──────────────────────────────────────────┐
            │      auto_resolve.py (NEW)               │
            │                                          │
            │  • Detects ResolutionImpossible errors  │
            │  • Strips version constraints            │
            │  • Retries installation (up to 3x)       │
            │  • Logs all attempts                     │
            │  • Returns success/failure               │
            └─────────────────┬──────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │  pip/uv subprocess   │
                    │  execution           │
                    └──────────────────────┘
```

## Installation Flow Diagram

```
START: User requests package installation
│
├─ Input: package_spec (e.g., "django==4.2")
│
▼
┌────────────────────────────────────────────────┐
│ ATTEMPT 1: Install with exact version         │
│ Command: pip install django==4.2              │
└──────────────┬─────────────────────────────────┘
               │
               ├─ Success ──┐
               │            │
               │ Failure    │
               ▼            │
        ┌──────────────────┐│
        │ Error detected?  ││
        │ (is_resolution   ││
        │  _error?)        ││
        └────────┬─────────┘│
                 │          │
              No │          │ Yes
                 │          │
                 ▼          │
           ┌─────────────────┐
           │  Return Error   │
           │  (Failure)      │
           └─────────────────┘
                 ▲            
                 │            
                 │ (retry exhausted)
                 │
                 └──────────────────┐
                                    │
                 ┌──────────────────┘
                 │
                 ▼ Yes (retry possible)
        ┌────────────────────────────────┐
        │ Strip version constraints      │
        │ "django==4.2" → "django"       │
        └────────┬──────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────┐
        │ ATTEMPT 2: Install without ver │
        │ Command: pip install django    │
        └────────┬──────────────────────┘
                 │
                 ├─ Success ──┐
                 │            │
                 │ Failure    │
                 ▼            │
          ┌──────────────────┐│
          │ Error detected?  ││
          │ (is_resolution   ││
          │  _error?)        ││
          └────────┬─────────┘│
                   │          │
                   │  No      │ Yes
                   │          │
                   ▼          │
            ┌────────────────┐│
            │ Return Error   ││
            │ (Failure)      ││
            └───────────────┘│
                             │
                  ┌──────────┘
                  │
                  ▼ (if retry_count < 3)
        ┌────────────────────────────────┐
        │ ATTEMPT 3: Retry again         │
        │ Same as attempt 2              │
        └────────┬──────────────────────┘
                 │
                 ├─ Success ──┐
                 │            │
                 │ Failure    │
                 ▼            │
          ┌──────────────────┐│
          │ Exhausted?       ││
          │ retry_count == 3 ││
          └────────┬─────────┘│
                   │          │
                Yes│          │ (always after 3)
                   │          │
                   ▼          │
            ┌──────────────────┐
            │ Return Error     │
            │ "Max retries     │
            │  reached"        │
            └──────────────────┘
                   ▲            
                   │            
                   └────────────┘

Success paths all lead to:
│
▼
┌──────────────────────────────────────────┐
│ RETURN SUCCESS                           │
│ Package installed (possibly different    │
│ version than requested, but compatible)  │
└──────────────────────────────────────────┘
│
│
▼
END
```

## Error Detection Flow

```
Error Output from pip/uv
         │
         ▼
    ┌─────────────────────────────────────┐
    │ Check for resolution keywords:      │
    │                                     │
    │ • ResolutionImpossible              │
    │ • dependency-resolution             │
    │ • dependency conflict               │
    │ • conflicting dependencies          │
    │ • No matching distribution          │
    │ • has requirement                   │
    │ • but you have                      │
    └──────────────┬──────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼ Match             ▼ No Match
    ┌─────────┐          ┌──────────┐
    │ RETRY   │          │ FAIL     │
    │ needed  │          │ (return) │
    └─────────┘          └──────────┘
```

## State Machine

```
                    ┌──────────────────────────┐
                    │   INITIAL STATE          │
                    │   retry_count = 0        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   ATTEMPT (try 1, 2, or 3)
                    │   Execute install cmd    │
                    └────────────┬─────────────┘
                                 │
                         ┌───────┴────────┐
                         │                │
                    Success            Failure
                         │                │
                         ▼                ▼
                    ┌─────────┐    ┌─────────────────┐
                    │ SUCCESS │    │ ERROR DETECTED? │
                    │  STATE  │    └────────┬────────┘
                    └─────────┘             │
                                    ┌───────┴───────┐
                                    │               │
                                   No              Yes
                                    │               │
                                    ▼               ▼
                            ┌──────────┐   ┌───────────────────┐
                            │ FAIL     │   │ Check retry_count │
                            │  STATE   │   └────────┬──────────┘
                            └──────────┘           │
                                                   ├─ < 3 ───┐
                                                   │         │
                                                   └─ = 3 ───┐
                                                             │
                                                   ┌─────────┴────┐
                                                   │              │
                                              Continue         Max
                                              Retry           Reached
                                                   │              │
                                                   ▼              ▼
                                            ┌────────────┐  ┌──────────┐
                                            │ increment  │  │  FAIL    │
                                            │ retry      │  │  STATE   │
                                            │ (→ ATTEMPT)│  └──────────┘
                                            └────────────┘
```

## Version Constraint Removal Process

```
Input: "django==4.2"
         │
         ▼
    ┌──────────────────────────────────────┐
    │ extract_package_name()               │
    │ Regex: ^([a-zA-Z0-9\-_\.]+)         │
    │ Matches: "django"                    │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │ Remove operators:                    │
    │ ==, >=, <=, ~=, !=, >, <             │
    └──────────────┬───────────────────────┘
                   │
                   ▼
Output: "django"
         (ready for retry)
```

## Logging Sequence

```
┌─────────────────────────────────────────────────────────┐
│ Log Sequence Example                                    │
├─────────────────────────────────────────────────────────┤
│ Installing django==4.2 in my_env                       │
│ ...                                                     │
│ ERROR: ResolutionImpossible: ...                       │
│                                                         │
│ [Auto-Resolve] Detected dependency conflict,           │
│                attempting auto-resolve...              │
│ [Auto-Resolve] Attempt 1: Installing 'django'          │
│                without version constraints             │
│ ...                                                     │
│ Successfully installed Django-3.2.13                    │
│                                                         │
│ [Auto-Resolve] ✓ Successfully installed 'django'       │
└─────────────────────────────────────────────────────────┘
```

## Configuration Impact

```
config.ini: auto_resolve_dependencies = true
                        │
                        ▼
            ┌──────────────────────┐
            │ Auto-resolve enabled │
            │ (default behavior)   │
            └──────────┬───────────┘
                       │
                       ▼ (on error)
            ┌──────────────────────┐
            │ Retry automatically  │
            │ User sees retries    │
            │ Package installs     │
            └──────────────────────┘


config.ini: auto_resolve_dependencies = false
                        │
                        ▼
            ┌──────────────────────┐
            │ Auto-resolve disabled│
            │ (future feature)     │
            └──────────┬───────────┘
                       │
                       ▼ (on error)
            ┌──────────────────────┐
            │ Return error to user │
            │ User handles it      │
            │ Manual retry needed  │
            └──────────────────────┘
```

---

These diagrams illustrate:
1. **System Architecture**: How components interact
2. **Installation Flow**: The complete retry process
3. **Error Detection**: How conflicts are identified
4. **State Machine**: State transitions during operation
5. **Version Stripping**: How constraints are removed
6. **Logging**: What users see in console
7. **Configuration**: Impact of settings
