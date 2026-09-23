"""Fixed-width progress gauge for CLI commands.

Desktop and terminal UX differ, so the gauge adapts instead of forcing one
behaviour on both:

* **Interactive terminal (TTY):** a single self-overwriting line on *stderr*
  — ``Creating env [████░░░░░░░░]  40% ensurepip`` — redrawn in place and
  erased on completion, so stdout stays clean for command output and pipes.
  When the total is unknown the gauge runs a marquee animation fed by a
  daemon ticker thread (the work itself stays on the calling thread).
* **Not a TTY** (pipe, CI log, ``> file``): nothing is ever redrawn.  Only
  coarse milestones are logged at ``INFO`` (25/55/75%), so logs stay readable
  and free of control characters.

Disable explicitly with ``--no-progress`` or ``PES_NO_PROGRESS=1``.

Example::

    with TaskProgress("Installing requests") as progress:
        install_package(env, "requests", log_callback=progress.note)
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
import time
from typing import IO, Optional

LOGGER = logging.getLogger(__name__)

FILLED = "█"
EMPTY = "░"
DEFAULT_BAR_WIDTH = 24
DEFAULT_STATUS_WIDTH = 42
DEFAULT_TICK_SECONDS = 0.08
MILESTONE_STEP = 0.25


def _truthy(value: Optional[str]) -> bool:
    return bool(value) and str(value).strip().lower() not in {"0", "false", "no", "off"}


class TaskProgress:
    """A single tracked CLI task. Use it as a context manager."""

    def __init__(
        self,
        label: str,
        total: Optional[float] = None,
        *,
        stream: Optional[IO[str]] = None,
        enabled: Optional[bool] = None,
        bar_width: int = DEFAULT_BAR_WIDTH,
        status_width: int = DEFAULT_STATUS_WIDTH,
        tick: float = DEFAULT_TICK_SECONDS,
        clock=time.monotonic,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.label = str(label)
        self.total = float(total) if total else None
        self._stream = stream if stream is not None else sys.stderr
        self._enabled = self._resolve_enabled(enabled)
        self._bar_width = max(4, int(bar_width))
        self._status_width = max(8, int(status_width))
        self._tick = max(0.01, float(tick))
        self._clock = clock
        self._logger = logger or LOGGER

        self._lock = threading.RLock()
        self._done = 0.0
        self._status = ""
        self._phase = "pending"  # pending -> running -> done|failed
        self._started_at: Optional[float] = None
        self._finished_at: Optional[float] = None
        self._position = 0  # marquee slider offset
        self._ticker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_line_length = 0
        self._last_milestone = 0.0
        self._columns = self._terminal_columns()

    # -- configuration ---------------------------------------------------
    @staticmethod
    def _resolve_enabled(enabled: Optional[bool]) -> bool:
        if enabled is not None:
            return bool(enabled)
        if _truthy(os.environ.get("PES_NO_PROGRESS")):
            return False
        if _truthy(os.environ.get("PES_PROGRESS")):
            return True
        try:
            return bool(sys.stderr.isatty())
        except Exception:  # closed/absent stream
            return False

    def _terminal_columns(self) -> int:
        try:
            return max(40, shutil.get_terminal_size((100, 24)).columns - 1)
        except Exception:
            return 99

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def indeterminate(self) -> bool:
        return self.total is None

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def fraction(self) -> float:
        with self._lock:
            if not self.total:
                return 0.0
            return min(max(self._done / self.total, 0.0), 1.0)

    # -- lifecycle -------------------------------------------------------
    def start(self) -> "TaskProgress":
        with self._lock:
            if self._phase != "pending":
                return self
            self._phase = "running"
            self._started_at = self._clock()
        if self._enabled:
            if self.indeterminate:
                self._start_ticker()
            self._render()
        return self

    def finish(self, message: Optional[str] = None) -> None:
        """Mark the task complete, show 100% briefly and erase the line."""
        self._close("done", message)

    def fail(self, error=None) -> None:
        """Mark the task failed and erase the line (caller reports the error)."""
        self._close("failed", str(error) if error is not None else None)

    def close(self) -> None:
        """Idempotent cleanup: stop the ticker and erase any drawn line."""
        with self._lock:
            phase = self._phase
        if phase == "running":
            self.finish()
            return
        self._erase()

    def _close(self, phase: str, message: Optional[str]) -> None:
        with self._lock:
            if self._phase in {"done", "failed"}:
                return
            self._phase = phase
            self._finished_at = self._clock()
            if message:
                self._status = self._truncate(message, self._status_width)
        self._stop.set()
        ticker = self._ticker
        if ticker is not None and ticker.is_alive():
            ticker.join(timeout=1.0)
        self._ticker = None
        if self._enabled:
            with self._lock:
                if phase == "done" and not self.indeterminate and self.total:
                    self._done = self.total
            self._render()
        self._erase()

    def __enter__(self) -> "TaskProgress":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            self.finish()
        else:
            self.fail(exc)
        return False  # never swallow the exception

    # -- progress input --------------------------------------------------
    def note(self, text) -> None:
        """Report the current step (a pip/uv line, a stage name, ...)."""
        if text is None:
            return
        clean = " ".join(str(text).split())
        if not clean:
            return
        with self._lock:
            self._status = self._truncate(clean, self._status_width)
        self._logger.debug("%s: %s", self.label, clean)
        if self._enabled and self._phase == "running":
            self._render()

    def advance(self, steps: float = 1) -> None:
        with self._lock:
            self.set_done(self._done + steps)

    def set_done(self, done: float) -> None:
        with self._lock:
            if self.total is None:
                return
            self._done = min(max(float(done), 0.0), self.total)
            fraction = self._done / self.total
        self._maybe_log_milestone(fraction)
        if self._enabled and self._phase == "running":
            self._render()

    def set_fraction(self, fraction: float) -> None:
        if self.total:
            self.set_done(float(fraction) * self.total)
            return
        # Determinate-looking update on an unknown total: synthesise a total so
        # the gauge can show real numbers instead of animating forever.
        with self._lock:
            self.total = 1.0
        self.set_done(float(fraction))

    def _maybe_log_milestone(self, fraction: float) -> None:
        milestone = (int(fraction // MILESTONE_STEP) * MILESTONE_STEP)
        if milestone <= self._last_milestone or milestone >= 1.0:
            return
        self._last_milestone = milestone
        percent = int(round(fraction * 100))
        detail = f" ({self._status})" if self._status else ""
        self._logger.info("%s: %d%%%s", self.label, percent, detail)

    # -- rendering -------------------------------------------------------
    @staticmethod
    def _truncate(text: str, width: int) -> str:
        text = str(text)
        if len(text) <= width:
            return text
        if width <= 1:
            return text[:width]
        return text[: width - 1] + "…"

    def _compose(self) -> str:
        if self.indeterminate:
            bar = f"[{self._slider_blocks()}]"
            percent, suffix = "  -", ""
        else:
            fraction = self.fraction
            filled = int(round(fraction * self._bar_width))
            bar = f"[{FILLED * filled}{EMPTY * (self._bar_width - filled)}]"
            percent, suffix = f"{int(round(fraction * 100)):>3}", "%"
        line = (
            f"{self._truncate(self.label, 22):<22} {bar} {percent}{suffix} "
            f"{self._truncate(self._status, self._status_width)}"
        )
        if len(line) > self._columns:
            line = line[: self._columns]
        return line

    def _slider_blocks(self) -> str:
        width = self._bar_width
        head = 3  # width of the moving chunk
        pos = self._position % (width + head)
        start = pos - head
        blocks = []
        for index in range(width):
            blocks.append(FILLED if start <= index < pos else EMPTY)
        return "".join(blocks)

    def _render(self) -> None:
        if not self._enabled or self._phase not in {"running", "done", "failed"}:
            return
        with self._lock:  # the ticker thread and the worker both redraw
            try:
                line = self._compose()
                padding = " " * max(0, self._last_line_length - len(line))
                # Leave the cursor at column 0 so the next redraw overwrites
                # this line in place instead of appending to it.
                self._stream.write("\r" + line + padding)
                self._stream.flush()
                self._last_line_length = len(line)
            except Exception:  # a broken pipe/status line must not kill the task
                self._enabled = False

    def _erase(self) -> None:
        if not self._enabled:
            return
        with self._lock:
            if self._last_line_length == 0:
                return
            try:
                # Overwrite the line, then park the cursor back at column 0.
                self._stream.write("\r" + " " * self._last_line_length + "\r")
                self._stream.flush()
            except Exception:
                pass
            self._last_line_length = 0

    # -- indeterminate animation ----------------------------------------
    def _start_ticker(self) -> None:
        if self._ticker is not None:
            return

        def _tick_loop() -> None:
            while not self._stop.wait(self._tick):
                with self._lock:
                    if self._phase != "running":
                        break
                    self._position += 1
                self._render()

        self._ticker = threading.Thread(
            target=_tick_loop, name="pes-progress", daemon=True
        )
        self._ticker.start()

    @property
    def elapsed(self) -> float:
        if self._started_at is None:
            return 0.0
        end = self._finished_at if self._finished_at is not None else self._clock()
        return max(0.0, end - self._started_at)


def task_progress(label: str, total: Optional[float] = None, **kwargs) -> TaskProgress:
    """Factory kept for call-site symmetry with ``run_async`` in the GUI."""
    return TaskProgress(label, total, **kwargs)
