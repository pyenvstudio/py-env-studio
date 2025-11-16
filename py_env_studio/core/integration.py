# import os, shutil
# from .strategies import run_strategy
from .tools import TOOLS

# VENV_DIR = ".venvs"  # adjust to your env storage path

# def detect_tools():
#     detected = []
#     for name, meta in TOOLS.items():
#         for exe in meta["executables"]:
#             exe_path = shutil.which(exe)
#             if exe_path:
#                 detected.append({
#                     "name": name,
#                     "path": exe_path,
#                     "strategy": meta["strategy"]
#                 })
#                 break
#     return detected


# def activate_env(env_name, directory=None, open_with=None, log_callback=None):
#     venv_dir = os.path.join(VENV_DIR, env_name)
#     if not os.path.exists(venv_dir):
#         if log_callback:
#             log_callback(f"Environment '{env_name}' not found at {venv_dir}")
#         return

#     target_dir = directory or os.getcwd()  # open in current working dir, not venv
#     tools = detect_tools()
#     tool_entry = next((t for t in tools if t["name"].lower() == open_with.lower()), None)

#     if not tool_entry:
#         if log_callback:
#             log_callback(f"Tool '{open_with}' not found on system")
#         return

#     run_strategy(tool_entry["strategy"], tool_entry["path"], venv_dir, target_dir)


# file: venv_tool_integration.py
import os
import json
import subprocess
from pathlib import Path
import shutil

from pathlib import Path
import os
import subprocess
import shutil
import json
from .tools import TOOLS


# config
VENV_DIR_ROOT = str(Path.home() / ".venvs")  # or your existing VENV_DIR


# helper
def _which(exe):
    return shutil.which(exe)


def detect_tools():
    detected = []
    for name, meta in TOOLS.items():
        for exe in meta["executables"]:
            exe_path = _which(exe)
            if exe_path:
                detected.append({"name": name, "path": exe_path, "strategy": meta["strategy"]})
                break
    return detected


# Strategy registry
STRATEGIES = {}
def register_strategy(name):
    def wrapper(func):
        STRATEGIES[name] = func
        return func
    return wrapper


def run_strategy(name, tool_path, venv_dir, target_dir, open_in_venv_cwd=False, log_callback=None):
    if name not in STRATEGIES:
        raise ValueError(f"No strategy {name} registered")
    return STRATEGIES[name](tool_path, venv_dir, target_dir, open_in_venv_cwd=open_in_venv_cwd, log_callback=log_callback)


# ===================================================================
#  STRATEGY 1: VENV INJECTION
# ===================================================================
@register_strategy("venv_injection")
def venv_injection(tool_path, venv_dir, target_dir, open_in_venv_cwd=False, log_callback=None):
    workspace_dir = Path(target_dir).expanduser().resolve()
    vscode_dir = workspace_dir / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    settings_path = vscode_dir / "settings.json"

    venv_path = Path(venv_dir).expanduser().resolve()
    if os.name == "nt":
        bin_dir = venv_path / "Scripts"
        python_exe = bin_dir / "python.exe"
    else:
        bin_dir = venv_path / "bin"
        python_exe = bin_dir / "python"

    if not python_exe.exists():
        raise FileNotFoundError(f"Python executable not found in {venv_path}")

    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            settings = {}

    settings["python.defaultInterpreterPath"] = str(python_exe)

    env_key = (
        "terminal.integrated.env.windows"
        if os.name == "nt"
        else "terminal.integrated.env.linux"
    )
    path_fragment = f"{bin_dir};${{env:PATH}}" if os.name == "nt" else f"{bin_dir}:${{env:PATH}}"
    settings.setdefault(env_key, {})
    settings[env_key]["VIRTUAL_ENV"] = str(venv_path)
    settings[env_key]["PATH"] = path_fragment

    if open_in_venv_cwd:
        candidate_cwd = bin_dir
        settings["terminal.integrated.cwd"] = (
            str(candidate_cwd) if candidate_cwd.exists() else "${workspaceFolder}"
        )

    settings.setdefault("terminal.integrated.cwd", "${workspaceFolder}")
    settings_path.write_text(json.dumps(settings, indent=4), encoding="utf-8")

    subprocess.Popen([tool_path, str(workspace_dir)])


# ===================================================================
#  STRATEGY 2: SHELL ACTIVATION (Refactored)
# ===================================================================
@register_strategy("shell_activation")
def shell_activation(tool_path, venv_dir, target_dir, **_):
    """
    Launch terminal (cmd, PowerShell, Linux terminal, etc.) with venv activated.
    """

    venv_path = Path(venv_dir)
    is_windows = os.name == "nt"
    print(f"[Shell] Activating venv at {venv_path} in terminal {tool_path}")

    # Define shell strategies
    shell_map = {
        # --- Windows ---
        "cmd": lambda: (
            str(venv_path / "Scripts" / "activate.bat"),
            f'call {venv_path / "Scripts" / "activate.bat"} && cd /d {target_dir}',
            ["start", "cmd", "/K"],
        ),
        "powershell": lambda: (
            str(venv_path / "Scripts" / "Activate.ps1"),
            f'& "{venv_path / "Scripts" / "Activate.ps1"}"; Set-Location "{target_dir}"',
            ["start", "powershell", "-NoExit", "-Command"],
        ),
        # --- Linux/macOS ---
        "bash": lambda: (
            str(venv_path / "bin" / "activate"),
            f'source "{venv_path / "bin" / "activate"}" && cd "{target_dir}" && exec $SHELL',
            ["gnome-terminal", "--", "bash", "-c"],
        ),
    }

    # Detect user-preferred shell
    preferred_shell = (
        Path(tool_path).stem.lower()
        if tool_path
        else ("cmd" if is_windows else "bash")
    )

    # Pick strategy
    if preferred_shell not in shell_map:
        raise ValueError(f"Unsupported shell: {preferred_shell}")

    activate_script, command, base_cmd = shell_map[preferred_shell]()

    if not Path(activate_script).exists():
        raise FileNotFoundError(f"Activation script not found: {activate_script}")

    # Launch the terminal
    try:
        subprocess.Popen(base_cmd + [command], shell=is_windows)
        print(f"[Shell] Opened new {preferred_shell} terminal with env: {venv_dir}")
    except Exception as err:
        print(f"Activation Error ({preferred_shell}): {err}")


# ===================================================================
#  PUBLIC API
# ===================================================================
def activate_env(env_name, directory=None, open_with="vscode", open_in_venv_cwd=False, log_callback=None):
    venv_dir = str(Path(VENV_DIR_ROOT) / env_name)
    target_dir = directory or os.getcwd()

    if not Path(venv_dir).exists():
        raise FileNotFoundError(f"Environment '{env_name}' not found at {venv_dir}")

    tools = detect_tools()
    tool_entry = next((t for t in tools if t["name"].lower() == open_with.lower()), None)
    if not tool_entry:
        raise RuntimeError(f"Tool '{open_with}' not found on system")

    return run_strategy(
        tool_entry["strategy"],
        tool_entry["path"],
        venv_dir,
        target_dir,
        open_in_venv_cwd=open_in_venv_cwd,
        log_callback=log_callback,
    )
