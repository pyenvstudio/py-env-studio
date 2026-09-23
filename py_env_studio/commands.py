import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from py_env_studio.core.bootstrap import initialize_app_runtime
from py_env_studio.core.env_manager import activate_env, create_env, delete_env, list_envs
from py_env_studio.core.pip_tools import (
    export_requirements,
    import_requirements,
    install_package,
    uninstall_package,
)
from py_env_studio.core.runtime_toggle import (
    disable_runtime,
    enable_runtime,
    execute_in_managed_env,
    get_project_status,
    init_project,
    list_registered_projects,
)
from py_env_studio.utils.app_logging import configure_logging
from py_env_studio.utils.progress import TaskProgress

logger = logging.getLogger(__name__)

# Flags consumed before argparse runs, so logging is configured before the
# first record is emitted (bootstrap/shortcut warnings included).
LEADING_VERBOSITY_FLAGS = ("-v", "--verbose", "-q", "--quiet")


def _extract_verbosity(argv: Sequence[str]) -> tuple[Optional[str], list[str]]:
    """Pop leading verbosity flags and return ``(verbosity, remaining)``."""
    verbosity: Optional[str] = None
    rest = list(argv)
    while rest and rest[0] in LEADING_VERBOSITY_FLAGS:
        flag = rest.pop(0)
        if flag in ("-q", "--quiet"):
            verbosity = "error"  # quiet wins over a bare -v
        elif verbosity != "error":
            verbosity = "debug"
    return verbosity, rest


def _verbosity_from_args(args: argparse.Namespace) -> Optional[str]:
    if getattr(args, "quiet", False):
        return "error"
    if getattr(args, "verbose", False):
        return "debug"
    return None


def _bar(args: argparse.Namespace, label: str, total: Optional[float] = None) -> TaskProgress:
    """CLI progress gauge that honours ``--no-progress`` / ``PES_NO_PROGRESS``."""
    disabled = bool(getattr(args, "no_progress", False))
    return TaskProgress(label, total, enabled=False if disabled else None)


def _split_two_values(raw_value: str, usage: str) -> Tuple[str, str]:
    try:
        return raw_value.split(",", 1)
    except ValueError:
        print(f"Error: Invalid value. Usage: {usage}")
        sys.exit(1)


def handle_create(args: argparse.Namespace) -> None:
    name = args.create
    logger.info(
        "Creating environment '%s'%s",
        name,
        " (upgrading pip)" if args.upgrade_pip else "",
    )
    with _bar(args, f"Creating {name}") as progress:
        create_env(name, upgrade_pip=args.upgrade_pip, log_callback=progress.note)


def handle_delete(args: argparse.Namespace) -> None:
    name = args.delete
    logger.info("Deleting environment '%s'", name)
    with _bar(args, f"Deleting {name}") as progress:
        delete_env(name, log_callback=progress.note)


def handle_list(_: argparse.Namespace) -> None:
    for env in list_envs():
        print(env)


def handle_activate(args: argparse.Namespace) -> None:
    logger.info("Activating environment '%s'", args.activate)
    activate_env(args.activate)


def handle_install(args: argparse.Namespace) -> None:
    env_name, package = _split_two_values(
        args.install,
        "py-env-studio --install env_name,package",
    )
    logger.info("Installing '%s' into environment '%s'", package, env_name)
    with _bar(args, f"Installing {package}") as progress:
        install_package(env_name, package, log_callback=progress.note)


def handle_uninstall(args: argparse.Namespace) -> None:
    env_name, package = _split_two_values(
        args.uninstall,
        "py-env-studio --uninstall env_name,package",
    )
    logger.info("Uninstalling '%s' from environment '%s'", package, env_name)
    with _bar(args, f"Uninstalling {package}") as progress:
        uninstall_package(env_name, package, log_callback=progress.note)


def handle_export(args: argparse.Namespace) -> None:
    env_name, file_path = _split_two_values(
        args.export,
        "py-env-studio --export env_name,file_path",
    )
    logger.info("Exporting packages of '%s' to %s", env_name, file_path)
    export_requirements(env_name, file_path)


def handle_import_requirements(args: argparse.Namespace) -> None:
    env_name, file_path = _split_two_values(
        args.import_reqs,
        "py-env-studio --import-reqs env_name,file_path",
    )
    logger.info("Installing requirements from %s into '%s'", file_path, env_name)
    with _bar(args, "Installing requirements") as progress:
        import_requirements(env_name, file_path, log_callback=progress.note)


