"""Template registry and discovery utilities."""

from __future__ import annotations

from typing import Dict, List

from .models import TemplateSpec


class TemplateRegistry:
    """Holds available project templates."""

    def __init__(self) -> None:
        self._templates: Dict[str, TemplateSpec] = {}

    def register(self, template: TemplateSpec) -> None:
        if template.id in self._templates:
            raise ValueError(f"Template id already registered: {template.id}")
        self._templates[template.id] = template

    def get(self, template_id: str) -> TemplateSpec:
        template = self._templates.get(template_id)
        if template is None:
            raise KeyError(f"Unknown template id: {template_id}")
        return template

    def list_all(self) -> List[TemplateSpec]:
        return sorted(self._templates.values(), key=lambda item: item.name.lower())

    def contains(self, template_id: str) -> bool:
        return template_id in self._templates


_default_registry: TemplateRegistry | None = None


def get_default_registry() -> TemplateRegistry:
    global _default_registry
    if _default_registry is None:
        from .builtin_templates import register_builtin_templates
        from .user_template_store import UserTemplateStore

        registry = TemplateRegistry()
        register_builtin_templates(registry)
        user_store = UserTemplateStore()
        for template in user_store.load_user_templates():
            if registry.contains(template.id):
                continue
            registry.register(template)
        _default_registry = registry
    return _default_registry


def refresh_default_registry() -> TemplateRegistry:
    global _default_registry
    _default_registry = None
    return get_default_registry()
