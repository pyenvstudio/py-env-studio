from __future__ import annotations

from types import SimpleNamespace

import py_env_studio.ui.main_window as main_window


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Widget:
    def __init__(self, mapped=False):
        self.mapped = mapped
        self.options = {}
        self.destroyed = False

    def configure(self, **options):
        self.options.update(options)

    def winfo_ismapped(self):
        return self.mapped

    def winfo_children(self):
        return []

    def grid_remove(self):
        self.mapped = False

    def destroy(self):
        self.destroyed = True

    def grid(self, **_kwargs):
        self.mapped = True

    def winfo_exists(self):
        return True


class Tree:
    def __init__(self, values_by_id):
        self.values_by_id = values_by_id
        self.selected = ()

    def exists(self, row_id):
        return row_id in self.values_by_id

    def item(self, row_id, _option=None):
        values = self.values_by_id[row_id]
        return values if _option == "values" else {"values": values}

    def selection_set(self, row_id):
        self.selected = (row_id,)

    def selection(self):
        return self.selected


class Harness:
    _select_environment = main_window.PyEnvStudio._select_environment
    _on_environment_tree_select = main_window.PyEnvStudio._on_environment_tree_select
    _restore_environment_selection = main_window.PyEnvStudio._restore_environment_selection
    _package_pane_is_visible = main_window.PyEnvStudio._package_pane_is_visible
    _package_request_is_current = main_window.PyEnvStudio._package_request_is_current
    _on_packages_loaded = main_window.PyEnvStudio._on_packages_loaded
    _on_packages_load_failed = main_window.PyEnvStudio._on_packages_load_failed

    def __init__(self, selected="A", mapped=True):
        self.selected_env_var = Value(selected)
        self.dir_var = Value("old-location")
        self.activate_button = Widget()
        self.selected_env_label = Widget()
        self.packages_list_frame = Widget(mapped=mapped)
        self.theme = SimpleNamespace(HIGHLIGHT_COLOR="highlight", ERROR_COLOR="error")
        self._package_list_generation = 1
        self._package_list_env_name = selected
        self._env_row_ids = {}
        self.refresh_calls = 0
        self.progress = Widget()
        self.env_tree = None

    def refresh_package_list(self):
        self.refresh_calls += 1
        self._package_list_generation += 1
        self._package_list_env_name = self.selected_env_var.get()


def test_old_package_success_is_discarded_after_selection_changes(monkeypatch):
    monkeypatch.setattr(main_window, "is_valid_env_selected", lambda _name: True)
    app = Harness(selected="A")
    app._select_environment("B", "location-B")

    app._on_packages_loaded("A", [("old", "1.0")], generation=1)

    assert app.refresh_calls == 1
    assert app.selected_env_var.get() == "B"
    assert app.packages_list_frame.winfo_children() == []


def test_package_pane_refreshes_for_new_selection(monkeypatch):
    monkeypatch.setattr(main_window, "is_valid_env_selected", lambda _name: True)
    app = Harness(selected="A", mapped=True)

    app._select_environment("B", "location-B")

    assert app.refresh_calls == 1
    assert app._package_list_env_name == "B"


def test_keyboard_tree_selection_updates_environment_location(monkeypatch):
    monkeypatch.setattr(main_window, "is_valid_env_selected", lambda _name: True)
    app = Harness(selected="A", mapped=False)
    app.env_tree = Tree({"row-b": ["B", "3.12", "uv", "location-B"]})
    app.env_tree.selection_set("row-b")

    app._on_environment_tree_select()

    assert app.selected_env_var.get() == "B"
    assert app.dir_var.get() == "location-B"
    assert app.activate_button.options["state"] == "normal"
    assert app.selected_env_label.options["text"] == "Selected Environment: B"


def test_refresh_restoration_uses_current_row_location_and_controls(monkeypatch):
    monkeypatch.setattr(main_window, "is_valid_env_selected", lambda _name: True)
    app = Harness(selected="B", mapped=False)
    app.env_tree = Tree({"row-b": ["B", "3.12", "uv", "new-location"]})
    app._env_row_ids = {"B": "row-b"}

    app._restore_environment_selection("B")

    assert app.env_tree.selection() == ("row-b",)
    assert app.selected_env_var.get() == "B"
    assert app.dir_var.get() == "new-location"
    assert app.activate_button.options["state"] == "normal"


def test_deleted_environment_clears_stale_selection_context(monkeypatch):
    monkeypatch.setattr(main_window, "is_valid_env_selected", lambda _name: False)
    app = Harness(selected="deleted", mapped=True)
    app.env_tree = Tree({})
    app._env_row_ids = {}

    app._restore_environment_selection("deleted")

    assert app.selected_env_var.get() == ""
    assert app.dir_var.get() == ""
    assert app.activate_button.options["state"] == "disabled"
    assert app.selected_env_label.options["text"] == "No valid environment selected."
    assert not app.packages_list_frame.winfo_ismapped()
    assert app._package_list_env_name is None


def test_old_package_failure_cannot_hide_or_replace_current_view():
    app = Harness(selected="B", mapped=True)
    app._package_list_generation = 2
    app._package_list_env_name = "B"

    app._on_packages_load_failed("A", RuntimeError("old request"), generation=1)

    assert app.packages_list_frame.winfo_ismapped()
    assert app.progress.options == {}


def test_old_package_success_cannot_modify_current_view():
    app = Harness(selected="B", mapped=True)
    app._package_list_generation = 2
    app._package_list_env_name = "B"

    app._on_packages_loaded("A", [("old", "1.0")], generation=1)

    assert app.packages_list_frame.winfo_children() == []
