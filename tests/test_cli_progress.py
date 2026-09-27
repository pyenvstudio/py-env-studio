"""Tests for the terminal progress gauge used by the CLI."""
from __future__ import annotations

import io
import logging
import threading
import time

import pytest

from py_env_studio.utils.progress import (
    FILLED,
    TaskProgress,
    task_progress,
)

PROGRESS_LOGGER = "py_env_studio.utils.progress"


def _messages(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == PROGRESS_LOGGER]


def test_disabled_gauge_writes_no_control_characters():
    stream = io.StringIO()
    with TaskProgress("Creating demo", 4, stream=stream, enabled=False) as progress:
        progress.note("running venv")
        progress.advance()
        progress.advance()
    assert stream.getvalue() == ""


def test_tty_gauge_draws_in_place_and_cleans_up():
    stream = io.StringIO()
    gauge = TaskProgress("Installing pkg", 2, stream=stream, enabled=True, bar_width=8)
    with gauge as progress:
        progress.note("Downloading wheels")
        progress.advance()
        drawn = stream.getvalue()
        assert "\r" in drawn and "[" in drawn and FILLED in drawn
        assert "Downloading wheels" in drawn
    final = stream.getvalue()
    # The last write wipes the line so the shell prompt starts clean.
    assert final.endswith("\r")
    assert final.split("\r")[-2].strip() == ""
    assert gauge.phase == "done"


def test_failure_cleans_up_and_propagates():
    stream = io.StringIO()
    gauge = TaskProgress("Boom", 2, stream=stream, enabled=True)
    with pytest.raises(ValueError):
        with gauge:
            raise ValueError("boom")
    assert gauge.phase == "failed"
    assert stream.getvalue().endswith("\r")
    assert stream.getvalue().split("\r")[-2].strip() == ""


def test_non_tty_logs_milestones_only(caplog):
    caplog.set_level(logging.INFO)
    stream = io.StringIO()
    with TaskProgress("Batch export", 4, stream=stream, enabled=False) as progress:
        for _ in range(4):
            progress.advance()
    messages = _messages(caplog)
    assert any("25%" in message for message in messages)
    assert any("50%" in message for message in messages)
    assert any("75%" in message for message in messages)
    # Completion is reported by the caller's own log line, not twice here.
    assert not any("100%" in message for message in messages)
    assert stream.getvalue() == ""


def test_note_lines_are_recorded_at_debug(caplog):
    caplog.set_level(logging.DEBUG)
    with TaskProgress("Installing requests", stream=io.StringIO(), enabled=False) as progress:
        progress.note("Collecting metadata")
    assert any("Collecting metadata" in message for message in _messages(caplog))


def test_over_advancing_clamps_to_hundred_percent():
    progress = TaskProgress("Clamping", 2, stream=io.StringIO(), enabled=False)
    progress.start()
    progress.advance(10)
    assert progress.fraction == 1.0


def test_set_fraction_on_unknown_total_becomes_determinate():
    progress = TaskProgress("Unknown", stream=io.StringIO(), enabled=False)
    progress.start()
    progress.set_fraction(0.5)
    assert progress.total == 1.0
    assert progress.fraction == 0.5


def test_indeterminate_gauge_starts_and_stops_its_ticker():
    progress = TaskProgress("Long operation", stream=io.StringIO(), enabled=True, tick=0.01)
    with progress:
        time.sleep(0.05)
        ticker = progress._ticker
        assert ticker is not None and ticker.is_alive()
    assert progress._ticker is None
    assert not any(
        thread.name == "pes-progress" and thread.is_alive()
        for thread in threading.enumerate()
    )


def test_no_progress_environment_variable_disables_gauge(monkeypatch):
    monkeypatch.setenv("PES_NO_PROGRESS", "1")
    assert TaskProgress("x", 1, stream=io.StringIO()).enabled is False


def test_progress_environment_variable_forces_gauge_on(monkeypatch):
    monkeypatch.setenv("PES_PROGRESS", "1")
    assert TaskProgress("x", 1, stream=io.StringIO()).enabled is True


def test_close_is_idempotent():
    stream = io.StringIO()
    progress = TaskProgress("Twice", 1, stream=stream, enabled=True)
    progress.start()
    progress.finish()
    progress.close()
    assert progress.phase == "done"


def test_factory_returns_a_usable_context_manager():
    stream = io.StringIO()
    with task_progress("Facts", 1, stream=stream, enabled=True) as progress:
        progress.advance()
    assert progress.phase == "done"
    assert progress.elapsed >= 0.0
