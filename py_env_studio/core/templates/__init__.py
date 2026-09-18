"""Template engine for project scaffolding in Py Env Studio."""

from .builtin_templates import register_builtin_templates
from .engine import TemplateEngine, TemplateEngineError
from .models import TemplateCreationRequest, TemplateCreationResult, TemplateSpec
from .registry import TemplateRegistry, refresh_default_registry
from .github_import import (
    GitHubImportError,
    clone_github_repository,
    extract_github_repository_name,
    validate_github_repository_url,
)
from .user_template_store import (
    UserTemplateError,
    UserTemplateStore,
    generate_template_id,
    validate_template_id,
    validate_template_name,
)
from .workflow import ProjectCreationState, ProjectCreationStatus, TemplateCreationWorkflow
from .community import (
    CommunityTemplateCandidate,
    CommunityTemplateError,
    CommunityTemplateInspection,
    CommunityTemplateRateLimitError,
    CommunityTemplateService,
)

__all__ = [
    "TemplateCreationRequest",
    "TemplateCreationResult",
    "TemplateEngine",
    "TemplateEngineError",
    "TemplateRegistry",
    "TemplateSpec",
    "register_builtin_templates",
    "refresh_default_registry",
    "GitHubImportError",
    "clone_github_repository",
    "extract_github_repository_name",
    "validate_github_repository_url",
    "UserTemplateError",
    "UserTemplateStore",
    "generate_template_id",
    "validate_template_id",
    "validate_template_name",
    "ProjectCreationState",
    "ProjectCreationStatus",
    "TemplateCreationWorkflow",
    "CommunityTemplateCandidate",
    "CommunityTemplateError",
    "CommunityTemplateInspection",
    "CommunityTemplateRateLimitError",
    "CommunityTemplateService",
]
