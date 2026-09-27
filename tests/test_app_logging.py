"""Tests for the shared logging setup (file, console, GUI queue sinks)."""
from __future__ import annotations

import io
import logging
import queue
from unittest.mock import patch

import pytest

from py_env_studio.utils.app_logging import (
    CONSOLE_TAG,
    FILE_TAG,
    UI_TAG,
    configure_logging,
    resolve_verbosity,
)


@pytest.fixture(autouse=True)
def restore_root_logging():
    """Snapshot the root logger so tests never leak handlers into others."""
    root = logging.getLogger()
    before_handlers = list(root.handlers)
    before_level = root.level
    yield
    for handler in list(root.handlers):
        if handler not in before_handlers:
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
    for handler in before_handlers:
        if handler not in root.handlers:
            root.addHandler(handler)
    root.setLevel(before_level)


def _tagged(tag: str) -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_pes_tag", None) == tag
    ]


def test_configures_file_and_console_sinks(tmp_path):
    stream = io.StringIO()
    summary = configure_logging("info", log_file=tmp_path / "pes.log", console_stream=stream)

    assert summary["verbosity"] == "info"
    assert len(_tagged(FILE_TAG)) == 1
    assert len(_tagged(CONSOLE_TAG)) == 1

    logger = logging.getLogger("py_env_studio.demo")
    logger.info("environment created")
    assert "environment created" in stream.getvalue()

    logger.debug("worker detail")
    file_text = (tmp_path / "pes.log").read_text(encoding="utf-8")
    assert "worker detail" in file_text
    assert "environment created" in file_text


def test_reconfiguring_updates_levels_without_duplicating(tmp_path):
    configure_logging("info", log_file=tmp_path / "same.log", console_stream=io.StringIO())
    file_handler = _tagged(FILE_TAG)[0]

    configure_logging("debug", log_file=tmp_path / "same.log", console_stream=io.StringIO())

    assert len(_tagged(FILE_TAG)) == 1
    assert len(_tagged(CONSOLE_TAG)) == 1
    assert _tagged(FILE_TAG)[0] is file_handler  # reused, not re-created
    assert _tagged(CONSOLE_TAG)[0].level == logging.DEBUG


def test_upgrades_import_time_file_handler(tmp_path):
    """env_manager's import-time basicConfig must not double-write the file."""
    log_file = tmp_path / "legacy.log"
    legacy = logging.FileHandler(log_file)
    legacy.setLevel(logging.INFO)
    logging.getLogger().addHandler(legacy)

    configure_logging("info", log_file=log_file, console=False)

    same_path = [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, logging.FileHandler)
        and str(handler.baseFilename) == str(log_file)
    ]
    assert len(same_path) == 1
    assert same_path[0] is not legacy
    assert getattr(same_path[0], "_pes_tag", None) == FILE_TAG


def test_console_survives_a_stream_that_cannot_encode_the_message(tmp_path):
    """A cp1252 console must not lose ✓/✗ records to a UnicodeEncodeError.

    ``logging`` reports a failing handler with a ``--- Logging error ---``
    traceback and drops the record, which is exactly what happened on a Windows
    console for "✓ Executed on_app_start hook".
    """
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252")
    logging_errors: list[logging.LogRecord] = []

    configure_logging("info", log_file=tmp_path / "cp1252.log", console_stream=stream)

    with patch.object(logging.Handler, "handleError", lambda self, record: logging_errors.append(record)):
        logger = logging.getLogger("py_env_studio.demo")
        logger.info("✓ Executed on_app_start hook for all plugins")
        logger.error("✗ Failed to auto-load plugin 'sample_plugin2'")
    stream.flush()

    printed = raw.getvalue().decode("cp1252")
    assert logging_errors == []
    assert "Executed on_app_start hook for all plugins" in printed
    assert "Failed to auto-load plugin 'sample_plugin2'" in printed
    # The glyph itself is kept as an escape instead of being dropped.
    assert "\\u2713" in printed
    assert "\\u2717" in printed


def test_console_writes_plain_ascii_unchanged(tmp_path):
    stream = io.StringIO()
    configure_logging("info", log_file=tmp_path / "ascii.log", console_stream=stream)

    logging.getLogger("py_env_studio.demo").warning("plain warning")

    assert stream.getvalue().strip().endswith("plain warning")


def test_quiet_forwards_errors_but_not_warnings(tmp_path):
    stream = io.StringIO()
    configure_logging("quiet", log_file=tmp_path / "quiet.log", console_stream=stream)
    logger = logging.getLogger("py_env_studio.demo")
    logger.warning("hidden warning")
    logger.error("shown error")
    assert "hidden warning" not in stream.getvalue()
    assert "shown error" in stream.getvalue()


def test_ui_queue_receives_warnings_and_errors_only(tmp_path):
    log_queue: queue.Queue = queue.Queue()
    configure_logging("info", log_file=tmp_path / "ui.log", console=False, ui_queue=log_queue)
    logger = logging.getLogger("py_env_studio.demo")
    logger.info("mirrored twice? no")
    logger.warning("needs the on-screen console")

    drained = []
    while not log_queue.empty():
        drained.append(log_queue.get_nowait())
    assert not any("mirrored twice?" in message for message in drained)
    assert any("needs the on-screen console" in message for message in drained)


def test_console_can_be_disabled(tmp_path):
    configure_logging("info", log_file=tmp_path / "silent.log", console=False)
    assert _tagged(CONSOLE_TAG) == []


@pytest.mark.parametrize(
    "explicit,expected",
    [
        ("debug", "debug"),
        ("info", "info"),
        ("warn", "warning"),
        ("silent", "quiet"),
        ("nonsense", "info"),
        (None, "info"),
    ],
)
def test_resolve_verbosity_normalises_names(monkeypatch, explicit, expected):
    monkeypatch.delenv("PES_LOG_LEVEL", raising=False)
    assert resolve_verbosity(explicit) == expected


def test_resolve_verbosity_reads_environment(monkeypatch):
    monkeypatch.setenv("PES_LOG_LEVEL", "WARN")
    assert resolve_verbosity(None) == "warning"
    assert resolve_verbosity("debug") == "debug"  # explicit value wins
