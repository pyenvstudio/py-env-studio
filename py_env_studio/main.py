import argparse
from  py_env_studio.ui.main_window import PyEnvStudio
from  py_env_studio.core.env_manager import create_env, list_envs, delete_env, activate_env
from  py_env_studio.core.pip_tools import install_package, uninstall_package, export_requirements, import_requirements

def main():
    parser = argparse.ArgumentParser(description="Virtual Environment Manager")
    parser.add_argument("--create", help="Create a new virtual environment")
    parser.add_argument("--upgrade-pip", action="store_true", help="Upgrade pip when creating a new environment")
    parser.add_argument("--delete", help="Delete a virtual environment")
    parser.add_argument("--list", action="store_true", help="List all virtual environments")
    parser.add_argument("--activate", help="Activate a virtual environment")
    parser.add_argument("--install", help="Install a package in the specified environment (format: env_name,package)")
    parser.add_argument("--uninstall", help="Uninstall a package from the specified environment (format: env_name,package)")
    parser.add_argument("--export", help="Export packages to requirements.txt (format: env_name,file_path)")
    parser.add_argument("--import-reqs", help="Install packages from requirements.txt (format: env_name,file_path)")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI")
    args = parser.parse_args()

    if args.create:
        create_env(args.create, upgrade_pip=args.upgrade_pip)
    elif args.delete:
        delete_env(args.delete)
    elif args.list:
        for env in list_envs():
            print(env)
    elif args.activate:
        activate_env(args.activate)
    elif args.install:
        env_name, package = args.install.split(",", 1)
        install_package(env_name, package)
    elif args.uninstall:
        env_name, package = args.uninstall.split(",", 1)
        uninstall_package(env_name, package)
    elif args.export:
        env_name, file_path = args.export.split(",", 1)
        export_requirements(env_name, file_path)
    elif args.import_reqs:
        env_name, file_path = args.import_reqs.split(",", 1)
        import_requirements(env_name, file_path)
    else:
        app = PyEnvStudio()
        app.mainloop()

if __name__ == "__main__":
    main()