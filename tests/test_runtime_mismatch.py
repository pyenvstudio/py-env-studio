from pathlib import Path
import sys

import pytest

from py_env_studio.core import env_manager, runtime_toggle
from py_env_studio.core.runtime_mismatch import (
    DetectedRuntime,
    RuntimeMatchState,
    RuntimeMismatch,
    detect_runtime_mismatch,
    notify_mismatch_once,
)


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "demo-project"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'demo-project'\n", encoding="utf-8")
    monkeypatch.setattr(runtime_toggle, "get_global_data_dir", lambda: tmp_path / "pes-data")
    monkeypatch.setattr(runtime_toggle, "get_envs_dir", lambda: tmp_path / "venvs")
    return root


def _attach_environment(project_root: Path, executable: Path, version: str = "3.12.4") -> None:
    runtime_toggle.save_project_metadata(
        project_root,
        {
            "project_name": project_root.name,
            "environment_id": "demo-env",
            "environment_path": str(executable.parent),
            "python_version": version,
            "package_manager": "pip",
        },
    )


def _fake_environment(monkeypatch, executable: Path, version: str = "3.12.4") -> None:
    monkeypatch.setattr(
        env_manager,
        "get_environment_info",
        lambda _env_id: {
            "environment_id": "demo-env",
            "python_executable": str(executable),
            "python_version": version,
            "package_manager": "pip",
            "path": str(executable.parent),
        },
    )


def test_project_environment_association_is_persisted(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "venvs" / "demo-env" / "python.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    _fake_environment(monkeypatch, executable)

    runtime_toggle.associate_environment_with_project(project_root, "demo-env")

    assert runtime_toggle.load_project_metadata(project_root)["environment_id"] == "demo-env"
    assert runtime_toggle.load_registry()[project_root.name]["environment_id"] == "demo-env"
    runtime_toggle.unregister_project_environment(project_root)
    assert runtime_toggle.load_project_metadata(project_root)["environment_id"] == ""
    assert executable.exists()


def test_detect_matching_runtime(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "venvs" / "demo-env" / "python.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    _attach_environment(project_root, executable)
    _fake_environment(monkeypatch, executable)

    result = detect_runtime_mismatch(
        project_root,
        DetectedRuntime(str(executable), "3.12.4"),
    )

    assert result.state is RuntimeMatchState.MATCH
    assert result.registered_environment_id == "demo-env"
    assert result.registered_python_version == "3.12.4"


def test_detect_mismatching_runtime(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    registered = tmp_path / "venvs" / "demo-env" / "python.exe"
    current = tmp_path / "python.exe"
    registered.parent.mkdir(parents=True)
    registered.touch()
    current.touch()
    _attach_environment(project_root, registered)
    _fake_environment(monkeypatch, registered)

    result = detect_runtime_mismatch(
        project_root,
        DetectedRuntime(str(current), "3.12.4"),
    )

    assert result.state is RuntimeMatchState.MISMATCH
    assert result.current_python_executable == str(current)


def test_registered_environment_unavailable(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "missing" / "python.exe"
    _attach_environment(project_root, executable)
    monkeypatch.setattr(env_manager, "get_environment_info", lambda _env_id: None)

    result = detect_runtime_mismatch(project_root, DetectedRuntime(sys.executable, "3.12.4"))

    assert result.state is RuntimeMatchState.REGISTERED_ENVIRONMENT_UNAVAILABLE


def test_no_project_association(project_root: Path) -> None:
    result = detect_runtime_mismatch(project_root, DetectedRuntime(sys.executable, "3.12.4"))
    assert result.state is RuntimeMatchState.NO_PROJECT_ASSOCIATION


def test_unreliable_runtime_is_unknown(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "venvs" / "demo-env" / "python.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    _attach_environment(project_root, executable)
    _fake_environment(monkeypatch, executable)

    result = detect_runtime_mismatch(project_root, DetectedRuntime(None, None, reliable=False))

    assert result.state is RuntimeMatchState.UNKNOWN


def test_legacy_project_metadata_loads_without_new_runtime_field(project_root: Path) -> None:
    (project_root / "pes.config").write_text(
        "[project]\nname = demo-project\n\n[environment]\nid = legacy-env\n",
        encoding="utf-8",
    )

    metadata = runtime_toggle.load_project_metadata(project_root)

    assert metadata["environment_id"] == "legacy-env"
    assert runtime_toggle.get_last_mismatch_signature(project_root) == ""


def test_same_mismatch_only_notifies_once(project_root: Path) -> None:
    result = RuntimeMismatch(
        project_path=str(project_root),
        project_name=project_root.name,
        registered_environment_id="demo-env",
        registered_python_executable="/pes/python",
        registered_python_version="3.12.4",
        current_python_executable="/global/python",
        current_python_version="3.12.4",
        state=RuntimeMatchState.MISMATCH,
    )

    assert notify_mismatch_once(result) is True
    assert notify_mismatch_once(result) is False