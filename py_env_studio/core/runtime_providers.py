from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PythonRuntime:
    version: str
    display: str
    architecture: str | None = None
    release_status: str | None = None
    implementation: str | None = None
    installed: bool = False
    path: str | None = None


class RuntimeProvider:
    NAME: str = "unknown"

    def list_installed(self) -> list[PythonRuntime]:
        raise NotImplementedError

    def list_available(self) -> list[PythonRuntime]:
        raise NotImplementedError

    def install(self, version: str, log_callback: Callable[[str], None] | None = None):
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError

    def get_executable(self, version: str) -> str | None:
        """Return an executable path for an installed runtime, when supported."""
        runtimes = self.list_installed()
        match = self.find_best_match(version, runtimes)
        if match is not None and match.path:
            return match.path
        return None

    def resolve_executable(self, version: str) -> str | None:
        """Resolve the best executable for ``version`` without extra I/O."""
        return self.get_executable(version)

    @staticmethod
    def find_best_match(
        requested: str, runtimes: list[PythonRuntime]
    ) -> PythonRuntime | None:
        """Return the best runtime for ``requested`` (exact, then prefix)."""
        wanted = RuntimeProvider.normalize_version_static(requested)
        if not wanted or not runtimes:
            return None
        # Exact match first.
        for runtime in runtimes:
            if RuntimeProvider.normalize_version_static(runtime.version) == wanted:
                return runtime
        # Prefix match: "3.12" matches installed "3.12.10" (highest patch wins).
        candidates = [
            runtime
            for runtime in runtimes
            if RuntimeProvider.normalize_version_static(runtime.version).startswith(wanted + ".")
            or wanted.startswith(RuntimeProvider.normalize_version_static(runtime.version) + ".")
        ]
        if not candidates:
            # Bare major version: "3" matches "3.12.10".
            candidates = [
                runtime
                for runtime in runtimes
                if RuntimeProvider.normalize_version_static(runtime.version).split(".")[0] == wanted
            ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: PythonInstallManagerProvider._version_key(item.version),
        )

    @staticmethod
    def normalize_version_static(version: str) -> str:
        text = str(version or "").strip().lower()
        if text.startswith("python "):
            text = text[len("python "):].strip()
        return text.rstrip("*").strip()

    def normalize_version(self, version: str) -> str:
        return self.normalize_version_static(version)


