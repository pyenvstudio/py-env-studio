"""Deterministic fixtures for the pes_check_consistency invocation probe.

Each scenario is a plain Python project containing exactly one kind of drift
between declared dependencies, resolved (lock) state, the installed
environment, and the interpreter. Nothing in this script calls PES, the MCP
server, the network, or a package manager: the trees are written straight to
disk so every experimental run starts from byte-identical state.

Usage (from the repository root):

    python experiments/consistency-probe/reset_scenarios.py --list
    python experiments/consistency-probe/reset_scenarios.py
    python experiments/consistency-probe/reset_scenarios.py -s s4-interpreter-mismatch
    python experiments/consistency-probe/reset_scenarios.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS_DIR = ROOT / "scenarios"

_PYPROJECT = (
    "[project]\n"
    "name = \"{name}\"\n"
    "version = \"0.1.0\"\n"
    "requires-python = \"{python}\"\n"
    "dependencies = [{dependencies}]\n"
    "\n"
    "[tool.pytest.ini_options]\n"
    "testpaths = [\"tests\"]\n"
)

_PYVENV = (
    "home = C:/Python\n"
    "include-system-site-packages = false\n"
    "version = {version}\n"
)


def _dist_info(name, version):
    return ".venv/Lib/site-packages/{}-{}.dist-info/METADATA".format(name, version)


def _metadata(name, version):
    return "Metadata-Version: 2.1\nName: {}\nVersion: {}\n".format(name, version)


def _test(source):
    header = (
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / \"src\"))\n"
        "\n"
    )
    return header + source


SCENARIOS = {
    "s1-declared-vs-installed": {
        "drift": "pyproject/requirements declare pandas==2.2.3; the environment has pandas 2.2.1",
        "task": "Add a to_markdown_rows helper to src/report/tables.py and run the tests.",
        "files": {
            "pyproject.toml": _PYPROJECT.format(
                name="orders-report", python=">=3.12", dependencies="\"pandas==2.2.3\""
            ),
            "requirements.txt": "pandas==2.2.3\n",
            _dist_info("pandas", "2.2.1"): _metadata("pandas", "2.2.1"),
            ".venv/pyvenv.cfg": _PYVENV.format(version="3.12.8"),
            "src/report/__init__.py": "",
            "src/report/tables.py": (
                "def totals(rows):\n"
                "    return sum(rows)\n"
            ),
            "tests/test_tables.py": _test(
                "from report.tables import totals\n"
                "\n"
                "\n"
                "def test_totals():\n"
                "    assert totals([1, 2, 3]) == 6\n"
            ),
        },
    },
    "s2-declared-vs-lock": {
        "drift": "pyproject/requirements allow httpx>=0.27; requirements.lock pins httpx==0.26.0",
        "task": "Give the retry helper in src/client.py a timeout argument and run the tests.",
        "files": {
            "pyproject.toml": _PYPROJECT.format(
                name="feed-client", python=">=3.12", dependencies="\"httpx>=0.27\""
            ),
            "requirements.txt": "httpx>=0.27\n",
            "requirements.lock": "httpx==0.26.0\n",
            _dist_info("httpx", "0.26.0"): _metadata("httpx", "0.26.0"),
            ".venv/pyvenv.cfg": _PYVENV.format(version="3.12.8"),
            "src/client.py": (
                "def build_url(base, path):\n"
                "    return base.rstrip(\"/\") + \"/\" + path.lstrip(\"/\")\n"
                "\n"
                "\n"
                "def retry(times, fn):\n"
                "    return [fn() for _ in range(times)]\n"
            ),
            "tests/test_client.py": _test(
                "from client import build_url, retry\n"
                "\n"
                "\n"
                "def test_build_url():\n"
                "    assert build_url(\"https://api/\", \"/v1\") == \"https://api/v1\"\n"
                "\n"
                "\n"
                "def test_retry():\n"
                "    assert retry(2, lambda: 7) == [7, 7]\n"
            ),
        },
    },
    "s3-lock-vs-installed": {
        "drift": "requirements.lock pins click==8.1.8; the environment has click 8.0.4",
        "task": "Add a --json flag to the argument handling in src/cli.py and run the tests.",
        "files": {
            "pyproject.toml": _PYPROJECT.format(
                name="task-cli", python=">=3.12", dependencies="\"click>=8.1\""
            ),
            "requirements.txt": "click>=8.1\n",
            "requirements.lock": "click==8.1.8\n",
            _dist_info("click", "8.0.4"): _metadata("click", "8.0.4"),
            ".venv/pyvenv.cfg": _PYVENV.format(version="3.12.8"),
            "src/cli.py": (
                "def parse_args(argv):\n"
                "    return {\"command\": argv[0] if argv else None}\n"
            ),
            "tests/test_cli.py": _test(
                "from cli import parse_args\n"
                "\n"
                "\n"
                "def test_parse_args():\n"
                "    assert parse_args([\"list\"])[\"command\"] == \"list\"\n"
            ),
        },
    },
    "s4-interpreter-mismatch": {
        "drift": ".python-version and pyproject require >=3.13; .venv/pyvenv.cfg reports 3.11.9",
        "task": "Refactor the chunk helper in src/batch.py to use itertools and run the tests.",
        "files": {
            "pyproject.toml": _PYPROJECT.format(
                name="batch-tool", python=">=3.13", dependencies=""
            ),
            ".python-version": "3.13\n",
            ".venv/pyvenv.cfg": _PYVENV.format(version="3.11.9"),
            "src/batch.py": (
                "def chunk(rows, size):\n"
                "    return [rows[i:i + size] for i in range(0, len(rows), size)]\n"
            ),
            "tests/test_batch.py": _test(
                "from batch import chunk\n"
                "\n"
                "\n"
                "def test_chunk():\n"
                "    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]\n"
            ),
        },
    },
    "s5-combined-drift": {
        "drift": (
            "pyproject declares django>=5.1 with requires-python >=3.12; "
            "requirements.lock pins django==5.0.6; .venv reports 3.11.9 and has django 5.0.1"
        ),
        "task": "Add an async view to src/views.py and run the tests.",
        "files": {
            "pyproject.toml": _PYPROJECT.format(
                name="survey-app", python=">=3.12", dependencies="\"django>=5.1\""
            ),
            "requirements.txt": "django>=5.1\n",
            "requirements.lock": "django==5.0.6\n",
            ".python-version": "3.12\n",
            _dist_info("django", "5.0.1"): _metadata("django", "5.0.1"),
            ".venv/pyvenv.cfg": _PYVENV.format(version="3.11.9"),
            "src/views.py": (
                "def view(request):\n"
                "    return {\"status\": 200, \"request\": request}\n"
            ),
            "tests/test_views.py": _test(
                "from views import view\n"
                "\n"
                "\n"
                "def test_view():\n"
                "    assert view(\"/\")[\"status\"] == 200\n"
            ),
        },
    },
}


def scenario_names():
    # type: () -> list
    return list(SCENARIOS)


def reset(name):
    # type: (str) -> Path
    """Recreate one scenario tree from scratch (idempotent, no side effects)."""
    target = SCENARIOS_DIR / name
    if target.exists():
        shutil.rmtree(target)
    for relative, text in sorted(SCENARIOS[name]["files"].items()):
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return target


def digest(name):
    # type: (str) -> str
    """Content digest of a scenario tree (proves resets are byte-identical)."""
    target = SCENARIOS_DIR / name
    hasher = hashlib.sha256()
    for path in sorted(p for p in target.rglob("*") if p.is_file()):
        relative = str(path.relative_to(target)).replace("\\", "/")
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def main(argv=None):
    # type: (list) -> int
    parser = argparse.ArgumentParser(
        description="Reset the five drift scenarios used by the PES invocation probe."
    )
    parser.add_argument("-s", "--scenario", action="append", choices=scenario_names(),
                        help="reset only this scenario (repeatable)")
    parser.add_argument("--verify", action="store_true",
                        help="reset each scenario twice and compare digests")
    parser.add_argument("--list", action="store_true",
                        help="list scenarios with their drift and task prompt")
    args = parser.parse_args(argv)

    if args.list:
        for name in scenario_names():
            print(name)
            print("  drift: {}".format(SCENARIOS[name]["drift"]))
            print("  task : {}".format(SCENARIOS[name]["task"]))
        return 0

    names = args.scenario or scenario_names()

    if args.verify:
        first = {}
        second = {}
        for name in names:
            reset(name)
            first[name] = digest(name)
        for name in names:
            reset(name)
            second[name] = digest(name)
        stable = first == second
        for name in names:
            state = "stable" if first[name] == second[name] else "UNSTABLE"
            print("{}: {} {}".format(name, state, first[name][:16]))
        print("verify: {}".format("PASS" if stable else "FAIL"))
        return 0 if stable else 1

    for name in names:
        target = reset(name)
        print("reset {} -> {} (sha256 {})".format(name, target, digest(name)[:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
