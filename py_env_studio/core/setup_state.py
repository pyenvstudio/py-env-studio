"""Setup lifecycle state manager for bootstrap and recovery flows."""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .runtime import get_runtime_config

CURRENT_SCHEMA = 1
INSTALL_TIMEOUT = timedelta(minutes=10)


class SetupStateManager:
    """Handles setup lifecycle markers, recovery, and versioning."""

    def __init__(self):
        runtime = get_runtime_config()
        self.state_dir = runtime.state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.sentinel_file = self.state_dir / "setup.complete"
        self.installing_marker = self.state_dir / ".isinstalling"
        self.failed_marker = self.state_dir / "setup.failed"
        self.current_version = runtime.app_version

    def _write_atomic(self, path: Path, data: bytes) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        tmp = Path(tmp_path)
        try:
            with os.fdopen(tmp_fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _read_json(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _write_json(self, path: Path, obj: dict) -> None:
        payload = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self._write_atomic(path, payload)

    def create_installing_marker(self) -> None:
        payload = {
            "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": self.current_version,
        }
        self._write_json(self.installing_marker, payload)

    def remove_installing_marker(self) -> None:
        self.installing_marker.unlink(missing_ok=True)

    def mark_setup_complete(self) -> None:
        payload = {
            "schema": CURRENT_SCHEMA,
            "appVersion": self.current_version,
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

    def _is_marker_stale(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = datetime.utcnow() - datetime.utcfromtimestamp(path.stat().st_mtime)
        return age > INSTALL_TIMEOUT

    def get_sentinel(self) -> Optional[dict]:
        return self._read_json(self.sentinel_file)

    def is_complete(self) -> bool:
        metadata = self.get_sentinel()
        return bool(metadata and int(metadata.get("schema", 0)) >= CURRENT_SCHEMA)

    def needs_migration(self) -> bool:
        metadata = self.get_sentinel()
        if not metadata:
            return False
        return metadata.get("appVersion") != self.current_version

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

    def get_state_path(self) -> Path:
        return self.state_dir
