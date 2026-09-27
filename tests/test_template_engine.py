from pathlib import Path

import pytest

from py_env_studio.core.templates import TemplateCreationRequest, TemplateEngine
from py_env_studio.core.templates.models import TemplateFile, TemplateSpec
from py_env_studio.core.templates.registry import TemplateRegistry
from py_env_studio.core.templates.validator import TemplateValidationError


PLACEHOLDERS = [
    "{project_name}",
    "{module_name}",
    "{distribution_name}",
    "{python_version}",
    "{python_tag}",
    "{cli_command_name}",
    "{author}",
    "{year}",
]


def _base_request(template_id: str, root: Path, name: str = "demo-project") -> TemplateCreationRequest:
    return TemplateCreationRequest(
        template_id=template_id,
        project_name=name,
        project_location=str(root),
        python_version="3.11",
        create_virtual_environment=False,
        initialize_git=False,
        package_name=None,
        cli_command_name=None,
        author="Template Tester",
        license_name="MIT",
    )


@pytest.mark.parametrize(
    "template_id,expected_files",
    [
        ("python-script", ["src/demo_project/main.py", "tests/test_main.py", "pyproject.toml"]),
        ("python-cli", ["src/demo_project/cli.py", "tests/test_cli.py", "pyproject.toml"]),
        ("python-package", ["src/demo_project/example.py", "tests/test_example.py", "pyproject.toml"]),
    ],
)
def test_generate_phase1_templates(template_id: str, expected_files: list[str], tmp_path: Path) -> None:
    engine = TemplateEngine()
    request = _base_request(template_id=template_id, root=tmp_path)

    result = engine.create_project(request)

    assert result.project_path.exists()
    for rel_path in expected_files:
        assert (result.project_path / rel_path).exists()

    for py_file in result.project_path.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        compile(source, str(py_file), "exec")
        for placeholder in PLACEHOLDERS:
            assert placeholder not in source, f"Unrendered placeholder found in {py_file}"


def test_variable_substitution_in_readme(tmp_path: Path) -> None:
    engine = TemplateEngine()
    request = _base_request(template_id="python-script", root=tmp_path, name="alpha project")

    result = engine.create_project(request)
    readme = (result.project_path / "README.md").read_text(encoding="utf-8")

    assert "alpha project" in readme
    assert "{project_name}" not in readme


def test_existing_directory_handling(tmp_path: Path) -> None:
    engine = TemplateEngine()
    target = tmp_path / "demo-project"
    target.mkdir(parents=True)
    (target / "existing.txt").write_text("x", encoding="utf-8")

    request = _base_request(template_id="python-script", root=tmp_path)

    with pytest.raises(TemplateValidationError):
        engine.create_project(request)


def test_invalid_project_name_handling(tmp_path: Path) -> None:
    engine = TemplateEngine()
    request = _base_request(template_id="python-script", root=tmp_path, name="*")

    with pytest.raises(TemplateValidationError):
        engine.create_project(request)


def test_environment_and_dependency_integration(tmp_path: Path, monkeypatch) -> None:
    engine = TemplateEngine()
    request = TemplateCreationRequest(
        template_id="python-cli",
        project_name="cli-demo",
        project_location=str(tmp_path),
        python_version="3.11",
        create_virtual_environment=True,
        initialize_git=False,
        package_name="cli_demo",
        cli_command_name="clidemo",
        author="Template Tester",
        license_name="MIT",
    )

    created_envs: list[str] = []
    installed_deps: list[str] = []

    def fake_list_pythons():
        return ["/usr/bin/python3.11"]

    def fake_detect_version(path: str):
        return "Python 3.11.9"

    def fake_create_env(name, python_path=None, upgrade_pip=False, log_callback=None):
        created_envs.append(name)

    def fake_install_package(env_name, package, log_callback=None):
        installed_deps.append(package)

    monkeypatch.setattr("py_env_studio.core.templates.engine.env_manager.list_pythons", fake_list_pythons)
    monkeypatch.setattr("py_env_studio.core.templates.engine.env_manager.is_valid_python_version_detected", fake_detect_version)
    monkeypatch.setattr("py_env_studio.core.templates.engine.env_manager.create_env", fake_create_env)
    monkeypatch.setattr("py_env_studio.core.templates.engine.package_manager.install_package", fake_install_package)
    monkeypatch.setattr("py_env_studio.core.runtime_toggle.save_project_metadata", lambda *args, **kwargs: None)

    result = engine.create_project(request)

    assert created_envs
    assert result.created_environment_name == created_envs[0]
    assert "pytest>=8.0" in installed_deps
    assert "mypy>=1.10" in installed_deps


def test_user_template_double_brace_rendering(tmp_path: Path) -> None:
    registry = TemplateRegistry()
    registry.register(
        TemplateSpec(
            id="user-template",
            name="User Template",
            version="1.0.0",
            description="User custom template",
            supported_python_versions=["3.11"],
            min_python="3.11",
            architecture="imported",
            style="custom",
            included_tooling=[],
            runtime_dependencies=[],
            dev_dependencies=[],
            structure_preview=["README.md"],
            files=[
                TemplateFile(path="README.md", content="Project {{ project_name }}"),
                TemplateFile(path="src/{{ module_name }}/__init__.py", content="name = '{{ project_name }}'\n"),
                    TemplateFile(path="pyproject.toml", content="[project]\nname='demo'\nversion='0.1.0'\n"),
            ],
            source="user",
            variable_style="double_brace",
        )
    )

    engine = TemplateEngine(registry=registry)
    request = TemplateCreationRequest(
        template_id="user-template",
        project_name="my user app",
        project_location=str(tmp_path),
        python_version="3.11",
        create_virtual_environment=False,
        initialize_git=False,
    )

    result = engine.create_project(request)
    readme = (result.project_path / "README.md").read_text(encoding="utf-8")
    assert "Project my user app" in readme
    assert "{{ project_name }}" not in readme
    assert (result.project_path / "src" / "my_user_app" / "__init__.py").exists()
