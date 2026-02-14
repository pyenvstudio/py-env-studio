"""Auto-resolve dependency conflicts for pip and uv.

This module provides automatic resolution of package dependency conflicts
by stripping version constraints and allowing the package manager to solve
the dependency graph.
"""

import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


def extract_package_name(package_spec: str) -> str:
    """Extract the package name from a package specification.
    
    Args:
        package_spec: Package specification (e.g., "django==4.2", "requests>=2.28.0")
    
    Returns:
        Package name without version constraints
    """
    # Split on common version operators
    match = re.match(r'^([a-zA-Z0-9\-_\.]+)', package_spec)
    if match:
        return match.group(1)
    return package_spec


def strip_version_constraints(package_spec: str) -> str:
    """Remove version constraints from a package specification.
    
    Args:
        package_spec: Package specification (e.g., "django==4.2")
    
    Returns:
        Package name without version constraints
    """
    return extract_package_name(package_spec)


def is_resolution_error(error_output: str) -> bool:
    """Check if the error is a dependency resolution error.
    
    Args:
        error_output: Error message from pip/uv
    
    Returns:
        True if it's a resolution error, False otherwise
    """
    resolution_keywords = [
        "ResolutionImpossible",
        "ERROR: ResolutionImpossible",
        "dependency-resolution",
        "dependency conflict",
        "conflicting dependencies",
        "No matching distribution",
        "has requirement",
        "but you have",
        "depends on",  # e.g., "mkdocs 1.6.1 depends on click>=7.0"
        "version conflict",
        "version mismatch",
        "requirement is incompatible",
    ]
    return any(keyword in error_output for keyword in resolution_keywords)


def parse_conflicting_packages(error_output: str) -> List[str]:
    """Extract package names involved in the dependency conflict.
    
    Args:
        error_output: Error message from pip/uv
    
    Returns:
        List of package names involved in the conflict
    """
    conflicting = []
    
    # Pattern: "package_name has requirement ..."
    # Pattern: "package_name version depends on constraint"
    # Pattern: "package_name requires ..."
    patterns = [
        r"(\w+[\w\-]*) has requirement",
        r"(\w+[\w\-]*)\s+[\d\.]+ depends on",  # e.g., "mkdocs 1.6.1 depends on"
        r"requires (\w+[\w\-]*)",
        r"The conflict is in the (\w+[\w\-]*)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, error_output, re.IGNORECASE)
        conflicting.extend(matches)
    
    return list(set(conflicting))  # Remove duplicates


class AutoResolver:
    """Handles automatic resolution of dependency conflicts."""
    
    def __init__(self, log_callback=None):
        """Initialize the auto-resolver.
        
        Args:
            log_callback: Optional callback for logging messages
        """
        self.log_callback = log_callback
        self.max_retries = 3
        self.retry_count = 0
    
    def log(self, message: str):
        """Log a message."""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)
    
    def should_retry(self, error_output: str) -> bool:
        """Determine if we should retry with version constraints removed.
        
        Args:
            error_output: Error message from installation attempt
        
        Returns:
            True if we should retry, False otherwise
        """
        if self.retry_count >= self.max_retries:
            self.log(f"[Auto-Resolve] Max retry attempts ({self.max_retries}) reached")
            return False
        
        if not is_resolution_error(error_output):
            return False
        
        self.log("[Auto-Resolve] Detected dependency conflict, attempting auto-resolve...")
        return True
    
    def prepare_retry_package(self, package_spec: str, attempt: int) -> str:
        """Prepare a modified package spec for retry.
        
        Args:
            package_spec: Original package specification
            attempt: Current retry attempt number
        
        Returns:
            Modified package specification
        """
        package_name = strip_version_constraints(package_spec)
        self.log(f"[Auto-Resolve] Attempt {attempt}: Installing '{package_name}' without version constraints")
        return package_name
    
    def resolve(self, package_spec: str, install_func, *args, **kwargs) -> Tuple[bool, str]:
        """Attempt to resolve installation with automatic fallback.
        
        Args:
            package_spec: Package specification to install
            install_func: Function to call for installation (must return (success, message))
            *args: Additional positional arguments for install_func
            **kwargs: Additional keyword arguments for install_func
        
        Returns:
            Tuple of (success, message)
        """
        self.retry_count = 0
        current_spec = package_spec
        last_error = None
        
        while self.retry_count < self.max_retries:
            # Attempt installation
            kwargs['package'] = current_spec
            success, message = install_func(*args, **kwargs)
            
            if success:
                if self.retry_count > 0:
                    self.log(f"[Auto-Resolve] ✓ Successfully installed '{current_spec}'")
                return True, message
            
            # Check if it's a resolution error
            last_error = message
            if not self.should_retry(message):
                return False, message
            
            # Prepare for retry with stripped version
            self.retry_count += 1
            current_spec = self.prepare_retry_package(package_spec, self.retry_count)
        
        # All retries exhausted
        error_msg = f"[Auto-Resolve] Failed after {self.retry_count} attempts. Last error: {last_error}"
        self.log(error_msg)
        return False, error_msg


def auto_resolve_install(package_spec: str, install_func, log_callback=None, *args, **kwargs) -> Tuple[bool, str]:
    """Convenience function for auto-resolved package installation.
    
    Args:
        package_spec: Package specification to install
        install_func: Function to call for installation
        log_callback: Optional logging callback
        *args: Additional positional arguments for install_func
        **kwargs: Additional keyword arguments for install_func
    
    Returns:
        Tuple of (success, message)
    """
    resolver = AutoResolver(log_callback=log_callback)
    return resolver.resolve(package_spec, install_func, *args, **kwargs)
