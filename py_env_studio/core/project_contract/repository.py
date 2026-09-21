"""SQLite persistence for the project contract (Phase A.1).

Uses DatabaseManager for execution and SQL templates from
core/schema/project_contract.sql. Upserts are keyed on the normalized
project path, so re-saving a project updates its single row.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from py_env_studio.core import schema as sql


_CONTRACT_COLUMNS = (
    "id",
    "project_path",
    "project_name",
    "environment_id",
    "python_version",
    "python_provider",
    "package_manager",
    "runtime_managed",
    "runtime_enabled",
    "runtime_auto_init",
    "config_path",
    "created_at",
    "updated_at",
)


def normalize_db_key(project_path) -> str:
    """Normalize a project path into its stable SQLite lookup key.

    pathlib only (no string surgery): resolves the absolute path and
    applies os.path.normcase so Windows drive-letter case differences map
    to the same row. Accepts str or Path.
    """
    return os.path.normcase(str(Path(str(project_path)).resolve()))


class ProjectContractRepository:
    """Registered-contract persistence. No parsing, no validation here."""

    def __init__(self, db_manager=None):
        self._db_manager = db_manager

    def _db(self):
        if self._db_manager is not None:
            return self._db_manager
        from py_env_studio.core.database import DatabaseManager

        return DatabaseManager()

    def upsert(
        self,
        project_path,
        project_name,
        environment_id,
        python_version,
        python_provider,
        package_manager,
        runtime_managed,
        runtime_enabled,
        runtime_auto_init,
        config_path,
    ) -> int:
        """Create or replace the registered row for a project path.

        Returns the row id.
        """
        key = normalize_db_key(project_path)
        dbm = self._db()
        with dbm.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                sql.get("project_contract", "upsert_project_contract"),
                (
                    key,
                    project_name,
                    environment_id,
                    python_version,
                    python_provider,
                    package_manager,
                    int(bool(runtime_managed)),
                    int(bool(runtime_enabled)),
                    int(bool(runtime_auto_init)),
                    str(config_path),
                ),
            )
            conn.commit()
            cur.execute(
                sql.get("project_contract", "select_project_contract_by_path"),
                (key,),
            )
            row = cur.fetchone()
        return int(row[0]) if row else -1

    def get_by_path(self, project_path) -> Optional[Dict[str, Any]]:
        """Return the registered row dict, or None when absent."""
        key = normalize_db_key(project_path)
        with self._db().connect() as conn:
            cur = conn.cursor()
            cur.execute(
                sql.get("project_contract", "select_project_contract_by_path"),
                (key,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        record = dict(zip(_CONTRACT_COLUMNS, row))
        for flag in ("runtime_managed", "runtime_enabled", "runtime_auto_init"):
            record[flag] = bool(record[flag])
        return record
