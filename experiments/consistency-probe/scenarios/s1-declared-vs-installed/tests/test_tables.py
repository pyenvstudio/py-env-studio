import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from report.tables import totals


def test_totals():
    assert totals([1, 2, 3]) == 6
