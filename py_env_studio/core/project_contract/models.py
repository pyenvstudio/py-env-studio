"""Typed internal models for the PES project contract (Phase A.1).

The contract represents DECLARED configuration from pes.config (project
intent), never dynamic environment state. Resolved/registered state lives
in SQLite (project_contract table) and on the runtime filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ContractError(Exception):
    """Raised for malformed pes.config files and unresolvable contracts."""


@dataclass(frozen=True)
class ProjectContract:
    """Declared project intent as written in pes.config.

    Portable by design: no absolute filesystem paths. The environment is
    referenced by ID and resolved through PES registry/database services.
    """

    project_name: str
    python_version: str
    python_provider: str
    environment_id: str
    package_manager: str
    runtime_managed: bool = True
    runtime_enabled: bool = False
    runtime_auto_init: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": {"name": self.project_name},
            "python": {
                "version": self.python_version,
                "provider": self.python_provider,
            },
            "environment": {
                "id": self.environment_id,
                "package_manager": self.package_manager,
            },
            "runtime": {
                "managed": self.runtime_managed,
                "enabled": self.runtime_enabled,
                "auto_init": self.runtime_auto_init,
            },
        }


@dataclass(frozen=True)
class ResolvedEnvironment:
    """Resolved/registered environment state for a contracted environment ID."""

    environment_id: str
    registered: bool
    exists: bool
    path: Optional[str] = None


@dataclass(frozen=True)
class ResolvedProjectContract:
    """Declared contract plus its resolution against PES persisted state."""

    contract: ProjectContract
    project_path: str
    config_path: str
    environment: ResolvedEnvironment


@dataclass(frozen=True)
class ContractValidationResult:
    """Structured validation outcome. No scores, no subjective terms."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
