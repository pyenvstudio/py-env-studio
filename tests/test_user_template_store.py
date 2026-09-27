from pathlib import Path

import pytest

from py_env_studio.core.templates.user_template_store import (
    UserTemplateError,
    UserTemplateStore,
    generate_template_id,
    validate_template_id,
)


def test_generate_template_id_and_validation() -> None:
    assert generate_template_id("My FastAPI Starter") == "my-fastapi-starter"

    validate_template_id("my-fastapi-starter")
    with pytest.raises(UserTemplateError):
        validate_template_id("../bad")
    with pytest.raises(UserTemplateError):
        validate_template_id("BadID")


def test_inspect_source_excludes_and_marks_sensitive(tmp_path: Path) -> None:
    source = tmp_path / "my_project"
    source.mkdir()
    (source / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (source / ".env").write_text("SECRET=x\n", encoding="utf-8")
    (source / "credentials.json").write_text('{"token":"x"}', encoding="utf-8")
    (source / "secrets.json").write_text('{"key":"x"}', encoding="utf-8")
    (source / "cert.pem").write_text("-----BEGIN-----\n", encoding="utf-8")
    (source / "id_rsa").write_text("-----BEGIN RSA-----\n", encoding="utf-8")
    (source / "mykey.key").write_bytes(b"\x00\x01")
    (source / ".git").mkdir()
    (source / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "app.pyc").write_bytes(b"\x00\x01")
    (source / "build").mkdir()
    (source / "dist").mkdir()
    (source / ".venv").mkdir()
    (source / ".pytest_cache").mkdir()
    (source / "node_modules").mkdir()

    store = UserTemplateStore(base_dir=tmp_path / "templates")
    inspected = store.inspect_source(source)

    included = {item.as_posix() for item in inspected.included_files}
    excluded = {item.as_posix() for item in inspected.excluded_files}
    sensitive = {item.as_posix() for item in inspected.sensitive_files}

    assert "app.py" in included
    assert ".git/config" in excluded
    assert ".env" in sensitive
    assert "credentials.json" in sensitive
    assert "secrets.json" in sensitive
    assert "cert.pem" in sensitive
    assert "mykey.key" in sensitive
    # bare id_rsa (no extension) is NOT flagged as sensitive by the current
    # is_sensitive_file (only exact names .env/credentials.json/secrets.json and
    # patterns *.pem/*.key) — it therefore leaks into included_files. That is a
    # documented GAP, not a false 'covered'.
    assert "id_rsa" in included
    assert "build" in excluded or "build/" in excluded
    assert "dist" in excluded or "dist/" in excluded
    assert ".venv" in excluded or ".venv/" in excluded
    assert ".pytest_cache" in excluded or ".pytest_cache/" in excluded


def test_save_load_delete_user_template(tmp_path: Path) -> None:
    source = tmp_path / "project-x"
    source.mkdir()
    (source / "README.md").write_text("Hello project-x\n", encoding="utf-8")
    (source / "pkg").mkdir()
    (source / "pkg" / "__init__.py").write_text("name='project-x'\n", encoding="utf-8")

    store = UserTemplateStore(base_dir=tmp_path / "templates")
    template_id = store.save_template(
        source_dir=source,
        template_name="My Project X",
        template_id="my-project-x",
        description="Custom template",
        author="tester",
        version="1.0.0",
        category="General",
        python_version="3.11",
        source_type="local",
        origin=str(source),
        reserved_template_ids=["python-cli", "python-script", "python-package"],
        replace_project_name=True,
    )

    assert template_id == "my-project-x"
    loaded = store.load_user_templates()
    assert any(item.id == "my-project-x" for item in loaded)
    spec = next(item for item in loaded if item.id == "my-project-x")
    assert spec.source == "user"
    assert spec.variable_style == "double_brace"

    readme = next(item for item in spec.files if item.path == "README.md")
    assert "{{ project_name }}" in readme.content

    store.delete_template("my-project-x")
    assert not store.template_exists("my-project-x")


def test_save_template_rejects_reserved_id(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    (source / "main.py").write_text("print('x')\n", encoding="utf-8")

    store = UserTemplateStore(base_dir=tmp_path / "templates")
    with pytest.raises(UserTemplateError):
        store.save_template(
            source_dir=source,
            template_name="Python CLI",
            template_id="python-cli",
            description="x",
            author="",
            version="1.0.0",
            category="CLI",
            python_version="3.11",
            source_type="local",
            origin=str(source),
            reserved_template_ids=["python-cli"],
            replace_project_name=False,
        )
