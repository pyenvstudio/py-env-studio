"""Project contract foundation — pes.config as declared environment contract.

Source-of-truth rules enforced by this package:

* pes.config: project intent, Python requirement, environment ID,
  package-manager preference, runtime management preference.
* SQLite project_contract table (+ environments table): environment
  registration, resolved environment path, existence, runtime state,
  dynamic metadata.
* Runtime filesystem: actual files, actual Python executable, actual
  installed packages.

Nothing here creates environments, installs packages, touches IDE
configuration, performs network access, or mutates unrelated files.
"""

from __future__ import annotations

from .models import (
    ContractError,
    ContractValidationResult,
    ProjectContract,
    ResolvedEnvironment,
    ResolvedProjectContract,
)
from .repository import ProjectContractRepository
from .service import ProjectContractService

__all__ = [
    "ContractError",
    "ContractValidationResult",
    "ProjectContract",
    "ProjectContractRepository",
    "ProjectContractService",
    "ResolvedEnvironment",
    "ResolvedProjectContract",
]
