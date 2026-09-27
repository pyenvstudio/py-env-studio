from __future__ import annotations
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from platformdirs import PlatformDirs
from typing import Optional

APP_NAME = "PyEnvStudio"
CURRENT_SCHEMA = 1
CURRENT_VERSION = "stable"

INSTALL_TIMEOUT = timedelta(minutes=10)  # After 10 mins, treat as failed


class SetupStateManager:
    """Handles setup lifecycle markers, recovery, and versioning."""

    def __init__(self):
        dirs = PlatformDirs(APP_NAME)
        self.state_dir = Path(dirs.user_data_dir) / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.sentinel_file = self.state_dir / "setup.complete"
        self.installing_marker = self.state_dir / ".isinstalling"
        self.failed_marker = self.state_dir / "setup.failed"

    # ------------- Generic helpers -------------

    def _write_atomic(self, path: Path, data: bytes) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        tmp = Path(tmp_path)
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _read_json(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    def _write_json(self, path: Path, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self._write_atomic(path, data)

    # ------------- Marker management -------------

    def create_installing_marker(self) -> None:
        payload = {
            "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": CURRENT_VERSION,
        }
        self._write_json(self.installing_marker, payload)

    def remove_installing_marker(self) -> None:
        self.installing_marker.unlink(missing_ok=True)

    def mark_setup_complete(self) -> None:
        payload = {
            "schema": CURRENT_SCHEMA,
            "appVersion": CURRENT_VERSION,
            "completedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._write_json(self.sentinel_file, payload)
        self.remove_installing_marker()
        self.failed_marker.unlink(missing_ok=True)

    def mark_setup_failed(self, reason: str) -> None:
        payload = {
            "failedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": reason,
        }
        self._write_json(self.failed_marker, payload)
        self.remove_installing_marker()

    # ------------- Validation / Recovery -------------

    def _is_marker_stale(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = datetime.utcnow() - datetime.utcfromtimestamp(path.stat().st_mtime)
        return age > INSTALL_TIMEOUT

    def get_sentinel(self) -> Optional[dict]:
        return self._read_json(self.sentinel_file)

    def is_complete(self) -> bool:
        meta = self.get_sentinel()
        return bool(meta and int(meta.get("schema", 0)) >= CURRENT_SCHEMA)

    def needs_migration(self) -> bool:
        meta = self.get_sentinel()
        if not meta:
            return False
        return meta.get("appVersion") != CURRENT_VERSION

    def check_installation_health(self) -> str:
        if self.failed_marker.exists():
            return "failed"

        if self.installing_marker.exists():
            if self._is_marker_stale(self.installing_marker):
                return "recover"
            return "installing"

        if not self.sentinel_file.exists():
            return "missing"

        if self.needs_migration():
            return "migrate"

        return "complete"

    # ------------- Diagnostics -------------

    def get_state_path(self) -> Path:
        """Expose the app's state directory for debugging/logging."""
        return self.state_dir
