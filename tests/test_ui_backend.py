import importlib
import sys
import tomllib
import types
from pathlib import Path


def test_project_dependency_contract_keeps_gui_packages_required():
    project_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    assert "customtkinter>=5.2.2" in dependencies
    assert "Pillow>=11.3.0" in dependencies
    assert "tkinter-dash>=0.1.5" in dependencies

    requirements = (project_root / "py_env_studio" / "requirements.txt").read_text(encoding="utf-8")
    assert "customtkinter==5.2.2" in requirements
    assert "Pillow==11.3.0" in requirements
    assert "tkinter-dash==0.1.5" in requirements


def test_detect_ui_backend_uses_ctk_when_available(monkeypatch):
    import py_env_studio.ui.backend as backend

    fake_ctk = types.SimpleNamespace(
        set_appearance_mode=lambda *a, **k: None,
        set_default_color_theme=lambda *a, **k: None,
        set_widget_scaling=lambda *a, **k: None,
        get_appearance_mode=lambda: "dark",
        CTk=object,
    )
    monkeypatch.setattr(backend, "_load_customtkinter", lambda: fake_ctk)
    backend_state = backend.detect_ui_backend()
    assert backend_state.name == "customtkinter"
    assert backend_state.ctk is fake_ctk


def test_detect_ui_backend_falls_back_to_tk_when_ctk_missing(monkeypatch):
    import py_env_studio.ui.backend as backend

    monkeypatch.setattr(backend, "_load_customtkinter", lambda: None)
    backend_state = backend.detect_ui_backend()
    assert backend_state.name == "tkinter"
    assert backend_state.ctk is not None
    assert hasattr(backend_state.ctk, "CTkFrame")


def test_cli_imports_without_customtkinter(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), *args, **kwargs):
        if name == "customtkinter":
            raise ModuleNotFoundError("No module named 'customtkinter'")
        return original_import(name, globals, locals, fromlist, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("customtkinter", None)
    sys.modules.pop("py_env_studio.ui.backend", None)
    import py_env_studio.commands as commands
    parser = commands.build_parser()
    assert parser is not None
