"""Per-environment package-update checks and their SQLite cache."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import schema as sql
from .database import DatabaseManager
from .env_manager import VENV_DIR, get_env_python
from .package_manager import check_outdated_packages, get_env_package_manager

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(hours=6)


class PackageUpdateMonitor:
    """Read cached update counts and refresh them through package_manager."""

    def __init__(self, db_manager: DatabaseManager | None = None, ttl: timedelta = CACHE_TTL):
        self._db = db_manager or DatabaseManager()
        self._ttl = ttl
        self._init_lock = threading.Lock()
        self._initialized = False
        self._check_locks_guard = threading.Lock()
        self._check_locks: dict[str, threading.Lock] = {}

    def _initialize(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if not self._initialized:
                self._db.initialize_database()
                self._initialized = True

    def _environment_id(self, env_name: str) -> int:
        env_path = str(Path(VENV_DIR) / env_name)
        self._initialize()
        with self._db.connect() as connection:
            cursor = connection.execute(
                sql.get("package_updates", "ensure_environment"),
                (env_name, env_path, datetime.now(timezone.utc).isoformat()),
            )
            row = connection.execute(
                sql.get("environments", "get_env_id"), (env_name,)
            ).fetchone()
            connection.commit()
        return int(row[0])

    def get_cached_result(self, env_name: str, package_manager: str) -> dict | None:
        """Return a cached result, including an unavailable result, if fresh."""
        env_id = self._environment_id(env_name)
        with self._db.connect() as connection:
            row = connection.execute(
                sql.get("package_updates", "get_cached_package_updates"), (env_id,)
            ).fetchone()
        if not row or row[2] != package_manager:
            return None
        try:
            last_checked = datetime.fromisoformat(row[1])
            if last_checked.tzinfo is None:
                last_checked = last_checked.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None
        if datetime.now(timezone.utc) - last_checked > self._ttl:
            return None
        try:
            outdated_packages = json.loads(row[4]) if row[4] else None
        except (TypeError, ValueError):
            logger.warning("Ignoring malformed cached package details for '%s'", env_name)
            outdated_packages = None
        return {
            "outdated_count": row[0],
            "last_checked_at": row[1],
            "package_manager": row[2],
            "error": row[3],
            "outdated_packages": outdated_packages,
        }

    def check_environment(self, env_name: str) -> dict:
        """Check one valid environment; failures are cached and returned."""
        manager = get_env_package_manager(env_name)
        env_python = Path(get_env_python(env_name))
        env_dir = env_python.parent.parent
        try:
            if not (env_dir / "pyvenv.cfg").is_file() or not env_python.is_file():
                raise FileNotFoundError(f"Environment '{env_name}' is not available")

            outdated = json.loads(check_outdated_packages(env_name))
            if not isinstance(outdated, list):
                raise ValueError("Package manager returned an invalid outdated-package result")
            return self.record_result(
                env_name,
                len(outdated),
                package_manager=manager,
                outdated_packages=outdated,
            )
        except Exception as exc:
            logger.warning("Package-update check failed for environment '%s': %s", env_name, exc)
            return self.record_result(env_name, None, package_manager=manager, error=str(exc))

    def record_result(
        self,
        env_name: str,
        outdated_count: int | None,
        *,
        package_manager: str | None = None,
        error: str | None = None,
        outdated_packages: list[dict] | None = None,
    ) -> dict:
        """Persist a result already obtained through the package-manager API."""
        result = {
            "outdated_count": outdated_count,
            "outdated_packages": outdated_packages,
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "package_manager": package_manager or get_env_package_manager(env_name),
            "error": error,
        }
        env_id = self._environment_id(env_name)
        self._initialize()
        with self._db.connect() as connection:
            connection.execute(
                sql.get("package_updates", "save_package_update_cache"),
                (
                    env_id,
                    result["outdated_count"],
                    json.dumps(result["outdated_packages"]) if outdated_packages is not None else None,
                    result["last_checked_at"],
                    result["package_manager"],
                    result["error"],
                ),
            )
            connection.commit()
        return result

    def check_if_stale(self, env_name: str) -> dict:
        """Return a fresh cached result or run one serialized refresh."""
        with self._check_locks_guard:
            lock = self._check_locks.setdefault(env_name, threading.Lock())
        with lock:
            manager = get_env_package_manager(env_name)
            cached = self.get_cached_result(env_name, manager)
            return cached if cached is not None else self.check_environment(env_name)

    def needs_check(self, env_name: str, package_manager: str) -> bool:
        return self.get_cached_result(env_name, package_manager) is None

    def invalidate_cache(self, env_name: str) -> None:
        """Discard results when an environment is removed or recreated."""
        with self._check_locks_guard:
            lock = self._check_locks.setdefault(env_name, threading.Lock())
        with lock:
            self._initialize()
            with self._db.connect() as connection:
                connection.execute(
                    sql.get("package_updates", "delete_package_update_cache"), (env_name,)
                )
                connection.commit()