"""Focused tests for Python runtime online-metadata caching (spec section 15)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from py_env_studio.core.database import DatabaseManager
from py_env_studio.core.runtime_cache import (
    ONLINE_METADATA_TTL,
    RuntimeCache,
    find_runtime_usage,
    map_runtime_usage,
)
from py_env_studio.core.runtime_providers import PythonInstallManagerProvider, PythonRuntime


def _rt(version: str) -> PythonRuntime:
    return PythonRuntime(
        version=version,
        display=f"Python {version}",
        architecture="64-bit",
        release_status="Supported",
        implementation="cpython",
        installed=False,
    )


def _cache(tmp_path: Path, **kwargs) -> RuntimeCache:
    dbm = DatabaseManager(db_path=tmp_path / "test.db")
    dbm.initialize_database()
    return RuntimeCache(db_manager=dbm, **kwargs)


class _FakeProvider(PythonInstallManagerProvider):
    """Provider double: local installed list + countable online queries."""

    def __init__(self, installed, online=None, online_error=None):
        super().__init__(py_executable="py")
        self._installed = list(installed)
        self._online = list(online or [])
        self.online_error = online_error
        self.online_calls = 0
        self.installed_calls = 0

    def is_available(self) -> bool:
        return True

    def list_installed(self):
        self.installed_calls += 1
        return list(self._installed)

    def list_online_releases(self):
        self.online_calls += 1
        if self.online_error is not None:
            raise RuntimeError(self.online_error)
        return list(self._online)


def test_ttl_constant_is_24_hours():
    assert ONLINE_METADATA_TTL == timedelta(hours=24)


def test_cache_hit_no_online_call(tmp_path: Path):
    cache = _cache(tmp_path)
    installed = [_rt("3.12.10")]
    installed[0] = PythonRuntime(**{**installed[0].__dict__, "installed": True})
    provider = _FakeProvider(
        installed=installed,
        online=[_rt("3.13.7"), _rt("3.12.10"), _rt("3.11.11")],
    )
    cache.save(provider._online)
    provider.online_calls = 0

    overview = cache.get_overview(provider)
    assert provider.online_calls == 0  # fresh cache -> no internet request
    assert overview.cache_present and not overview.stale
    assert [r.version for r in overview.cached_releases] == ["3.13.7", "3.12.10", "3.11.11"]
    assert [r.version for r in overview.available] == ["3.13.7", "3.11.11"]
    assert overview.last_checked is not None


def test_cache_miss_queries_online_and_updates_db(tmp_path: Path):
    cache = _cache(tmp_path)
    provider = _FakeProvider(installed=[], online=[_rt("3.13.7")])

    overview = cache.get_overview(provider)
    assert provider.online_calls == 1
    assert overview.cache_present and not overview.stale
    cached, _ = cache.load_cached()
    assert [r.version for r in cached] == ["3.13.7"]


def test_expired_cache_refreshes_and_marks_stale_on_failure(tmp_path: Path):
    now = datetime.now(timezone.utc)
    moments = {"now": now}
    cache = _cache(tmp_path, now_fn=lambda: moments["now"])
    provider = _FakeProvider(installed=[], online=[_rt("3.13.7")])
    cache.save(provider._online)
    provider.online_calls = 0

    # Within TTL: no refresh.
    moments["now"] = now + timedelta(hours=1)
    cache.get_overview(provider)
    assert provider.online_calls == 0

    # Expired: refresh succeeds.
    moments["now"] = now + timedelta(hours=25)
    provider._online = [_rt("3.13.7"), _rt("3.14.0")]
    overview = cache.get_overview(provider)
    assert provider.online_calls == 1
    assert [r.version for r in overview.available] == ["3.14.0", "3.13.7"]

    # Expired + online failure: stale data preserved, UI usable.
    moments["now"] = now + timedelta(hours=50)
    provider.online_error = "network down"
    overview = cache.get_overview(provider)
    assert overview.cache_present and overview.stale
    assert "Unable to refresh" in (overview.error or "")
    assert [r.version for r in overview.cached_releases] == ["3.14.0", "3.13.7"]
    cached, _ = cache.load_cached()
    assert [r.version for r in cached] == ["3.14.0", "3.13.7"]


def test_empty_cache_plus_offline_graceful(tmp_path: Path):
    cache = _cache(tmp_path)
    provider = _FakeProvider(installed=[], online_error="no internet")
    overview = cache.get_overview(provider)
    assert not overview.cache_present
    assert overview.available == []
    assert "No online release information" in (overview.error or "")


def test_explicit_refresh_forces_online_query(tmp_path: Path):
    cache = _cache(tmp_path)
    provider = _FakeProvider(installed=[], online=[_rt("3.13.7")])
    cache.save(provider._online)
    provider.online_calls = 0
    overview = cache.get_overview(provider, force_refresh=True)
    assert provider.online_calls == 1
    assert overview.cache_present and not overview.stale


def test_installed_filtering_needs_no_online_request(tmp_path: Path):
    cache = _cache(tmp_path)
    cached = [_rt("3.13.7"), _rt("3.12.10"), _rt("3.11.11")]
    cache.save(cached)
    installed = [
        PythonRuntime(version="3.13.7", display="Python 3.13.7", installed=True),
        PythonRuntime(version="3.12.10", display="Python 3.12.10", installed=True),
    ]
    assert [r.version for r in RuntimeCache.filter_available(cached, installed)] == ["3.11.11"]


def test_single_refresh_for_many_installed(tmp_path: Path):
    """One metadata refresh covers 3.14/3.13/3.12/3.11 rows (no per-row fetch)."""
    cache = _cache(tmp_path)
    provider = _FakeProvider(
        installed=[
            PythonRuntime(version="3.14.0", display="Python 3.14.0", installed=True),
            PythonRuntime(version="3.13.0", display="Python 3.13.0", installed=True),
            PythonRuntime(version="3.12.0", display="Python 3.12.0", installed=True),
            PythonRuntime(version="3.11.0", display="Python 3.11.0", installed=True),
        ],
        online=[_rt("3.14.7"), _rt("3.13.7"), _rt("3.12.10"), _rt("3.11.11")],
    )
    overview = cache.get_overview(provider)
    assert provider.online_calls == 1
    candidates = cache.update_candidates(overview.installed, overview.cached_releases)
    assert candidates["3.14.0"].version == "3.14.7"
    assert candidates["3.13.0"].version == "3.13.7"
    assert candidates["3.12.0"].version == "3.12.10"
    assert candidates["3.11.0"].version == "3.11.11"


def test_update_candidate_none_when_current(tmp_path: Path):
    cache = _cache(tmp_path)
    assert cache.find_update_candidate("3.13.7", [_rt("3.13.7"), _rt("3.12.10")]) is None
    # Different minor lines are not "updates" (no surprising major jumps).
    assert cache.find_update_candidate("3.12.10", [_rt("3.13.7")]) is None


def test_used_by_detection_local_only(tmp_path: Path, monkeypatch):
    import py_env_studio.core.runtime_cache as rc

    venv_root = tmp_path / "venvs"
    (venv_root / "env-a").mkdir(parents=True)
    (venv_root / "env-a" / "pyvenv.cfg").write_text("version = 3.12.10\n", encoding="utf-8")
    (venv_root / "env-b").mkdir(parents=True)
    (venv_root / "env-b" / "pyvenv.cfg").write_text("version = 3.13.7\n", encoding="utf-8")

    monkeypatch.setattr("py_env_studio.core.env_manager.VENV_DIR", str(venv_root))
    monkeypatch.setattr("py_env_studio.core.env_manager.ENV_DATA_FILE", str(tmp_path / "env_data.json"))
    monkeypatch.setattr(rc, "get_env_runtime_version",
                        lambda name, venv_dir=None: {"env-a": "3.12.10", "env-b": "3.13.7"}.get(name))

    assert find_runtime_usage("3.12.10", env_names=["env-a", "env-b"]) == ["env-a"]
    assert find_runtime_usage("3.12", env_names=["env-a", "env-b"]) == ["env-a"]  # prefix match
    mapping = map_runtime_usage(
        [PythonRuntime(version="3.12.10", display="x", installed=True),
         PythonRuntime(version="3.13.7", display="y", installed=True)],
        env_names=["env-a", "env-b"],
    )
    assert mapping == {"3.12.10": ["env-a"], "3.13.7": ["env-b"]}


def test_uninstall_flows_through_provider_and_keeps_cache(tmp_path: Path):
    cache = _cache(tmp_path)
    cache.save([_rt("3.13.7"), _rt("3.12.10")])
    provider = _FakeProvider(
        installed=[PythonRuntime(version="3.13.7", display="Python 3.13.7", installed=True)],
        online=[_rt("3.13.7")],
    )
    removed = []

    def fake_run(args, log_callback=None):
        removed.append(args)
        return ""

    import unittest.mock as mock
    with mock.patch("shutil.which", return_value="py"), mock.patch(
        "py_env_studio.core.runtime_providers._probe_python_install_manager",
        return_value=True,
    ):
        real = PythonInstallManagerProvider(py_executable="py")
    # Patch the instance so the fake keeps its own (args, log_callback) signature.
    with mock.patch.object(real, "_run", fake_run):
        assert real.uninstall("3.13.7") == "3.13.7"
    assert removed[0][:2] == ["uninstall", "3.13.7"]
    # Cache untouched by uninstall (only local state changes).
    cached, _ = cache.load_cached()
    assert {r.version for r in cached} == {"3.13.7", "3.12.10"}
    assert [r.version for r in RuntimeCache.filter_available(cached, [])] == ["3.13.7", "3.12.10"]
