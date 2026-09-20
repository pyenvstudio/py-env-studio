"""SQL statement templates for Py Env Studio.

Each ``<purpose>.sql`` file in this package holds named statements. A
statement starts with a ``-- name: <key>`` header line; everything until
the next header (or end of file) is the statement body.

Values are NEVER interpolated into these templates. All runtime values
use DB-API ``?`` placeholders at the call site. The single exception is
``migration.copy_legacy_scans``, whose ``{source_col}`` identifier is
validated against a two-value whitelist in ``database.py`` before
formatting (identifiers cannot be bound parameters).
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path


def _read_sql_file(purpose: str) -> str:
    """Read ``<purpose>.sql`` from the installed package or source tree."""
    resource = f"{purpose}.sql"
    try:
        from importlib import resources as _resources

        try:
            # Python 3.7+ API (also works on newer versions).
            text = _resources.read_text(__name__, resource)
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            text = None
        if text is not None:
            return text
    except ImportError:  # pragma: no cover - very old Python
        pass
    # Fallback: source-tree layout next to this file.
    return (Path(__file__).resolve().parent / resource).read_text(encoding="utf-8")


def _parse_statements(text: str) -> "OrderedDict[str, str]":
    """Parse ``-- name: <key>`` blocks, preserving file order."""
    statements: "OrderedDict[str, str]" = OrderedDict()
    current: str | None = None
    buffer: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.lower().startswith("-- name:"):
            if current is not None:
                statements[current] = "\n".join(buffer).strip()
            current = stripped.split(":", 1)[1].strip()
            if not current:
                raise ValueError("SQL template has an empty '-- name:' header")
            if current in statements:
                raise ValueError(f"Duplicate SQL template name: {current!r}")
            buffer = []
            continue
        buffer.append(raw_line)
    if current is not None:
        statements[current] = "\n".join(buffer).strip()
    return statements


_CACHE: dict[str, "OrderedDict[str, str]"] = {}


def _load(purpose: str) -> "OrderedDict[str, str]":
    if purpose not in _CACHE:
        _CACHE[purpose] = _parse_statements(_read_sql_file(purpose))
    return _CACHE[purpose]


def get(purpose: str, name: str) -> str:
    """Return the ``name`` statement from the ``<purpose>.sql`` template file."""
    try:
        return _load(purpose)[name]
    except KeyError:
        available = ", ".join(_load(purpose).keys()) or "<none>"
        raise KeyError(
            f"Unknown SQL template {name!r} in {purpose}.sql "
            f"(available: {available})"
        ) from None


def statements(purpose: str) -> list[str]:
    """Return every statement in ``<purpose>.sql`` in file order."""
    return list(_load(purpose).values())


def available(purpose: str) -> list[str]:
    """Return the statement names defined in ``<purpose>.sql``."""
    return list(_load(purpose).keys())


def clear_cache() -> None:
    """Drop the parsed-template cache (mainly for tests)."""
    _CACHE.clear()
