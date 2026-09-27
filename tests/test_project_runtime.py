"""Regression tests for the project runtime toggle (`pes init` / `pes on` / `pes off`).

These tests target the public API of :mod:`py_env_studio.core.runtime_toggle`.

They replace the previous stale tests that called ``env_manager.initialize_project_runtime``,
``env_manager.disable_project_runtime`` and ``env_manager.load_project_runtime_state`` — none of those
functions exist in the production code, so the whole module failed with ``AttributeError``
(audit finding F-02, catalog cases TC-RT-016 / TC-RT-017).

Determinism: managed-environment creation is stubbed and every runtime path (envs dir, registry) is
redirected into ``tmp_path``, so no real virtual environment is created and nothing outside ``tmp_path``
is written.
"""

from pathlib import Path

import pytest

from py_env_studio.core import runtime_toggle


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch) -> Path:
    """Create a throw-away project directory and make it the working directory."""
    root = tmp_path / "demo-project"
    root.mkdir()
    monkeypatch.chdir(root)
    return root


@pytest.fixture()
def runtime_paths(tmp_path: Path, monkeypatch) -> dict:
    """Redirect runtime state to ``tmp_path`` and stub virtual-environment creation."""
    envs_dir = tmp_path / "venvs"
    data_dir = tmp_path / "data"
    created: list[str] = []

    def fake_create_managed_environment(env_id: str, python_version: str) -> Path:
        created.append(env_id)
        env_path = envs_dir / env_id
        env_path.mkdir(parents=True, exist_ok=True)
        (env_path / "pyvenv.cfg").write_text("home = /tmp\n", encoding="utf-8")
        return env_path

    monkeypatch.setattr(runtime_toggle, "get_envs_dir", lambda: envs_dir)
    monkeypatch.setattr(runtime_toggle, "get_global_data_dir", lambda: data_dir)
    monkeypatch.setattr(runtime_toggle, "create_managed_environment", fake_create_managed_environment)
    monkeypatch.setattr(runtime_toggle, "get_preferred_package_manager", lambda: "pip")
    return {"envs_dir": envs_dir, "data_dir": data_dir, "created": created}


def test_init_project_creates_environment_once_and_reuses_it(project_root: Path, runtime_paths: dict) -> None:
    """`pes init` creates the managed environment once and reuses it on later runs."""
    first = runtime_toggle.init_project(project_root=project_root)
    second = runtime_toggle.init_project(project_root=project_root)

    assert first["success"] is True
    assert second["success"] is True
    assert runtime_paths["created"] == [first["environment_id"]]
    assert second["environment_id"] == first["environment_id"]

    assert runtime_toggle.get_project_metadata_path(project_root).exists()
    assert runtime_toggle.is_runtime_enabled(project_root) is True

    registry = runtime_toggle.load_registry()
    assert registry[project_root.name]["environment_id"] == first["environment_id"]


def test_disable_runtime_turns_runtime_off_and_keeps_environment(project_root: Path, runtime_paths: dict) -> None:
    """`pes off` disables the runtime without touching the managed environment, `pes on` re-enables it."""
    first = runtime_toggle.init_project(project_root=project_root)
    assert first["success"] is True

    disabled = runtime_toggle.disable_runtime(project_root=project_root)

    assert disabled["success"] is True
    assert runtime_toggle.is_runtime_enabled(project_root) is False

    metadata = runtime_toggle.load_project_metadata(project_root)
    assert metadata["runtime_enabled"] is False
    assert metadata["environment_id"] == first["environment_id"]
    assert not runtime_toggle.load_registry()[project_root.name]["runtime_enabled"]

    # Disabling the runtime must never delete the managed environment.
    assert (runtime_paths["envs_dir"] / metadata["environment_id"]).exists()

    assert runtime_toggle.enable_runtime(project_root=project_root)["success"] is True
    assert runtime_toggle.is_runtime_enabled(project_root) is True

