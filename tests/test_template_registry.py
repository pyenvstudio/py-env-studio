from py_env_studio.core.templates import TemplateRegistry, register_builtin_templates
from py_env_studio.core.templates.models import TemplateFile, TemplateSpec
from py_env_studio.core.templates.registry import refresh_default_registry
import py_env_studio.core.templates.registry as registry_module


def test_registry_register_and_lookup() -> None:
    registry = TemplateRegistry()
    register_builtin_templates(registry)

    assert registry.contains("python-script")
    script = registry.get("python-script")
    assert script.name == "Python Script"


def test_registry_duplicate_registration_fails() -> None:
    registry = TemplateRegistry()
    register_builtin_templates(registry)

    template = registry.get("python-script")
    try:
        registry.register(template)
        assert False, "Expected duplicate registration to fail"
    except ValueError as exc:
        assert "already registered" in str(exc)


def test_registry_unknown_template_raises() -> None:
    registry = TemplateRegistry()
    register_builtin_templates(registry)

    try:
        registry.get("does-not-exist")
        assert False, "Expected unknown template lookup to fail"
    except KeyError as exc:
        assert "Unknown template id" in str(exc)


def test_default_registry_discovers_user_templates(monkeypatch) -> None:
    class FakeStore:
        def __init__(self):
            pass

        def load_user_templates(self):
            return [
                TemplateSpec(
                    id="my-user-template",
                    name="My User Template",
                    version="1.0.0",
                    description="user template",
                    supported_python_versions=["3.11"],
                    min_python="3.11",
                    architecture="imported",
                    style="custom",
                    included_tooling=[],
                    runtime_dependencies=[],
                    dev_dependencies=[],
                    structure_preview=["README.md"],
                    files=[TemplateFile(path="README.md", content="Hello")],
                    source="user",
                    variable_style="double_brace",
                )
            ]

    registry_module._default_registry = None
    monkeypatch.setattr(
        "py_env_studio.core.templates.user_template_store.UserTemplateStore",
        FakeStore,
    )
    registry = refresh_default_registry()
    assert registry.contains("python-script")
    assert registry.contains("my-user-template")
    registry_module._default_registry = None
