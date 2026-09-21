"""Typed internal models for project intelligence (read-only report)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ProjectContext:
    path: Optional[str]
    name: Optional[str]
    managed_by_pes: bool
    registered: bool


@dataclass(frozen=True)
class EnvironmentContext:
    available: bool
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    python_executable: Optional[str] = None
    python_version: Optional[str] = None
    package_manager: Optional[str] = None
    status: Optional[str] = None
    size: Optional[str] = None
    last_scanned: Optional[str] = None


@dataclass(frozen=True)
class PythonContext:
    available: bool
    version: Optional[str] = None
    executable: Optional[str] = None
    executable_available: Optional[bool] = None
    provider: Optional[str] = None


@dataclass(frozen=True)
class PackageManagerContext:
    available: bool
    manager: Optional[str] = None
    configured: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class RuntimeContext:
    managed_by_pes: bool
    status: Optional[str] = None  # "enabled" | "disabled" (actual PES states)


@dataclass(frozen=True)
class ConflictItem:
    package: str
    requirement: str
    reason: str


@dataclass(frozen=True)
class DependencyContext:
    analysis_available: bool
    installed: Optional[int] = None
    requirements_checked: int = 0
    requirements_skipped: int = 0
    conflicts: List[ConflictItem] = field(default_factory=list)
    scope: str = (
        "Offline cross-check of installed requirements from local pip "
        "metadata; not a full dependency-solver proof."
    )
    reason: Optional[str] = None


@dataclass(frozen=True)
class OutdatedItem:
    name: str
    current_version: Optional[str] = None
    latest_version: Optional[str] = None


@dataclass(frozen=True)
class OutdatedContext:
    analysis_available: bool
    count: Optional[int] = None
    items: List[OutdatedItem] = field(default_factory=list)
    reason: Optional[str] = None


@dataclass(frozen=True)
class SecurityContext:
    scan_available: bool
    total: Optional[int] = None
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unknown: int = 0
    reason: Optional[str] = None


@dataclass(frozen=True)
class PesConfigContext:
    registered: bool
    environment_id: Optional[str] = None
    environment_path: Optional[str] = None
    python_version: Optional[str] = None
    package_manager: Optional[str] = None
    runtime_enabled: Optional[bool] = None
    runtime_provider: Optional[str] = None


@dataclass(frozen=True)
class AnalysisSummary:
    environment_available: bool
    dependency_analysis_available: bool
    dependency_conflicts: Optional[int] = None
    outdated_packages: Optional[int] = None
    security_scan_available: bool = False
    vulnerabilities: Optional[int] = None


@dataclass(frozen=True)
class ProjectAnalysis:
    project: ProjectContext
    environment: EnvironmentContext
    python: PythonContext
    package_manager: PackageManagerContext
    runtime: RuntimeContext
    dependencies: DependencyContext
    outdated: OutdatedContext
    security: SecurityContext
    pes_config: PesConfigContext
    summary: AnalysisSummary

    def to_dict(self) -> Dict[str, Any]:
        # type: () -> Dict[str, Any]
        return {
            "project": {
                "path": self.project.path,
                "name": self.project.name,
                "managed_by_pes": self.project.managed_by_pes,
                "registered": self.project.registered,
            },
            "environment": {
                "available": self.environment.available,
                "id": self.environment.id,
                "name": self.environment.name,
                "path": self.environment.path,
                "python_executable": self.environment.python_executable,
                "python_version": self.environment.python_version,
                "package_manager": self.environment.package_manager,
                "status": self.environment.status,
                "size": self.environment.size,
                "last_scanned": self.environment.last_scanned,
            },
            "python": {
                "available": self.python.available,
                "version": self.python.version,
                "executable": self.python.executable,
                "executable_available": self.python.executable_available,
                "provider": self.python.provider,
            },
            "package_manager": {
                "available": self.package_manager.available,
                "manager": self.package_manager.manager,
                "configured": self.package_manager.configured,
                "reason": self.package_manager.reason,
            },
            "runtime": {
                "managed_by_pes": self.runtime.managed_by_pes,
                "status": self.runtime.status,
            },
            "dependencies": {
                "analysis_available": self.dependencies.analysis_available,
                "installed": self.dependencies.installed,
                "requirements_checked": self.dependencies.requirements_checked,
                "requirements_skipped": self.dependencies.requirements_skipped,
                "conflicts": {
                    "count": len(self.dependencies.conflicts),
                    "items": [
                        {
                            "package": item.package,
                            "requirement": item.requirement,
                            "reason": item.reason,
                        }
                        for item in self.dependencies.conflicts
                    ],
                },
                "scope": self.dependencies.scope,
                "reason": self.dependencies.reason,
            },
            "outdated": {
                "analysis_available": self.outdated.analysis_available,
                "count": self.outdated.count,
                "items": [
                    {
                        "name": item.name,
                        "current_version": item.current_version,
                        "latest_version": item.latest_version,
                    }
                    for item in self.outdated.items
                ],
                "reason": self.outdated.reason,
            },
            "security": {
                "scan_available": self.security.scan_available,
                "vulnerabilities": {
                    "total": self.security.total,
                    "critical": self.security.critical,
                    "high": self.security.high,
                    "medium": self.security.medium,
                    "low": self.security.low,
                    "unknown": self.security.unknown,
                },
                "reason": self.security.reason,
            },
            "pes_config": {
                "registered": self.pes_config.registered,
                "environment_id": self.pes_config.environment_id,
                "environment_path": self.pes_config.environment_path,
                "python_version": self.pes_config.python_version,
                "package_manager": self.pes_config.package_manager,
                "runtime_enabled": self.pes_config.runtime_enabled,
                "runtime_provider": self.pes_config.runtime_provider,
            },
            "summary": {
                "environment_available": self.summary.environment_available,
                "dependency_analysis_available": self.summary.dependency_analysis_available,
                "dependency_conflicts": self.summary.dependency_conflicts,
                "outdated_packages": self.summary.outdated_packages,
                "security_scan_available": self.summary.security_scan_available,
                "vulnerabilities": self.summary.vulnerabilities,
            },
        }
