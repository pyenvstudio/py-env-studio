"""Py-Tonic guidance for practical Python environment best practices."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


MOST_USED_BEST_PRACTICES = [
    "Always use a dedicated virtual environment per project.",
    "Pin dependencies in requirements.txt to keep builds reproducible.",
    "Update key tooling (pip, setuptools, wheel) regularly.",
    "Scan dependencies for vulnerabilities before release.",
    "Use clear environment names that match project intent.",
]

PY_TONIC_TOPICS = ("core_python", "python_django")
PY_TONIC_NOTIFICATION_MODES = ("daily", "weekly", "manual")
PY_TONIC_LEARNING_MODES = ("strict", "learning")

_ACTION_ADVICE = {
    "general": {
        "notification": "Keep environments isolated and dependencies pinned.",
        "bad_example": "Installing packages globally and sharing one env across projects.",
        "recommended": "Create one environment per project and export pinned requirements.",
    },
    "create_env": {
        "notification": "Use descriptive environment names and explicit Python versions.",
        "bad_example": "Creating generic env names like test1 without tracking Python version.",
        "recommended": "Use names like api-py312 and verify interpreter before creation.",
    },
    "rename_env": {
        "notification": "Use consistent naming to simplify team collaboration.",
        "bad_example": "Switching names frequently with no naming rule.",
        "recommended": "Adopt a naming convention: project-purpose-pyversion.",
    },
    "delete_env": {
        "notification": "Export dependency lock info before deleting environments.",
        "bad_example": "Deleting an environment before capturing installed dependencies.",
        "recommended": "Run package export first, then delete unused environments.",
    },
    "activate_env": {
        "notification": "Activate the environment where project files actually live.",
        "bad_example": "Running tools in an unrelated working directory.",
        "recommended": "Open the project root and activate the matching environment.",
    },
    "install_package": {
        "notification": "Prefer pinned package versions for stable installs.",
        "bad_example": "Using unbounded installs like requests without version constraints.",
        "recommended": "Install specific versions and update requirements after changes.",
    },
    "uninstall_package": {
        "notification": "Review dependency impact before uninstalling a package.",
        "bad_example": "Removing shared dependencies blindly and breaking runtime.",
        "recommended": "Uninstall, then verify imports/tests and refresh dependency files.",
    },
    "update_package": {
        "notification": "Update packages in small batches and verify compatibility.",
        "bad_example": "Bulk updating everything without testing.",
        "recommended": "Update critical packages first and run checks after each update.",
    },
    "import_requirements": {
        "notification": "Validate requirements files before installing.",
        "bad_example": "Installing unknown requirements from outdated files.",
        "recommended": "Review and clean requirements before applying to an environment.",
    },
    "export_requirements": {
        "notification": "Export dependencies after meaningful package changes.",
        "bad_example": "Forgetting to export after updates and shipping stale pins.",
        "recommended": "Commit a fresh requirements.txt after dependency updates.",
    },
}

_TOPIC_HINTS = {
    "core_python": [
        "Remember import order and explicit dependencies.",
        "Prefer deterministic requirements for reproducible builds.",
        "Activate the exact venv tied to your project folder.",
    ],
    "python_django": [
        "Keep Django and plugins pinned in requirements.",
        "Run migrations only from the intended project environment.",
        "Protect settings and secrets via environment variables.",
    ],
}

_CHALLENGE_BANK = {
    "core_python": [
        {
            "id": "core-python-venv-import",
            "title": "Core Python: Fill Missing Import",
            "prompt": "Complete the missing import to use Path safely.",
            "partial_code": "___ pathlib import Path\nprint(Path('.').resolve())",
            "expected_answer": "from",
            "hint_steps": [
                "Python imports use the format: from module import symbol.",
                "The module here is pathlib.",
                "The missing keyword is one token.",
            ],
        },
        {
            "id": "core-python-pip-pin",
            "title": "Core Python: Pin Dependency",
            "prompt": "Fill the placeholder with a pinned package example.",
            "partial_code": "requirements_line = 'requests___'",
            "expected_answer": "==2.32.3",
            "hint_steps": [
                "Use double equals to pin versions.",
                "Pinned syntax is package==version.",
                "Complete only the missing suffix.",
            ],
        },
    ],
    "python_django": [
        {
            "id": "django-manage-command",
            "title": "Django: Fill Manage.py Command",
            "prompt": "Complete the command to create migrations.",
            "partial_code": "python manage.py ___",
            "expected_answer": "makemigrations",
            "hint_steps": [
                "This command generates migration files.",
                "It starts with the word 'make'.",
                "The full answer is one word.",
            ],
        },
        {
            "id": "django-runserver-port",
            "title": "Django: Fill Runserver Port",
            "prompt": "Complete the local server command for port 8000.",
            "partial_code": "python manage.py runserver ___",
            "expected_answer": "8000",
            "hint_steps": [
                "Default Django dev port is numeric.",
                "It is four digits.",
                "Use the standard default port.",
            ],
        },
    ],
}


def _profile_path():
    try:
        base = Path.home() / ".py_env_studio"
        base.mkdir(parents=True, exist_ok=True)
        return base / "py_tonic_profile.json"
    except Exception:
        return None


def default_py_tonic_profile():
    return {
        "notification_frequency": "daily",
        "mode": "learning",
        "topics": ["core_python"],
        "last_notified_at": None,
    }


def load_py_tonic_profile():
    path = _profile_path()
    if path is None:
        return default_py_tonic_profile()
    if not path.exists():
        profile = default_py_tonic_profile()
        save_py_tonic_profile(profile)
        return profile
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        profile = default_py_tonic_profile()
    return sanitize_py_tonic_profile(profile)


def sanitize_py_tonic_profile(profile):
    data = default_py_tonic_profile()
    if isinstance(profile, dict):
        data.update(profile)
    if data.get("notification_frequency") not in PY_TONIC_NOTIFICATION_MODES:
        data["notification_frequency"] = "daily"
    if data.get("mode") not in PY_TONIC_LEARNING_MODES:
        data["mode"] = "learning"
    topics = data.get("topics") or ["core_python"]
    valid_topics = [t for t in topics if t in PY_TONIC_TOPICS]
    data["topics"] = valid_topics or ["core_python"]
    return data


def save_py_tonic_profile(profile):
    clean = sanitize_py_tonic_profile(profile)
    path = _profile_path()
    if path is None:
        return clean
    try:
        path.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    except Exception:
        return clean
    return clean


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def should_notify(profile):
    freq = profile.get("notification_frequency", "daily")
    if freq == "manual":
        return False
    now = datetime.now()
    last_notified = _parse_iso(profile.get("last_notified_at"))
    # Always notify if never notified before (first time)
    if not last_notified:
        return True
    # For daily notifications, check if at least 1 day has passed
    if freq == "daily":
        return now - last_notified >= timedelta(days=1)
    # For weekly notifications, check if at least 7 days have passed
    elif freq == "weekly":
        return now - last_notified >= timedelta(days=7)
    return False


def mark_notified(profile):
    updated = sanitize_py_tonic_profile(profile.copy())
    updated["last_notified_at"] = datetime.now().isoformat()
    return save_py_tonic_profile(updated)


def get_random_challenge(profile):
    topics = profile.get("topics") or ["core_python"]
    pool = []
    for topic in topics:
        pool.extend(_CHALLENGE_BANK.get(topic, []))
    if not pool:
        pool = _CHALLENGE_BANK["core_python"]
    challenge = random.choice(pool).copy()
    challenge["topic"] = next(
        (topic for topic, items in _CHALLENGE_BANK.items() if any(x["id"] == challenge["id"] for x in items)),
        "core_python",
    )
    challenge["topic_hint"] = _TOPIC_HINTS.get(challenge["topic"], [])
    return challenge


def evaluate_challenge_answer(challenge, answer):
    expected = str(challenge.get("expected_answer", "")).strip().lower()
    actual = str(answer or "").strip().lower()
    return expected == actual


def get_py_tonic_advice(action="general"):
    """Return structured Py-Tonic advice for a specific action."""
    advice = _ACTION_ADVICE.get(action, _ACTION_ADVICE["general"]).copy()
    advice["most_used"] = MOST_USED_BEST_PRACTICES
    return advice
