"""Orchestration for consolidated project analysis (strictly read-only).

Call order is fixed to avoid repeated work::

    Project context
          |
    Environment context (single get_environment_info call)
          |
    Package/dependency context (single list_packages call)
          |
    Security context (single vulnerability-cache read)
          |
    Aggregate response

Only ``get_*``/``list_*``/``load_*`` service calls are used here. Nothing
in this module creates, modifies, deletes, installs, upgrades, scans over
the network, or writes to pes.config, the registry, or the database.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from py_env_studio.core.mcp.errors import (
    AMBIGUOUS_PROJECT,
    INVALID_INPUT,
    PROJECT_NOT_FOUND,
    SERVICE_UNAVAILABLE,
    McpError,
)

from .models import (
    AnalysisSummary,
    ConflictItem,
    DependencyContext,
    EnvironmentContext,
    OutdatedContext,
    OutdatedItem,
    PackageManagerContext,
    PesConfigContext,
    ProjectAnalysis,
    ProjectContext,
    PythonContext,
    RuntimeContext,
    SecurityContext,
)

logger = logging.getLogger(__name__)

try:
    from packaging.requirements import InvalidRequirement, Requirement

    _PACKAGING_AVAILABLE = True
except Exception:  # pragma: no cover - degraded path
    Requirement = None  # type: ignore
    InvalidRequirement = Exception  # type: ignore
    _PACKAGING_AVAILABLE = False

_DEFAULT_RUNTIME_PROVIDER = "Python Install Manager"

_SEVERITY_LEVELS = ("critical", "high", "medium", "low")


def _normalize_project_path(raw):
    # type: (Any) -> Optional[Path]
    """Normalize a user-supplied project path with pathlib only.

    Returns None for empty input (caller falls back to cwd detection).
    Raises McpError INVALID_INPUT for non-string input. Windows paths
    (drive letters, spaces, Unicode, parentheses) are handled by pathlib
    without any manual string surgery.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise McpError(INVALID_INPUT, "project_path must be a string.")
    text = raw.strip()
    if not text:
        return None
    return Path(os.path.expanduser(text))


def _path_exists(path):
    # type: (Any) -> bool
    try:
        return bool(path) and Path(str(path)).exists()
    except Exception:
        return False


def _canonical_name(name):
    # type: (Any) -> str
    return str(name).strip().lower().replace("_", "-").replace(".", "-")


