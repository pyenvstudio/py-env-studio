from pathlib import Path
import shutil
from .tools import TOOLS

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

