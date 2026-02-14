"""SQLite lifecycle manager for Py Env Studio."""

from __future__ import annotations

import sqlite3
from pathlib import Path

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
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to connect to DB: {exc}") from exc

    def initialize_database(self) -> None:
        try:
            with self.connect() as conn:
                cur = conn.cursor()

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """
                )

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS environments (
                        env_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        env_name TEXT UNIQUE NOT NULL,
                        env_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS env_vulnerability_info (
                        vid INTEGER PRIMARY KEY AUTOINCREMENT,
                        env_id INTEGER NOT NULL,
                        vulnerabilities TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (env_id) REFERENCES environments(env_id)
                    )
                    """
                )

                self._migrate_legacy_schema(cur)
                conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"SQLite initialization error: {exc}") from exc
        except Exception as exc:
            raise DatabaseError(f"Unexpected error initializing DB: {exc}") from exc

    def _migrate_legacy_schema(self, cur: sqlite3.Cursor) -> None:
        migrated = cur.execute(
            "SELECT value FROM app_metadata WHERE key='legacy_migrated'"
        ).fetchone()
        if migrated and migrated[0] == "1":
            return

        legacy_table = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='env_vulneribility_info'"
        ).fetchone()
        if not legacy_table:
            cur.execute(
                "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('legacy_migrated', '1')"
            )
            return

        columns = {
            row[1]
            for row in cur.execute("PRAGMA table_info(env_vulneribility_info)").fetchall()
        }
        source_col = "vulnerabilities" if "vulnerabilities" in columns else "vulneribilities"

        cur.execute(
            f"""
            INSERT INTO env_vulnerability_info (env_id, vulnerabilities, created_at)
            SELECT env_id, {source_col}, created_at
            FROM env_vulneribility_info
            """
        )

        cur.execute(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('legacy_migrated', '1')"
        )

    def db_exists(self) -> bool:
        return self.db_path.exists()

    def get_db_path(self) -> Path:
        return self.db_path
