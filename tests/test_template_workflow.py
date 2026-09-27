from pathlib import Path

import pytest

from py_env_studio.core.templates import TemplateCreationRequest, TemplateCreationResult, TemplateEngine
from py_env_studio.core.templates.workflow import ProjectCreationStatus, TemplateCreationWorkflow


class SuccessfulEngine(TemplateEngine):
    def __init__(self) -> None:
        pass

    def create_project(self, request, log_callback=None):
        return TemplateCreationResult(
            template_id=request.template_id,
            project_path=Path(request.project_location) / request.project_name,
        )


class FailingEngine(TemplateEngine):
    def __init__(self) -> None:
        pass

    def create_project(self, request, log_callback=None):
        raise RuntimeError("simulated failure")


def _request(tmp_path: Path) -> TemplateCreationRequest:
    return TemplateCreationRequest(
        template_id="python-script",
        project_name="demo",
        project_location=str(tmp_path),
        python_version="3.11",
        create_virtual_environment=False,
        initialize_git=False,
    )


def test_workflow_success_state(tmp_path: Path) -> None:
    workflow = TemplateCreationWorkflow(SuccessfulEngine())
    result = workflow.create_project(_request(tmp_path))

    assert workflow.state.status == ProjectCreationStatus.SUCCESS
    assert result.project_path.name == "demo"


def test_workflow_failure_state(tmp_path: Path) -> None:
    workflow = TemplateCreationWorkflow(FailingEngine())

    with pytest.raises(RuntimeError):
        workflow.create_project(_request(tmp_path))

    assert workflow.state.status == ProjectCreationStatus.FAILED
    assert "simulated failure" in workflow.state.error_message
