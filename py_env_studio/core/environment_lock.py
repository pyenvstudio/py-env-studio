"""PEP 751 package locks associated with managed environments."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tomllib
from packaging.markers import InvalidMarker, Marker, default_environment
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from . import schema as sql
from .database import DatabaseManager
from .env_manager import VENV_DIR, _is_valid_env_name, get_env_python
from .package_manager import get_env_package_manager, list_packages, sync_from_lock_file

logger = logging.getLogger(__name__)

LOCK_FILE_NAME = "pylock.toml"
LOCK_FORMAT = "PEP 751"
LOCK_VERSION = "1.0"
MAX_LOCK_SIZE = 16 * 1024 * 1024
PROCESS_TIMEOUT = 600


class EnvironmentLockError(RuntimeError):
    """Raised for unusable locks or unsupported native lock tooling."""


@dataclass(frozen=True)
class LockDifference:
    kind: str
    package: str
    expected: str | None = None
    installed: str | None = None


@dataclass
class LockVerification:
    status: str
    lock_file: str | None = None
    differences: list[LockDifference] = field(default_factory=list)
    error: str | None = None


@dataclass
class LockSyncPreview:
    status: str
    additions: list[LockDifference] = field(default_factory=list)
    upgrades: list[LockDifference] = field(default_factory=list)
    removals: list[LockDifference] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    breaking_changes: list[str] = field(default_factory=list)
    preview_errors: list[str] = field(default_factory=list)

    @property
    def change_count(self) -> int:
        return len(self.additions) + len(self.upgrades) + len(self.removals)


class EnvironmentLockService:
    """Generate and verify standard pylock.toml files per managed environment."""

    def __init__(self, db_manager: DatabaseManager | None = None):
        self._db = db_manager or DatabaseManager()
        self._initialized = False

    @staticmethod
    def environment_path(env_name: str) -> Path:
        if not _is_valid_env_name(env_name):
            raise ValueError(f"Invalid environment name: {env_name!r}")
        path = Path(VENV_DIR) / env_name
        if path.is_symlink():
            raise EnvironmentLockError("Managed environment path must not be a symbolic link")
        if not path.is_dir() or not (path / "pyvenv.cfg").is_file():
            raise FileNotFoundError(f"Environment '{env_name}' is unavailable")
        return path

    def lock_path(self, env_name: str) -> Path:
        return self.environment_path(env_name) / LOCK_FILE_NAME

    def _initialize(self) -> None:
        if not self._initialized:
            self._db.initialize_database()
            self._initialized = True

    def _environment_id(self, env_name: str) -> int:
        env_path = str(self.environment_path(env_name))
        self._initialize()
        with self._db.connect() as connection:
            row = connection.execute(
                sql.get("environments", "get_env_id"), (env_name,)
            ).fetchone()
            if row is None:
                connection.execute(
                    sql.get("environments", "create_environment"),
                    (env_name, env_path, _now()),
                )
                row = connection.execute(
                    sql.get("environments", "get_env_id"), (env_name,)
                ).fetchone()
            connection.commit()
        return int(row[0])

    def _metadata_row(self, env_name: str):
        env_id = self._environment_id(env_name)
        with self._db.connect() as connection:
            return connection.execute(
                sql.get("environment_locks", "get_environment_lock_metadata"),
                (env_id,),
            ).fetchone()

    def _save_metadata(
        self,
        env_name: str,
        lock_path: Path,
        lock_hash: str,
        lock_status: str,
        *,
        lock_version: str = LOCK_VERSION,
        last_verified_at: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        env_id = self._environment_id(env_name)
        previous = self._metadata_row(env_name)
        now = updated_at or _now()
        created_at = previous[3] if previous else now
        verified_at = last_verified_at if last_verified_at is not None else (
            previous[7] if previous and lock_status == "Unchecked" else None
        )
        with self._db.connect() as connection:
            connection.execute(
                sql.get("environment_locks", "upsert_environment_lock_metadata"),
                (
                    env_id,
                    str(lock_path),
                    LOCK_FORMAT,
                    lock_version,
                    created_at,
                    now,
                    lock_hash,
                    lock_status,
                    verified_at,
                ),
            )
            connection.commit()

    def _delete_metadata(self, env_name: str) -> None:
        env_id = self._environment_id(env_name)
        with self._db.connect() as connection:
            connection.execute(
                sql.get("environment_locks", "delete_environment_lock_metadata"),
                (env_id,),
            )
            connection.commit()

    def get_status(self, env_name: str) -> dict[str, Any]:
        path = self.lock_path(env_name)
        row = self._metadata_row(env_name)
        if path.is_symlink():
            return {
                "status": "Invalid Lock",
                "lock_file": str(path),
                "lock_hash": None,
                "error": "Lock file must not be a symbolic link",
            }
        if not path.exists():
            if row:
                self._save_metadata(env_name, path, row[5], "Lock Missing", lock_version=row[2])
            return {"status": "No Lock", "lock_file": str(path), "lock_hash": None}
        if not path.is_file():
            return {
                "status": "Invalid Lock",
                "lock_file": str(path),
                "lock_hash": None,
                "error": "Lock path is not a regular file",
            }
        try:
            lock_hash = _hash_file(path)
        except (EnvironmentLockError, OSError) as exc:
            return {
                "status": "Invalid Lock",
                "lock_file": str(path),
                "lock_hash": None,
                "error": str(exc),
            }
        if row is None:
            try:
                document = _read_lock(path)
                _validate_document(document)
                lock_version = document["lock-version"]
            except EnvironmentLockError as exc:
                return {
                    "status": "Invalid Lock",
                    "lock_file": str(path),
                    "lock_hash": lock_hash,
                    "error": str(exc),
                }
            self._save_metadata(env_name, path, lock_hash, "Locked", lock_version=lock_version)
            row = self._metadata_row(env_name)
        elif row[5] != lock_hash:
            self._save_metadata(env_name, path, lock_hash, "Unchecked", lock_version=row[2])
            row = self._metadata_row(env_name)
        return {
            "status": row[6],
            "lock_file": str(path),
            "lock_format": row[1],
            "lock_version": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "lock_hash": row[5],
            "last_verified_at": row[7],
        }

    def mark_drift(self, env_name: str) -> None:
        """Mark an associated lock as requiring verification after package changes."""
        try:
            status = self.get_status(env_name)
            if status["status"] in {"Locked", "Verified", "Drift Detected", "Unchecked"}:
                self._save_metadata(
                    env_name,
                    Path(status["lock_file"]),
                    status["lock_hash"] or "",
                    "Unchecked",
                    lock_version=status.get("lock_version", LOCK_VERSION),
                )
        except FileNotFoundError:
            return

    def create_lock(self, env_name: str, *, update: bool = False) -> dict[str, Any]:
        """Capture the environment using its configured manager's native PEP 751 locker."""
        env_path = self.environment_path(env_name)
        python = Path(get_env_python(env_name))
        if not python.is_file():
            raise FileNotFoundError(f"Environment Python executable is missing: {python}")
        target = env_path / LOCK_FILE_NAME
        if target.exists() and not update:
            raise FileExistsError(f"A lock already exists for '{env_name}'; use Update Lock")
        if target.is_symlink():
            raise EnvironmentLockError("Refusing to replace a symbolic-link lock file")

        manager = get_env_package_manager(env_name)
        environment = self._capture_freeze(env_name, manager, python)
        if not environment.strip():
            raise EnvironmentLockError("The selected environment has no packages to lock")

        with tempfile.TemporaryDirectory(prefix=".pes-lock-", dir=env_path) as temp_dir:
            temp_root = Path(temp_dir)
            requirements_file = temp_root / "environment-freeze.txt"
            generated_lock = temp_root / LOCK_FILE_NAME
            requirements_file.write_text(environment, encoding="utf-8")
            command = self._lock_command(manager, python, requirements_file, generated_lock)
            _run_tool(command, timeout=PROCESS_TIMEOUT, operation="Lock generation")
            if not generated_lock.is_file():
                raise EnvironmentLockError("The lock tool did not produce pylock.toml")
            document = _read_lock(generated_lock)
            _validate_document(document)
            if not document["packages"]:
                raise EnvironmentLockError("The generated pylock.toml contains no packages")
            os.replace(generated_lock, target)

        lock_hash = _hash_file(target)
        self._save_metadata(
            env_name,
            target,
            lock_hash,
            "Locked",
            lock_version=LOCK_VERSION,
        )
        return self.get_status(env_name)

    def _capture_freeze(self, env_name: str, manager: str, python: Path) -> str:
        if manager == "uv":
            uv = shutil.which("uv")
            if not uv:
                raise EnvironmentLockError("uv is not available to inspect this environment")
            command = [uv, "pip", "freeze", "--python", str(python)]
        else:
            command = [str(python), "-m", "pip", "freeze", "--all"]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout or "package listing failed").strip()
            raise EnvironmentLockError(f"Could not capture '{env_name}' packages: {details}")
        return result.stdout

    @staticmethod
    def _lock_command(
        manager: str,
        python: Path,
        requirements_file: Path,
        output_file: Path,
    ) -> list[str]:
        if manager == "uv":
            uv = shutil.which("uv")
            if not uv:
                raise EnvironmentLockError("uv is not available to create this lock")
            return [
                uv,
                "pip",
                "compile",
                str(requirements_file),
                "--python",
                str(python),
                "--no-deps",
                "--generate-hashes",
                "--format",
                "pylock.toml",
                "--output-file",
                str(output_file),
            ]
        return [
            str(python),
            "-m",
            "pip",
            "lock",
            "--no-deps",
            "--requirement",
            str(requirements_file),
            "--output",
            str(output_file),
        ]

    def verify(self, env_name: str) -> LockVerification:
        try:
            env_path = self.environment_path(env_name)
            python = Path(get_env_python(env_name))
            if not python.is_file():
                return LockVerification("Environment Unavailable", error="Python executable is missing")
        except (FileNotFoundError, OSError) as exc:
            return LockVerification("Environment Unavailable", error=str(exc))

        path = env_path / LOCK_FILE_NAME
        if path.is_symlink():
            self._record_verification(env_name, path, None, "Invalid Lock", None)
            return LockVerification(
                "Invalid Lock", str(path), error="Lock file must not be a symbolic link"
            )
        if not path.is_file():
            self._record_verification(env_name, path, None, "Lock Missing", None)
            return LockVerification("Lock Missing", str(path))
        lock_hash: str | None = None
        try:
            lock_hash = _hash_file(path)
            document = _read_lock(path)
            _validate_document(document)
            marker_environment, python_version = self._marker_environment(python)
            self._validate_compatibility(document, marker_environment, python_version)
            expected = self._active_packages(document, marker_environment)
            installed_pairs = list_packages(env_name)
            installed = {canonicalize_name(name): (name, version) for name, version in installed_pairs}
        except EnvironmentLockError as exc:
            status = "Incompatible Python" if str(exc).startswith("Incompatible Python") else "Invalid Lock"
            self._record_verification(env_name, path, lock_hash, status, None)
            return LockVerification(status, str(path), error=str(exc))
        except Exception as exc:
            logger.warning("Lock verification failed for '%s': %s", env_name, exc, exc_info=True)
            self._record_verification(env_name, path, lock_hash, "Environment Unavailable", None)
            return LockVerification("Environment Unavailable", str(path), error=str(exc))

        differences: list[LockDifference] = []
        for name, expected_version in expected.items():
            current = installed.get(name)
            if current is None:
                differences.append(LockDifference("Missing", name, expected_version, None))
            elif expected_version is not None and not _versions_match(expected_version, current[1]):
                differences.append(LockDifference("Version mismatch", name, expected_version, current[1]))
            elif expected_version is None:
                differences.append(LockDifference("Unverifiable source version", name, None, current[1]))

        for name, (original_name, installed_version) in installed.items():
            if name not in expected:
                differences.append(LockDifference("Unexpected", original_name, None, installed_version))

        status = "Drift Detected" if differences else "Verified"
        self._record_verification(env_name, path, lock_hash, status, _now(), document["lock-version"])
        return LockVerification(status, str(path), differences)

    def preview_sync(self, env_name: str) -> LockSyncPreview:
        verification = self.verify(env_name)
        plan = LockSyncPreview(verification.status)
        if verification.status in {"Lock Missing", "Invalid Lock", "Incompatible Python", "Environment Unavailable"}:
            plan.preview_errors.append(verification.error or verification.status)
            return plan
        for difference in verification.differences:
            if difference.kind == "Missing":
                plan.additions.append(difference)
            elif difference.kind == "Version mismatch":
                plan.upgrades.append(difference)
            elif difference.kind == "Unexpected":
                plan.removals.append(difference)
            elif difference.kind == "Unverifiable source version":
                plan.preview_errors.append(
                    f"Cannot verify the installed source version for {difference.package}"
                )

        if get_env_package_manager(env_name) == "uv":
            uv = shutil.which("uv")
            if uv:
                command = [
                    uv,
                    "pip",
                    "sync",
                    "--python",
                    get_env_python(env_name),
                    "--dry-run",
                    str(self.lock_path(env_name)),
                ]
                result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    plan.preview_errors.append((result.stderr or result.stdout).strip())
                elif result.stdout.strip():
                    plan.conflicts.append(result.stdout.strip()[:4000])
        else:
            from .dependency_preview import DependencyPreviewError, preview_install

            for change in [*plan.additions, *plan.upgrades]:
                if not change.expected:
                    continue
                try:
                    result = preview_install(env_name, f"{change.package}=={change.expected}")
                    plan.conflicts.extend(str(item) for item in result.conflicts)
                    plan.breaking_changes.extend(
                        f"{item.package}: {item.reason}" for item in result.breaking_changes
                    )
                except DependencyPreviewError as exc:
                    plan.preview_errors.append(f"{change.package}: {exc}")
        return plan

    def sync_from_lock(self, env_name: str) -> LockVerification:
        document = _read_lock(self.lock_path(env_name))
        _validate_document(document)
        marker_environment, python_version = self._marker_environment(Path(get_env_python(env_name)))
        self._validate_compatibility(document, marker_environment, python_version)
        expected = self._active_packages(document, marker_environment)
        sync_from_lock_file(env_name, self.lock_path(env_name), set(expected))
        return self.verify(env_name)

    def remove_lock(self, env_name: str) -> None:
        path = self.lock_path(env_name)
        if path.is_symlink():
            raise EnvironmentLockError("Refusing to remove a symbolic-link lock file")
        if path.exists():
            path.unlink()
        self._delete_metadata(env_name)

    def read_lock_text(self, env_name: str) -> str:
        path = self.lock_path(env_name)
        if path.is_symlink():
            raise EnvironmentLockError("Lock file must not be a symbolic link")
        if not path.is_file():
            raise FileNotFoundError(f"No pylock.toml exists for '{env_name}'")
        if path.stat().st_size > MAX_LOCK_SIZE:
            raise EnvironmentLockError("Lock file exceeds the 16 MiB safety limit")
        return path.read_text(encoding="utf-8")

    def _marker_environment(self, python: Path) -> tuple[dict[str, str], str]:
        probe = (
            "import json,platform,sys; "
            "print(json.dumps({'python_version':f'{sys.version_info.major}.{sys.version_info.minor}',"
            "'python_full_version':platform.python_version(),"
            "'implementation_name':sys.implementation.name,"
            "'implementation_version':platform.python_version(),"
            "'platform_python_implementation':platform.python_implementation()}))"
        )
        result = subprocess.run(
            [str(python), "-c", probe], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            raise EnvironmentLockError("Could not read target environment Python metadata")
        target = json.loads(result.stdout)
        environment = default_environment()
        environment.update(target)
        return environment, target["python_full_version"]

    @staticmethod
    def _validate_compatibility(
        document: dict[str, Any], environment: dict[str, str], python_version: str
    ) -> None:
        required_python = document.get("requires-python")
        if required_python is not None and not isinstance(required_python, str):
            raise EnvironmentLockError("pylock.toml requires-python must be a string")
        environments = document.get("environments", [])
        if not isinstance(environments, list) or any(
            not isinstance(marker, str) or not marker.strip() for marker in environments
        ):
            raise EnvironmentLockError("pylock.toml environments must contain marker strings")
        if required_python is not None:
            try:
                if Version(python_version) not in SpecifierSet(required_python):
                    raise EnvironmentLockError(
                        f"Incompatible Python: lock requires {required_python}, "
                        f"environment has Python {python_version}"
                    )
            except InvalidSpecifier as exc:
                raise EnvironmentLockError(f"Invalid requires-python value: {required_python}") from exc
        markers = document.get("environments", [])
        if markers and not any(_marker_matches(value, environment) for value in markers):
            raise EnvironmentLockError("Incompatible Python/platform: no lock environment marker matches")

    @staticmethod
    def _active_packages(
        document: dict[str, Any], environment: dict[str, str]
    ) -> dict[str, str | None]:
        packages: dict[str, str | None] = {}
        for package in document["packages"]:
            marker = package.get("marker")
            if marker and not _marker_matches(marker, environment):
                continue
            name = canonicalize_name(package["name"])
            if name in packages:
                raise EnvironmentLockError(f"Ambiguous duplicate lock entry for '{name}'")
            packages[name] = package.get("version")
        return packages

    def _record_verification(
        self,
        env_name: str,
        path: Path,
        lock_hash: str | None,
        status: str,
        verified_at: str | None,
        lock_version: str = LOCK_VERSION,
    ) -> None:
        if lock_hash is None:
            row = self._metadata_row(env_name)
            if row is None:
                return
            lock_hash = row[5]
        self._save_metadata(
            env_name,
            path,
            lock_hash,
            status,
            lock_version=lock_version,
            last_verified_at=verified_at,
        )


def _read_lock(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise EnvironmentLockError("Lock file must not be a symbolic link")
    if not path.is_file():
        raise FileNotFoundError(f"Lock file does not exist: {path}")
    if path.stat().st_size > MAX_LOCK_SIZE:
        raise EnvironmentLockError("Lock file exceeds the 16 MiB safety limit")
    try:
        with path.open("rb") as lock_stream:
            document = tomllib.load(lock_stream)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise EnvironmentLockError(f"Cannot parse pylock.toml: {exc}") from exc
    if not isinstance(document, dict):
        raise EnvironmentLockError("pylock.toml root must be a TOML table")
    return document


def _validate_document(document: dict[str, Any]) -> None:
    if document.get("lock-version") != LOCK_VERSION:
        raise EnvironmentLockError(
            f"Unsupported pylock.toml lock-version: {document.get('lock-version')!r}"
        )
    if not isinstance(document.get("created-by"), str) or not document["created-by"].strip():
        raise EnvironmentLockError("pylock.toml requires a non-empty created-by string")
    packages = document.get("packages")
    if not isinstance(packages, list):
        raise EnvironmentLockError("pylock.toml packages must be an array of tables")
    for item in packages:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
            raise EnvironmentLockError("Every pylock.toml package requires a name")
        if item.get("version") is not None:
            if not isinstance(item["version"], str):
                raise EnvironmentLockError(
                    f"Version for package {item['name']!r} must be a string"
                )
            try:
                Version(str(item["version"]))
            except InvalidVersion as exc:
                raise EnvironmentLockError(
                    f"Invalid version for package {item['name']!r}: {item['version']!r}"
                ) from exc
        if "marker" in item and (
            not isinstance(item["marker"], str) or not item["marker"].strip()
        ):
            raise EnvironmentLockError(
                f"Invalid environment marker for package {item['name']!r}"
            )
        _validate_package_source(item)


def _validate_package_source(package: dict[str, Any]) -> None:
    name = package["name"]
    direct_sources = [key for key in ("vcs", "directory", "archive") if key in package]
    distributions = [key for key in ("sdist", "wheels") if key in package]
    if len(direct_sources) > 1 or (direct_sources and distributions):
        raise EnvironmentLockError(f"Conflicting source records for package {name!r}")
    if not direct_sources and not distributions:
        raise EnvironmentLockError(f"Package {name!r} has no installable source")

    for key in direct_sources:
        source = package[key]
        if not isinstance(source, dict):
            raise EnvironmentLockError(f"Package {name!r} has an invalid {key} source")
        if key == "directory":
            if not isinstance(source.get("path"), str) or not source["path"].strip():
                raise EnvironmentLockError(f"Package {name!r} directory source requires a path")
        elif key == "vcs":
            if not isinstance(source.get("type"), str) or not source["type"].strip():
                raise EnvironmentLockError(f"Package {name!r} VCS source requires a type")
            if not isinstance(source.get("commit-id"), str) or not source["commit-id"].strip():
                raise EnvironmentLockError(f"Package {name!r} VCS source requires a commit-id")
            _validate_location(source, name, "VCS")
        else:
            _validate_file_record(source, name, "archive")

    if "sdist" in package:
        source = package["sdist"]
        if not isinstance(source, dict):
            raise EnvironmentLockError(f"Package {name!r} has an invalid sdist source")
        _validate_file_record(source, name, "sdist")

    if "wheels" in package:
        wheels = package["wheels"]
        if not isinstance(wheels, list):
            raise EnvironmentLockError(f"Package {name!r} wheels must be an array of tables")
        for wheel in wheels:
            if not isinstance(wheel, dict):
                raise EnvironmentLockError(f"Package {name!r} has an invalid wheel record")
            _validate_file_record(wheel, name, "wheel")


def _validate_file_record(record: dict[str, Any], package_name: str, kind: str) -> None:
    _validate_location(record, package_name, kind)
    hashes = record.get("hashes")
    if not isinstance(hashes, dict) or not hashes or any(
        not isinstance(algorithm, str)
        or not algorithm.strip()
        or not isinstance(value, str)
        or not value.strip()
        for algorithm, value in hashes.items()
    ):
        raise EnvironmentLockError(f"Package {package_name!r} {kind} requires artifact hashes")


def _validate_location(record: dict[str, Any], package_name: str, kind: str) -> None:
    if not any(
        isinstance(record.get(key), str) and record[key].strip()
        for key in ("url", "path")
    ):
        raise EnvironmentLockError(f"Package {package_name!r} {kind} requires a URL or path")


def _marker_matches(expression: str, environment: dict[str, str]) -> bool:
    try:
        return Marker(expression).evaluate(environment=environment)
    except InvalidMarker as exc:
        raise EnvironmentLockError(f"Unsupported or invalid environment marker: {expression}") from exc


def _versions_match(expected: str, actual: str) -> bool:
    try:
        return Version(expected) == Version(actual)
    except InvalidVersion:
        return expected == actual


def _hash_file(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise EnvironmentLockError(f"Cannot access pylock.toml: {exc}") from exc
    if size > MAX_LOCK_SIZE:
        raise EnvironmentLockError("Lock file exceeds the 16 MiB safety limit")
    digest = hashlib.sha256()
    with path.open("rb") as lock_stream:
        for chunk in iter(lambda: lock_stream.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_tool(command: list[str], *, timeout: int, operation: str) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "package tool exited with an error").strip()
        raise EnvironmentLockError(f"{operation} failed: {details[-4000:]}")
    return result