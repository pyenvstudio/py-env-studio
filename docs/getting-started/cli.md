# ⌨️ CLI Reference

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

## Activating Environments
Manually activate your environment after creation:
Windows:

    .\envs\<environment name>\Scripts\activate

Linux/macOS:

    source envs/<environment name>/bin/activate

## MCP server (local, read-only)
    py-env-studio mcp

Starts the MCP control plane over stdio for AI clients such as VS Code
Copilot. No GUI, no network required. See `Reference → Features & Implementation` (section 25).

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
