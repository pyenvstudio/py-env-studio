"""GitHub template import helpers."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class GitHubImportError(RuntimeError):
    """Raised when GitHub template import fails."""


_GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def validate_github_repository_url(url: str) -> str:
    candidate = url.strip()
    match = _GITHUB_URL_PATTERN.match(candidate)
    if not match:
        raise GitHubImportError("Invalid GitHub repository URL. Use https://github.com/owner/repo")
    owner = match.group("owner")
    repo = match.group("repo")
    return f"https://github.com/{owner}/{repo}.git"


def extract_github_repository_name(url: str) -> str:
    """Extract repository name from a GitHub URL.

    Accepts both .git and non-.git URL variants.
    """
    candidate = url.strip()
    match = _GITHUB_URL_PATTERN.match(candidate)
    if not match:
        raise GitHubImportError("Invalid GitHub repository URL.")
    return match.group("repo")


def clone_github_repository(
    repository_url: str,
    destination_dir: Path,
    timeout_seconds: int = 240,
    log_callback=None,
) -> Path:
    git_path = shutil.which("git")
    if not git_path:
        raise GitHubImportError("Git is not installed or not available in PATH.")

    destination = destination_dir.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        raise GitHubImportError(f"Destination already exists: {destination}")

    cmd = [git_path, "clone", "--depth", "1", repository_url, str(destination)]
    if log_callback:
        log_callback("Cloning repository...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitHubImportError("Repository clone timed out.") from exc
    except Exception as exc:
        raise GitHubImportError(f"Repository clone failed: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GitHubImportError(
            f"Failed to clone repository. {stderr or 'Unknown git error.'}"
        )

    return destination