def _print_runtime_result(result: Dict[str, object]) -> None:
    message = str(result["message"])
    print(message)
    # The message already reached the terminal on stdout; the file log keeps
    # the record without printing it a second time on stderr.
    logger.debug("%s", message)
    if not result["success"]:
        sys.exit(1)


def handle_init(_: argparse.Namespace) -> None:
    _print_runtime_result(init_project())


def handle_on(_: argparse.Namespace) -> None:
    _print_runtime_result(enable_runtime())


def handle_off(_: argparse.Namespace) -> None:
    _print_runtime_result(disable_runtime())


def handle_status(_: argparse.Namespace) -> None:
    status = get_project_status()
    print(f"Initialized: {status['initialized']}")
    if status["initialized"]:
        print(f"Project: {status.get('project_name', 'Unknown')}")
        print(f"Project Root: {status['project_root']}")
        print(f"Runtime Enabled: {status['runtime_enabled']}")
        print(f"Environment ID: {status.get('environment_id', 'N/A')}")
        print(f"Environment Exists: {status['environment_exists']}")
        print(f"Environment Path: {status.get('environment_path', 'N/A')}")
        print(f"Python Version: {status['python_version']}")


def handle_list_projects(_: argparse.Namespace) -> None:
    projects = list_registered_projects()
    if not projects:
        print("No projects registered.")
        return
    for project in projects:
        status = "ON" if project["runtime_enabled"] else "OFF"
        env_status = "EXISTS" if project["environment_exists"] else "MISSING"
        print(
            f"{project['name']} [{status}] [{env_status}] - "
            f"{project['project_root']} (Python {project['python_version']})"
        )


def handle_run(args: argparse.Namespace) -> None:
    if not args.args:
        print("Error: No script provided. Usage: pes run <script.py> [args...]")
        sys.exit(1)

    # No gauge here: the child process owns the terminal and its output must
    # not be interleaved with redrawn status lines.
    logger.info("Running %s in the managed environment", list(args.args))
    result = execute_in_managed_env(Path.cwd(), list(args.args))
    if result:
        logger.error("Script exited with status %s", result)
    sys.exit(result)


def handle_mcp(_: argparse.Namespace) -> None:
    from py_env_studio.core.mcp.server import run_stdio

    logger.info("Starting the PES MCP server on stdio")
    sys.exit(run_stdio())


def launch_gui(args: argparse.Namespace) -> None:
    # Imported lazily so headless commands (e.g. `mcp`) work without GUI deps.
    from py_env_studio.ui.main_window import PyEnvStudio

    logger.info("Launching the PyEnvStudio GUI")
    app = PyEnvStudio(verbosity=_verbosity_from_args(args))
    # Route window close through on_closing so plugin shutdown hooks and
    # background-task shutdown actually run (previously only wired up when
    # started via python -m py_env_studio.ui.main_window).
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


FLAG_COMMANDS = {
    "create": {
        "option": "--create",
        "function": handle_create,
        "help": "Create a new virtual environment",
    },
    "delete": {
        "option": "--delete",
        "function": handle_delete,
        "help": "Delete a virtual environment",
    },
    "list": {
        "option": "--list",
        "function": handle_list,
        "help": "List all virtual environments",
        "action": "store_true",
    },
    "activate": {
        "option": "--activate",
        "function": handle_activate,
        "help": "Activate a virtual environment",
    },
    "install": {
        "option": "--install",
        "function": handle_install,
        "help": "Install a package in the specified environment (format: env_name,package)",
    },
    "uninstall": {
        "option": "--uninstall",
        "function": handle_uninstall,
        "help": "Uninstall a package from the specified environment (format: env_name,package)",
    },
    "export": {
        "option": "--export",
        "function": handle_export,
        "help": "Export packages to requirements.txt (format: env_name,file_path)",
    },
    "import_reqs": {
        "option": "--import-reqs",
        "function": handle_import_requirements,
        "help": "Install packages from requirements.txt (format: env_name,file_path)",
    },
    "gui": {
        "option": "--gui",
        "function": launch_gui,
        "help": "Launch the GUI",
        "action": "store_true",
    },
}

