import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cli import parse_args


def test_parse_args():
    assert parse_args(["list"])["command"] == "list"
