import os, shutil
from .strategies import run_strategy
from .tools import TOOLS

VENV_DIR = "venvs"  # adjust to your env storage path

def detect_tools():
    detected = []
    for name, meta in TOOLS.items():
        for exe in meta["executables"]:
            exe_path = shutil.which(exe)
            if exe_path:
                detected.append({
                    "name": name,
                    "path": exe_path,
                    "strategy": meta["strategy"]
                })
                break
    return detected


def activate_env(env_name,directory=None, open_with=None,log_callback=None):
    venv_dir = os.path.join(VENV_DIR, env_name)
    target_dir = directory if directory else venv_dir

    tools = detect_tools()
    tool_entry = next((t for t in tools if t["name"].lower() == open_with.lower()), None)

    if not tool_entry:
        if log_callback:
            log_callback(f"Tool '{open_with}' not found on system")
        return

    run_strategy(tool_entry["strategy"], tool_entry["path"], venv_dir, target_dir)