class ProjectIntelligenceService:
    """Aggregates existing PES services into one project report."""

    def analyze(self, project_path=None):
        # type: (Any) -> ProjectAnalysis
        start = _normalize_project_path(project_path)
        if start is None:
            start = Path.cwd()
        elif not _path_exists(start):
            raise McpError(
                PROJECT_NOT_FOUND,
                "Project path does not exist: {}".format(project_path),
                {"project_path": str(project_path)},
            )

        from py_env_studio.core import runtime_toggle

        root = runtime_toggle.get_project_root(start)
        if root is None:
            if project_path is not None and _normalize_project_path(project_path) is not None:
                raise McpError(
                    PROJECT_NOT_FOUND,
                    "No PES project found at or above '{}'.".format(start),
                    {"project_path": str(start)},
                )
            self._raise_if_ambiguous()
            raise McpError(
                PROJECT_NOT_FOUND,
                "No PES project found at or above '{}'.".format(start),
                {"project_path": str(start)},
            )

        try:
            status = runtime_toggle.get_project_status(root)
        except Exception as exc:
            raise McpError(
                SERVICE_UNAVAILABLE,
                "Could not load project status: {}".format(exc),
            )
        try:
            metadata = runtime_toggle.load_project_metadata(Path(root))
        except Exception:
            metadata = {}

        managed = bool(metadata)
        project_name = status.get("project_name") or metadata.get("project_name")
        if not project_name and root is not None:
            try:
                project_name = Path(root).name
            except Exception:
                project_name = None

        project = ProjectContext(
            path=str(root),
            name=project_name,
            managed_by_pes=managed,
            registered=managed,
        )

        env_id = status.get("environment_id") or metadata.get("environment_id")
        env_info = self._load_environment(env_id) if env_id else None
        environment = self._build_environment(env_info, env_id, status)

        python = self._build_python(env_info)
        package_manager = self._build_package_manager(env_info, env_id)
        runtime = self._build_runtime(status, managed)
        pes_config = self._build_pes_config(status, metadata, managed)

        installed = self._load_installed(env_info, env_id)
        if installed is None:
            dependencies = DependencyContext(
                analysis_available=False,
                reason="Installed-package information is unavailable "
                "for this environment.",
            )
            outdated = OutdatedContext(
                analysis_available=False,
                reason="Outdated-package metadata is unavailable "
                "for this environment.",
            )
        else:
            dependencies = self._build_dependencies(env_info, env_id, installed)
            outdated = self._build_outdated(env_info, env_id)

        security = self._build_security(env_info, env_id)

        conflict_count = (
            len(dependencies.conflicts) if dependencies.analysis_available else None
        )
        summary = AnalysisSummary(
            environment_available=environment.available,
            dependency_analysis_available=dependencies.analysis_available,
            dependency_conflicts=conflict_count,
            outdated_packages=outdated.count,
            security_scan_available=security.scan_available,
            vulnerabilities=security.total,
        )
        return ProjectAnalysis(
            project=project,
            environment=environment,
            python=python,
            package_manager=package_manager,
            runtime=runtime,
            dependencies=dependencies,
            outdated=outdated,
            security=security,
            pes_config=pes_config,
            summary=summary,
        )

    # -- project resolution -------------------------------------------------
    @staticmethod
    def _raise_if_ambiguous():
        # type: () -> None
        """Refuse to guess when several registered projects could apply.

        Only reached when no explicit path was given and cwd-based
        detection found nothing: with more than one registered project
        there is no unique answer, so report ambiguity instead of picking
        one.
        """
        try:
            from py_env_studio.core import runtime_toggle

            registered = runtime_toggle.list_registered_projects()
        except Exception:
            return
        if isinstance(registered, list) and len(registered) > 1:
            candidates = [
                str(entry.get("project_root") or entry.get("name"))
                for entry in registered
                if isinstance(entry, dict)
            ]
            raise McpError(
                AMBIGUOUS_PROJECT,
                "Multiple PES projects are registered; specify "
                "project_path explicitly.",
                {"candidates": candidates},
            )

    # -- environment ---------------------------------------------------------
    @staticmethod
    def _load_environment(env_id):
        # type: (str) -> Optional[Dict[str, Any]]
        from py_env_studio.core import env_manager

        try:
            return env_manager.get_environment_info(env_id)
        except Exception as exc:
            logger.warning("Environment lookup failed for %r: %s", env_id, exc)
            return None

    @staticmethod
    def _build_environment(env_info, env_id, status):
        # type: (Optional[Dict[str, Any]], Any, Dict[str, Any]) -> EnvironmentContext
        if not env_info:
            return EnvironmentContext(available=False)
        meta = env_info.get("metadata") or {}
        return EnvironmentContext(
            available=True,
            id=env_info.get("environment_id"),
            name=env_info.get("name"),
            path=env_info.get("path"),
            python_executable=env_info.get("python_executable"),
            python_version=env_info.get("python_version"),
            package_manager=env_info.get("package_manager"),
            status=env_info.get("status") or ("available" if status.get("environment_exists") else "missing"),
            size=meta.get("size"),
            last_scanned=meta.get("last_scanned"),
        )

    # -- python ----------------------------------------------------------------
    def _build_python(self, env_info):
        # type: (Optional[Dict[str, Any]]) -> PythonContext
        if not env_info:
            return PythonContext(available=False, provider=self._runtime_provider())
        exe = env_info.get("python_executable")
        return PythonContext(
            available=bool(env_info.get("python_version") or exe),
            version=env_info.get("python_version"),
            executable=exe,
            executable_available=_path_exists(exe) if exe else False,
            provider=self._runtime_provider(),
        )

    @staticmethod
    def _runtime_provider():
        # type: () -> Optional[str]
        """Configured runtime provider name (read-only preference lookup)."""
        try:
            from py_env_studio.core.configuration import AppConfig

            return (
                AppConfig().get_param(
                    "settings", "runtime_provider", fallback=_DEFAULT_RUNTIME_PROVIDER
                )
                or _DEFAULT_RUNTIME_PROVIDER
            )
        except Exception:
            return None

    # -- package manager ---------------------------------------------------------
    @staticmethod
    def _build_package_manager(env_info, env_id):
        # type: (Optional[Dict[str, Any]], Any) -> PackageManagerContext
        if not env_info or not env_id:
            return PackageManagerContext(
                available=False, reason="No environment is associated with this project."
            )
        configured = (env_info.get("metadata") or {}).get("package_manager") or env_info.get(
            "package_manager"
        )
        try:
            from py_env_studio.core import package_manager

            effective = package_manager.get_env_package_manager(env_id)
        except Exception as exc:
            return PackageManagerContext(
                available=False,
                configured=configured,
                reason="Package-manager lookup failed: {}".format(exc),
            )
        if effective not in ("pip", "uv"):
            return PackageManagerContext(
                available=False,
                manager=None,
                configured=configured,
                reason="Unsupported package manager reported: {!r}.".format(effective),
            )
        if effective == "uv":
            try:
                from py_env_studio.core import uv_tools

                if not uv_tools.is_uv_installed():
                    return PackageManagerContext(
                        available=False,
                        manager="uv",
                        configured=configured,
                        reason="'uv' is configured for this environment "
                        "but is not installed.",
                    )
            except Exception as exc:
                return PackageManagerContext(
                    available=False,
                    manager="uv",
                    configured=configured,
                    reason="Could not verify 'uv' availability: {}".format(exc),
                )
        return PackageManagerContext(
            available=True, manager=effective, configured=configured or effective
        )

    # -- runtime -------------------------------------------------------------------
    @staticmethod
    def _build_runtime(status, managed):
        # type: (Dict[str, Any], bool) -> RuntimeContext
        if not managed:
            return RuntimeContext(managed_by_pes=False)
        enabled = bool(status.get("runtime_enabled"))
        return RuntimeContext(
            managed_by_pes=True, status="enabled" if enabled else "disabled"
        )

    # -- pes config ------------------------------------------------------------------
    def _build_pes_config(self, status, metadata, managed):
        # type: (Dict[str, Any], Dict[str, Any], bool) -> PesConfigContext
        if not managed:
            return PesConfigContext(registered=False)
        return PesConfigContext(
            registered=True,
            environment_id=status.get("environment_id") or metadata.get("environment_id"),
            environment_path=status.get("environment_path")
            or metadata.get("environment_path"),
            python_version=status.get("python_version") or metadata.get("python_version"),
            package_manager=metadata.get("package_manager"),
            runtime_enabled=bool(status.get("runtime_enabled", False)),
            runtime_provider=self._runtime_provider(),
        )

    # -- packages / dependencies ---------------------------------------------------------
    @staticmethod
    def _load_installed(env_info, env_id):
        # type: (Optional[Dict[str, Any]], Any) -> Optional[Dict[str, str]]
        if not env_info or not env_id:
            return None
        try:
            from py_env_studio.core import package_manager

            raw = package_manager.list_packages(env_id) or []
            installed = {}
            for entry in raw:
                try:
                    name, version = entry
                except Exception:
                    continue
                installed[str(name)] = str(version)
            return installed
        except Exception as exc:
            logger.warning("Package listing failed for %r: %s", env_id, exc)
            return None

    def _build_dependencies(self, env_info, env_id, installed):
        # type: (Optional[Dict[str, Any]], Any, Dict[str, str]) -> DependencyContext
        try:
            from py_env_studio.core import dependency_preview
            from py_env_studio.core import env_manager
        except Exception as exc:
            return DependencyContext(
                analysis_available=False,
                installed=len(installed),
                reason="Dependency service unavailable: {}".format(exc),
            )
        try:
            python_path = env_manager.get_env_python(env_id)
        except Exception as exc:
            return DependencyContext(
                analysis_available=False,
                installed=len(installed),
                reason="Environment Python path unavailable: {}".format(exc),
            )
        conflicts = []  # type: List[ConflictItem]
        checked = 0
        skipped = 0
        lowered = {_canonical_name(name): (name, version) for name, version in installed.items()}
        for display_name in sorted(installed):
            try:
                requirements = dependency_preview.get_package_dependencies(
                    python_path, display_name
                )
            except Exception:
                skipped += 1
                continue
            if not requirements:
                continue
            items = requirements.items() if isinstance(requirements, dict) else []
            for _dep, req_string in items:
                outcome = self._check_requirement(req_string, lowered)
                if outcome is None:
                    skipped += 1
                else:
                    checked += 1
                    if outcome is not True:
                        conflicts.append(
                            ConflictItem(
                                package=display_name,
                                requirement=str(req_string),
                                reason=outcome,
                            )
                        )
        return DependencyContext(
            analysis_available=True,
            installed=len(installed),
            requirements_checked=checked,
            requirements_skipped=skipped,
            conflicts=conflicts,
        )

    @staticmethod
    def _check_requirement(req_string, lowered):
        # type: (Any, Dict[str, Tuple[str, str]]) -> Any
        """Check one requirement string against installed versions.

        Returns True when satisfied, a reason string when unsatisfied,
        or None when the requirement cannot be evaluated (never fabricate
        a conflict verdict for unparseable metadata).
        """
        text = str(req_string or "").strip()
        if not text:
            return None
        if not _PACKAGING_AVAILABLE:
            # Degraded path: presence-only check, no version evaluation.
            name = text.split(";")[0].split()[0].split("[")[0].strip()
            if _canonical_name(name) not in lowered:
                return "Requirement '{}' is not installed.".format(text)
            return True
        try:
            req = Requirement(text)
        except Exception:
            return None
        try:
            if req.marker is not None and not req.marker.evaluate():
                return None  # Not applicable to this interpreter/platform.
        except Exception:
            return None
        target = lowered.get(_canonical_name(req.name))
        if target is None:
            return "Package '{}' requires '{}', which is not installed.".format(
                req.name, text
            )
        _display, installed_version = target
        if not req.specifier:
            return True
        try:
            satisfied = installed_version in req.specifier
        except Exception:
            return None
        if satisfied:
            return True
        return "Installed {} {} does not satisfy requirement '{}'.".format(
            req.name, installed_version, text
        )

    # -- outdated --------------------------------------------------------------------------
    @staticmethod
    def _build_outdated(env_info, env_id):
        # type: (Optional[Dict[str, Any]], Any) -> OutdatedContext
        try:
            from py_env_studio.core import package_manager

            raw_text = package_manager.check_outdated_packages(env_id)
        except Exception as exc:
            return OutdatedContext(
                analysis_available=False,
                reason="Outdated-package metadata is unavailable "
                "(package index access failed or the check is unsupported): "
                "{}".format(exc),
            )
        try:
            raw = json.loads(raw_text) if isinstance(raw_text, str) else (raw_text or [])
        except Exception:
            return OutdatedContext(
                analysis_available=False,
                reason="Outdated-package metadata could not be parsed.",
            )
        items = []
        if isinstance(raw, list):
            for entry in raw:
                if not isinstance(entry, dict) or not entry.get("name"):
                    continue
                items.append(
                    OutdatedItem(
                        name=str(entry.get("name")),
                        current_version=(
                            str(entry.get("version")) if entry.get("version") is not None else None
                        ),
                        latest_version=(
                            str(entry.get("latest_version"))
                            if entry.get("latest_version") is not None
                            else None
                        ),
                    )
                )
        return OutdatedContext(analysis_available=True, count=len(items), items=items)

    # -- security ------------------------------------------------------------------------------
    @staticmethod
    def _build_security(env_info, env_id):
        # type: (Optional[Dict[str, Any]], Any) -> SecurityContext
        if not env_info or not env_id:
            return SecurityContext(
                scan_available=False,
                reason="No environment is associated with this project.",
            )
        try:
            from py_env_studio.utils.handlers import DBHelper

            cached = DBHelper.get_vulnerability_info(env_id)
        except Exception as exc:
            return SecurityContext(
                scan_available=False,
                reason="Cached vulnerability data is unavailable: {}".format(exc),
            )
        counts = {level: 0 for level in _SEVERITY_LEVELS}
        unknown = 0
        total = 0
        for finding in _iter_findings(cached):
            total += 1
            level = str((finding.get("severity") or {}).get("level") or "").strip().lower()
            if level in counts:
                counts[level] += 1
            else:
                unknown += 1
        if total == 0:
            return SecurityContext(
                scan_available=False,
                reason="No cached vulnerability scan found for this "
                "environment. Scans are performed by PES itself; no "
                "network lookup was attempted.",
            )
        return SecurityContext(
            scan_available=True,
            total=total,
            critical=counts["critical"],
            high=counts["high"],
            medium=counts["medium"],
            low=counts["low"],
            unknown=unknown,
        )


def _iter_matrices(payload):
    # type: (Any) -> List[Dict[str, Any]]
    """Yield vulnerability matrices from either cached payload shape."""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("vulnerability_insights")
    if isinstance(raw, dict):
        return [raw]
    matrices = []
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            if "developer_view" in entry:
                matrices.append(entry)
            else:
                for inner in entry.values():
                    if isinstance(inner, dict) and "developer_view" in inner:
                        matrices.append(inner)
    return matrices


def _iter_findings(payload):
    # type: (Any) -> List[Dict[str, Any]]
    findings = []
    for matrix in _iter_matrices(payload):
        for vuln in matrix.get("developer_view") or []:
            if isinstance(vuln, dict):
                findings.append(vuln)
    return findings


def analyze_project(project_path=None):
    # type: (Any) -> ProjectAnalysis
    """Convenience entry point for a one-shot read-only project analysis."""
    return ProjectIntelligenceService().analyze(project_path)
