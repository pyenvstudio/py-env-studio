import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from views import view


def test_view():
    assert view("/")["status"] == 200
