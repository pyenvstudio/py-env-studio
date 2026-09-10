"""Shared helpers for comparing PEP 440-ish version strings and computing the
remediation status (fixed / not fixed) of a vulnerability based on the
installed version vs. the fixed versions."""

import re

_MISSING = {"", "?", "—", "-", "None", "Unknown", "n/a"}


def version_key(version):
    """Return a comparable numeric tuple derived from a version string.

    "4.4.1" -> (4, 4, 1); "1.0" -> (1, 0); unknown/empty -> (0,)
    """
    parts = re.findall(r"\d+", version or "")
    return tuple(int(p) for p in parts) or (0,)


def is_known_version(version):
    """True when the version string carries real version information."""
    return version is not None and str(version).strip() not in _MISSING


def vuln_status(current_version, fixed_versions):
    """Compute the remediation status for a vulnerability.

    Returns "fixed" when the installed ``current_version`` meets or exceeds the
    highest fixed version in ``fixed_versions``, otherwise "not fixed".
    """
    fixed_keys = [version_key(f) for f in (fixed_versions or []) if is_known_version(f)]
    if not fixed_keys:
        return "not fixed"
    if not is_known_version(current_version):
        return "not fixed"
    best = max(fixed_keys)
    return "fixed" if version_key(current_version) >= best else "not fixed"