SUBCOMMANDS = {
    "init": {
        "function": handle_init,
        "help": "Initialize the current project for Py Env Studio",
    },
    "on": {
        "function": handle_on,
        "help": "Enable Py Env Studio runtime interception",
    },
    "off": {
        "function": handle_off,
        "help": "Disable Py Env Studio runtime interception",
    },
    "status": {
        "function": handle_status,
        "help": "Show current project status",
    },
    "list-projects": {
        "function": handle_list_projects,
        "help": "List all registered projects",
    },
    "run": {
        "function": handle_run,
        "help": "Run a script inside the managed environment",
        "extra_values": ("script.py", "[args...]"),
    },
    "mcp": {
        "function": handle_mcp,
        "help": "Start the PES MCP server over stdio (local, read-only)",
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Virtual Environment Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser.add_argument(
        "--upgrade-pip",
        action="store_true",
        help="Upgrade pip when creating a new environment",
    )
    _add_output_options(parser)

    for command in FLAG_COMMANDS.values():
        parser_kwargs = {"help": command["help"]}
        if "action" in command:
            parser_kwargs["action"] = command["action"]
        parser.add_argument(command["option"], **parser_kwargs)

    for name, command in SUBCOMMANDS.items():
        subparser = subparsers.add_parser(name, help=command["help"])
        # Same output options after the subcommand (`pes status -v`).  SUPPRESS
        # defaults keep a value parsed before the subcommand from being
        # overwritten by the subparser's defaults.
        _add_output_options(subparser, suppress_defaults=True)
        if "extra_values" in command:
            subparser.add_argument(
                "args",
                nargs=argparse.REMAINDER,
                help=" ".join(command["extra_values"]),
            )

    return parser


def _add_output_options(parser: argparse.ArgumentParser, suppress_defaults: bool = False) -> None:
    """Attach the shared ``-v``/``-q``/``--no-progress`` output controls."""
    default = argparse.SUPPRESS if suppress_defaults else False
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=default,
        help="Show detailed diagnostics (DEBUG logs and tracebacks)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        default=default,
        help="Only report errors",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        default=default,
        help="Disable the CLI progress gauge (PES_NO_PROGRESS=1 does the same)",
    )


def dispatch_command(args: argparse.Namespace) -> None:
    for name, command in FLAG_COMMANDS.items():
        if getattr(args, name, None):
            command["function"](args)
            return

    if args.command in SUBCOMMANDS:
        SUBCOMMANDS[args.command]["function"](args)
        return

    launch_gui(args)


class _ErrorMarker(logging.Handler):
    """Silent sentinel: records whether any ERROR reached the logging system.

    ``main`` attaches it to the root logger around dispatch so the catch-all
    handler does not print a second, vaguer error line when the layer that
    failed (``pip_tools``, ``env_manager``, ...) already logged the specific
    cause.  ``emit`` deliberately writes nothing — this handler only watches.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.seen = False

    def emit(self, record: logging.LogRecord) -> None:
        self.seen = True


def main(argv: Optional[Sequence[str]] = None) -> None:
    argv = list(argv) if argv is not None else sys.argv[1:]
    verbosity, argv = _extract_verbosity(argv)
    # Configure logging first: bootstrap and every handler below emit through
    # it, and the file sink must not miss startup problems.
    configure_logging(verbosity)
    verbose = verbosity == "debug"

    initialize_app_runtime()

    # Watches for an ERROR already reported by the failing layer, so the
    # catch-all below does not print a second, vaguer copy of the same failure.
    marker = _ErrorMarker()
    root_logger = logging.getLogger()
    root_logger.addHandler(marker)
    try:
        if argv and not argv[0].startswith("-") and argv[0] not in SUBCOMMANDS:
            # `pes script.py [args...]` shorthand for `pes run ...`.
            handle_run(argparse.Namespace(args=argv))
            return

        parser = build_parser()
        args = parser.parse_args(argv)
        verbosity = _verbosity_from_args(args) or verbosity
        verbose = verbosity == "debug" if verbosity else verbose
        configure_logging(verbosity)
        dispatch_command(args)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:
        if verbose:
            raise
        # Traceback goes to the log file; the terminal gets one clean line.
        logger.debug("Unhandled CLI failure", exc_info=True)
        if not marker.seen:
            logger.error("%s: %s", type(exc).__name__, exc)
        sys.exit(1)
    finally:
        root_logger.removeHandler(marker)


if __name__ == "__main__":
    main()
