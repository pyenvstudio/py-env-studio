"""Workflow state tracking for template project creation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from .engine import TemplateEngine
from .models import TemplateCreationRequest, TemplateCreationResult


class ProjectCreationStatus(str, Enum):
    IDLE = "idle"
    CREATING = "creating"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class ProjectCreationState:
    status: ProjectCreationStatus = ProjectCreationStatus.IDLE
    template_id: str = ""
    project_name: str = ""
    location: str = ""
    error_message: str = ""


class TemplateCreationWorkflow:
    """Small coordinator that tracks project creation state transitions."""

    def __init__(self, engine: TemplateEngine) -> None:
        self.engine = engine
        self.state = ProjectCreationState()

    def create_project(
        self,
        request: TemplateCreationRequest,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> TemplateCreationResult:
        self.state = ProjectCreationState(
            status=ProjectCreationStatus.CREATING,
            template_id=request.template_id,
            project_name=request.project_name,
            location=request.project_location,
        )
        try:
            result = self.engine.create_project(request, log_callback=log_callback)
            self.state.status = ProjectCreationStatus.SUCCESS
            self.state.error_message = ""
            return result
        except Exception as exc:
            self.state.status = ProjectCreationStatus.FAILED
            self.state.error_message = str(exc)
            raise
