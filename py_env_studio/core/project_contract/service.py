"""Project contract service — load/save/resolve/validate (Phase A.1).

Read-only except for save(), which writes only pes.config (portable,
declared intent) and the project_contract SQLite row. No environments
are created, no packages installed, no IDE files touched, no network
access, no shell commands.
"""

from __future__ import annotations

import logging
import re
from configparser import ConfigParser, Error as ConfigParserError
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from py_env_studio.core import schema as sql
from py_env_studio.core.configuration import ConfigurationService

from .models import (
    ContractError,
    ContractValidationResult,
    ProjectContract,
    ResolvedEnvironment,
    ResolvedProjectContract,
)
from .repository import ProjectContractRepository, normalize_db_key

logger = logging.getLogger(__name__)

_PYTHON_VERSION_RE = re.compile(r"^\d+(?:\.\d+){0,2}$")

_PROVIDER_ALIASES = {
    "python install manager": "Python Install Manager",
    "python-install-manager": "Python Install Manager",
    "system": "System",
    "custom": "Custom",
}

_DEFAULT_PROVIDER = "Python Install Manager"


def _metadata_file(project_root: Path) -> Path:
    from py_env_studio.core.runtime_toggle import get_project_metadata_path

    return get_project_metadata_path(project_root)


def _configured_provider_default() -> str:
    try:
        prefs = ConfigurationService().load_preferences()
        provider = (prefs.runtime_provider or "").strip()
        if provider:
            return provider
    except Exception as exc:
        logger.debug("Provider preference lookup failed: %s", exc)
    return _DEFAULT_PROVIDER


