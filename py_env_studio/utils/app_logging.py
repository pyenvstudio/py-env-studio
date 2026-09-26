"""Central logging setup shared by the GUI, CLI and MCP entry points.

Every Py Env Studio entry point funnels records into the same three sinks:

* **File** (always, ``DEBUG``): the rotating ``py_env_studio.log`` in the
  platform data directory.  This is where full tracebacks and worker-thread
  detail live, so a failure can be diagnosed after the fact.
* **stderr console** (level from verbosity): the CLI's voice.  Diagnostics
  never share stdout with command output, so ``pes --list | grep x`` keeps
  working while progress and status lines stay visible in a terminal.
* **UI queue** (optional, GUI only): mirrors ``WARNING``+ records into the
  on-screen activity console.  ``INFO`` records are not mirrored because the
  GUI already shows those lines through its own ``log_callback`` plumbing —
  mirroring them would print every pip line twice.

Handlers are tagged and reconfigured in place, so calling
:func:`configure_logging` more than once (CLI preflight, GUI startup, tests)
adjusts levels instead of duplicating records.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import IO, Optional

# Verbosity name -> console threshold.  "quiet" still shows errors: silence
# that hides failures is worse than a noisy success.
VERBOSITY_LEVELS: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "quiet": logging.ERROR,
}
DEFAULT_VERBOSITY = "info"

# The file always keeps everything: it is the only sink that survives a
# closed window or a piped stdout.
FILE_LEVEL = logging.DEBUG

_VERBOSITY_ALIASES = {
    "warn": "warning",
    "warnings": "warning",
    "critical": "error",
    "fatal": "error",
    "silent": "quiet",
    "none": "quiet",
    "off": "quiet",
}

FILE_TAG = "pes.file"
CONSOLE_TAG = "pes.console"
UI_TAG = "pes.ui"

FILE_FORMAT = "%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s"
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _ShortNameFormatter(logging.Formatter):
    """Console/queue formatter that drops the ``py_env_studio.`` package prefix."""

    def format(self, record: logging.LogRecord) -> str:
        original = record.name
        if original.startswith("py_env_studio."):
            record.name = original[len("py_env_studio."):]
        try:
            return super().format(record)
        finally:
            record.name = original


class _EncodingSafeStreamHandler(logging.StreamHandler):
    """stderr handler that survives a stream which cannot encode the message.

    Windows consoles are frequently cp1252 (cmd.exe, a redirected pipe, CI
    capture).  A record carrying a glyph such as ``✓``/``✗``/``⚠`` would then
    raise ``UnicodeEncodeError`` inside ``emit``; ``logging`` prints a
    ``--- Logging error ---`` traceback and the message itself is lost.

    The line is written as usual, and only when the stream rejects it is the
    whole record re-encoded with ``backslashreplace`` (``\\u2713``) so the text
    still arrives and logging never becomes the reason a run looks broken.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:  # noqa: BLE001 - logging must not raise into app code
            self.handleError(record)
            return
        try:
            self.stream.write(message + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            try:
                encoding = getattr(self.stream, "encoding", None) or "utf-8"
                safe = message.encode(encoding, "backslashreplace").decode(
                    encoding, "replace"
                )
                self.stream.write(safe + self.terminator)
                self.flush()
            except Exception:  # noqa: BLE001 - logging must not raise
                self.handleError(record)
        except RecursionError:
            raise
        except Exception:  # noqa: BLE001 - logging must not raise into app code
            self.handleError(record)


class QueueLogHandler(logging.Handler):
    """Forward formatted records into a :mod:`queue` consumed by the GUI.

    The Tk console textbox cannot be touched from worker threads, so the GUI
    drains a queue on its own timer.  ``emit`` swallows every error: logging
    must never be the reason an application breaks.
    """

    def __init__(self, log_queue, level: int = logging.WARNING) -> None:
        super().__init__(level=level)
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.log_queue.put(self.format(record))
        except Exception:  # noqa: BLE001 - logging must not raise into app code
            pass


def resolve_verbosity(explicit: Optional[str] = None) -> str:
    """Normalise a verbosity name from an argument or ``PES_LOG_LEVEL``.

    Unknown values fall back to :data:`DEFAULT_VERBOSITY` rather than raising,
    so a typo in an environment variable cannot stop the application.
    """
    raw = explicit or os.environ.get("PES_LOG_LEVEL") or DEFAULT_VERBOSITY
    name = str(raw).strip().lower()
    name = _VERBOSITY_ALIASES.get(name, name)
    return name if name in VERBOSITY_LEVELS else DEFAULT_VERBOSITY


def _tag(handler: logging.Handler) -> Optional[str]:
    return getattr(handler, "_pes_tag", None)


def _find_file_handler(log_file) -> Optional[logging.FileHandler]:
    """Existing file handler writing to ``log_file``, if any.

    ``env_manager`` still calls ``logging.basicConfig(filename=...)`` at import
    time as a fallback for embedders that never configure logging.  Reusing (and
    upgrading) that handler keeps a single writer per file — two handlers on
    the same path would write every record twice.
    """
    root = logging.getLogger()
    target = str(log_file)
    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler) and str(handler.baseFilename) == target:
            return handler
    return None


