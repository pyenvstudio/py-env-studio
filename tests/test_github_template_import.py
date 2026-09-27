from pathlib import Path
from types import SimpleNamespace

import pytest

from py_env_studio.core.templates.github_import import (
    GitHubImportError,
    clone_github_repository,
    extract_github_repository_name,
    validate_github_repository_url,
)


def test_validate_github_repository_url_success() -> None:
    assert (
        validate_github_repository_url("https://github.com/user/project")
        == "https://github.com/user/project.git"
    )
    assert (
        validate_github_repository_url("https://github.com/user/project.git")
        == "https://github.com/user/project.git"
    )
    assert (
        validate_github_repository_url("https://github.com/user/project/")
        == "https://github.com/user/project.git"
    )


def test_validate_github_repository_url_failure() -> None:
    for url in (
        "https://example.com/user/project",
        "https://gitlab.com/owner/repo.git",
        "http://github.com/user/repo",
        "https://github.com/",
        "https://github.com/user",
        "",
        "not-a-url",
    ):
        with pytest.raises(GitHubImportError):
            validate_github_repository_url(url)


def test_extract_github_repository_name() -> None:
    assert extract_github_repository_name("https://github.com/safi-io/fastapi-starter-kit") == "fastapi-starter-kit"
    assert extract_github_repository_name("https://github.com/safi-io/fastapi-starter-kit.git") == "fastapi-starter-kit"
    assert extract_github_repository_name("https://github.com/safi-io/fastapi-starter-kit/") == "fastapi-starter-kit"
    with pytest.raises(GitHubImportError):
        extract_github_repository_name("https://example.com/x/y")
    with pytest.raises(GitHubImportError):
        extract_github_repository_name("https://gitlab.com/owner/repo.git")


def test_clone_github_repository_git_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("py_env_studio.core.templates.github_import.shutil.which", lambda *_: None)
    with pytest.raises(GitHubImportError):
        clone_github_repository("https://github.com/user/project.git", tmp_path / "repo")


def test_clone_github_repository_nonzero_exit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("py_env_studio.core.templates.github_import.shutil.which", lambda *_: "git")

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stderr="not found")

    monkeypatch.setattr("py_env_studio.core.templates.github_import.subprocess.run", fake_run)
    with pytest.raises(GitHubImportError) as exc:
        clone_github_repository("https://github.com/user/project.git", tmp_path / "repo")
    assert "Failed to clone repository" in str(exc.value)


def test_clone_github_repository_success(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "repo"
    monkeypatch.setattr("py_env_studio.core.templates.github_import.shutil.which", lambda *_: "git")

    def fake_run(cmd, **kwargs):
        destination.mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("py_env_studio.core.templates.github_import.subprocess.run", fake_run)
    result = clone_github_repository("https://github.com/user/project.git", destination)
    assert result == destination.resolve()
