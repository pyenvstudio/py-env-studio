# 📥 Installation

## Requirements

- Python **3.12 or newer**
- `pip` (or `uv` if you prefer to install and manage packages with uv)
- Windows, Linux, or macOS

Internet access to [PyPI](https://pypi.org) is required during installation.
Runtime features additionally use public [deps.dev](https://deps.dev) and
[OSV.dev](https://osv.dev) APIs for dependency and vulnerability data.

## Install from PyPI

```bash
pip install py-env-studio
```

## Upgrade to the latest version

```bash
pip install --upgrade py-env-studio
```

## Verify the installation

```bash
py-env-studio --list      # prints the environments PES manages
py-env-studio -v --list   # same, with DEBUG diagnostics
py-env-studio --help      # flags, subcommands, and output options
```

The package also installs the aliases `pyenvstudio` and `pes`, so
`pes --list` is equivalent to `py-env-studio --list`.

## Launch the GUI

```bash
py-env-studio
```

Running the command without arguments opens the desktop application. You can
also force it with `py-env-studio --gui`.

## Optional extras

```bash
pip install "py-env-studio[dev]"    # pytest, black, isort
pip install "py-env-studio[gui]"    # explicit Pillow dependency
```

`uv` is optional: install it separately and select it as the package manager
for an environment (or as the default in **Tools → Configuration**). If `uv` is
unavailable or a `uv` operation fails, PES falls back to `pip` automatically.

## Uninstall

```bash
pip uninstall py-env-studio
```

Uninstalling the package does not delete your environments, templates, plugins,
logs, or database. Those live in the platform user-data directory and can be
removed manually if you want a clean slate.

## Next steps

- [Usage manual](usage.md) — GUI workflows, tips, and templates
- [CLI reference](cli.md) — every flag, subcommand, and output option
- [MCP reference (beta)](../reference/mcp.md) — connect AI coding agents
- [Troubleshooting and logging](https://github.com/pyenvstudio/py-env-studio/issues) —
  report problems with the log file
  (`py_env_studio.log` in the platform data directory)