def configure_logging(
    verbosity: Optional[str] = None,
    *,
    log_file=None,
    console: bool = True,
    console_stream: Optional[IO[str]] = None,
    console_level: Optional[int] = None,
    ui_queue=None,
    ui_queue_level: int = logging.WARNING,
) -> dict:
    """Install/refresh the file, console and UI log handlers (idempotent).

    Returns a small summary (verbosity, resolved file path, console level) so
    callers and tests can assert what was configured.
    """
    from ..core.runtime import get_runtime_config

    level_name = resolve_verbosity(verbosity)
    threshold = VERBOSITY_LEVELS[level_name]

    if log_file is None:
        log_file = get_runtime_config().log_path
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # handlers decide what leaves the process

    # --- file sink -------------------------------------------------------
    file_handler = next(
        (h for h in root.handlers if _tag(h) == FILE_TAG and isinstance(h, logging.FileHandler)),
        None,
    )
    stale = _find_file_handler(log_file) if file_handler is None else None
    if file_handler is None and stale is not None:
        # Upgrade the import-time fallback handler to a rotating DEBUG one.
        root.removeHandler(stale)
        stale.close()
    if file_handler is None:
        # Explicit UTF-8: the locale code page would drop non-ASCII records.
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, delay=True, encoding="utf-8"
        )
        file_handler._pes_tag = FILE_TAG  # type: ignore[attr-defined]
        root.addHandler(file_handler)
    file_handler.setLevel(FILE_LEVEL)
    file_handler.setFormatter(
        logging.Formatter(FILE_FORMAT, datefmt=FILE_DATE_FORMAT)
    )

    # --- stderr console sink -------------------------------------------
    for handler in [h for h in root.handlers if _tag(h) == CONSOLE_TAG]:
        root.removeHandler(handler)
        handler.close()
    stream = console_stream if console_stream is not None else sys.stderr
    if console and stream is not None:
        # Encoding-safe: a cp1252 console must still receive ✓/✗ records.
        console_handler = _EncodingSafeStreamHandler(stream)
        console_handler._pes_tag = CONSOLE_TAG  # type: ignore[attr-defined]
        console_handler.setLevel(console_level if console_level is not None else threshold)
        console_handler.setFormatter(
            _ShortNameFormatter("%(levelname)-7s %(name)s: %(message)s")
        )
        root.addHandler(console_handler)

    # --- GUI on-screen sink ---------------------------------------------
    for handler in [h for h in root.handlers if _tag(h) == UI_TAG]:
        root.removeHandler(handler)
        handler.close()
    if ui_queue is not None:
        ui_handler = QueueLogHandler(ui_queue, level=ui_queue_level)
        ui_handler._pes_tag = UI_TAG  # type: ignore[attr-defined]
        ui_handler.setFormatter(
            _ShortNameFormatter("%(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(ui_handler)

    # Third-party debug chatter would bury our own records in the file.
    logging.getLogger("PIL").setLevel(logging.WARNING)

    return {
        "verbosity": level_name,
        "log_file": str(log_file),
        "console_level": (
            console_level if console_level is not None else threshold
        )
        if console
        else None,
    }
