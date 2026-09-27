from pathlib import Path

import pytest
import requests

from py_env_studio.core.templates.community import (
    CommunityTemplateCandidate,
    CommunityTemplateError,
    CommunityTemplateRateLimitError,
    CommunityTemplateService,
)
from py_env_studio.core.templates.user_template_store import UserTemplateStore


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _candidate() -> CommunityTemplateCandidate:
    return CommunityTemplateCandidate(
        name="fastapi-starter",
        full_name="example/fastapi-starter",
        url="https://github.com/example/fastapi-starter",
        description="Starter project",
        stars=12,
        updated_at="2026-09-10T00:00:00Z",
        language="Python",
        license_name="MIT",
        topics=["fastapi", "template"],
        default_branch="main",
    )


def test_search_parses_github_candidates_and_caches() -> None:
    session = FakeSession(
        FakeResponse(
            200,
            {
                "items": [
                    {
                        "name": "fastapi-starter",
                        "full_name": "example/fastapi-starter",
                        "html_url": "https://github.com/example/fastapi-starter",
                        "description": "Starter project",
                        "stargazers_count": 12,
                        "updated_at": "2026-09-10T00:00:00Z",
                        "language": "Python",
                        "license": {"spdx_id": "MIT"},
                        "topics": ["fastapi", "template"],
                        "default_branch": "main",
                    }
                ]
            },
        )
    )
    service = CommunityTemplateService(session=session)

    results = service.search("FastAPI", category="FastAPI")
    cached_results = service.search("FastAPI", category="FastAPI")

    assert results == cached_results
    assert results[0].full_name == "example/fastapi-starter"
    assert len(session.calls) == 1
    params = session.calls[0][1]["params"]
    assert params["q"] == "FastAPI language:Python topic:fastapi"
    assert params["sort"] == "stars"


def test_search_handles_network_rate_limit_and_invalid_responses() -> None:
    unavailable = CommunityTemplateService(session=FakeSession(requests.RequestException("offline")))
    with pytest.raises(CommunityTemplateError, match="Unable to reach GitHub"):
        unavailable.search()

    limited = CommunityTemplateService(session=FakeSession(FakeResponse(403, {})))
    with pytest.raises(CommunityTemplateRateLimitError):
        limited.search()

    failed = CommunityTemplateService(session=FakeSession(FakeResponse(500, {})))
    with pytest.raises(CommunityTemplateError, match="HTTP 500"):
        failed.search()

    malformed = CommunityTemplateService(session=FakeSession(FakeResponse(200, {"items": "invalid"})))
    with pytest.raises(CommunityTemplateError, match="invalid"):
        malformed.search()

    empty = CommunityTemplateService(session=FakeSession(FakeResponse(200, {"items": []})))
    assert empty.search() == []


def test_inspection_is_static_and_reports_repository_signals(tmp_path: Path, monkeypatch) -> None:
    store = UserTemplateStore(base_dir=tmp_path / "templates")
    service = CommunityTemplateService(session=FakeSession(FakeResponse(200, {"items": []})), template_store=store)

    def fake_clone(_url: str, destination: Path, **_kwargs) -> Path:
        destination.mkdir(parents=True)
        (destination / "README.md").write_text("# FastAPI starter\n", encoding="utf-8")
        (destination / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        (destination / ".env").write_text("SECRET=not-imported\n", encoding="utf-8")
        (destination / "tests").mkdir()
        (destination / "tests" / "test_app.py").write_text("assert True\n", encoding="utf-8")
        (destination / ".github" / "workflows").mkdir(parents=True)
        (destination / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
        return destination

    monkeypatch.setattr("py_env_studio.core.templates.community.clone_github_repository", fake_clone)
    inspection = service.inspect(_candidate())

    assert inspection.has_python_project
    assert inspection.has_tests
    assert inspection.has_workflows
    assert inspection.has_environment_files
    assert "pyproject.toml" in inspection.detected_files
    assert inspection.readme_excerpt.startswith("# FastAPI")
    assert Path(".env") in inspection.source_inspection.sensitive_files
    assert Path(".github/workflows/ci.yml") in inspection.source_inspection.excluded_files

    service.cleanup_inspection(inspection)
    assert not inspection.cleanup_dir.exists()


def test_find_existing_import_uses_origin_identity(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("hello\n", encoding="utf-8")
    store = UserTemplateStore(base_dir=tmp_path / "templates")
    store.save_template(
        source_dir=source,
        template_name="FastAPI Starter",
        template_id="fastapi-starter",
        description="starter",
        author=None,
        version="1.0.0",
        category="Web/API",
        python_version="3.11",
        source_type="github",
        origin="https://github.com/example/fastapi-starter.git",
        reserved_template_ids=[],
    )
    service = CommunityTemplateService(template_store=store)

    assert service.find_existing_import("https://github.com/example/fastapi-starter") == "fastapi-starter"
