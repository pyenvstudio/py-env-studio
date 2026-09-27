import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from client import build_url, retry


def test_build_url():
    assert build_url("https://api/", "/v1") == "https://api/v1"


def test_retry():
    assert retry(2, lambda: 7) == [7, 7]