class ProjectContractService:
    """Declared-contract lifecycle on top of existing PES persistence."""

    def __init__(self, db_manager=None):
        self._db_manager = db_manager
        self._repository = ProjectContractRepository(db_manager=db_manager)

    def _db(self):
        if self._db_manager is not None:
            return self._db_manager
        from py_env_studio.core.database import DatabaseManager

        return DatabaseManager()

    # -- load ------------------------------------------------------------------
    def load(self, project_path) -> Optional[ProjectContract]:
        """Load the declared contract, or None when no pes.config exists.

        Raises ContractError for malformed files and missing required values.
        Never creates anything.
        """
        parsed = self._parse(project_path)
        return parsed[0]

    def _parse(self, project_path) -> Tuple[Optional[ProjectContract], List[str], Dict[str, Any]]:
        """Return (contract|None, warnings, legacy_hints).

        Raises ContractError on malformed content or missing required values.
        """
        root = self._project_dir(project_path, must_exist=False)
        config_path = _metadata_file(root)
        if not config_path.exists():
            return None, [], {}
        parser = ConfigParser(interpolation=None)
        try:
            parser.read(config_path, encoding="utf-8")
        except (ConfigParserError, OSError, UnicodeDecodeError) as exc:
            raise ContractError(
                "Malformed pes.config at '{}': {}".format(config_path, exc)
            )
        if not parser.sections():
            return None, [], {}

        warnings: List[str] = []
        legacy: Dict[str, Any] = {}
        for key in ("root",):
            if parser.has_option("project", key):
                legacy["project_root"] = parser.get("project", key)
                warnings.append(
                    "pes.config contains a legacy absolute 'project:{}' entry; "
                    "it is ignored (contracts resolve locations, not paths).".format(key)
                )
        for key in ("path",):
            if parser.has_option("environment", key):
                legacy["environment_path"] = parser.get("environment", key)
                warnings.append(
                    "pes.config contains a legacy absolute 'environment:{}' entry; "
                    "the environment is resolved by ID instead.".format(key)
                )

        name = parser.get("project", "name", fallback="").strip()
        if not name:
            raise ContractError("pes.config is missing the required project name.")
        env_id = parser.get("environment", "id", fallback="").strip()
        if not env_id:
            raise ContractError("pes.config is missing the required environment ID.")

        version = parser.get("python", "version", fallback="").strip()
        if not version:
            # Backward compatibility: python_version historically lived here.
            version = parser.get("environment", "python_version", fallback="").strip()
        if not version:
            raise ContractError("pes.config is missing the required Python version.")

        provider_raw = parser.get("python", "provider", fallback="").strip()
        provider = _PROVIDER_ALIASES.get(provider_raw.lower(), provider_raw.strip())
        if not provider:
            provider = _configured_provider_default()

        package_manager = parser.get("environment", "package_manager", fallback="pip").strip()
        if not package_manager:
            package_manager = "pip"
        try:
            runtime_managed = parser.getboolean("runtime", "managed", fallback=True)
            runtime_enabled = parser.getboolean("runtime", "enabled", fallback=False)
            runtime_auto_init = parser.getboolean("runtime", "auto_init", fallback=True)
        except ValueError as exc:
            raise ContractError(
                "pes.config has an invalid runtime configuration: {}".format(exc)
            )

        contract = ProjectContract(
            project_name=name,
            python_version=version,
            python_provider=provider,
            environment_id=env_id,
            package_manager=package_manager,
            runtime_managed=runtime_managed,
            runtime_enabled=runtime_enabled,
            runtime_auto_init=runtime_auto_init,
        )
        return contract, warnings, legacy

    @staticmethod
    def _project_dir(project_path, must_exist=True) -> Path:
        if isinstance(project_path, Path):
            root = project_path
        elif isinstance(project_path, str) and project_path.strip():
            from os.path import expanduser

            root = Path(expanduser(project_path.strip()))
        else:
            raise ContractError("A project directory path is required.")
        if root.exists() and not root.is_dir():
            raise ContractError(
                "Project path '{}' is not a directory.".format(project_path)
            )
        if must_exist and not root.exists():
            raise ContractError(
                "Project directory does not exist: '{}'.".format(project_path)
            )
        return root.resolve()

    # -- save --------------------------------------------------------------------
    def save(self, project_path, contract: ProjectContract) -> ProjectContract:
        """Persist the declared contract to pes.config + SQLite row.

        Writes portable content only (no absolute paths). Creates nothing
        else: no environment, no registry entry, no IDE files.
        """
        if not isinstance(contract, ProjectContract):
            raise ContractError("contract must be a ProjectContract.")
        problems = self._structural_errors(contract)
        if problems:
            raise ContractError(
                "Refusing to save an invalid contract: {}".format("; ".join(problems))
            )
        root = self._project_dir(project_path, must_exist=True)
        config_path = _metadata_file(root)

        parser = ConfigParser(interpolation=None)
        parser["project"] = {"name": contract.project_name}
        parser["python"] = {
            "version": contract.python_version,
            "provider": contract.python_provider,
        }
        parser["environment"] = {
            "id": contract.environment_id,
            "package_manager": contract.package_manager,
        }
        parser["runtime"] = {
            "managed": str(bool(contract.runtime_managed)).lower(),
            "enabled": str(bool(contract.runtime_enabled)).lower(),
            "auto_init": str(bool(contract.runtime_auto_init)).lower(),
        }
        try:
            with open(config_path, "w", encoding="utf-8") as handle:
                parser.write(handle)
        except OSError as exc:
            raise ContractError(
                "Could not write pes.config at '{}': {}".format(config_path, exc)
            )

        self._repository.upsert(
            project_path=root,
            project_name=contract.project_name,
            environment_id=contract.environment_id,
            python_version=contract.python_version,
            python_provider=contract.python_provider,
            package_manager=contract.package_manager,
            runtime_managed=contract.runtime_managed,
            runtime_enabled=contract.runtime_enabled,
            runtime_auto_init=contract.runtime_auto_init,
            config_path=config_path,
        )
        return contract

    # -- resolve --------------------------------------------------------------------
    def resolve(self, project_path) -> ResolvedProjectContract:
        """Resolve the declared contract against registered PES state.

        Raises ContractError when no contract exists. Never repairs.
        """
        parsed_contract, _warnings, _legacy = self._parse(project_path)
        if parsed_contract is None:
            raise ContractError(
                "No project contract found for '{}': no pes.config.".format(project_path)
            )
        root = self._project_dir(project_path, must_exist=False)
        registered = self._is_registered(parsed_contract.environment_id)
        info = self._environment_info(parsed_contract.environment_id)
        environment = ResolvedEnvironment(
            environment_id=parsed_contract.environment_id,
            registered=registered,
            exists=info is not None,
            path=(info.get("path") if info else None),
        )
        return ResolvedProjectContract(
            contract=parsed_contract,
            project_path=normalize_db_key(root),
            config_path=str(_metadata_file(root)),
            environment=environment,
        )

    def _is_registered(self, environment_id: str) -> bool:
        try:
            with self._db().connect() as conn:
                row = conn.execute(
                    sql.get("environments", "get_env_id"), (environment_id,)
                ).fetchone()
            return row is not None
        except Exception as exc:
            logger.warning("Environment registration lookup failed: %s", exc)
            return False

    @staticmethod
    def _environment_info(environment_id: str) -> Optional[Dict[str, Any]]:
        try:
            from py_env_studio.core import env_manager

            return env_manager.get_environment_info(environment_id)
        except Exception as exc:
            logger.warning("Environment lookup failed for %r: %s", environment_id, exc)
            return None

    # -- validate ----------------------------------------------------------------------
    def validate(self, project_path) -> ContractValidationResult:
        """Check the contract structurally. Detects, never repairs."""
        errors: List[str] = []
        warnings: List[str] = []
        try:
            parsed_contract, parse_warnings, legacy = self._parse(project_path)
            warnings.extend(parse_warnings)
        except ContractError as exc:
            return ContractValidationResult(valid=False, errors=[str(exc)])
        if parsed_contract is None:
            return ContractValidationResult(
                valid=False,
                errors=[
                    "No pes.config found for '{}': project is not PES-managed.".format(
                        project_path
                    )
                ],
            )
        errors.extend(self._structural_errors(parsed_contract))
        if errors:
            return ContractValidationResult(valid=False, errors=errors, warnings=warnings)

        env_id = parsed_contract.environment_id
        registered = self._is_registered(env_id)
        if not registered:
            errors.append(
                "Environment ID '{}' is not registered in PES.".format(env_id)
            )
            return ContractValidationResult(valid=False, errors=errors, warnings=warnings)
        info = self._environment_info(env_id)
        if info is None:
            errors.append(
                "Environment '{}' is registered but no longer exists.".format(env_id)
            )
        else:
            legacy_path = (legacy.get("environment_path") or "").strip()
            if legacy_path and legacy_path != str(info.get("path") or ""):
                warnings.append(
                    "Legacy declared environment path differs from the resolved "
                    "environment path; the resolved path is authoritative."
                )
        return ContractValidationResult(
            valid=not errors, errors=errors, warnings=warnings
        )

    @staticmethod
    def _structural_errors(contract: ProjectContract) -> List[str]:
        problems: List[str] = []
        if not contract.project_name or not contract.project_name.strip():
            problems.append("Missing project name.")
        if not contract.environment_id or not contract.environment_id.strip():
            problems.append("Missing environment ID.")
        if not _PYTHON_VERSION_RE.match((contract.python_version or "").strip()):
            problems.append(
                "Invalid Python version format: {!r}.".format(contract.python_version)
            )
        if contract.package_manager not in ConfigurationService.SUPPORTED_PACKAGE_MANAGERS:
            problems.append(
                "Invalid package manager: {!r} (supported: {}).".format(
                    contract.package_manager,
                    ", ".join(ConfigurationService.SUPPORTED_PACKAGE_MANAGERS),
                )
            )
        if contract.python_provider not in ConfigurationService.SUPPORTED_RUNTIME_PROVIDERS:
            problems.append(
                "Invalid Python provider: {!r} (supported: {}).".format(
                    contract.python_provider,
                    ", ".join(ConfigurationService.SUPPORTED_RUNTIME_PROVIDERS),
                )
            )
        return problems

    # -- registered-state read --------------------------------------------------------------
    def registered(self, project_path) -> Optional[Dict[str, Any]]:
        """Return the SQLite-registered row for a project, or None."""
        return self._repository.get_by_path(project_path)
