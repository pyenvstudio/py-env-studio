"""SQLite lifecycle manager for Py Env Studio."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import schema as sql
from .runtime import get_runtime_config


class DatabaseError(Exception):
    """Custom exception for DB initialization or access failures."""


class DatabaseManager:
    """Manages SQLite lifecycle, schema creation, and basic migration."""

    def __init__(self, db_path: Path | None = None):
        runtime = get_runtime_config()
        self.db_path = Path(db_path or runtime.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(sql.get("schema_core", "enable_foreign_keys"))
            return conn
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to connect to DB: {exc}") from exc

    def initialize_database(self) -> None:
        try:
            with self.connect() as conn:
                cur = conn.cursor()

                # DDL lives in core/schema/*.sql; executed in file order.
                # enable_foreign_keys is a connection PRAGMA, not DDL: skip it.
                for name in sql.available("schema_core"):
                    if name == "enable_foreign_keys":
                        continue
                    cur.execute(sql.get("schema_core", name))
                for statement in sql.statements("schema_runtime_cache"):
                    cur.execute(statement)
                # project_contract.sql mixes DDL with DML templates: only the
                # create_* statements are schema, the rest are fetched by name
                # at the call site (see ProjectContractRepository).
                for name in sql.available("project_contract"):
                    if name.startswith("create_"):
                        cur.execute(sql.get("project_contract", name))

                self._migrate_legacy_schema(cur)
                conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"SQLite initialization error: {exc}") from exc
        except Exception as exc:
            raise DatabaseError(f"Unexpected error initializing DB: {exc}") from exc

    #: Columns the legacy table may use for the scan payload. Identifiers
    #: cannot be bound parameters, so the template is formatted only with
    #: a value from this whitelist (see core/schema/migration.sql).
    _LEGACY_PAYLOAD_COLUMNS = ("vulnerabilities", "vulneribilities")

    def _migrate_legacy_schema(self, cur: sqlite3.Cursor) -> None:
        migrated = cur.execute(sql.get("migration", "select_migration_flag")).fetchone()
        if migrated and migrated[0] == "1":
            return

        legacy_table = cur.execute(sql.get("migration", "select_legacy_table")).fetchone()
        if not legacy_table:
            cur.execute(sql.get("migration", "mark_migrated"))
            return

        columns = {
            row[1]
            for row in cur.execute(sql.get("migration", "pragma_legacy_table_info")).fetchall()
        }
        source_col = "vulnerabilities" if "vulnerabilities" in columns else "vulneribilities"
        if source_col not in self._LEGACY_PAYLOAD_COLUMNS:  # pragma: no cover - defensive
            raise DatabaseError(f"Unexpected legacy column: {source_col!r}")

        cur.execute(sql.get("migration", "copy_legacy_scans").format(source_col=source_col))

        cur.execute(sql.get("migration", "mark_migrated"))

    def db_exists(self) -> bool:
        return self.db_path.exists()

    def get_db_path(self) -> Path:
        return self.db_path
