"""Application bootstrap orchestration for setup state and DB readiness."""

from __future__ import annotations

import shutil
import logging

from .database import DatabaseManager
from .runtime import get_runtime_config
from .setup_state import SetupStateManager
from .windows_apps import ensure_windows_apps_shortcut

LOGGER = logging.getLogger(__name__)


def initialize_app_runtime() -> str:
    """Initialize setup state and database, returning startup health status."""
    runtime = get_runtime_config()
    state = SetupStateManager()
    health = state.check_installation_health()

    if not runtime.db_path.exists() and runtime.legacy_db_path.exists():
        runtime.db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runtime.legacy_db_path, runtime.db_path)

    should_repair = health in {"missing", "recover", "failed", "migrate"}
    if should_repair:
        state.create_installing_marker()

    try:
        db = DatabaseManager(runtime.db_path)
        db.initialize_database()
        try:
            ensure_windows_apps_shortcut()
        except Exception as shortcut_exc:
            LOGGER.warning("Windows Apps shortcut setup skipped: %s", shortcut_exc)
        if should_repair or health == "complete":
            state.mark_setup_complete()
    except Exception as exc:
        state.mark_setup_failed(str(exc))
        raise

    return health
