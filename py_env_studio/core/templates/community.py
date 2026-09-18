"""GitHub-backed discovery and safe static inspection for community templates."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .github_import import clone_github_repository, validate_github_repository_url
from .user_template_store import SourceInspectionResult, UserTemplateStore

logger = logging.getLogger(__name__)


class CommunityTemplateError(RuntimeError):
    """Raised when community template discovery or inspection fails."""


class CommunityTemplateRateLimitError(CommunityTemplateError):
    """Raised when the unauthenticated GitHub API limit is exhausted."""


@dataclass(frozen=True)
class CommunityTemplateCandidate:
    """Public metadata returned by a community template provider."""

    name: str
    full_name: str
    url: str
    description: str
    stars: int
    updated_at: str
    language: str | None
    license_name: str | None
    topics: list[str]
    default_branch: str | None


@dataclass(frozen=True)
class CommunityTemplateInspection:
    """Static, non-executing inspection result for one cloned repository."""

    candidate: CommunityTemplateCandidate
    source_dir: Path
    cleanup_dir: Path
    source_inspection: SourceInspectionResult
    readme_excerpt: str
    detected_files: list[str]
    has_python_project: bool
    has_tests: bool
    has_workflows: bool
    has_environment_files: bool


class CommunityTemplateService:
    """Discover GitHub candidates and inspect them as untrusted source data."""

    SEARCH_URL = "https://api.github.com/search/repositories"
    PAGE_SIZE = 20
    CACHE_SECONDS = 300
    CATEGORIES = (
        "All",
        "Python",
        "CLI",
        "Web",
        "FastAPI",
        "Django",
        "Data Science",
        "Machine Learning",
        "AI / GenAI",
        "Automation",
        "Package",
        "Other",
    )
    _CATEGORY_TOPICS = {
        "CLI": "cli",
        "Web": "web",
        "FastAPI": "fastapi",
        "Django": "django",
        "Data Science": "data-science",
        "Machine Learning": "machine-learning",
        "AI / GenAI": "generative-ai",
        "Automation": "automation",
        "Package": "python-package",
    }
    _SORTS = {
        "Popular": "stars",
        "Recently Updated": "updated",
        "Recently Added": "indexed",
    }

    def __init__(
        self,
        session: requests.Session | None = None,
        template_store: UserTemplateStore | None = None,
        timeout_seconds: int = 15,
    ) -> None:
        self._session = session or requests.Session()
        self._template_store = template_store or UserTemplateStore()
        self._timeout_seconds = timeout_seconds
        self._cache: dict[tuple[str, str, str, int], tuple[float, list[CommunityTemplateCandidate]]] = {}

    def search(
        self,
        query: str = "",
        category: str = "All",
        sort: str = "Popular",
        page: int = 1,
    ) -> list[CommunityTemplateCandidate]:
        """Return one page of GitHub repository candidates without cloning."""
        normalized_category = category if category in self.CATEGORIES else "All"
        normalized_sort = sort if sort in self._SORTS else "Popular"
        normalized_query = query.strip()
        normalized_page = max(1, int(page))
        key = (normalized_query.lower(), normalized_category, normalized_sort, normalized_page)

        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self.CACHE_SECONDS:
            return list(cached[1])

        params = {
            "q": self._build_query(normalized_query, normalized_category),
            "sort": self._SORTS[normalized_sort],
            "order": "desc",
            "per_page": self.PAGE_SIZE,
            "page": normalized_page,
        }
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        logger.info("Community template search started: query=%r category=%s page=%d", normalized_query, normalized_category, normalized_page)

        try:
            response = self._session.get(
                self.SEARCH_URL,
                params=params,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.warning("Community template search request failed: %s", exc)
            raise CommunityTemplateError("Unable to reach GitHub. Check your network connection and try again.") from exc

        if response.status_code in (403, 429):
            logger.warning("GitHub rate limit encountered during community template search")
            raise CommunityTemplateRateLimitError(
                "GitHub's request limit has been reached. Please wait a few minutes and try again."
            )
        if response.status_code != 200:
            logger.warning("GitHub community template search failed: status=%s", response.status_code)
            raise CommunityTemplateError(
                f"GitHub could not retrieve community templates (HTTP {response.status_code})."
            )

        try:
            payload = response.json()
            items = payload.get("items", [])
            if not isinstance(items, list):
                raise ValueError("items is not a list")
        except (TypeError, ValueError) as exc:
            logger.warning("GitHub community template response was invalid: %s", exc)
            raise CommunityTemplateError("GitHub returned an invalid community template response.") from exc

        candidates = [candidate for item in items if (candidate := self._candidate_from_item(item))]
        self._cache[key] = (time.monotonic(), candidates)
        logger.info("Community template search completed: results=%d", len(candidates))
        return list(candidates)

    def inspect(self, candidate: CommunityTemplateCandidate) -> CommunityTemplateInspection:
        """Clone and statically inspect a candidate; repository code is never executed."""
        logger.info("Community template inspection started: %s", candidate.full_name)
        temp_root = Path(tempfile.mkdtemp(prefix="pes-community-template-"))
        source_dir = temp_root / "repository"
        try:
            clone_github_repository(
                validate_github_repository_url(candidate.url),
                source_dir,
                log_callback=lambda message: logger.info("Community template %s: %s", candidate.full_name, message),
            )
            source_inspection = self._template_store.inspect_source(source_dir)
            paths = [path.as_posix() for path in source_inspection.included_files]
            root_files = {path.name.lower() for path in source_dir.iterdir() if path.is_file()}
            readme_excerpt = self._read_readme(source_dir)
            detected_files = self._detect_files(source_dir, paths)
            inspection = CommunityTemplateInspection(
                candidate=candidate,
                source_dir=source_dir,
                cleanup_dir=temp_root,
                source_inspection=source_inspection,
                readme_excerpt=readme_excerpt,
                detected_files=detected_files,
                has_python_project=("pyproject.toml" in root_files or "setup.py" in root_files or "setup.cfg" in root_files),
                has_tests=(source_dir / "tests").is_dir(),
                has_workflows=(source_dir / ".github" / "workflows").is_dir(),
                has_environment_files=bool(source_inspection.sensitive_files),
            )
            logger.info("Community template inspection completed: %s", candidate.full_name)
            return inspection
        except Exception:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise

    def find_existing_import(self, repository_url: str) -> str | None:
        """Return an existing user template ID for the same repository, if present."""
        return self._template_store.find_template_by_origin(repository_url)

    @staticmethod
    def cleanup_inspection(inspection: CommunityTemplateInspection) -> None:
        """Remove a temporary clone after preview is dismissed or saved."""
        shutil.rmtree(inspection.cleanup_dir, ignore_errors=True)

    def _build_query(self, query: str, category: str) -> str:
        terms = [query or "template", "language:Python"]
        topic = self._CATEGORY_TOPICS.get(category)
        if topic:
            terms.append(f"topic:{topic}")
        return " ".join(term for term in terms if term)

    @staticmethod
    def _candidate_from_item(item: Any) -> CommunityTemplateCandidate | None:
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        full_name = item.get("full_name")
        url = item.get("html_url")
        if not all(isinstance(value, str) and value for value in (name, full_name, url)):
            return None
        license_data = item.get("license") or {}
        topics = item.get("topics") or []
        return CommunityTemplateCandidate(
            name=name,
            full_name=full_name,
            url=url,
            description=item.get("description") or "No repository description provided.",
            stars=int(item.get("stargazers_count") or 0),
            updated_at=item.get("updated_at") or "Unknown",
            language=item.get("language"),
            license_name=license_data.get("spdx_id") or license_data.get("name") if isinstance(license_data, dict) else None,
            topics=[topic for topic in topics if isinstance(topic, str)][:12],
            default_branch=item.get("default_branch"),
        )

    @staticmethod
    def _read_readme(source_dir: Path, limit: int = 4000) -> str:
        for name in ("README.md", "README.rst", "README.txt", "readme.md"):
            path = source_dir / name
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8", errors="replace")[:limit]
                except OSError:
                    return ""
        return ""

    @staticmethod
    def _detect_files(source_dir: Path, included_paths: list[str]) -> list[str]:
        interesting = {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "tox.ini", "dockerfile"}
        detected = [path for path in included_paths if Path(path).name.lower() in interesting]
        requirements_dir = source_dir / "requirements"
        if requirements_dir.is_dir():
            detected.extend(path.as_posix() for path in requirements_dir.glob("*.txt"))
        return sorted(set(detected))[:50]
