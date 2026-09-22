"""Cache for Python Install Manager online release metadata.

Architecture::

    Python Runtime UI -> RuntimeCache -> Local DB Cache + Runtime Provider

- Installed runtimes: always queried locally (``py list --format=json``).
- Official available releases: cached in the existing SQLite DB; the
  network-backed ``list_online_releases`` (``py list --online``) runs only
  when the cache is missing, expired, or the user explicitly refreshes.
- Install/update/uninstall still execute through the real provider.

Only one online metadata query is ever issued per refresh, never one per
installed-runtime row.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import schema as sql
from .database import DatabaseManager
from .runtime_providers import PythonInstallManagerProvider, PythonRuntime

LOGGER = logging.getLogger(__name__)

#: Default TTL for cached online release metadata (spec section 3).
ONLINE_METADATA_TTL = timedelta(hours=24)

_PROVIDER_DEFAULT = "Python Install Manager"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        value = raw
    else:
        text = str(raw).strip()
        if not text:
            return None
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_age(last_updated: datetime | None, now: datetime | None = None) -> str:
    if last_updated is None:
        return "never"
    now = now or _utcnow()
    delta = now - last_updated
    seconds = max(0, int(delta.total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def _version_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(version).strip().split("."))
    except (TypeError, ValueError):
        return (999999,)


def _major_minor(version: str) -> str:
    parts = str(version).strip().split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else str(version).strip()


@dataclass
class RuntimeOverview:
    """Everything the Configuration > Python Runtime UI needs in one shot."""

    provider_name: str
    provider_available: bool
    installed: list[PythonRuntime] = field(default_factory=list)
    cached_releases: list[PythonRuntime] = field(default_factory=list)
    available: list[PythonRuntime] = field(default_factory=list)
    last_checked: datetime | None = None
    stale: bool = True
    cache_present: bool = False
    error: str | None = None
    background_refresh_needed: bool = False

    @property
    def last_checked_label(self) -> str:
        if self.last_checked is None:
            return "Last checked: never"
        return f"Last checked: {_format_age(self.last_checked)}"


def runtime_to_record(runtime: PythonRuntime) -> dict:
    return {
        "version": runtime.version,
        "display": runtime.display,
        "architecture": runtime.architecture,
        "release_status": runtime.release_status,
        "implementation": runtime.implementation,
        "installed": False,
        "path": None,
        "provider": _PROVIDER_DEFAULT,
    }


def record_to_runtime(record: dict) -> PythonRuntime | None:
    version = str(record.get("version") or "").strip()
    if not version:
        return None
    display = str(record.get("display") or f"Python {version}")
    return PythonRuntime(
        version=version,
        display=display,
        architecture=record.get("architecture"),
        release_status=record.get("release_status"),
        implementation=record.get("implementation") or "cpython",
        installed=False,
        path=None,
    )


class RuntimeCache:
    """TTL-based cache for official Python release metadata (existing DB)."""

    def __init__(
        self,
        db_path: Path | None = None,
        db_manager: DatabaseManager | None = None,
        ttl: timedelta = ONLINE_METADATA_TTL,
        now_fn: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._dbm = db_manager or DatabaseManager(db_path=db_path)
        self._ttl = ttl
        self._now_fn = now_fn
        # Ensure schema exists (idempotent; reuses existing DB file).
        try:
            self._dbm.initialize_database()
        except Exception:
            LOGGER.debug("RuntimeCache could not initialize database", exc_info=True)

    # ------------------------------------------------------------------
    # Low-level cache access
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = self._dbm.connect()
        # Rows accessed by index; keep stdlib-only.
        return conn

    def load_cached(
        self, provider_name: str = _PROVIDER_DEFAULT
    ) -> tuple[list[PythonRuntime], datetime | None]:
        """Return (cached releases, last_updated). Empty list when no cache."""
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                try:
                    rows = cur.execute(
                        sql.get("runtime_cache", "select_metadata_by_provider"),
                        (provider_name,),
                    ).fetchall()
                except sqlite3.OperationalError:
                    return [], None  # table missing (old DB, unmigrated)
                releases: list[PythonRuntime] = []
                for (payload,) in rows:
                    try:
                        record = json.loads(payload)
                    except (TypeError, ValueError):
                        continue
                    runtime = record_to_runtime(record)
                    if runtime is not None:
                        releases.append(runtime)
                releases.sort(key=lambda item: _version_key(item.version), reverse=True)
                try:
                    state = cur.execute(
                        sql.get("runtime_cache", "select_cache_state"),
                        (provider_name,),
                    ).fetchone()
                except sqlite3.OperationalError:
                    state = None
                last_updated = _parse_ts(state[0]) if state else None
                return releases, last_updated
        except Exception:
            LOGGER.debug("Failed to load cached runtime metadata", exc_info=True)
            return [], None

    def is_fresh(self, last_updated: datetime | None) -> bool:
        if last_updated is None:
            return False
        return (self._now_fn() - last_updated) < self._ttl

    def save(
        self, releases: list[PythonRuntime], provider_name: str = _PROVIDER_DEFAULT
    ) -> datetime:
        """Persist normalized metadata in one transaction. Returns timestamp."""
        now = self._now_fn()
        stamp = now.isoformat()
        with self._connect() as conn:
            cur = conn.cursor()
            # Single transaction/batch write (spec section 11).
            cur.execute(
                sql.get("runtime_cache", "delete_metadata_by_provider"), (provider_name,)
            )
            cur.executemany(
                sql.get("runtime_cache", "insert_metadata_row"),
                [
                    (
                        provider_name,
                        rt.version,
                        rt.release_status,
                        rt.architecture,
                        rt.implementation,
                        json.dumps(runtime_to_record(rt)),
                        stamp,
                    )
                    for rt in releases
                ],
            )
            cur.execute(
                sql.get("runtime_cache", "upsert_cache_state"),
                (provider_name, stamp),
            )
            conn.commit()
        return now

    def record_error(self, message: str, provider_name: str = _PROVIDER_DEFAULT) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    sql.get("runtime_cache", "record_cache_error"),
                    (provider_name, self._now_fn().isoformat(), message[:500]),
                )
                conn.commit()
        except Exception:
            LOGGER.debug("Failed to record cache error", exc_info=True)

    # ------------------------------------------------------------------
    # High-level policy
    # ------------------------------------------------------------------
    @staticmethod
    def filter_available(
        cached: list[PythonRuntime], installed: list[PythonRuntime]
    ) -> list[PythonRuntime]:
        """available_to_install = cached_official_releases - installed (local only)."""
        installed_keys = {_version_key(rt.version) for rt in installed}
        return [rt for rt in cached if _version_key(rt.version) not in installed_keys]

    @staticmethod
    def find_update_candidate(
        installed_version: str, cached: list[PythonRuntime]
    ) -> PythonRuntime | None:
        """Newest cached patch on the same major.minor line, if newer."""
        wanted = _major_minor(installed_version)
        installed_key = _version_key(installed_version)
        candidates = [
            rt
            for rt in cached
            if _major_minor(rt.version) == wanted and _version_key(rt.version) > installed_key
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: _version_key(item.version))

    def update_candidates(
        self, installed: list[PythonRuntime], cached: list[PythonRuntime]
    ) -> dict[str, PythonRuntime]:
        """Map installed version -> newer cached release (single metadata set)."""
        result: dict[str, PythonRuntime] = {}
        for rt in installed:
            candidate = self.find_update_candidate(rt.version, cached)
            if candidate is not None:
                result[rt.version] = candidate
        return result

    def refresh_online(
        self,
        provider: PythonInstallManagerProvider | None = None,
        provider_name: str = _PROVIDER_DEFAULT,
    ) -> list[PythonRuntime]:
        """Query the online catalogue once and update the cache.

        Raises on failure without touching the existing cache (spec 6/10:
        at most 1 metadata refresh, never one request per runtime row).
        """
        provider = provider or PythonInstallManagerProvider()
        releases = provider.list_online_releases()
        self.save(releases, provider_name=provider_name)
        return releases

    def get_overview(
        self,
        provider=None,
        provider_name: str = _PROVIDER_DEFAULT,
        *,
        force_refresh: bool = False,
    ) -> RuntimeOverview:
        """Load UI state without unnecessary network access.

        - Fresh cache (or non-PyManager provider): no online request.
        - Missing/expired cache (or force): exactly one online query.
        - Online failure: existing cache preserved, error attached.
        """
        from .runtime_providers import get_runtime_provider  # local import: avoid cycle

        if provider is None:
            try:
                provider = get_runtime_provider(provider_name)
            except ValueError as exc:
                return RuntimeOverview(
                    provider_name=provider_name,
                    provider_available=False,
                    error=str(exc),
                )

        try:
            provider_available = bool(provider.is_available())
        except Exception:
            provider_available = False
        if not provider_available:
            return RuntimeOverview(
                provider_name=getattr(provider, "NAME", provider_name),
                provider_available=False,
                error=f"{getattr(provider, 'NAME', provider_name)} is not available on this system.",
            )

        # Installed runtimes are local machine state: always query locally.
        try:
            installed = provider.list_installed()
        except Exception as exc:
            LOGGER.warning("Local installed-runtime query failed: %s", exc)
            installed = []

        # Only the Install Manager has an online catalogue worth caching.
        if getattr(provider, "NAME", "") != _PROVIDER_DEFAULT:
            return RuntimeOverview(
                provider_name=provider.NAME,
                provider_available=True,
                installed=installed,
                cached_releases=[],
                available=[],
                last_checked=None,
                stale=False,
                cache_present=False,
            )

        cached, last_updated = self.load_cached(provider_name)
        fresh = self.is_fresh(last_updated)

        if force_refresh or not cached or not fresh:
            try:
                fresh_releases = self.refresh_online(provider, provider_name=provider_name)
                _, last_updated = self.load_cached(provider_name)
                cached = fresh_releases
                fresh = True
            except Exception as exc:
                LOGGER.warning("Online metadata refresh failed; using cache: %s", exc)
                self.record_error(str(exc), provider_name=provider_name)
                if not cached:
                    return RuntimeOverview(
                        provider_name=provider_name,
                        provider_available=True,
                        installed=installed,
                        cached_releases=[],
                        available=[],
                        last_checked=last_updated,
                        stale=True,
                        cache_present=False,
                        error=(
                            "No online release information is currently available. "
                            f"({exc})"
                        ),
                    )
                return RuntimeOverview(
                    provider_name=provider_name,
                    provider_available=True,
                    installed=installed,
                    cached_releases=cached,
                    available=self.filter_available(cached, installed),
                    last_checked=last_updated,
                    stale=True,
                    cache_present=True,
                    error=(
                        "Unable to refresh Python release information. "
                        "Showing cached data."
                    ),
                )

        return RuntimeOverview(
            provider_name=provider_name,
            provider_available=True,
            installed=installed,
            cached_releases=cached,
            available=self.filter_available(cached, installed),
            last_checked=last_updated,
            stale=not fresh,
            cache_present=bool(cached),
        )

    def get_overview_stale_while_revalidate(
        self,
        provider=None,
        provider_name: str = _PROVIDER_DEFAULT,
        *,
        on_refreshed: Callable[[RuntimeOverview], None] | None = None,
        dispatcher: Callable[[Callable[[], None]], object] | None = None,
    ) -> RuntimeOverview:
        """Return stale cache immediately; refresh expired cache in background.

        Used by the UI thread so opening Configuration never blocks on the
        network (spec sections 7/14).

        Threading contract: the background refresh runs on a worker thread, so
        ``on_refreshed`` is invoked **off the Tk main thread** and must not
        touch widgets directly.  UI callers pass ``dispatcher`` — a callable
        that schedules a zero-argument callback on the main thread, e.g.
        ``lambda cb: post_to_ui(self, cb)`` — and the fresh overview is
        delivered through it::

            cache.get_overview_stale_while_revalidate(
                on_refreshed=self._apply_overview,
                dispatcher=lambda cb: post_to_ui(self, cb),
            )

        Without a dispatcher the callback runs on the worker thread, which is
        only appropriate for non-UI consumers (CLI/MCP).
        """
        import threading

        overview = self.get_overview(provider, provider_name)
        # get_overview above already refreshes synchronously on miss/expiry.
        # For the UI path we instead want: serve stale immediately and refresh
        # behind. So if it came back stale-with-data, kick off a background
        # refresh; the synchronous refresh inside get_overview only happens
        # when cache was missing entirely (unavoidable single query).
        if overview.cache_present and overview.stale and on_refreshed is not None:
            prov = provider
            cb = on_refreshed

            def _deliver(fresh: RuntimeOverview) -> None:
                if dispatcher is None:
                    cb(fresh)
                else:
                    dispatcher(lambda: cb(fresh))

            def _bg() -> None:
                try:
                    fresh = self.get_overview(prov, provider_name, force_refresh=True)
                except Exception as exc:  # never crash the background thread
                    LOGGER.debug("Background metadata refresh failed: %s", exc)
                    return
                try:
                    _deliver(fresh)
                except Exception:
                    LOGGER.debug("Refresh callback failed", exc_info=True)

            threading.Thread(target=_bg, daemon=True).start()
        return overview


# ----------------------------------------------------------------------
# Used By environment detection (local only, no network)
# ----------------------------------------------------------------------
def _read_venv_version(venv_dir: Path) -> str | None:
    """Read the base Python version of a venv without launching subprocesses."""
    cfg = venv_dir / "pyvenv.cfg"
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip().lower() == "version":
            candidate = value.strip().split()[0]
            if candidate and candidate[0].isdigit():
                return candidate
    return None


def get_env_runtime_version(env_name: str, venv_dir: Path | None = None) -> str | None:
    """Best-effort local detection of which Python an env was built with."""
    # 1. Stored metadata (fast path, written at creation time).
    try:
        from . import env_manager as _env_manager

        data = _env_manager.get_env_data(env_name) or {}
        stored = str(data.get("python_version") or "").strip()
        if stored:
            return stored
    except Exception:
        pass
    # 2. pyvenv.cfg of the venv directory (no subprocess, no network).
    try:
        from .env_manager import VENV_DIR as _default_venv_dir

        base = Path(venv_dir) if venv_dir is not None else Path(_default_venv_dir)
        version = _read_venv_version(base / env_name)
        if version:
            return version
    except Exception:
        pass
    return None


def _matches_runtime(env_version: str, runtime_version: str) -> bool:
    env_key = _version_key(env_version)
    rt_key = _version_key(runtime_version)
    if env_key == rt_key:
        return True
    # "3.12" runtime satisfies "3.12.10" env and vice versa (prefix match).
    env_parts = str(env_version).strip().split(".")
    rt_parts = str(runtime_version).strip().split(".")
    shortest = min(len(env_parts), len(rt_parts))
    return env_parts[:shortest] == rt_parts[:shortest]


def find_runtime_usage(
    runtime_version: str,
    env_names: list[str] | None = None,
    venv_dir: Path | None = None,
) -> list[str]:
    """Return env names built with ``runtime_version`` (local only)."""
    try:
        from . import env_manager as _env_manager

        names = list(env_names) if env_names is not None else _env_manager.list_envs()
    except Exception:
        names = list(env_names or [])
    used_by: list[str] = []
    for name in names:
        detected = get_env_runtime_version(name, venv_dir=venv_dir)
        if detected and _matches_runtime(detected, runtime_version):
            used_by.append(name)
    return sorted(used_by)


def map_runtime_usage(
    installed: list[PythonRuntime],
    env_names: list[str] | None = None,
    venv_dir: Path | None = None,
) -> dict[str, list[str]]:
    """Map each installed runtime version -> envs using it (one local pass)."""
    try:
        from . import env_manager as _env_manager

        names = list(env_names) if env_names is not None else _env_manager.list_envs()
    except Exception:
        names = list(env_names or [])
    detected_versions: dict[str, str | None] = {
        name: get_env_runtime_version(name, venv_dir=venv_dir) for name in names
    }
    mapping: dict[str, list[str]] = {}
    for rt in installed:
        mapping[rt.version] = sorted(
            name
            for name, detected in detected_versions.items()
            if detected and _matches_runtime(detected, rt.version)
        )
    return mapping
