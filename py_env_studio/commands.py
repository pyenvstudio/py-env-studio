import argparse
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
from py_env_studio.ui.main_window import PyEnvStudio


def _split_two_values(raw_value: str, usage: str) -> Tuple[str, str]:
    try:
        return raw_value.split(",", 1)
    except ValueError:
        print(f"Error: Invalid value. Usage: {usage}")
        sys.exit(1)


def handle_create(args: argparse.Namespace) -> None:
    create_env(args.create, upgrade_pip=args.upgrade_pip)


def handle_delete(args: argparse.Namespace) -> None:
    delete_env(args.delete)


def handle_list(_: argparse.Namespace) -> None:
    for env in list_envs():
        print(env)


def handle_activate(args: argparse.Namespace) -> None:
    activate_env(args.activate)


def handle_install(args: argparse.Namespace) -> None:
    env_name, package = _split_two_values(
        args.install,
        "py-env-studio --install env_name,package",
    )
    install_package(env_name, package)


def handle_uninstall(args: argparse.Namespace) -> None:
    env_name, package = _split_two_values(
        args.uninstall,
        "py-env-studio --uninstall env_name,package",
    )
    uninstall_package(env_name, package)


def handle_export(args: argparse.Namespace) -> None:
    env_name, file_path = _split_two_values(
        args.export,
        "py-env-studio --export env_name,file_path",
    )
    export_requirements(env_name, file_path)


def handle_import_requirements(args: argparse.Namespace) -> None:
    env_name, file_path = _split_two_values(
        args.import_reqs,
        "py-env-studio --import-reqs env_name,file_path",
    )
    import_requirements(env_name, file_path)


def _print_runtime_result(result: Dict[str, object]) -> None:
    print(result["message"])
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

    result = execute_in_managed_env(Path.cwd(), list(args.args))
    sys.exit(result)


def launch_gui(_: argparse.Namespace) -> None:
    app = PyEnvStudio()
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
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Virtual Environment Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser.add_argument(
        "--upgrade-pip",
        action="store_true",
        help="Upgrade pip when creating a new environment",
    )

    for command in FLAG_COMMANDS.values():
        parser_kwargs = {"help": command["help"]}
        if "action" in command:
            parser_kwargs["action"] = command["action"]
        parser.add_argument(command["option"], **parser_kwargs)

    for name, command in SUBCOMMANDS.items():
        subparser = subparsers.add_parser(name, help=command["help"])
        if "extra_values" in command:
            subparser.add_argument(
                "args",
                nargs=argparse.REMAINDER,
                help=" ".join(command["extra_values"]),
            )

    return parser


def dispatch_command(args: argparse.Namespace) -> None:
    for name, command in FLAG_COMMANDS.items():
        if getattr(args, name, None):
            command["function"](args)
            return

    if args.command in SUBCOMMANDS:
        SUBCOMMANDS[args.command]["function"](args)
        return

    launch_gui(args)


def main(argv: Optional[Sequence[str]] = None) -> None:
    initialize_app_runtime()
    argv = list(argv) if argv is not None else sys.argv[1:]

    if argv and not argv[0].startswith("-") and argv[0] not in SUBCOMMANDS:
        handle_run(argparse.Namespace(args=argv))
        return

    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch_command(args)


if __name__ == "__main__":
    main()