class PythonInstallManagerProvider(RuntimeProvider):
    """Adapter around the official Python Install Manager on Windows."""

    NAME = "Python Install Manager"
    _VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")

    def __init__(self, py_executable: str | None = None):
        self._py = py_executable or self._find_py()

    @staticmethod
    def _find_py() -> str | None:
        # Prefer the unambiguous official command. `py.exe` may still refer to
        # a legacy launcher on machines that have not migrated yet.
        for candidate in ("pymanager.exe", "pymanager", "py.exe", "py"):
            path = shutil.which(candidate)
            if path:
                LOGGER.debug("Python Install Manager candidate found: %s", path)
                return path
        return None

    def is_available(self) -> bool:
        if not self._py:
            return False
        # `shutil.which` also handles an absolute executable path.
        return shutil.which(self._py) is not None

    def _run(self, args: list[str], log_callback: Callable[[str], None] | None = None) -> str:
        if not self.is_available():
            raise RuntimeError("Python Install Manager is not available on this system.")

        cmd = [self._py, *args]
        LOGGER.debug("Running Python Install Manager: %s", subprocess.list2cmdline(cmd))
        try:
            completed = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                check=False,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            msg = "Python Install Manager command timed out."
            LOGGER.warning("%s: %s", msg, exc)
            raise RuntimeError(msg) from exc
        except OSError as exc:
            msg = f"Python Install Manager command failed to start: {exc}"
            LOGGER.warning(msg)
            raise RuntimeError(msg) from exc

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        if log_callback:
            for line in (stdout + ("\n" if stdout and stderr else "") + stderr).splitlines():
                stripped = line.strip()
                if stripped:
                    log_callback(stripped)

        if completed.returncode != 0:
            detail = stderr.strip() or stdout.strip() or f"exit code {completed.returncode}"
            msg = f"Python Install Manager command failed: {detail}"
            LOGGER.warning("%s (rc=%s)", msg, completed.returncode)
            raise RuntimeError(msg)

        return stdout

    # ------------------------------------------------------------------
    # Installed runtimes
    # ------------------------------------------------------------------
    def list_installed(self) -> list[PythonRuntime]:
        if not self.is_available():
            return []

        # JSON is the stable machine-readable interface of the current manager.
        try:
            stdout = self._run(["list", "--format=json"])
            parsed = self._parse_runtime_json(stdout, installed=True)
            if parsed:
                return self._dedupe_runtimes(parsed)
        except RuntimeError:
            LOGGER.debug("py list --format=json failed; trying legacy formats", exc_info=True)
        except ValueError:
            LOGGER.debug("Invalid JSON from py list; trying legacy formats", exc_info=True)

        # Compatibility with older launchers.
        try:
            stdout = self._run(["-0p"])
            parsed = self._parse_installed_with_paths(stdout)
            if parsed:
                return self._dedupe_runtimes(parsed)
        except RuntimeError:
            LOGGER.debug("py -0p failed; falling back to py -0", exc_info=True)

        try:
            stdout = self._run(["-0"])
            return self._dedupe_runtimes(self._parse_installed_plain(stdout))
        except RuntimeError:
            LOGGER.debug("py -0 failed; returning empty installed list", exc_info=True)
            return []

    def get_executable(self, version: str) -> str | None:
        normalized = self.normalize_version(version)
        runtimes = self.list_installed()
        match = self.find_best_match(normalized, runtimes)
        if match is not None and match.path:
            return match.path

        # The current manager can launch a specific runtime. Resolve its actual
        # interpreter path without exposing subprocess details to the UI.
        if not self.is_available() or not self._VERSION_RE.fullmatch(normalized):
            return None
        try:
            stdout = self._run([
                f"-V:{normalized}",
                "-c",
                "import sys; print(sys.executable)",
            ])
        except RuntimeError:
            return None
        path = stdout.strip().splitlines()[-1].strip() if stdout.strip() else ""
        return path or None

    def _parse_installed_with_paths(self, stdout: str) -> list[PythonRuntime]:
        results = []
        for raw in stdout.splitlines():
            line = raw.strip()
            if not line:
                continue
            parsed = self._parse_installed_line(line)
            if parsed:
                results.append(parsed)
        return results

    def _parse_installed_plain(self, stdout: str) -> list[PythonRuntime]:
        results = []
        for raw in stdout.splitlines():
            line = raw.strip()
            if not line or not line.startswith("-"):
                continue
            parsed = self._parse_installed_line(line)
            if parsed:
                results.append(parsed)
        return results

    def _parse_installed_line(self, line: str) -> PythonRuntime | None:
        m = re.match(r"^\s*-(\d+(?:\.\d+)*)\s*(?:\*)?\s*(.*?)\s*$", line, flags=re.IGNORECASE)
        if not m:
            return None

        version = self.normalize_version(m.group(1))
        rest = m.group(2) or ""
        return PythonRuntime(
            version=version,
            display=self._format_installed_display(version, rest),
            architecture=self._extract_architecture(rest),
            release_status=self._extract_release_status(rest),
            implementation=self._extract_implementation(rest),
            installed=True,
            path=self._extract_path(rest),
        )

    # ------------------------------------------------------------------
    # Available official releases
    # ------------------------------------------------------------------
    def list_available(self) -> list[PythonRuntime]:
        if not self.is_available():
            return []

        installed = self.list_installed()
        installed_versions = {self._version_key(rt.version) for rt in installed}

        try:
            stdout = self._run(["list", "--online", "--format=json"])
            available = self._parse_runtime_json(stdout, installed=False, official_only=True)
        except RuntimeError:
            LOGGER.debug("py list --online --format=json failed; trying text output", exc_info=True)
            try:
                stdout = self._run(["list", "--online"])
                available = self._parse_available(stdout)
            except RuntimeError:
                LOGGER.debug("py list --online failed", exc_info=True)
                return []
        except ValueError:
            LOGGER.debug("Invalid JSON from py list --online; trying text output", exc_info=True)
            try:
                stdout = self._run(["list", "--online"])
                available = self._parse_available(stdout)
            except RuntimeError:
                return []

        filtered = [
            item for item in available
            if self._version_key(item.version) not in installed_versions
        ]
        return self._dedupe_runtimes(filtered)

    def _parse_available(self, stdout: str) -> list[PythonRuntime]:
        results = []
        for raw in stdout.splitlines():
            line = raw.strip()
            if not line:
                continue
            parsed = self._parse_available_line(line)
            if parsed:
                results.append(parsed)
        return results

    def _parse_available_line(self, line: str) -> PythonRuntime | None:
        m = re.match(r"^\s*(\d+(?:\.\d+)*)\s*(.*)$", line, flags=re.IGNORECASE)
        if not m:
            return None
        version = self.normalize_version(m.group(1))
        rest = m.group(2) or ""
        return PythonRuntime(
            version=version,
            display=self._format_available_display(version, rest),
            architecture=self._extract_architecture(rest),
            release_status=self._extract_release_status(rest),
            implementation=self._extract_implementation(rest) or "cpython",
            installed=False,
            path=None,
        )

    def _parse_runtime_json(
        self,
        stdout: str,
        *,
        installed: bool,
        official_only: bool = False,
    ) -> list[PythonRuntime]:
        payload = json.loads(stdout)
        records = list(self._iter_runtime_records(payload))
        results: list[PythonRuntime] = []

        for record in records:
            version = self._record_version(record)
            if not version:
                continue

            company = self._record_text(record, "company", "publisher", "distributor")
            implementation = self._record_text(record, "implementation", "impl")
            tag = self._record_text(record, "tag", "identifier", "id")

            # Online results are intended to represent official CPython releases.
            # If the manager doesn't expose company/implementation metadata, keep
            # the version rather than incorrectly discarding it.
            if official_only and (company or implementation):
                identity = f"{company} {implementation} {tag}".lower()
                if not (
                    "pythoncore" in identity
                    or "cpython" in identity
                    or "python" in identity and "core" in identity
                ):
                    continue

            display = self._record_text(
                record,
                "display",
                "display_name",
                "name",
                "description",
            ) or f"Python {version}"
            if not display.lower().startswith("python"):
                display = f"Python {display}"

            architecture = self._record_text(record, "architecture", "arch", "platform")
            release_status = self._record_text(record, "release_status", "status", "release")
            path = self._record_text(record, "path", "executable", "exe", "executable_path")

            results.append(
                PythonRuntime(
                    version=version,
                    display=self._format_json_display(display, version, release_status),
                    architecture=self._normalize_architecture(architecture),
                    release_status=self._normalize_status(release_status),
                    implementation=(implementation or "cpython").lower() if implementation else "cpython",
                    installed=installed,
                    path=path,
                )
            )

        return self._dedupe_runtimes(results)

    @classmethod
    def _iter_runtime_records(cls, value):
        if isinstance(value, list):
            for item in value:
                yield from cls._iter_runtime_records(item)
            return
        if isinstance(value, dict):
            keys = {str(k).lower() for k in value.keys()}
            if keys.intersection({"version", "tag", "identifier", "id"}):
                yield value
            for item in value.values():
                if isinstance(item, (dict, list)):
                    yield from cls._iter_runtime_records(item)

    @classmethod
    def _record_text(cls, record: dict, *names: str) -> str | None:
        lowered = {str(k).lower(): v for k, v in record.items()}
        for name in names:
            value = lowered.get(name.lower())
            if value is not None and not isinstance(value, (dict, list)):
                text = str(value).strip()
                if text:
                    return text
        return None

    @classmethod
    def _record_version(cls, record: dict) -> str | None:
        raw = cls._record_text(record, "version", "tag", "identifier", "id")
        if not raw:
            return None
        match = re.search(r"(?<!\d)(\d+\.\d+(?:\.\d+)?)(?!\d)", raw)
        return match.group(1).strip() if match else None

    @classmethod
    def _version_key(cls, version: str) -> tuple[int, ...]:
        try:
            return tuple(int(part) for part in str(version).strip().split("."))
        except (TypeError, ValueError):
            return (999999,)

    @classmethod
    def _dedupe_runtimes(cls, runtimes: list[PythonRuntime]) -> list[PythonRuntime]:
        result: list[PythonRuntime] = []
        seen: set[tuple[int, ...]] = set()
        for runtime in sorted(runtimes, key=lambda item: cls._version_key(item.version), reverse=True):
            key = cls._version_key(runtime.version)
            if key in seen:
                continue
            seen.add(key)
            result.append(runtime)
        return result

    def _fallback_available(self):
        # Kept as a compatibility hook for callers/tests from the earlier
        # provider implementation. The current manager's online index is the
        # only authoritative source, so we never invent versions here.
        return []

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------
    def install(self, version: str, log_callback: Callable[[str], None] | None = None):
        if not self._py:
            raise RuntimeError("Python Install Manager is not available on this system.")

        normalized = self.normalize_version(version)
        if not self._VERSION_RE.fullmatch(normalized):
            raise ValueError(f"Unsupported Python version identifier: {version!r}")

        attempts = [normalized]
        major_minor = self._major_minor(normalized)
        if major_minor != normalized:
            attempts.append(major_minor)

        last_error = None
        for attempt in attempts:
            try:
                self._run(["install", attempt], log_callback=log_callback)
                LOGGER.info("Python Install Manager installed Python %s", attempt)
                return attempt
            except RuntimeError as exc:
                last_error = exc
                error_text = str(exc)
                if re.search(r"already installed", error_text, re.IGNORECASE):
                    return attempt
                if re.search(
                    r"no match|not found|invalid|unavailable|download|more python versions",
                    error_text,
                    re.IGNORECASE,
                ):
                    continue
                raise

        raise RuntimeError(f"Failed to install Python {version}: {last_error}") from last_error

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_path(text: str) -> str | None:
        # Legacy output may contain a Windows executable path after the metadata.
        match = re.search(r"([A-Za-z]:[\\/][^\r\n]*?python(?:\.exe)?)(?:\s|$)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_architecture(text: str | None):
        if not text:
            return None
        m = re.search(r"(64-?bit|32-?bit|x64|amd64|x86|arm64|\barm\b)", text, flags=re.IGNORECASE)
        if not m:
            return None
        token = m.group(1).lower()
        if token.startswith("64") or token in ("x64", "amd64"):
            return "64-bit"
        if token.startswith("32") or token == "x86":
            return "32-bit"
        if token == "arm64":
            return "ARM64"
        return "ARM"

    @staticmethod
    def _normalize_architecture(value: str | None):
        return PythonInstallManagerProvider._extract_architecture(value) or value

    @staticmethod
    def _extract_implementation(text: str | None):
        if not text:
            return None
        m = re.search(r"\b(pypy|jython|ironpython|cpython)\b", text, flags=re.IGNORECASE)
        return m.group(1).lower() if m else None

    @staticmethod
    def _extract_release_status(text: str | None):
        if not text:
            return None
        lowered = text.lower()
        if "latest" in lowered:
            return "Latest"
        if "security" in lowered:
            return "Security"
        if "support" in lowered or "supported" in lowered:
            return "Supported"
        if "eol" in lowered or "end of life" in lowered or "ended" in lowered:
            return "EOL"
        if "dev" in lowered or "preview" in lowered or "beta" in lowered or "rc" in lowered:
            return "Dev/Preview"
        return None

    @staticmethod
    def _normalize_status(value: str | None):
        return PythonInstallManagerProvider._extract_release_status(value) or value

    @classmethod
    def _format_installed_display(cls, version: str, rest: str):
        base = f"Python {version}"
        if "64" in rest and "64-bit" not in base.lower():
            base = f"Python {version} (64-bit)"
        return base

    @classmethod
    def _format_available_display(cls, version: str, rest: str):
        base = f"Python {version}"
        if "64-bit" in rest.lower() or "64" in rest:
            base = f"Python {version} (64-bit)"
        status = cls._extract_release_status(rest)
        return f"{base} [{status}]" if status else base

    @classmethod
    def _format_json_display(cls, display: str, version: str, status: str | None):
        # Normalize manager-specific display strings while keeping useful status.
        if display.lower() in {version.lower(), f"python {version}".lower()}:
            display = f"Python {version}"
        normalized_status = cls._normalize_status(status)
        if normalized_status and f"[{normalized_status}]".lower() not in display.lower():
            display = f"{display} [{normalized_status}]"
        return display

    @staticmethod
    def _major_minor(version: str) -> str:
        parts = version.split(".")
        return ".".join(parts[:2]) if len(parts) >= 2 else version


class SystemRuntimeProvider(RuntimeProvider):
    """Runtimes already discoverable on PATH (cross-platform fallback)."""

    NAME = "System"

    def is_available(self) -> bool:
        try:
            from py_env_studio.core.env_manager import list_pythons
        except Exception:
            return shutil.which("python3") is not None or shutil.which("python") is not None
        try:
            return bool(list_pythons())
        except Exception:
            return False

    def list_installed(self) -> list[PythonRuntime]:
        try:
            from py_env_studio.core.env_manager import (
                is_valid_python_version_detected,
                list_pythons,
            )
        except Exception:
            LOGGER.debug("System provider cannot import env_manager", exc_info=True)
            return []
        runtimes: list[PythonRuntime] = []
        try:
            interpreters = list_pythons()
        except Exception:
            LOGGER.debug("System provider failed to list interpreters", exc_info=True)
            return []
        for interpreter in interpreters:
            try:
                detected = is_valid_python_version_detected(interpreter)
            except Exception:
                continue
            if not detected or not detected.startswith("Python "):
                continue
            version = detected.split(" ", 1)[1].strip()
            if not version:
                continue
            runtimes.append(
                PythonRuntime(
                    version=version,
                    display=f"Python {version}",
                    installed=True,
                    path=interpreter,
                )
            )
        return PythonInstallManagerProvider._dedupe_runtimes(runtimes)

    def list_available(self) -> list[PythonRuntime]:
        return []

    def install(self, version: str, log_callback: Callable[[str], None] | None = None):
        raise RuntimeError(
            "The System provider cannot install Python. "
            "Install it from python.org (or your OS package manager) "
            "and it will appear here automatically."
        )


class CustomRuntimeProvider(RuntimeProvider):
    """Single explicit interpreter chosen by the user (Preferences override)."""

    NAME = "Custom"

    def __init__(self, custom_path: str | None = None):
        self._custom_path = (custom_path or "").strip() or None

    def is_available(self) -> bool:
        return bool(self._custom_path)

    def list_installed(self) -> list[PythonRuntime]:
        if not self._custom_path:
            return []
        try:
            from py_env_studio.core.env_manager import is_valid_python_version_detected
        except Exception:
            return []
        try:
            detected = is_valid_python_version_detected(self._custom_path)
        except Exception:
            return []
        if not detected or not detected.startswith("Python "):
            return []
        version = detected.split(" ", 1)[1].strip()
        if not version:
            return []
        return [
            PythonRuntime(
                version=version,
                display=f"Python {version} (custom)",
                installed=True,
                path=self._custom_path,
            )
        ]

    def list_available(self) -> list[PythonRuntime]:
        return []

    def install(self, version: str, log_callback: Callable[[str], None] | None = None):
        raise RuntimeError(
            "The Custom provider uses your explicit interpreter path and cannot install Python."
        )


SUPPORTED_RUNTIME_PROVIDERS: tuple[str, ...] = (
    "Python Install Manager",
    "System",
    "Custom",
)


def get_runtime_provider(
    name: str | None,
    *,
    custom_path: str | None = None,
    py_executable: str | None = None,
) -> RuntimeProvider:
    """Factory returning the provider for ``name`` (never None)."""
    normalized = (name or "").strip() or "Python Install Manager"
    if normalized == PythonInstallManagerProvider.NAME:
        return PythonInstallManagerProvider(py_executable=py_executable)
    if normalized == SystemRuntimeProvider.NAME:
        return SystemRuntimeProvider()
    if normalized == CustomRuntimeProvider.NAME:
        return CustomRuntimeProvider(custom_path=custom_path)
    raise ValueError(
        f"Unsupported runtime provider: {name!r}. Supported: {', '.join(SUPPORTED_RUNTIME_PROVIDERS)}"
    )


