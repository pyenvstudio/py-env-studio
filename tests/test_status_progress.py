"""Tests for the fixed status-bar gauge coordinator (UI-independent logic)."""
from __future__ import annotations

import threading

from py_env_studio.ui.status_bar import (
    STATE_DONE,
    STATE_ERROR,
    STATE_IDLE,
    STATE_WORKING,
    ProgressCoordinator,
)


class FakeClock:
    """Deterministic monotonic clock so retention windows are testable."""

    def __init__(self, start: float = 100.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_idle_snapshot_reports_ready():
    snapshot = ProgressCoordinator(clock=FakeClock()).snapshot()
    assert snapshot["state"] == STATE_IDLE
    assert snapshot["label"] == "Ready"
    assert snapshot["fraction"] == 0.0
    assert snapshot["percent"] == "0%"
    assert snapshot["show_gauge"] is False


def test_gauge_is_shown_only_while_a_task_runs():
    clock = FakeClock()
    coordinator = ProgressCoordinator(clock=clock, retain_seconds=4.0)
    assert coordinator.snapshot()["show_gauge"] is False  # idle: no widgets

    token = coordinator.begin("Installing requests", total=1)
    assert coordinator.snapshot()["show_gauge"] is True  # running

    coordinator.finish(token, "Installed requests", ok=True)
    assert coordinator.snapshot()["show_gauge"] is False  # over: bar disappears

    clock.advance(4.5)  # retention window ends
    assert coordinator.snapshot()["show_gauge"] is False


def test_gauge_hides_after_a_failure_too():
    coordinator = ProgressCoordinator(clock=FakeClock())
    token = coordinator.begin("Installing broken-package")
    coordinator.finish(token, "Installing broken-package failed: 404", ok=False)
    assert coordinator.snapshot()["show_gauge"] is False


def test_stacked_sessions_keep_the_gauge_up_until_the_last_one_finishes():
    coordinator = ProgressCoordinator(clock=FakeClock())
    lower = coordinator.begin("Long batch update", total=3)
    upper = coordinator.begin("Quick install")
    coordinator.finish(upper, "Quick install done", ok=True)
    assert coordinator.snapshot()["show_gauge"] is True  # lower still running

    coordinator.finish(lower, "Batch update done", ok=True)
    assert coordinator.snapshot()["show_gauge"] is False


def test_unknown_total_animates_with_placeholder_percent():
    coordinator = ProgressCoordinator(clock=FakeClock())
    coordinator.begin("Creating environment 'demo'")
    snapshot = coordinator.snapshot()
    assert snapshot["state"] == STATE_WORKING
    assert snapshot["fraction"] is None
    assert snapshot["percent"] == "···"
    assert snapshot["label"] == "Creating environment 'demo'"


def test_determinate_progress_reports_real_percent():
    coordinator = ProgressCoordinator(clock=FakeClock())
    token = coordinator.begin("Updating 4 packages", total=4)
    coordinator.update(token=token, done=1)
    assert coordinator.snapshot()["percent"] == "25%"
    coordinator.update(token=token, done=4)
    snapshot = coordinator.snapshot()
    assert snapshot["fraction"] == 1.0
    assert snapshot["percent"] == "100%"


def test_done_is_clamped_to_total():
    coordinator = ProgressCoordinator(clock=FakeClock())
    token = coordinator.begin("Work", total=2)
    coordinator.update(token=token, done=99)
    assert coordinator.snapshot()["fraction"] == 1.0


def test_fraction_update_synthesises_a_total():
    coordinator = ProgressCoordinator(clock=FakeClock())
    coordinator.begin("Cloning repository")
    coordinator.update(fraction=0.45)
    snapshot = coordinator.snapshot()
    assert snapshot["fraction"] == 0.45
    assert snapshot["percent"] == "45%"


def test_worker_status_line_becomes_the_detail():
    coordinator = ProgressCoordinator(clock=FakeClock())
    token = coordinator.begin("Installing requests")
    coordinator.update(token=token, status="Collecting requests")
    snapshot = coordinator.snapshot()
    assert snapshot["detail"] == "Collecting requests"


def test_status_without_session_updates_idle_activity():
    coordinator = ProgressCoordinator(clock=FakeClock())
    coordinator.set_status("3 environments listed")
    snapshot = coordinator.snapshot()
    assert snapshot["state"] == STATE_IDLE
    assert snapshot["label"] == "3 environments listed"


def test_success_is_retained_then_returns_to_idle():
    clock = FakeClock()
    coordinator = ProgressCoordinator(clock=clock, retain_seconds=4.0)
    token = coordinator.begin("Deleting environment 'old'")
    coordinator.finish(token, "Environment 'old' deleted", ok=True)
    snapshot = coordinator.snapshot()
    assert snapshot["state"] == STATE_DONE
    assert snapshot["percent"] == "100%"
    assert snapshot["label"] == "Environment 'old' deleted"

    clock.advance(4.5)
    idle = coordinator.snapshot()
    assert idle["state"] == STATE_IDLE
    assert idle["label"] == "Environment 'old' deleted"  # keeps last activity


def test_failure_state_uses_error_percent():
    coordinator = ProgressCoordinator(clock=FakeClock())
    token = coordinator.begin("Installing broken-package")
    coordinator.finish(token, "Installing broken-package failed: 404", ok=False)
    snapshot = coordinator.snapshot()
    assert snapshot["state"] == STATE_ERROR
    assert snapshot["percent"] == "✕"
    assert snapshot["fraction"] == 1.0


def test_stacked_sessions_reveal_the_lower_one():
    coordinator = ProgressCoordinator(clock=FakeClock())
    lower = coordinator.begin("Long batch update", total=3)
    upper = coordinator.begin("Quick install")
    assert coordinator.snapshot()["label"] == "Quick install"

    coordinator.finish(upper, "Quick install done", ok=True)
    revealed = coordinator.snapshot()
    assert revealed["state"] == STATE_WORKING
    assert revealed["token"] == lower


def test_finishing_an_unknown_token_is_ignored():
    coordinator = ProgressCoordinator(clock=FakeClock())
    token = coordinator.begin("Task")
    coordinator.finish(token + 99, "not mine", ok=True)
    snapshot = coordinator.snapshot()
    assert snapshot["state"] == STATE_WORKING
    assert coordinator.active_count == 1


def test_update_targets_top_session_without_a_token():
    coordinator = ProgressCoordinator(clock=FakeClock())
    coordinator.begin("First", total=10)
    coordinator.update(done=5)  # no token: applies to the newest session
    assert coordinator.snapshot()["fraction"] == 0.5


def test_concurrent_updates_are_not_lost():
    coordinator = ProgressCoordinator(clock=FakeClock())
    token = coordinator.begin("Eight workers", total=800)

    def _worker() -> None:
        for _ in range(100):
            coordinator.update(token=token, steps=1)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert coordinator.active_count == 1
    assert coordinator.snapshot()["fraction"] == 1.0
