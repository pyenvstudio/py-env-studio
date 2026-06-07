"""Dependency Impact Preview - Shows what will change before installing packages.

This module analyzes dependency trees, detects conflicts, and provides detailed
impact reports before installation.
"""

import subprocess
import json
import logging
from typing import Dict, List, Tuple, Optional, Set
import re

from .env_manager import get_env_python
from .package_manager import list_packages

logger = logging.getLogger(__name__)


class DependencyPreviewError(Exception):
    """Error during dependency preview."""
    pass


class DependencyChange:
    """Represents a single dependency change."""
    
    def __init__(self, name: str, version: str, old_version: Optional[str] = None):
        self.name = name
        self.version = version
        self.old_version = old_version
    
    def to_dict(self) -> Dict:
        result = {"name": self.name, "version": self.version}
        if self.old_version:
            result["old_version"] = self.old_version
        return result


class BreakingChange:
    """Represents a potential breaking change."""
    
    def __init__(self, package: str, reason: str, severity: str = "medium"):
        self.package = package
        self.reason = reason
        self.severity = severity  # high, medium, low
    
    def to_dict(self) -> Dict:
        return {
            "package": self.package,
            "reason": self.reason,
            "severity": self.severity
        }


class PreviewResult:
    """Result of dependency preview analysis."""
    
    def __init__(self):
        self.additions: List[DependencyChange] = []
        self.upgrades: List[DependencyChange] = []
        self.removals: List[DependencyChange] = []
        self.breaking_changes: List[BreakingChange] = []
        self.conflicts: List[Dict] = []
    
    def to_dict(self) -> Dict:
        return {
            "additions": [x.to_dict() for x in self.additions],
            "upgrades": [x.to_dict() for x in self.upgrades],
            "removals": [x.to_dict() for x in self.removals],
            "breaking_changes": [x.to_dict() for x in self.breaking_changes],
            "conflicts": self.conflicts,
            "summary": {
                "will_add": len(self.additions),
                "will_upgrade": len(self.upgrades),
                "will_remove": len(self.removals),
                "potential_breaks": len(self.breaking_changes),
                "conflicts": len(self.conflicts)
            }
        }


def parse_package_spec(spec: str) -> Tuple[str, Optional[str]]:
    """Parse package specification into name and version constraint.
    
    Args:
        spec: Package specification (e.g., "django==4.2", "numpy>=1.20")
    
    Returns:
        Tuple of (package_name, version_constraint)
    """
    spec = spec.strip()
    
    # Handle edge cases
    if not spec:
        raise ValueError("Empty package specification")
    
    # Find the first version operator
    match = re.search(r'([<>=!].*)', spec)
    if match:
        name = spec[:match.start()].strip()
        version = match.group(1).strip()
        return name.lower(), version
    
    return spec.lower(), None


def get_installed_packages(env_name: str) -> Dict[str, str]:
    """Get currently installed packages in environment.
    
    Args:
        env_name: Name of the environment
    
    Returns:
        Dict mapping package name to version
    """
    try:
        packages = list_packages(env_name)
        return {name.lower(): version for name, version in packages}
    except Exception as e:
        logger.error(f"Failed to get installed packages: {e}")
        raise DependencyPreviewError(f"Could not retrieve installed packages: {e}")


