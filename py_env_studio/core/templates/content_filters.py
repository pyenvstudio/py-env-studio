"""Centralized file-filtering rules for template imports."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
}

EXCLUDED_FILE_NAMES = {
    ".gitignore",
}

EXCLUDED_FILE_PATTERNS = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.egg-info",
}

SENSITIVE_FILE_NAMES = {
    ".env",
    "credentials.json",
    "secrets.json",
}

SENSITIVE_FILE_PATTERNS = {
    "*.pem",
    "*.key",
}


def _matches_patterns(name: str, patterns: set[str]) -> bool:
    for pattern in patterns:
        if fnmatch(name.lower(), pattern.lower()):
            return True
    return False


def is_excluded_path(relative_path: Path, is_dir: bool) -> bool:
    parts = [part for part in relative_path.parts if part not in (".", "")]
    if not parts:
        return False

    for part in parts[:-1] if not is_dir else parts:
        if part.lower() in {name.lower() for name in EXCLUDED_DIR_NAMES}:
            return True

    name = parts[-1]
    if is_dir:
        return name.lower() in {entry.lower() for entry in EXCLUDED_DIR_NAMES}

    if name.lower() in {entry.lower() for entry in EXCLUDED_FILE_NAMES}:
        return True
    if _matches_patterns(name, EXCLUDED_FILE_PATTERNS):
        return True
    return False


def is_sensitive_file(relative_path: Path) -> bool:
    filename = relative_path.name.lower()
    if filename in {name.lower() for name in SENSITIVE_FILE_NAMES}:
        return True
    if _matches_patterns(filename, SENSITIVE_FILE_PATTERNS):
        return True
    return False


def is_path_safe(relative_path: Path) -> bool:
    if relative_path.is_absolute():
        return False
    if ".." in relative_path.parts:
        return False
    return True
