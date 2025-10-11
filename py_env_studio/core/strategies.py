import os, subprocess, json
from pathlib import Path

# registry
STRATEGIES = {}

def register_strategy(name):
    def wrapper(func):
        STRATEGIES[name] = func
        return func
    return wrapper

def run_strategy(name, tool_path, venv_dir, target_dir):
    if name not in STRATEGIES:
        raise ValueError(f"No strategy {name} registered")
    STRATEGIES[name](tool_path, venv_dir, target_dir)


@register_strategy("venv_injection")
def venv_injection(tool_path, venv_dir, target_dir):
    """Inject venv into tool settings (e.g., VSCode, PyCharm, Sublime)."""
    vscode_dir = Path(target_dir) / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings_path = vscode_dir / "settings.json"

    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except Exception:
            settings = {}

    python_exe = Path(venv_dir) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    settings["python.defaultInterpreterPath"] = str(python_exe)

    settings_path.write_text(json.dumps(settings, indent=4))
    subprocess.Popen([tool_path, target_dir])
    print(f"[VSCode/PyCharm] Auto-set interpreter to {python_exe}")


@register_strategy("shell_activation")
def shell_activation(tool_path, venv_dir, target_dir):
    """Open shell with activated venv (CMD, Terminal)."""
    if os.name == "nt":
        scripts_dir = Path(venv_dir) / "Scripts"
        command = f'cd /d "{scripts_dir}" && activate && cd /d "{target_dir}"'
        subprocess.Popen([tool_path, "/K", command])
    else:
        bin_dir = Path(venv_dir) / "bin"
        command = f'cd "{bin_dir}" && source activate && cd "{target_dir}"'
        subprocess.Popen([tool_path, "-e", command])
    print(f"[Shell] Opened {tool_path} with environment activated")


@register_strategy("auto_detect")
def auto_detect(tool_path, venv_dir, target_dir):
    """Let the tool detect env automatically (Positron, Poetry-aware IDEs)."""
    subprocess.Popen([tool_path, target_dir])
    print(f"[Auto-detect] Opened {tool_path} (tool manages env itself)")
