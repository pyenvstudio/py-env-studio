"""Tests for the CLI's output/verbosity options and progress wiring."""
from __future__ import annotations

import argparse
import logging

import pytest

from py_env_studio import commands


def test_parser_accepts_output_flags():
    args = commands.build_parser().parse_args(["-v", "--no-progress", "--list"])
    assert args.verbose is True
    assert args.no_progress is True
    assert args.list is True


def test_verbosity_flag_after_subcommand_parses():
    args = commands.build_parser().parse_args(["status", "-v"])
    assert args.verbose is True


def test_subparser_default_does_not_clobber_earlier_flag():
    # argparse subparser defaults overwrite values parsed before the
    # subcommand unless the option uses SUPPRESS.
    args = commands.build_parser().parse_args(["-v", "status"])
    assert args.verbose is True


def test_quiet_wins_over_verbose():
    args = commands.build_parser().parse_args(["-v", "-q", "--list"])
    assert commands._verbosity_from_args(args) == "error"


def test_verbosity_from_args_reports_none_by_default():
    args = commands.build_parser().parse_args(["--list"])
    assert commands._verbosity_from_args(args) is None


def test_extract_verbosity_pops_leading_flags_only():
    verbosity, rest = commands._extract_verbosity(["-v", "--create", "demo"])
    assert verbosity == "debug"
    assert rest == ["--create", "demo"]

    verbosity, rest = commands._extract_verbosity(["-v", "-q", "status"])
    assert verbosity == "error"
    assert rest == ["status"]

    verbosity, rest = commands._extract_verbosity(["status"])
    assert verbosity is None
    assert rest == ["status"]


def test_bar_honours_no_progress_flag(monkeypatch):
    monkeypatch.setenv("PES_PROGRESS", "1")
    enabled_args = argparse.Namespace(no_progress=False)
    disabled_args = argparse.Namespace(no_progress=True)
    assert commands._bar(enabled_args, "Task", 1).enabled is True
    assert commands._bar(disabled_args, "Task", 1).enabled is False


def test_bar_honours_no_progress_environment(monkeypatch):
    monkeypatch.setenv("PES_NO_PROGRESS", "1")
    args = argparse.Namespace(no_progress=False)
    assert commands._bar(args, "Task").enabled is False


def test_bar_defaults_to_stream_detection(monkeypatch):
    import sys

    monkeypatch.delenv("PES_NO_PROGRESS", raising=False)
    monkeypatch.delenv("PES_PROGRESS", raising=False)
    progress = commands._bar(argparse.Namespace(no_progress=False), "Task", 2)
    assert progress.enabled is bool(sys.stderr.isatty())


def _run_main(monkeypatch, caplog, argv, dispatch):
    """Run ``main`` with bootstrap/logging side effects stubbed out."""
    monkeypatch.setattr(commands, "configure_logging", lambda *a, **k: None)
    monkeypatch.setattr(commands, "initialize_app_runtime", lambda: None)
    monkeypatch.setattr(commands, "dispatch_command", dispatch)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(SystemExit) as exc:
            commands.main(argv)
    return exc.value.code, [
        record for record in caplog.records if record.levelno >= logging.ERROR
    ]


def test_main_does_not_repeat_an_error_already_logged(monkeypatch, caplog):
    # The failing layer (e.g. pip_tools) reports the specific cause; the
    # catch-all in main must not add a second, vaguer ERROR line for it.
    def dispatch(args):
        logging.getLogger("test.inner").error("inner failure detail")
        raise RuntimeError("boom")

    code, errors = _run_main(monkeypatch, caplog, ["--list"], dispatch)
    assert code == 1
    assert len(errors) == 1
    assert "inner failure detail" in errors[0].getMessage()


def test_main_reports_a_failure_that_nothing_else_logged(monkeypatch, caplog):
    def dispatch(args):
        raise RuntimeError("boom")

    code, errors = _run_main(monkeypatch, caplog, ["--list"], dispatch)
    assert code == 1
    assert len(errors) == 1
    assert errors[0].getMessage() == "RuntimeError: boom"


def test_error_marker_only_trips_on_error_level():
    marker = commands._ErrorMarker()
    logger = logging.getLogger("test.marker")
    logger.setLevel(logging.DEBUG)  # don't rely on root's level here
    logger.addHandler(marker)
    try:
        logger.info("just chatter")
        assert marker.seen is False
        logger.error("a real failure")
        assert marker.seen is True
    finally:
        logger.removeHandler(marker)
        logger.setLevel(logging.NOTSET)
