"""Progress state behind the fixed status-bar gauge in the main window.

Why a separate module:

* **Thread safety.**  Long operations run on the shared worker pool, so
  ``begin``/``update``/``finish`` are called from worker threads while the Tk
  thread reads.  All mutation happens under one lock; the Tk thread only ever
  calls :meth:`ProgressCoordinator.snapshot` from its periodic poll — the only
  sanctioned way to cross into Tk.
* **Testability.**  No tkinter/customtkinter imports here, so the scheduling
  logic (session stack, clamping, idle/done/error transitions, retention of the
  last outcome) is unit-testable headless, with an injectable clock.

The view (widgets, colours, marquee animation) lives in
``py_env_studio.ui.main_window.PyEnvStudio`` and renders whatever
``snapshot()`` returns.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

STATE_IDLE = "idle"
STATE_WORKING = "working"
STATE_DONE = "done"
STATE_ERROR = "error"

DEFAULT_RETAIN_SECONDS = 4.0


@dataclass
class _Session:
    """One in-flight task shown by the gauge."""

    token: int
    label: str
    total: Optional[float] = None
    done: float = 0.0
    status: str = ""
    ok: bool = True
    started_at: float = 0.0
    finished_at: Optional[float] = None
    message: str = ""
    events: int = field(default=0)


class ProgressCoordinator:
    """Thread-safe stack of task sessions feeding the status-bar gauge."""

    def __init__(
        self,
        *,
        retain_seconds: float = DEFAULT_RETAIN_SECONDS,
        clock=time.monotonic,
        status_width: int = 90,
    ) -> None:
        self._lock = threading.RLock()
        self._clock = clock
        self._retain_seconds = max(0.0, float(retain_seconds))
        self._status_width = max(20, int(status_width))
        self._sessions: list[_Session] = []
        self._finished: Optional[_Session] = None
        self._finished_at: Optional[float] = None
        self._activity = ""  # most recent activity line (idle label/detail)
        self._next_token = 1

    # -- worker-facing API (any thread) ---------------------------------
    def begin(self, label: str, total: Optional[float] = None) -> int:
        """Register a task and return its token (used to finish/step it)."""
        with self._lock:
            token = self._next_token
            self._next_token += 1
            resolved_total = float(total) if total else None
            if resolved_total is not None and resolved_total <= 0:
                resolved_total = None
            self._sessions.append(
                _Session(
                    token=token,
                    label=str(label),
                    total=resolved_total,
                    started_at=self._clock(),
                )
            )
            self._finished = None
            self._finished_at = None
            self._activity = str(label)
            return token

    def update(
        self,
        *,
        token: Optional[int] = None,
        done: Optional[float] = None,
        steps: Optional[float] = None,
        fraction: Optional[float] = None,
        status: Optional[str] = None,
    ) -> None:
        """Advance/report progress. Targets ``token``, else the top session."""
        clean_status = self._clean(status)
        with self._lock:
            session = self._resolve(token)
            if session is None:
                if clean_status:
                    self._activity = clean_status
                return
            session.events += 1
            if clean_status:
                session.status = clean_status
                self._activity = clean_status
            if fraction is not None:
                if session.total is None:
                    session.total = 1.0
                session.done = min(max(float(fraction), 0.0), 1.0) * session.total
            elif done is not None:
                session.done = float(done)
            elif steps is not None:
                session.done += float(steps)
            if session.total is not None:
                session.done = min(max(session.done, 0.0), session.total)

    def finish(
        self,
        token: Optional[int] = None,
        message: Optional[str] = None,
        ok: bool = True,
    ) -> None:
        """Close a session. Unknown/no tokens are ignored (never raises)."""
        now = self._clock()
        with self._lock:
            session = self._resolve(token)
            if session is None:
                if message:
                    self._activity = self._clean(message) or self._activity
                return
            session.finished_at = now
            session.ok = ok
            session.message = self._clean(message) or session.label
            if session.total is not None and ok:
                session.done = session.total
            self._sessions = [s for s in self._sessions if s.token != session.token]
            self._finished = session
            self._finished_at = now
            self._activity = session.message

    def set_status(self, text) -> None:
        """Record the latest activity line without starting a task.

        Used for cheap operations (list refreshes, pip output) so the status
        bar always shows what the application is doing even when no gauge
        session is running.
        """
        clean = self._clean(text)
        if not clean:
            return
        with self._lock:
            self._activity = clean

    # -- Tk-facing API (poll loop only) ---------------------------------
    def snapshot(self) -> dict:
        """Return an immutable view of what the gauge should show right now.

        ``show_gauge`` tells the view whether the bar/percent widgets belong
        on screen: only while a task is actually running.  Idle (and the
        done/error outcome window) keep the status *text* — the outcome is
        read from the coloured label — but hide the widgets so an empty bar
        never sits in the status strip pretending to measure something.
        """
        now = self._clock()
        with self._lock:
            if self._sessions:
                session = self._sessions[-1]
                if session.total:
                    fraction = min(max(session.done / session.total, 0.0), 1.0)
                    percent = f"{int(round(fraction * 100))}%"
                else:
                    fraction, percent = None, "···"
                detail = session.status or (self._activity if self._activity != session.label else "")
                return {
                    "state": STATE_WORKING,
                    "label": session.label,
                    "detail": detail,
                    "fraction": fraction,
                    "percent": percent,
                    "token": session.token,
                    "show_gauge": True,
                }

            if self._finished is not None and self._finished_at is not None:
                if now - self._finished_at <= self._retain_seconds:
                    session = self._finished
                    ok = session.ok
                    return {
                        "state": STATE_DONE if ok else STATE_ERROR,
                        "label": session.message,
                        "detail": "",
                        # The task is over: the gauge hides and the view moves
                        # the outcome cue onto the status text (green/red),
                        # so a finished bar never reads as "still in progress".
                        "fraction": 1.0,
                        "percent": "100%" if ok else "✕",
                        "token": session.token,
                        "show_gauge": False,
                    }
                self._finished = None
                self._finished_at = None

            return {
                "state": STATE_IDLE,
                "label": self._activity or "Ready",
                "detail": "",
                "fraction": 0.0,
                "percent": "0%",
                "token": None,
                "show_gauge": False,
            }

    # -- helpers ---------------------------------------------------------
    def _resolve(self, token: Optional[int]) -> Optional[_Session]:
        if token is None:
            return self._sessions[-1] if self._sessions else None
        for session in self._sessions:
            if session.token == token:
                return session
        return None

    @staticmethod
    def _clean(text) -> str:
        if text is None:
            return ""
        collapsed = " ".join(str(text).split())
        return collapsed

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    @property
    def last_activity(self) -> str:
        with self._lock:
            return self._activity
