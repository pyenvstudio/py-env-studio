"""Thread-safe background work for the Tk UI (Python 3.12+).

Two rules live here so every call site obeys them:

1. **Never block the Tk main thread.**  Subprocesses, network calls, database
   work and heavy loops run on a shared
   :class:`~concurrent.futures.ThreadPoolExecutor`.  A ``time.sleep()`` or a
   long loop inside a Tk callback stops ``mainloop()`` from dispatching clicks
   and repaints — that is what users experience as a frozen window.
2. **Only the main thread may touch widgets.**  Tkinter is neither re-entrant
   nor thread safe, so results travel back through ``widget.after(0, ...)``,
   the single queue Tk accepts from other threads.  Updating a widget directly
   from a worker thread crashes the app (or corrupts its state).

Typical use::

    run_in_background(
        lambda: list_packages(env_name),
        ui=self,
        on_done=self._render_package_list,
        on_error=lambda exc: show_error(str(exc)),
    )

``on_done`` / ``on_error`` / ``on_finished`` are always marshalled back to the
Tk main thread, and are silently dropped when the window is already gone, so a
long-running task can safely outlive the UI that started it.
"""

from __future__ import annotations

import logging
import threading
import tkinter
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

# Generic callback shapes (PEP 695 type aliases, Python 3.12+).
type ResultCallback[ValueT] = Callable[[ValueT], None]
type ErrorCallback = Callable[[BaseException], None]
type VoidCallback = Callable[[], None]
type UiCallback = Callable[..., object]

logger = logging.getLogger(__name__)

MAX_WORKERS = 8
_WORKER_NAME_PREFIX = "pes-worker"

_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    """Return the shared worker pool, creating it on first use.

    Lazy creation keeps the CLI/MCP entry points free of threads they never
    need, and reuses a bounded pool instead of spawning a thread per task.
    """
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=MAX_WORKERS,
                thread_name_prefix=_WORKER_NAME_PREFIX,
            )
        return _executor


def is_ui_thread() -> bool:
    """True when the caller is the Tk main thread."""
    return threading.current_thread() is threading.main_thread()


def post_to_ui(
    ui: tkinter.Misc,
    callback: UiCallback,
    *args: object,
    delay_ms: int = 0,
) -> str | None:
    """Queue ``callback`` on the Tk main thread; safe to call from anywhere.

    ``widget.after`` is the sanctioned cross-thread door into Tk: the call is
    handed to the main thread's event queue and executed there.  Returns the
    ``after`` id, or ``None`` when the widget/main loop has already been torn
    down (background tasks routinely outlive the window that started them).
    """
    try:
        return ui.after(delay_ms, callback, *args)
    except (RuntimeError, tkinter.TclError):
        # "main thread is not in main loop" (loop gone) or a Tcl error from a
        # destroyed widget: the callback can no longer run, so drop it.
        logger.debug("Dropped UI callback; widget or main loop is gone", exc_info=True)
        return None
    except Exception:
        logger.debug("Failed to schedule UI callback", exc_info=True)
        return None


def run_in_background[ValueT](
    work: Callable[[], ValueT],
    *,
    ui: tkinter.Misc,
    on_done: ResultCallback[ValueT] | None = None,
    on_error: ErrorCallback | None = None,
    on_finished: VoidCallback | None = None,
) -> Future[ValueT]:
    """Run ``work`` on the worker pool and deliver results on the UI thread.

    Parameters
    ----------
    work:
        Blocking work.  Runs off the Tk thread — no widget may be touched
        inside it; hand plain data back instead.
    ui:
        Widget whose event queue marshals the callbacks (usually the main
        window).  Only used for its ``after``.
    on_done:
        Called with ``work``'s result on the main thread.
    on_error:
        Called with the raised exception on the main thread.  When omitted the
        failure is logged instead of being swallowed silently.
    on_finished:
        Called unconditionally after the outcome, on the main thread.

    Returns the :class:`~concurrent.futures.Future`, so callers can keep a
    handle (for example to cancel a superseded refresh).
    """
    future = _get_executor().submit(work)

    def _deliver() -> None:
        if future.cancelled():
            return
        exc = future.exception()
        if exc is not None:
            if on_error is not None:
                on_error(exc)
            else:
                logger.warning("Background task failed: %s", exc, exc_info=exc)
        elif on_done is not None:
            try:
                on_done(future.result())
            except Exception:
                logger.exception("Background completion handler raised")
        if on_finished is not None:
            try:
                on_finished()
            except Exception:
                logger.exception("Background completion callback raised")

    # Runs in the worker thread; post_to_ui hops it onto the Tk main thread.
    future.add_done_callback(lambda _finished: post_to_ui(ui, _deliver))
    return future


def shutdown_background_tasks(*, wait: bool = False) -> None:
    """Cancel queued work and stop the pool (called during app shutdown).

    In-flight tasks are *not* killed: a half-finished ``venv``/``pip`` run is
    worse than letting it finish, so the process waits only for work that has
    already started.  Everything still queued is cancelled.
    """
    global _executor
    with _executor_lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=wait, cancel_futures=True)
