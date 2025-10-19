TOOLS = {
    "vscode": {"executables": ["code"], "strategy": "venv_injection"},
    "pycharm": {"executables": ["charm", "pycharm"], "strategy": "venv_injection"},
    "sublime": {"executables": ["subl"], "strategy": "venv_injection"},
    "positron": {"executables": ["positron"], "strategy": "auto_detect"},
    "cmd": {"executables": ["cmd.exe"], "strategy": "shell_activation"},
    "terminal": {"executables": ["gnome-terminal", "xterm"], "strategy": "shell_activation"},
}