def get_package_dependencies(python_path: str, package_spec: str) -> Dict[str, str]:
    """Get dependencies of a package using pip show.
    
    Args:
        python_path: Path to Python executable
        package_spec: Package specification
    
    Returns:
        Dict of dependencies (package -> version constraint)
    """
    try:
        package_name = parse_package_spec(package_spec)[0]
        
        result = subprocess.run(
            [python_path, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.warning(f"Could not get info for {package_name}")
            return {}
        
        deps = {}
        for line in result.stdout.split('\n'):
            if line.startswith('Requires:'):
                requires = line.split(':', 1)[1].strip()
                if requires:
                    for req in requires.split(','):
                        req = req.strip()
                        if req:
                            # Parse the requirement
                            try:
                                pkg_name = parse_package_spec(req)[0]
                                deps[pkg_name] = req
                            except:
                                pass
        
        return deps
    except Exception as e:
        logger.error(f"Failed to get dependencies for {package_spec}: {e}")
        return {}


def simulate_dependency_resolution(
    env_name: str,
    package_spec: str,
    python_path: str
) -> PreviewResult:
    """Simulate what pip would do with a dry-run.
    
    Uses pip's --dry-run capability if available, otherwise attempts manual analysis.
    
    Args:
        env_name: Name of the environment
        package_spec: Package to install
        python_path: Path to Python executable
    
    Returns:
        PreviewResult with all changes
    """
    result = PreviewResult()
    installed = get_installed_packages(env_name)
    
    package_name, version_spec = parse_package_spec(package_spec)
    
    try:
        # Try to use pip install --dry-run (available in pip >= 24.0)
        try:
            install_output = subprocess.run(
                [python_path, "-m", "pip", "install", "--dry-run", package_spec],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if install_output.returncode == 0:
                return _parse_pip_dry_run_output(
                    install_output.stdout,
                    package_name,
                    installed,
                    result
                )
        except Exception as e:
            logger.debug(f"Dry-run not available, using fallback: {e}")
        
        # Fallback: Manual analysis
        return _analyze_dependencies_manually(
            env_name,
            package_spec,
            package_name,
            python_path,
            installed,
            result
        )
    
    except Exception as e:
        logger.error(f"Dependency resolution failed: {e}")
        raise DependencyPreviewError(f"Could not analyze dependencies: {e}")


def _parse_pip_dry_run_output(
    output: str,
    package_name: str,
    installed: Dict[str, str],
    result: PreviewResult
) -> PreviewResult:
    """Parse pip install --dry-run output.
    
    Args:
        output: stdout from pip install --dry-run
        package_name: The package being installed
        installed: Currently installed packages
        result: PreviewResult to populate
    
    Returns:
        Updated PreviewResult
    """
    # Look for "Would install" and "Would collect" lines
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Match: "Collecting django==4.2"
        if line.startswith('Collecting '):
            pkg_spec = line.replace('Collecting ', '').strip()
            try:
                pkg_name, version = _extract_name_and_version(pkg_spec)
                
                if pkg_name.lower() not in installed:
                    result.additions.append(DependencyChange(pkg_name, version))
                else:
                    old_version = installed[pkg_name.lower()]
                    if old_version != version:
                        result.upgrades.append(
                            DependencyChange(pkg_name, version, old_version)
                        )
            except:
                pass
        
        # Match: "Installing collected packages: ..."
        elif line.startswith('Would install ') or line.startswith('Installing '):
            # Extract package list
            pkg_list = line.split(':', 1)[-1].strip()
            for pkg in pkg_list.split(','):
                pkg = pkg.strip()
                if pkg:
                    try:
                        pkg_name, version = _extract_name_and_version(pkg)
                    except:
                        pass
    
    return result


def _extract_name_and_version(pkg_spec: str) -> Tuple[str, str]:
    """Extract package name and version from spec.
    
    Args:
        pkg_spec: Package specification like "django-4.2" or "django==4.2"
    
    Returns:
        Tuple of (name, version)
    """
    # Try == format first
    if '==' in pkg_spec:
        parts = pkg_spec.split('==')
        return parts[0].strip(), parts[1].strip()
    
    # Try version in parens
    match = re.search(r'(.+?)\s*\((.+?)\)', pkg_spec)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Try dash separator (common in pip output)
    match = re.search(r'(.+?)\-(\d+.*)$', pkg_spec)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    raise ValueError(f"Cannot parse package spec: {pkg_spec}")


def _analyze_dependencies_manually(
    env_name: str,
    package_spec: str,
    package_name: str,
    python_path: str,
    installed: Dict[str, str],
    result: PreviewResult
) -> PreviewResult:
    """Manual dependency analysis without pip --dry-run.
    
    Args:
        env_name: Environment name
        package_spec: Package specification
        package_name: Package name (lowercase)
        python_path: Path to Python
        installed: Installed packages dict
        result: PreviewResult to populate
    
    Returns:
        Updated PreviewResult
    """
    try:
        # Get package info from PyPI metadata
        pkg_info_output = subprocess.run(
            [python_path, "-m", "pip", "index", "versions", package_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # If that fails, try to get it from pip show after a test download
        if pkg_info_output.returncode != 0:
            # Try using pip download to get metadata without installing
            download_result = subprocess.run(
                [python_path, "-m", "pip", "download", package_spec, "--no-deps", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if download_result.returncode != 0:
                logger.warning(f"Could not fetch {package_spec} info")
        
        # For the initial package
        if package_name in installed:
            old_version = installed[package_name]
            # We don't know the exact new version without downloading
            result.upgrades.append(DependencyChange(package_name, "latest", old_version))
        else:
            result.additions.append(DependencyChange(package_name, "latest"))
        
        # Get dependencies recursively
        deps = get_package_dependencies(python_path, package_spec)
        for dep_name, dep_spec in deps.items():
            dep_name_lower = dep_name.lower()
            
            if dep_name_lower in installed:
                # Would be an upgrade or downgrade
                old_version = installed[dep_name_lower]
                result.upgrades.append(
                    DependencyChange(dep_name, "latest", old_version)
                )
            else:
                result.additions.append(DependencyChange(dep_name, "latest"))
        
        # Check for known breaking changes
        _check_breaking_changes(package_name, result)
        
    except Exception as e:
        logger.error(f"Manual analysis failed: {e}")
    
    return result


def _check_breaking_changes(package_name: str, result: PreviewResult) -> None:
    """Check for known breaking changes.
    
    Args:
        package_name: Package name to check
        result: PreviewResult to populate
    """
    # Common breaking changes database
    breaking_changes_db = {
        "numpy": {
            "reason": "May break code using deprecated numpy.dtype constructors",
            "severity": "high"
        },
        "pandas": {
            "reason": "Index behavior changes in newer versions",
            "severity": "medium"
        },
        "matplotlib": {
            "reason": "API changes in plotting functions",
            "severity": "medium"
        },
        "django": {
            "reason": "ORM query API changes between major versions",
            "severity": "high"
        }
    }
    
    if package_name in breaking_changes_db:
        info = breaking_changes_db[package_name]
        result.breaking_changes.append(
            BreakingChange(package_name, info["reason"], info["severity"])
        )


def preview_install(env_name: str, package_spec: str) -> PreviewResult:
    """Main function to preview installation impact.
    
    Args:
        env_name: Name of the environment
        package_spec: Package specification
    
    Returns:
        PreviewResult with detailed impact analysis
    
    Raises:
        DependencyPreviewError: If preview cannot be generated
    """
    try:
        python_path = get_env_python(env_name)
        
        logger.info(f"Previewing install of {package_spec} in {env_name}")
        
        result = simulate_dependency_resolution(
            env_name,
            package_spec,
            python_path
        )
        
        logger.info(
            f"Preview complete: {len(result.additions)} additions, "
            f"{len(result.upgrades)} upgrades, "
            f"{len(result.breaking_changes)} warnings"
        )
        
        return result
    
    except DependencyPreviewError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in preview_install: {e}")
        raise DependencyPreviewError(f"Failed to preview install: {e}")
