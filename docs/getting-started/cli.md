# ⌨️ CLI Reference

## Command aliases

The package installs three equivalent entry points for the same CLI and GUI:

| Command | Notes |
|---------|-------|
| `py-env-studio` | full name — used in all examples below |
| `pes` | short alias; also used for managed projects (`pes init`, `pes run …`) |
| `pyenvstudio` | alias without hyphens |

Every example written as `py-env-studio …` works identically as `pes …` or
`pyenvstudio …` (for example `pes --list`, `pes mcp`, `pyenvstudio init`).

## Create environment
    py-env-studio --create <<env_name>>

## Create & upgrade pip
    py-env-studio --create <<env_name>> --upgrade-pip

## Delete environment
    py-env-studio --delete <<env_name>>

## List all environments
    py-env-studio --list

## Install package
    py-env-studio --install <<env_name>>,numpy

## Uninstall package
    py-env-studio --uninstall <<env_name>>,numpy

## Export requirements
    py-env-studio --export <<env_name>>,requirements.txt

## Import requirements
    py-env-studio --import-reqs <<env_name>>,requirements.txt

## Activate environment
    py-env-studio --activate <<env_name>>

## Launch the GUI
    py-env-studio --gui

Running the command with no flags or subcommands also opens the GUI.

## Managed project runtime
These subcommands manage the project in the current working directory:

| Command | Purpose |
|---------|---------|
| `py-env-studio init` | Initialize the current project as a PES-managed project (`pes.config` + managed environment) |
| `py-env-studio on` | Enable runtime interception for the project |
| `py-env-studio off` | Disable runtime interception for the project |
| `py-env-studio status` | Show project, environment, and runtime status |
| `py-env-studio list-projects` | List every registered project with its runtime and environment state |
| `py-env-studio run <script.py> [args...]` | Run a script inside the managed environment |

`pes <script.py> [args...]` is a shorthand for `pes run …`.

```bash
cd path/to/project
py-env-studio init
py-env-studio on
py-env-studio status
py-env-studio run app.py --debug
```

## MCP server (beta, local, read-only)
    py-env-studio mcp

Starts the MCP control plane over stdio for AI clients such as VS Code
Copilot. No GUI and no network are required; the server exposes read-only
environment, package, dependency, security, and project information and never
mutates environments or packages.

MCP is a **beta** feature: client configuration, trust steps, the tool list,
and troubleshooting are documented in the [MCP reference](../reference/mcp.md).
Set `enabled = false` in the `[mcp]` section of `config.ini` to refuse startup.

## Activating Environments
Manually activate your environment after creation:
Windows:

    .\envs\<environment name>\Scripts\activate

Linux/macOS:

    source envs/<environment name>/bin/activate

## Global output flags
These work before any command (and after subcommands too):

    py-env-studio -v --list        # debug logs + full tracebacks on failure
    py-env-studio -q status        # errors only

| Flag | Effect |
|------|--------|
| `-v`, `--verbose` | DEBUG diagnostics; failures re-raise with a traceback instead of the one-line summary |
| `-q`, `--quiet` | Only errors are printed (wins over `-v`) |
| `--no-progress` | Disable the terminal progress gauge |

`PES_LOG_LEVEL=debug|info|warning|error|quiet` sets the same verbosity via
the environment; `PES_NO_PROGRESS=1` disables the gauge like `--no-progress`,
and `PES_PROGRESS=1` forces it on when stderr is not a TTY.

Failures print a single `ERROR <component>: ...` line on stderr and exit `1`;
the full traceback is always kept in the rotating log file
(`py_env_studio.log` in the platform data directory). Command output stays on
stdout, so pipes like `py-env-studio --list | grep x` keep working.

## Terminal progress gauge
Long-running commands (`--create`, `--install`, `--import-reqs`, …) draw a
single-line progress bar on **stderr** when it is a TTY: an animated bar for
steps with a known size, a marquee when the total is unknown. Piped/redirected
output stays clean — only a 25/50/75 % milestone note is logged instead. The
gauge never interleaves with `py-env-studio run …`, because the child script
owns the terminal.
