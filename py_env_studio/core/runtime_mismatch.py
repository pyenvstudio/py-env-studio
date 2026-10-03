"""Conservative comparison of a project's PES environment and a known runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
import os
import sys

from . import env_manager, runtime_toggle


class RuntimeMatchState(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    REGISTERED_ENVIRONMENT_UNAVAILABLE = "REGISTERED_ENVIRONMENT_UNAVAILABLE"
    NO_PROJECT_ASSOCIATION = "NO_PROJECT_ASSOCIATION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DetectedRuntime:
    """Runtime facts supplied by PES or a future integration adapter."""

    executable: str | None
    python_version: str | None
    reliable: bool = True


@dataclass(frozen=True)
class RuntimeMismatch:
    project_path: str | None
    project_name: str | None
    registered_environment_id: str | None
    registered_python_executable: str | None
    registered_python_version: str | None
    current_python_executable: str | None
    current_python_version: str | None
    state: RuntimeMatchState


def _process_runtime() -> DetectedRuntime:
    """Return the interpreter running PES, not an IDE's selected interpreter."""
    version = sys.version_info
    return DetectedRuntime(
        executable=sys.executable or None,
        python_version=f"{version.major}.{version.minor}.{version.micro}",
        reliable=bool(sys.executable),
    )


def _canonical_path(path: str) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def detect_runtime_mismatch(
    project_root: Path | str | None = None,
    current_runtime: DetectedRuntime | None = None,
) -> RuntimeMismatch:
    """Compare registered and current executables without inferring IDE state."""
    root = Path(project_root).resolve() if project_root is not None else runtime_toggle.get_project_root()
    metadata = runtime_toggle.load_project_metadata(root) if root else {}
    runtime = current_runtime if current_runtime is not None else _process_runtime()
    env_id = metadata.get("environment_id") or None

    registered_executable = None
    registered_version = None
    state = RuntimeMatchState.UNKNOWN
    if not env_id:
        state = RuntimeMatchState.NO_PROJECT_ASSOCIATION
    else:
        info = env_manager.get_environment_info(str(env_id))
        if info is None:
            state = RuntimeMatchState.REGISTERED_ENVIRONMENT_UNAVAILABLE
        else:
            registered_executable = str(info.get("python_executable") or "") or None
            registered_version = info.get("python_version") or metadata.get("python_version") or None
            if not registered_executable or not Path(registered_executable).is_file():
                state = RuntimeMatchState.REGISTERED_ENVIRONMENT_UNAVAILABLE
            elif not runtime.reliable or not runtime.executable or not Path(runtime.executable).is_file():
                state = RuntimeMatchState.UNKNOWN
            else:
                same_executable = _canonical_path(registered_executable) == _canonical_path(runtime.executable)
                if same_executable:
                    if runtime.python_version and registered_version and runtime.python_version != registered_version:
                        state = RuntimeMatchState.MISMATCH
                    elif runtime.python_version:
                        state = RuntimeMatchState.MATCH
                else:
                    state = RuntimeMatchState.MISMATCH

    return RuntimeMismatch(
        project_path=str(root) if root else None,
        project_name=metadata.get("project_name") if metadata else (root.name if root else None),
        registered_environment_id=str(env_id) if env_id else None,
        registered_python_executable=registered_executable,
        registered_python_version=str(registered_version) if registered_version else None,
        current_python_executable=runtime.executable,
        current_python_version=runtime.python_version,
        state=state,
    )


def notify_mismatch_once(result: RuntimeMismatch) -> bool:
    """Persist a per-project mismatch signature and report only new mismatches."""
    if result.state is not RuntimeMatchState.MISMATCH or not result.project_path:
        return False

    signature_data = "\0".join(
        str(value or "")
        for value in (
            result.registered_environment_id,
            result.registered_python_executable,
            result.registered_python_version,
            result.current_python_executable,
            result.current_python_version,
        )
    )
    signature = sha256(signature_data.encode("utf-8")).hexdigest()
    root = Path(result.project_path)
    if runtime_toggle.get_last_mismatch_signature(root) == signature:
        return False
    runtime_toggle.set_last_mismatch_signature(root, signature)
    return True


def clear_mismatch_notification(project_root: Path | str) -> None:
    """Allow a later recurrence to notify after a project returns to a match."""
    root = Path(project_root).resolve()
    if runtime_toggle.get_last_mismatch_signature(root):
        runtime_toggle.set_last_mismatch_signature(root, "")