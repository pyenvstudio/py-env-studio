from __future__ import annotations
import sqlite3
import os
import tempfile
from pathlib import Path
from platformdirs import PlatformDirs
from typing import Optional
from setup.state import APP_NAME


class DatabaseError(Exception):
    """Custom exception for DB initialization or access failures."""

class DatabaseManager:
    """Manages SQLite database lifecycle and schema creation."""

    def __init__(self):
        dirs = PlatformDirs(APP_NAME)
        self.db_dir = Path(dirs.user_data_dir) / "data"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "pyenvstudio.db"

    # ---------------------------
    # Core helpers
    # ---------------------------

    def _write_atomic(self, src_path: Path, data: bytes) -> None:
        """Write data atomically to avoid corruption."""
        tmp_fd, tmp_path = tempfile.mkstemp(dir=src_path.parent, prefix=".tmp-")
        tmp = Path(tmp_path)
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(src_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def connect(self) -> sqlite3.Connection:
        """Create and return a SQLite connection."""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to DB: {e}")

    # ---------------------------
    # Schema & Initialization
    # ---------------------------

    def initialize_database(self) -> None:
        """Initialize DB if it doesn't exist yet."""
        if self.db_path.exists():
            return  # Already initialized

        try:
            with self.connect() as conn:
                cur = conn.cursor()

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS environments (
                        env_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        env_name TEXT UNIQUE NOT NULL,
                        env_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS env_vulnerability_info (
                        vid INTEGER PRIMARY KEY AUTOINCREMENT,
                        env_id INTEGER NOT NULL,
                        vulnerabilities TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (env_id) REFERENCES environments(env_id)
                    )
                """)

                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"SQLite initialization error: {e}")
        except Exception as e:
            raise DatabaseError(f"Unexpected error initializing DB: {e}")

    # ---------------------------
    # Query APIs
    # ---------------------------
    def query(self, query, params=()):
        """Run read queries safely."""
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def execute(self, query, params=()):
        """Run write/update queries safely."""
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()

    # ---------------------------
    # Diagnostics
    # ---------------------------

    def db_exists(self) -> bool:
        return self.db_path.exists()

    def get_db_path(self) -> Path:
        """Expose the resolved DB path (AppData safe)."""
        return self.db_path

# If run standalone
if __name__ == "__main__":
    db = DatabaseManager()
    db.initialize_database()
