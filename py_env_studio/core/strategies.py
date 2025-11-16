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

    # Inject interpreter path
    settings["python.defaultInterpreterPath"] = str(python_exe)

    # Inject terminal environment for all shells
    if os.name == "nt":
        env_key = "terminal.integrated.env.windows"
        venv_bin = Path(venv_dir) / "Scripts"
        path_var = f"{venv_bin};${{env:PATH}}"
    else:
        env_key = "terminal.integrated.env.linux"
        venv_bin = Path(venv_dir) / "bin"
        path_var = f"{venv_bin}:${{env:PATH}}"

    settings.setdefault(env_key, {})
    settings[env_key]["VIRTUAL_ENV"] = str(venv_dir)
    settings[env_key]["PATH"] = path_var

    settings_path.write_text(json.dumps(settings, indent=4))
    subprocess.Popen([tool_path, target_dir])
    print(f"[VSCode] Injected interpreter + terminal env: {python_exe}")

@register_strategy("shell_activation")
def shell_activation(tool_path, venv_dir, target_dir):
    """Open shell with activated venv (CMD, Terminal)."""
    os_name = os.name
    if os_name == "nt":
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
