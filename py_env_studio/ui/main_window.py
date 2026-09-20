# standard libraries --------------------------------
import tkinter,json
from tkinter import messagebox, filedialog
import ctypes
import customtkinter as ctk
import os
from PIL import Image
import importlib.resources as pkg_resources
from datetime import datetime as DT
import webbrowser
import logging
from configparser import ConfigParser
import threading
import queue
import datetime
import tkinter.ttk as ttk
from pathlib import Path
import tempfile
import shutil

# project modules --------------------------------
from py_env_studio.core.env_manager import (
    create_env, rename_env, delete_env, activate_env, search_envs,
    get_env_data, set_env_data, is_valid_env_selected,
    list_pythons, is_valid_python_version_detected,
    get_available_tools, add_tool, refresh_runtime_paths
)
from py_env_studio.core.package_manager import (
    list_packages, install_package, uninstall_package, update_package,
    export_requirements, import_requirements, check_outdated_packages)
from py_env_studio.core.py_tonic import (
    PY_TONIC_LEARNING_MODES,
    PY_TONIC_NOTIFICATION_MODES,
    PY_TONIC_TOPICS,
    evaluate_challenge_answer,
    get_py_tonic_advice,
    get_random_challenge,
    load_py_tonic_profile,
    mark_notified,
    save_py_tonic_profile,
    should_notify,
)
from py_env_studio.utils.vulneribility_scanner import DBHelper, SecurityMatrix
from py_env_studio.utils.app_icon import install_window_icon_hook, schedule_window_icon
from  py_env_studio.utils.vulneribility_insights  import VulnerabilityInsightsApp
from py_env_studio.core.plugins import PluginManager
from py_env_studio.core.templates import TemplateEngine, TemplateCreationRequest
from py_env_studio.core.templates import TemplateCreationWorkflow, ProjectCreationStatus
from py_env_studio.core.templates.validator import sanitize_module_name
from py_env_studio.core.templates import (
    CommunityTemplateCandidate,
    CommunityTemplateInspection,
    CommunityTemplateService,
    UserTemplateError,
    UserTemplateStore,
    generate_template_id,
    refresh_default_registry,
    extract_github_repository_name,
    validate_github_repository_url,
    clone_github_repository,
)
from py_env_studio.core.project_launcher import (
    discover_project_open_tools,
    find_tool_by_id,
    open_project_with_tool,
)
from py_env_studio.core.configuration import (
    AppConfig,
    AppPreferences,
    ConfigurationError,
    ConfigurationService,
)
from py_env_studio.core.runtime import refresh_runtime_config
from py_env_studio.core.runtime_providers import (
    PythonInstallManagerProvider,
    PythonRuntime,
    RuntimeProvider,
    get_runtime_provider,
)
# ===== THEME & CONSTANTS =====
class Theme:
    PADDING = 10
    BUTTON_HEIGHT = 32
    ENTRY_WIDTH = 250
    SIDEBAR_WIDTH = 200
    LOGO_SIZE = (150, 150)
    TABLE_ROW_HEIGHT = 35
    TABLE_FONT_SIZE = 14
    CONSOLE_HEIGHT = 120

    PRIMARY_COLOR = "#3B8ED0" #"#092E53"#7F7C72" 
    HIGHLIGHT_COLOR = "#F2A42D"
    BORDER_COLOR = "#2B4F6B"
    ERROR_COLOR = "#FF4C4C"
    SUCCESS_COLOR = "#61D759"
    WARNING_COLOR = "#FFA500"
    SECONDARY_COLOR = "#A9A9A9"
    TEXT_COLOR_LIGHT = "#FFFFFF"
    TEXT_COLOR_DARK = "#000000"

    FONT_REGULAR = ("Segoe UI", 12)
    FONT_BOLD = ("Segoe UI", 12, "bold")
    FONT_CONSOLE = ("Courier", 12)


def get_config_path():
    try:
        with pkg_resources.path('py_env_studio', 'config.ini') as config_path:
            return str(config_path)
    except Exception:
        return os.path.join(os.path.dirname(__file__), 'config.ini')


def show_error(msg):
    messagebox.showerror("Error", msg)


def show_info(msg):
    messagebox.showinfo("Info", msg)

def open_link(link):
        webbrowser.open(link)

class MoreActionsDialog(ctk.CTkToplevel):
    """Custom dialog for showing More actions with Vulnerability Report and Scan Now buttons"""
    
    def __init__(self, parent, env_name, callback_vulnerability, callback_scan):
        super().__init__(parent)
        
        self.env_name = env_name
        self.callback_vulnerability = callback_vulnerability
        self.callback_scan = callback_scan
        
        # Configure dialog
        self.title(f"Actions for {env_name}")
        self.geometry("300x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center the dialog
        self.geometry(f"+{parent.winfo_rootx() + 900}+{parent.winfo_rooty() + 500}")
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)
        
        # Title label
        title_label = ctk.CTkLabel(
            self, 
            text=f"Environment: {env_name}", 
            font=("Segoe UI", 14, "bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Vulnerability Report button
        vulnerability_btn = ctk.CTkButton(
            self,
            text="📊 Vulnerability Report",
            command=self.vulnerability_report,
            height=35,
            width=250
        )
        vulnerability_btn.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        # Scan Now button
        scan_btn = ctk.CTkButton(
            self,
            text="🔍 Scan Now",
            command=self.scan_now,
            height=35,
            width=250
        )
        scan_btn.grid(row=2, column=0, padx=20, pady=(5, 20), sticky="ew")
        
    def vulnerability_report(self):
        """Handle Vulnerability Report button click"""
        self.destroy()
        if self.callback_vulnerability:
            self.callback_vulnerability(self.env_name)
    
    def scan_now(self):
        """Handle Scan Now button click"""
        self.destroy()
        if self.callback_scan:
            self.callback_scan(self.env_name)


class PyEnvStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.theme = Theme()
        self._setup_config()
        self._setup_vars()
        self._setup_window()
        self.icons = self._load_icons()
        self._setup_plugins()
        self.template_engine = TemplateEngine()
        self.template_creation_workflow = TemplateCreationWorkflow(self.template_engine)
        self.user_template_store = UserTemplateStore()
        self.community_template_service = CommunityTemplateService(
            template_store=self.user_template_store
        )
        self._setup_ui()
        self._setup_logging()

    def _setup_config(self):
        self.app_config = ConfigParser()
        self.app_config.read(get_config_path())
        self.version = self.app_config.get('project', 'version', fallback='1.0.0')

    def _setup_vars(self):
        self.configuration_service = ConfigurationService()
        self.preferences = self.configuration_service.load_preferences()
        self.env_search_var = tkinter.StringVar()
        self.selected_env_var = tkinter.StringVar()
        self.dir_var = tkinter.StringVar()
        # Load open_with tools from config or default
        self.open_with_tools = self._load_open_with_tools()
        self.open_with_var = tkinter.StringVar(value=self.open_with_tools[0] if self.open_with_tools else "CMD")
        self.choosen_python_var = tkinter.StringVar()
        self.env_log_queue = queue.Queue()
        self.py_tonic_profile = load_py_tonic_profile()
        self.py_tonic_profile = save_py_tonic_profile(self.py_tonic_profile)

    def _load_open_with_tools(self):
        tools = get_available_tools()
        names = [t["name"] for t in tools]
        if "Add Tool..." not in names:
            names.append("Add Tool...")
        return names

    def _save_open_with_tools(self):
        # Save current open_with_tools to config via env_manager
        # Only save user-added tools (skip 'Add Tool...')
        for t in self.open_with_tools:
            if t != "Add Tool...":
                add_tool(t)

    def _setup_window(self):
        # Add Windows taskbar icon fix at the start
        if os.name == 'nt':  # Windows only
            try:
                myappid = 'pyenvstudio.application.1.0'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception as e:
                logging.warning(f"Could not set Windows AppUserModelID: {e}")

        # Make every window created from now on (dialogs, plugin windows, the
        # Vulnerability Insights Dashboard, ...) use the Py Env Studio icon.
        install_window_icon_hook()

        appearance_mode = self.preferences.appearance_mode if self.preferences.appearance_mode else "System"
        ctk.set_appearance_mode(appearance_mode)
        scaling = self.preferences.ui_scaling if self.preferences.ui_scaling else "100%"
        ctk.set_widget_scaling(int(scaling.replace("%", "")) / 100)
        ctk.set_default_color_theme("blue")
        self.title("PyEnvStudio")
        self.geometry('1100x700')
        self.minsize(800, 600)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Apply the Py Env Studio icon to the main window as well. CustomTkinter
        # sets its own default icon shortly after creation, so the icon is
        # applied immediately and re-applied once more with a short delay.
        schedule_window_icon(self)


    def _setup_logging(self):
        # Initialize console logger with queue for UI display
        self.env_search_var.trace_add('write', lambda *_: self.refresh_env_list())
        self.after(100, self.process_log_queues)

    # ===== Widget Factories =====
    def btn(self, parent, text, cmd, image=None, width=150, height=None, **kw):
        return ctk.CTkButton(parent, text=text, command=cmd, image=image,
                             width=width, height=height or self.theme.BUTTON_HEIGHT,
                             fg_color=self.theme.PRIMARY_COLOR, hover_color="#104E8B", **kw)

    def entry(self, parent, ph="", var=None, width=None, **kw):
        return ctk.CTkEntry(parent, placeholder_text=ph, textvariable=var,
                            width=width or self.theme.ENTRY_WIDTH, **kw)

    def lbl(self, parent, text, **kw):
        return ctk.CTkLabel(parent, text=text, **kw)

    def frame(self, parent, **kw):
        return ctk.CTkFrame(parent, **kw)

    def optmenu(self, parent, vals, cmd=None, var=None, **kw):
        return ctk.CTkOptionMenu(parent, values=vals, command=cmd, variable=var,
                                 height=self.theme.BUTTON_HEIGHT, **kw)

    def chk(self, parent, text, **kw):
        return ctk.CTkCheckBox(parent, text=text, **kw)

    # ===== PLUGINS =====
    def _setup_plugins(self):
        """Initialize plugin manager and auto-load enabled plugins on startup."""
        self.plugin_manager = PluginManager()
        self.plugin_manager.set_app_context({
            "app": self,
            "config": self.app_config,
            "logger": logging.getLogger(__name__)
        })
        
        # Discover plugins and auto-load only enabled ones
        discovered = self.plugin_manager.discover_plugins()
        logging.info(f"Discovered {len(discovered)} plugins: {discovered}")
        
        # Get list of enabled plugins from saved state
        enabled_plugins = self.plugin_manager.get_enabled_plugins_list()
        logging.info(f"Enabled plugins (from state): {enabled_plugins}")
        
        # Auto-load only enabled plugins on startup
        for plugin_name in enabled_plugins:
            try:
                self.plugin_manager.load_plugin(plugin_name)
                logging.info(f"✓ Auto-loaded plugin: {plugin_name}")
            except Exception as e:
                logging.error(f"✗ Failed to auto-load plugin '{plugin_name}': {e}")
        
        # Execute on_app_start hook for all loaded plugins
        try:
            self.plugin_manager.execute_hook("on_app_start", {
                "app": self,
                "version": self.version
            })
            logging.info("✓ Executed on_app_start hook for all plugins")
        except Exception as e:
            logging.error(f"Error executing on_app_start hook: {e}")

    # ===== ICONS =====
    def _load_icons(self):
        names = ["logo", "create-env", "delete-env", "selected-env", "activate-env",
                 "install", "uninstall", "requirements", "export", "packages", "update", "about"]
        out = {}
        for n in names:
            try:
                with pkg_resources.path('py_env_studio.ui.static.icons', f"{n}.png") as p:
                    out[n] = ctk.CTkImage(Image.open(str(p)))
            except Exception:
                out[n] = None
        return out

    # ===== UI SETUP =====
    def _setup_ui(self):
        self._setup_menubar()
        self._setup_sidebar()
        self._setup_tabview()
        self._setup_env_tab()
        self._setup_pkg_tab()
        self._setup_console()


    def _setup_menubar(self):
        menubar = tkinter.Menu(self)

        # === File Menu ===
        file_menu = tkinter.Menu(menubar, tearoff=0)
        # Use the _pkg_install_section for install package dialog
        file_menu.add_command(label="Install Package", command=self.show_install_package_dialog)

        file_menu.add_command(label="Install Requirements", command=self.install_requirements)
        file_menu.add_command(label="Export Packages", command=self.export_packages)
        # file_menu.add_command(label="Preferences", command=self.show_preferences_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        # === Edit Menu ===
        edit_menu = tkinter.Menu(menubar, tearoff=0)
        # edit_menu.add_command(label="Rename Env", command=lambda: self.rename_selected_env())
        # edit_menu.add_command(label="Delete Env", command=lambda: self.delete_selected_env())

        # === View Menu ===
        view_menu = tkinter.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Refresh Environments", command=self.refresh_env_list)

        # === Tools Menu ===
        tools_menu = tkinter.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Scan Now", command=lambda: self.scan_environment_now(self.selected_env_var.get()))
        tools_menu.add_command(label="Vulnerability Report", command=lambda: self.show_vulnerability_report(self.selected_env_var.get()))
        tools_menu.add_command(label="Check for Package Updates", command=lambda: self.check_for_package_updates(self.selected_env_var.get()))
        # tools_menu.add_command(label="Py-Tonic Advisor", command=self.show_py_tonic_advisor)
        tools_menu.add_command(label="Configuration", command=self.show_preferences_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Plugins", command=self.show_plugins_dialog)

        # === Templates Menu ===
        templates_menu = tkinter.Menu(menubar, tearoff=0)
        for template in self.template_engine.list_templates():
            templates_menu.add_command(
                label=template.name,
                command=lambda template_id=template.id: self.open_template_wizard(template_id),
            )
        templates_menu.add_separator()
        templates_menu.add_command(label="Manage Templates", command=self.show_manage_templates_dialog)
        templates_menu.add_command(label="Community Templates", command=self.show_community_templates_dialog)

        # === Help Menu ===
        help_menu = tkinter.Menu(menubar, tearoff=0)
        # read the docs link
        help_menu.add_command(label="Documentation", command=lambda: open_link("https://py-env-studio.readthedocs.io/en/latest/"))
        help_menu.add_command(label="About", command=self.show_about_dialog)
        # help_menu.add_command(label="Check for Updates", command=self.check_outdated_packages)

        # === set menubar ===
        menubar.add_cascade(label="File", menu=file_menu)
        # menubar.add_cascade(label="Edit", menu=edit_menu)
        menubar.add_cascade(label="View", menu=view_menu)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        menubar.add_cascade(label="Templates", menu=templates_menu)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _setup_sidebar(self):
        sb = self.frame(self, width=self.theme.SIDEBAR_WIDTH, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_rowconfigure(4, weight=1)
        try:
            with pkg_resources.path('py_env_studio.ui.static.icons', 'pes-default-transparrent.png') as p:
                img = ctk.CTkImage(Image.open(str(p)), size=self.theme.LOGO_SIZE)
        except:
            img = None
        self.lbl(sb, text="", image=img).grid(row=0, column=0, padx=10, pady=(10, 20))
        # self.btn(sb, "About", self.show_about_dialog, self.icons.get("about"), width=150).grid(row=4, column=0, padx=10, pady=(10, 20), sticky="ew")

    def _setup_tabview(self):
        self.tabview = ctk.CTkTabview(self, command=self.on_tab_changed)
        self.tabview.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.tabview.add("Environments")
        self.tabview.add("Packages")
        self.tabview.tab("Environments").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Packages").grid_columnconfigure(0, weight=1)

    # === ENV TAB CARD LAYOUT ===
    def _setup_env_tab(self):
        env_tab = self.tabview.tab("Environments")
        env_tab.grid_rowconfigure(5, weight=1)
        env_tab.grid_rowconfigure(6, weight=0)
        self._env_create_section(env_tab)
        self._env_activate_section(env_tab)
        self._env_search_section(env_tab)
        self._env_list_section(env_tab)

    def _env_create_section(self, parent):

        f = self.frame(parent, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        f.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        f.grid_columnconfigure(1, weight=1)

        # Environment name label and entry
        self.lbl(f, "New Environment Name:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.entry_env_name = self.entry(f, "Enter environment name")
        self.entry_env_name.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        # Python path label, entry, and browse button on row 1
        self.lbl(f, "Python Path (Optional):").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        # Smaller width for python path entry to fit button and option menu on same row
        self.entry_python_path = self.entry(f, "Enter Python interpreter path", width=180)
        self.entry_python_path.grid(row=1, column=1, padx=(0, 5), pady=5, sticky="ew")
        default_python_path = (self.preferences.default_python_path or "").strip()
        if default_python_path:
            self.entry_python_path.insert(0, default_python_path)

        self.btn(f, "Browse", self.browse_python_path, width=80).grid(row=1, column=2, padx=(5, 5), pady=5)

        # "or select:" label next to browse button
        
        self.lbl(f, "or select:").grid(row=1, column=3, padx=(5, 5), pady=5, sticky="w")

        # OptionMenu for python interpreters on same row, next column
        self.available_python = self.optmenu(
            f,
            list_pythons(),
            var=self.choosen_python_var,
            cmd=self.browse_python_path,
            width=150
        )
        self.available_python.grid(row=1, column=4, padx=(5, 10), pady=5, sticky="w")

        # Managed Python runtime selection. This is intentionally separate from
        # the explicit interpreter-path override above. The runtime selector is
        # backed by the configured RuntimeProvider and therefore does not require
        # users to browse for python.exe manually.
        self.lbl(f, "Python Runtime:").grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")
        self.env_runtime_var = tkinter.StringVar(value="System Default")
        self.env_runtime_menu = self.optmenu(
            f,
            ["System Default"],
            var=self.env_runtime_var,
            width=180,
            cmd=lambda _value: self._on_env_runtime_selected(),
        )
        self.env_runtime_menu.grid(row=2, column=1, padx=(0, 5), pady=5, sticky="w")
        self.btn(f, "Refresh", self.refresh_env_runtime_choices, width=80).grid(
            row=2, column=2, padx=5, pady=5, sticky="w"
        )
        self.env_runtime_hint = self.lbl(
            f, "", font=("Segoe UI", 10), text_color=self.theme.SECONDARY_COLOR
        )
        self.env_runtime_hint.grid(row=2, column=3, columnspan=2, padx=5, pady=5, sticky="w")

        # Upgrade pip checkbox below, full width
        self.checkbox_upgrade_pip = self.chk(f, "Upgrade pip during creation")
        self.checkbox_upgrade_pip.select()
        self.checkbox_upgrade_pip.grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky="w")

        # Package manager selection
        self.lbl(f, "Package Manager:").grid(row=4, column=0, padx=(10, 5), pady=5, sticky="w")
        self.create_env_pkg_mgr = self.optmenu(
            f,
            ["pip", "uv"],
            var=None,
            width=150
        )
        self.create_env_pkg_mgr.grid(row=4, column=1, padx=(0, 5), pady=5, sticky="w")
        from py_env_studio.core.env_manager import get_preferred_package_manager
        self.create_env_pkg_mgr.set(get_preferred_package_manager())

        # show python version information label below checkbox
        self.python_version_info = self.lbl(f, "USING PYTHON: Default", font=self.theme.FONT_BOLD, text_color=self.theme.HIGHLIGHT_COLOR)
        self.python_version_info.grid(row=5, column=0, columnspan=5, padx=10, pady=5, sticky="w")

        # Create environment button below
        self.btn_create_env = self.btn(f, "Create Environment", self.create_env, self.icons.get("create-env"))
        self.btn_create_env.grid(row=6, column=0, columnspan=5, padx=10, pady=5)

        self.refresh_env_runtime_choices()

    def _env_activate_section(self, parent):
        p = self.frame(parent, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        p.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        p.grid_columnconfigure(1, weight=1)
        self.lbl(p, "Open At:", font=self.theme.FONT_BOLD).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="e")
        self.dir_entry = self.entry(p, "Directory", var=self.dir_var, width=150)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn(p, "Browse", self.browse_dir, width=80).grid(row=0, column=2, padx=5, pady=5)
        self.lbl(p, "Open With:", font=self.theme.FONT_BOLD).grid(row=0, column=3, padx=(10, 5), pady=5, sticky="e")
        self.open_with_dropdown = self.optmenu(p, self.open_with_tools, cmd=self.on_open_with_change, var=self.open_with_var, width=120)
        self.open_with_dropdown.grid(row=0, column=4, padx=5, pady=5)
        self.activate_button = self.btn(p, "Activate", self.activate_with_dir, self.icons.get("activate-env"), width=100)
        self.activate_button.grid(row=0, column=5, padx=(5, 10), pady=5)

    def on_open_with_change(self, value):
        if value == "Add Tool...":
            dialog = ctk.CTkInputDialog(text="Enter tool name (and optionally path, e.g. Sublime:/path/to/sublime):", title="Add Open With Tool")
            dialog.geometry("+%d+%d" % (self.winfo_rootx() + 600, self.winfo_rooty() + 300))
            entry = dialog.get_input()
            if entry:
                if ':' in entry:
                    name, path = entry.split(':', 1)
                else:
                    name, path = entry, None
                
                add_tool(name, path)
                # Reload tools
                self.open_with_tools = self._load_open_with_tools()
                self.open_with_dropdown.configure(values=self.open_with_tools)
                self.open_with_var.set(name)

    def add_open_with_tool(self):
        # Prompt user to add a new tool
        dialog = ctk.CTkInputDialog(text="Enter tool name to add (e.g. Sublime, Atom):", title="Add Open With Tool")
        dialog.geometry("+%d+%d" % (self.winfo_rootx() + 600, self.winfo_rooty() + 300))
        tool_name = dialog.get_input()
        if tool_name and tool_name not in self.open_with_tools:
            self.open_with_tools.append(tool_name)
            self._save_open_with_tools()
            self.open_with_dropdown.configure(values=self.open_with_tools)
            self.open_with_var.set(tool_name)

    def _env_search_section(self, parent):
        f = self.frame(parent, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        f.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        f.grid_columnconfigure(1, weight=1)
        self.lbl(f, "Search Environments:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.entry(f, "Search environments...", var=self.env_search_var).grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

    def _env_list_section(self, parent):
        self.env_scrollable_frame = ctk.CTkScrollableFrame(parent, label_text=f"Available Environments",)
        self.env_scrollable_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.env_scrollable_frame.grid_columnconfigure(0, weight=1)
        self.refresh_env_list()

    def _setup_console(self):

        self.console_frame = ctk.CTkTextbox(self, height=self.theme.CONSOLE_HEIGHT, state="disabled", font=self.theme.FONT_CONSOLE)
        self.console_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # === PKG TAB ===
    def _setup_pkg_tab(self):
        pkg_tab = self.tabview.tab("Packages")
        pkg_tab.grid_rowconfigure(4, weight=1)
        pkg_tab.grid_rowconfigure(5, weight=0)
        self._pkg_header(pkg_tab)
        self._pkg_install_section(pkg_tab)
        self._pkg_bulk_section(pkg_tab)
        self._pkg_manage_section(pkg_tab)

    def _pkg_header(self, parent):
        self.selected_env_label = self.lbl(parent, "", font=self.theme.FONT_BOLD)
        self.selected_env_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

    def _pkg_install_section(self, parent):
        f = self.frame(parent, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        f.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        f.grid_columnconfigure(1, weight=1)
        self.lbl(f, "Package Name:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.entry_package_name = self.entry(f, "Enter package name", takefocus=True)
        self.entry_package_name.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.checkbox_confirm_install = self.chk(f, "Confirm package actions")
        self.checkbox_confirm_install.select()
        self.checkbox_confirm_install.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.btn_install_package = self.btn(f, "Install Package", self.install_package, self.icons.get("install"))
        self.btn_install_package.grid(row=2, column=0, columnspan=2, padx=10, pady=5)

    def _pkg_bulk_section(self, parent):
        f = self.frame(parent, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        f.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.btn_install_requirements = self.btn(f, "Install Requirements", self.install_requirements, self.icons.get("requirements"))
        self.btn_install_requirements.grid(row=0, column=0, padx=(10, 5), pady=10)
        self.btn_export_packages = self.btn(f, "Export Packages", self.export_packages, self.icons.get("export"))
        self.btn_export_packages.grid(row=0, column=1, padx=(5, 10), pady=10)

    def _pkg_manage_section(self, parent):
        self.btn_view_packages = self.btn(parent, "Manage Packages", self.view_installed_packages,
                                          self.icons.get("packages"), width=300)
        self.btn_view_packages.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.packages_list_frame = ctk.CTkScrollableFrame(parent, label_text="Installed Packages")
        self.packages_list_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.packages_list_frame.grid_remove()

    def notify_py_tonic(self, action="general"):
        # Only respect "manual" mode to disable notifications completely
        if self.py_tonic_profile.get("notification_frequency") == "manual":
            return
        advice = get_py_tonic_advice(action)
        self.env_log_queue.put(f"[Py-Tonic] {advice['notification']}")
        self.env_log_queue.put(f"[Py-Tonic] Bad example: {advice['bad_example']}")
        self.env_log_queue.put(f"[Py-Tonic] Recommended: {advice['recommended']}")

    def _save_py_tonic_settings(self, frequency, mode, topic_flags):
        topics = [topic for topic, enabled in topic_flags.items() if enabled]
        if not topics:
            topics = ["core_python"]
        profile = self.py_tonic_profile.copy()
        profile["notification_frequency"] = frequency
        profile["mode"] = mode
        profile["topics"] = topics
        # Reset notification timer when settings change
        profile["last_notified_at"] = None
        self.py_tonic_profile = save_py_tonic_profile(profile)
        self.env_log_queue.put(
            f"[Py-Tonic] Settings saved: {frequency}, {mode}, {', '.join(topics)}"
        )

    def _show_py_tonic_challenge_dialog(self, challenge, strict=False):
        result = {"passed": False}
        top = ctk.CTkToplevel(self)
        top.title("Py-Tonic Coding Challenge")
        top.geometry("760x520")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(2, weight=1)
        top.grid_rowconfigure(4, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 300}+{self.winfo_rooty() + 170}")

        ctk.CTkLabel(
            top,
            text=f"{challenge['title']} ({challenge['topic']})",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")
        ctk.CTkLabel(top, text=challenge["prompt"], anchor="w").grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")

        code_box = ctk.CTkTextbox(top, wrap="none", height=140)
        code_box.grid(row=2, column=0, padx=16, pady=6, sticky="nsew")
        code_box.insert("end", challenge["partial_code"])
        code_box.configure(state="disabled")

        ctk.CTkLabel(top, text="Your answer:").grid(row=3, column=0, padx=16, pady=(6, 0), sticky="w")
        answer_box = ctk.CTkTextbox(top, wrap="word", height=90)
        answer_box.grid(row=4, column=0, padx=16, pady=6, sticky="nsew")
        status = ctk.CTkLabel(top, text="", anchor="w")
        status.grid(row=5, column=0, padx=16, pady=(2, 0), sticky="ew")

        hint_index = {"value": 0}
        learning_mode = self.py_tonic_profile.get("mode", "learning") == "learning"

        def check_answer():
            answer = answer_box.get("1.0", "end").strip()
            if not answer:
                status.configure(text="Please enter an answer.", text_color=self.theme.ERROR_COLOR)
                return
            if evaluate_challenge_answer(challenge, answer):
                result["passed"] = True
                status.configure(text="Correct. Challenge passed.", text_color=self.theme.SUCCESS_COLOR)
                self.env_log_queue.put(f"[Py-Tonic] Challenge solved: {challenge['id']}")
                top.after(200, top.destroy)
                return
            status.configure(text="Incorrect. Try again.", text_color=self.theme.ERROR_COLOR)

        def show_hint():
            hints = challenge.get("hint_steps", [])
            if not hints:
                status.configure(text="No hints available.", text_color=self.theme.ERROR_COLOR)
                return
            if hint_index["value"] >= len(hints):
                status.configure(text=f"Hint: {hints[-1]}", text_color=self.theme.HIGHLIGHT_COLOR)
                return
            status.configure(text=f"Hint: {hints[hint_index['value']]}", text_color=self.theme.HIGHLIGHT_COLOR)
            hint_index["value"] += 1

        btn_frame = self.frame(top)
        btn_frame.grid(row=6, column=0, padx=16, pady=(8, 12), sticky="e")
        self.btn(btn_frame, "Check Answer", check_answer, width=120).grid(row=0, column=0, padx=4)

        if learning_mode and not strict:
            self.btn(btn_frame, "Hint", show_hint, width=90).grid(row=0, column=1, padx=4)
            self.btn(
                btn_frame,
                "Show Solution",
                lambda: status.configure(text=f"Solution: {challenge['expected_answer']}", text_color=self.theme.HIGHLIGHT_COLOR),
                width=120,
            ).grid(row=0, column=2, padx=4)
            self.btn(btn_frame, "Close", top.destroy, width=90).grid(row=0, column=3, padx=4)
        else:
            self.btn(btn_frame, "Cancel", top.destroy, width=90).grid(row=0, column=1, padx=4)

        self.wait_window(top)
        return result["passed"]

    def _enforce_strict_py_tonic(self, action):
        if self.py_tonic_profile.get("mode") != "strict":
            return True
        challenge = get_random_challenge(self.py_tonic_profile)
        self.env_log_queue.put(f"[Py-Tonic] Strict challenge required before '{action}'.")
        passed = self._show_py_tonic_challenge_dialog(challenge, strict=True)
        if not passed:
            self.env_log_queue.put("[Py-Tonic] Action blocked by strict mode.")
            show_error("Strict mode enabled. Solve the Py-Tonic challenge to continue.")
            return False
        return True

    def show_py_tonic_advisor(self):
        top = ctk.CTkToplevel(self)
        top.title("Py-Tonic Advisor")
        top.geometry("950x620")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=1)
        top.grid_rowconfigure(2, weight=1)
        top.grid_rowconfigure(3, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 300}+{self.winfo_rooty() + 180}")

        ctk.CTkLabel(top, text="Py-Tonic: Python Best Practices", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="w"
        )

        profile = self.py_tonic_profile
        frequency_var = tkinter.StringVar(value=profile.get("notification_frequency", "daily"))
        mode_var = tkinter.StringVar(value=profile.get("mode", "learning"))
        action_options = [
            "general", "create_env", "rename_env", "delete_env", "activate_env",
            "install_package", "uninstall_package", "update_package",
            "import_requirements", "export_requirements",
        ]
        action_var = tkinter.StringVar(value="general")
        topic_vars = {
            topic: tkinter.BooleanVar(value=topic in profile.get("topics", []))
            for topic in PY_TONIC_TOPICS
        }

        settings = self.frame(top, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        settings.grid(row=1, column=0, columnspan=2, padx=16, pady=8, sticky="ew")
        settings.grid_columnconfigure(5, weight=1)
        self.lbl(settings, "Notify:", font=self.theme.FONT_BOLD).grid(row=0, column=0, padx=(10, 4), pady=10, sticky="w")
        self.optmenu(settings, list(PY_TONIC_NOTIFICATION_MODES), var=frequency_var, width=120).grid(row=0, column=1, padx=4, pady=10)
        self.lbl(settings, "Mode:", font=self.theme.FONT_BOLD).grid(row=0, column=2, padx=(12, 4), pady=10, sticky="w")
        self.optmenu(settings, list(PY_TONIC_LEARNING_MODES), var=mode_var, width=120).grid(row=0, column=3, padx=4, pady=10)
        self.lbl(settings, "Topics:", font=self.theme.FONT_BOLD).grid(row=0, column=4, padx=(12, 4), pady=10, sticky="w")
        self.chk(settings, "Core Python", variable=topic_vars["core_python"]).grid(row=0, column=5, padx=4, pady=10, sticky="w")
        self.chk(settings, "Python Django", variable=topic_vars["python_django"]).grid(row=0, column=6, padx=4, pady=10, sticky="w")
        self.btn(
            settings,
            "Save Settings",
            lambda: self._save_py_tonic_settings(
                frequency_var.get(),
                mode_var.get(),
                {topic: var.get() for topic, var in topic_vars.items()},
            ),
            width=130,
        ).grid(row=0, column=7, padx=(8, 10), pady=10)

        left = self.frame(top, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        left.grid(row=2, column=0, rowspan=2, padx=(16, 8), pady=8, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        self.lbl(left, "Action Advice", font=self.theme.FONT_BOLD).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")
        self.optmenu(left, action_options, var=action_var, width=190).grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")
        advice_box = ctk.CTkTextbox(left, wrap="word")
        advice_box.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="nsew")

        right = self.frame(top, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        right.grid(row=2, column=1, rowspan=2, padx=(8, 16), pady=8, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)
        right.grid_rowconfigure(4, weight=1)
        self.lbl(right, "Interactive Coding Window", font=self.theme.FONT_BOLD).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")
        challenge_code = ctk.CTkTextbox(right, wrap="none", height=130)
        challenge_code.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="nsew")
        self.lbl(right, "Your answer (fill missing code):").grid(row=3, column=0, padx=12, pady=(0, 4), sticky="w")
        challenge_answer = ctk.CTkTextbox(right, wrap="word", height=80)
        challenge_answer.grid(row=4, column=0, padx=12, pady=(0, 6), sticky="nsew")
        challenge_status = self.lbl(right, "", anchor="w")
        challenge_status.grid(row=5, column=0, padx=12, pady=(0, 6), sticky="ew")

        challenge_state = {"challenge": None, "hint_idx": 0}

        def render_advice():
            advice = get_py_tonic_advice(action_var.get())
            advice_box.configure(state="normal")
            advice_box.delete("1.0", "end")
            advice_box.insert(
                "end",
                "Notification:\n"
                f"- {advice['notification']}\n\n"
                "Bad example:\n"
                f"- {advice['bad_example']}\n\n"
                "Recommended:\n"
                f"- {advice['recommended']}\n\n"
                "Most used:\n"
                + "\n".join([f"- {item}" for item in advice["most_used"]])
            )
            advice_box.configure(state="disabled")

        def load_challenge():
            temp_topics = [topic for topic, var in topic_vars.items() if var.get()] or ["core_python"]
            temp_profile = self.py_tonic_profile.copy()
            temp_profile["topics"] = temp_topics
            temp_profile["mode"] = mode_var.get()
            challenge_state["challenge"] = get_random_challenge(temp_profile)
            challenge_state["hint_idx"] = 0
            challenge_code.configure(state="normal")
            challenge_code.delete("1.0", "end")
            challenge_code.insert(
                "end",
                f"{challenge_state['challenge']['title']}\n"
                f"Topic: {challenge_state['challenge']['topic']}\n"
                f"Prompt: {challenge_state['challenge']['prompt']}\n\n"
                f"{challenge_state['challenge']['partial_code']}\n"
            )
            challenge_code.configure(state="disabled")
            challenge_answer.delete("1.0", "end")
            challenge_status.configure(text="", text_color=self.theme.TEXT_COLOR_LIGHT)

        def check_challenge():
            challenge = challenge_state["challenge"]
            if not challenge:
                challenge_status.configure(text="Load a challenge first.", text_color=self.theme.ERROR_COLOR)
                return
            answer = challenge_answer.get("1.0", "end").strip()
            if evaluate_challenge_answer(challenge, answer):
                challenge_status.configure(text="Correct answer.", text_color=self.theme.SUCCESS_COLOR)
                self.env_log_queue.put(f"[Py-Tonic] Advisor challenge solved: {challenge['id']}")
            else:
                challenge_status.configure(text="Incorrect answer. Try again.", text_color=self.theme.ERROR_COLOR)

        def show_next_hint():
            challenge = challenge_state["challenge"]
            if not challenge:
                challenge_status.configure(text="Load a challenge first.", text_color=self.theme.ERROR_COLOR)
                return
            if mode_var.get() != "learning":
                challenge_status.configure(text="Hints are available in learning mode.", text_color=self.theme.ERROR_COLOR)
                return
            hints = challenge.get("hint_steps", [])
            if not hints:
                challenge_status.configure(text="No hints available.", text_color=self.theme.ERROR_COLOR)
                return
            idx = min(challenge_state["hint_idx"], len(hints) - 1)
            challenge_status.configure(text=f"Hint: {hints[idx]}", text_color=self.theme.HIGHLIGHT_COLOR)
            challenge_state["hint_idx"] = idx + 1

        btns = self.frame(right)
        btns.grid(row=6, column=0, padx=12, pady=(0, 12), sticky="e")
        self.btn(btns, "Load Challenge", load_challenge, width=130).grid(row=0, column=0, padx=4)
        self.btn(btns, "Check", check_challenge, width=90).grid(row=0, column=1, padx=4)
        self.btn(btns, "Hint", show_next_hint, width=90).grid(row=0, column=2, padx=4)
        self.btn(
            btns,
            "Modal Challenge",
            lambda: self._show_py_tonic_challenge_dialog(
                challenge_state["challenge"] or get_random_challenge(self.py_tonic_profile),
                strict=False,
            ),
            width=130,
        ).grid(row=0, column=3, padx=4)

        action_var.trace_add("write", lambda *_: render_advice())
        render_advice()
        load_challenge()

        close_btn = self.btn(top, "Close", top.destroy, width=120)
        close_btn.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="e")

    # === Environment & Package Logic follows (using Treeview for Packages) ===
    # ===== LOGIC: Async, logging, events, environment ops, package ops =====
    def run_async(self, func, success_msg=None, error_msg=None, callback=None, py_tonic_action=None):
        if py_tonic_action and not self._enforce_strict_py_tonic(py_tonic_action):
            return

        def target():
            try:
                func()
                if py_tonic_action:
                    self._safe_after(0, lambda action=py_tonic_action: self.notify_py_tonic(action))
                if success_msg:
                    self._safe_after(0, lambda: show_info(success_msg))
            except Exception as e:
                if error_msg:
                    self._safe_after(0, lambda e=e: show_error(f"{error_msg}: {str(e)}"))
            if callback:
                self._safe_after(0, callback)
        threading.Thread(target=target, daemon=True).start()

    def _safe_after(self, delay_ms, func, *args):
        """Schedule ``func`` on the Tk main loop; no-op if the loop is gone.

        Background threads routinely outlive the main window (e.g. a runtime
        refresh still running when the app is closed). A bare ``self.after``
        then raises ``RuntimeError: main thread is not in main loop``, which
        surfaces as an unhandled thread exception. Swallow that (and Tcl
        errors from torn-down widgets) and return None.
        """
        try:
            return self.after(delay_ms, func, *args)
        except (RuntimeError, tkinter.TclError):
            return None
        except Exception:
            logging.debug("Failed to schedule UI callback", exc_info=True)
            return None

    def process_log_queues(self):
        self._process_log_queue(self.env_log_queue, self.console_frame)
        self.after(100, self.process_log_queues)

    def _process_log_queue(self, q, console):
        try:
            while True:
                msg = q.get_nowait()
                console.configure(state="normal")
                console.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
                console.configure(state="disabled")
                console.see("end")
        except queue.Empty:
            pass

    def update_treeview_style(self):
        mode = ctk.get_appearance_mode()
        bg_color = self.theme.TEXT_COLOR_DARK if mode == "Light" else self.theme.TEXT_COLOR_LIGHT
        fg_color = self.theme.TEXT_COLOR_LIGHT if mode == "Light" else self.theme.TEXT_COLOR_DARK
        style = ttk.Style()
        style.configure("Treeview", background=bg_color, foreground=fg_color,
                        fieldbackground=bg_color, rowheight=self.theme.TABLE_ROW_HEIGHT,
                        font=self.theme.FONT_REGULAR)
        style.map("Treeview", background=[('selected', self.theme.HIGHLIGHT_COLOR)],
                  foreground=[('selected', fg_color)])
        style.configure("Treeview.Heading", font=self.theme.FONT_BOLD)

    # ===== ENVIRONMENTS TABLE =====
    
    def refresh_env_list(self):
        for widget in self.env_scrollable_frame.winfo_children():
            widget.destroy()
        envs = search_envs(self.env_search_var.get())
        # Updated columns - added VM_TOOL after PYTHON_VERSION
        columns = ("ENVIRONMENT", "PYTHON_VERSION", "VM_TOOL", "LAST_LOCATION", "SIZE", "RENAME", "DELETE", "LAST_SCANNED", "MORE")
        self.env_tree = ttk.Treeview(
            self.env_scrollable_frame, columns=columns, show="headings", height=8, selectmode="browse"
        )
        for col, text, width, anchor in [
            ("ENVIRONMENT", "Environment", 200, "w"),
            ("PYTHON_VERSION", "Python Version", 110, "center"),
            ("VM_TOOL", "VM Tool", 100, "center"),
            ("LAST_LOCATION", "Recent Location", 160, "center"),
            ("SIZE", "Size", 100, "center"),
            ("RENAME", "Rename", 80, "center"),
            ("DELETE", "Delete", 80, "center"),
            ("LAST_SCANNED", "Last Scanned", 120, "center"),
            ("MORE", "More", 80, "center")  # New More column
        ]:
            self.env_tree.heading(col, text=text)
            self.env_tree.column(col, width=width, anchor=anchor)
        self.env_tree.grid(row=0, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")
        self.update_treeview_style()

        for env in envs:
            data = get_env_data(env)
            # Get the VM tool display - use get_env_package_manager to get the correct manager
            from py_env_studio.core.env_manager import get_package_manager_display
            from py_env_studio.core.package_manager import get_env_package_manager
            manager = get_env_package_manager(env)
            vm_tool = get_package_manager_display(manager)
            
            self.env_tree.insert("", "end", values=(
                env,
                data.get("python_version", "-"),
                vm_tool,
                data.get("recent_location", "-"),
                data.get("size", "-"),
                "🖊",
                "🗑️",
                data.get("last_scanned", "-"),
                "⋮"  # more
            ))

        def on_tree_click(event):
            col = self.env_tree.identify_column(event.x)
            row = self.env_tree.identify_row(event.y)
            recent_location = self.env_tree.item(row)['values'][3]
            if not row:
                return
            env = self.env_tree.item(row)['values'][0]

            # 1.Environment| 2.Version | 3.VM Tool | 4.Recent Location | 5.Size | 8.Last Scanned 
            if col in ("#1","#2", "#3", "#5", "#8"):
                if recent_location and recent_location != "-":
                    try:
                        self.env_tree.selection_set(row)
                    except Exception:
                        pass
                    self.selected_env_var.set(env)
                    self.activate_button.configure(state="normal")
                    self.dir_var.set(recent_location)
                return
            
            if col == "#4":  # Recent Location
                if recent_location and recent_location != "-":
                    try:
                        self.env_tree.selection_set(row)
                    except Exception:
                        pass
                    self.selected_env_var.set(env)
                    self.activate_button.configure(state="normal")
                    self.dir_var.set(recent_location)

                     # Copy location to clipboard
                    self.clipboard_clear()
                    self.clipboard_append(recent_location)
                    self.update()  # ensures clipboard is updated
                    # Log the copy action in the log window
                    self.env_log_queue.put(f"Path:'{recent_location}' copied to clipboard!")
                return

            if col == "#6":  # Rename
                dialog = ctk.CTkInputDialog(
                    text=f"Enter new name for '{env}':",
                    title="Environment Rename"
                )
                dialog.geometry("+%d+%d" % (self.winfo_rootx() + 600, self.winfo_rooty() + 300))
                new_name = dialog.get_input()
                if new_name and new_name != env:
                    self.run_async(
                        lambda: rename_env(
                            env, new_name,
                            log_callback=lambda msg: self.env_log_queue.put(msg)
                        ),
                        success_msg=f"Environment '{env}' renamed to '{new_name}'.",
                        error_msg="Failed to rename environment",
                        callback=self.refresh_env_list,
                        py_tonic_action="rename_env",
                    )
            elif col == "#7":  # Delete
                if messagebox.askyesno("Confirm", f"Delete environment '{env}'?"):
                    self.run_async(
                        lambda: delete_env(env, log_callback=lambda msg: self.env_log_queue.put(msg)),
                        success_msg=f"Environment '{env}' deleted successfully.",
                        error_msg="Failed to delete environment",
                        callback=self.refresh_env_list,
                        py_tonic_action="delete_env",
                    )
            elif col == "#9":  # More
                self.show_more_actions_dialog(env)

        def on_tree_double_click(event):
            col = self.env_tree.identify_column(event.x)
            row = self.env_tree.identify_row(event.y)
            if not row:
                return

            # Double click to trigger Activate button
            if col in ("#1","#2", "#3", "#5", "#8"):
                self.activate_button.invoke()

        self.env_tree.bind("<Button-1>", on_tree_click)
        self.env_tree.bind("<Double-1>", on_tree_double_click)

        def on_tree_select(event):
            sel = self.env_tree.selection()
            if sel:
                env = self.env_tree.item(sel[0])['values'][0]
                self.selected_env_var.set(env)
                self.activate_button.configure(state="normal")


        self.env_tree.bind("<<TreeviewSelect>>", on_tree_select)

    def show_more_actions_dialog(self, env_name):
        """Show the More actions dialog with Vulnerability Report and Scan Now buttons"""
        dialog = MoreActionsDialog(
            parent=self,
            env_name=env_name,
            callback_vulnerability=self.show_vulnerability_report,
            callback_scan=self.scan_environment_now
        )
        
    def show_vulnerability_report(self, env_name):
        """Handle Vulnerability Report action"""
        try:
            # Check if environment has been scanned
            data = get_env_data(env_name)
            if not data.get("last_scanned"):
                if messagebox.askyesno(
                    "No Scan Data", 
                    f"Environment '{env_name}' hasn't been scanned yet.\nWould you like to scan it first?"
                ):
                    self.scan_environment_now(env_name)
                return
            
            # Launch vulnerability insights app
            self.launch_vulnerability_insights(env_name)

        except Exception as e:
            show_error(f"Failed to show vulnerability report: {str(e)}")

    def launch_vulnerability_insights(self, env_name):
        """Launch the Vulnerability Insights application."""
        root = ctk.CTk()
        app = VulnerabilityInsightsApp(root, env_name)
        root.mainloop()

    def scan_environment_now(self, env_name):
        """Handle Scan Now action with run_async"""
        if not messagebox.askyesno("Confirm", f"Scan environment '{env_name}' for vulnerabilities?"):
            return

        def scan_task():
            # db initialization
            db = DBHelper().init_db()

            # start scan
            scanner = SecurityMatrix()
            if not scanner.scan_env(env_name, log_callback=lambda msg: self.env_log_queue.put(msg)):
                raise RuntimeError("Scanner failed to start.")
            # update last scanned time
            set_env_data(env_name, last_scanned=DT.now().isoformat())
            self.env_log_queue.put(f"Environment '{env_name}' scan completed.")

        # Run scan asynchronously
        self.run_async(
            scan_task,
            success_msg=f"Environment '{env_name}' scanned successfully.",
            error_msg="Failed to scan environment",
            callback=self.refresh_env_list,
            py_tonic_action="general",
        )

    def show_updatable_packages(self, updatable_packages):
        if not updatable_packages:
            show_info("All packages are up to date.")
            return

        # Create a new window to display updatable packages
        top = ctk.CTkToplevel(self)
        top.title("Updatable Packages")
        top.geometry("500x320")
        top.transient(self)
        top.grab_set()

        # Center the dialog
        top.geometry(f"+{self.winfo_rootx() + 600}+{self.winfo_rooty() + 300}")

        # Configure grid
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)

        # Treeview for updatable packages
        columns = ("PACKAGE", "CURRENT_VERSION", "NEW_VERSION")
        tree = ttk.Treeview(top, columns=columns, show="headings", height=10, selectmode="extended")
        for col, text, width, anchor in [
            ("PACKAGE", "Package", 140, "w"),
            ("CURRENT_VERSION", "Current Version", 100, "center"),
            ("NEW_VERSION", "New Version", 100, "center"),
           
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)
        tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        for pkg_name, current_version, new_version, _ in updatable_packages:
            tree.insert("", "end", values=(pkg_name, current_version, new_version))

        # select desired
        tree.bind("<Control-a>", lambda event: tree.selection_set(tree.get_children()))

        def update_selected_packages():
            selected_items = tree.selection()
            if not selected_items:
                show_info("No packages selected for update.")
                return
            
            pkg_names = [tree.item(item)["values"][0] for item in selected_items]
            env_name = self.selected_env_var.get().strip()
            self.batch_update_packages(env_name, pkg_names, top)

        def update_all_packages():
            """Update all packages in the list"""
            pkg_names = [tree.item(item)["values"][0] for item in tree.get_children()]
            env_name = self.selected_env_var.get().strip()
            self.batch_update_packages(env_name, pkg_names, top)

        # Button frame
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=(0, 10), sticky="ew", padx=10)
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)

        # Update Selected button
        btn_update = self.btn(btn_frame, "Update Selected", update_selected_packages)
        btn_update.grid(row=0, column=0, padx=5)

        # Update All button
        btn_update_all = self.btn(btn_frame, "Update All", update_all_packages)
        btn_update_all.grid(row=0, column=1, padx=5)

        # Close button
        btn_close = self.btn(btn_frame, "Close", top.destroy)
        btn_close.grid(row=0, column=2, padx=5)

    def check_for_package_updates(self, env_name):
        """Check for package updates in the selected environment."""
        if not env_name:
            show_error("Please select an environment to check for updates.")
            return

        def task():
            try:
                # check_outdated_packages returns a JSON string
                result_json = check_outdated_packages(env_name, log_callback=lambda msg: self.env_log_queue.put(msg))
                updatable_packages = []
                if result_json:
                    data = json.loads(result_json)
                    # Expecting: [{"name": ..., "version": ..., "latest_version": ..., "latest_filetype": ...}, ...]
                    for pkg in data:
                        updatable_packages.append((
                            pkg.get("name", ""),
                            pkg.get("version", ""),
                            pkg.get("latest_version", ""),
                            pkg.get("latest_filetype", "")
                        ))
                self._safe_after(0, lambda: self.show_updatable_packages(updatable_packages))
            except Exception as e:
                self._safe_after(0, lambda: show_error(f"Failed to check for package updates: {str(e)}"))

        self.run_async(
            task,
            success_msg=None,
            error_msg=None,
            callback=None
        )

    # ===== PACKAGES TABLE =====
    def view_installed_packages(self):
        env_name = self.selected_env_var.get().strip()
        self.packages_list_frame.grid()
        self.refresh_package_list()

    def refresh_package_list(self):
        for widget in self.packages_list_frame.winfo_children():
            widget.destroy()

        env_name = self.selected_env_var.get().strip()
        if not env_name or not is_valid_env_selected(env_name):
            self.selected_env_label.configure(
                text="No valid environment selected.",
                text_color=self.theme.ERROR_COLOR
            )
            self.packages_list_frame.grid_remove()
            return

        try:
            packages = list_packages(env_name)
            columns = ("PACKAGE", "VERSION", "DELETE", "UPDATE")
            self.pkg_tree = ttk.Treeview(
                self.packages_list_frame, columns=columns, show="headings", height=10, selectmode="none"
            )
            for col, text, width, anchor in [
                ("PACKAGE", "Package", 220, "w"),
                ("VERSION", "Version", 100, "center"),
                ("DELETE", "Delete", 80, "center"),
                ("UPDATE", "Update", 80, "center"),
            ]:
                self.pkg_tree.heading(col, text=text)
                self.pkg_tree.column(col, width=width, anchor=anchor)
            self.pkg_tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
            self.update_treeview_style()

            for pkg_name, pkg_version in packages:
                self.pkg_tree.insert("", "end", values=(pkg_name, pkg_version, "🗑️", "⟳"))

            def on_pkg_click(event):
                col = self.pkg_tree.identify_column(event.x)
                row = self.pkg_tree.identify_row(event.y)
                if not row:
                    return
                pkg = self.pkg_tree.item(row)["values"][0]
                if col == "#3":  # Delete
                    if pkg != "pip" and messagebox.askyesno("Confirm", f"Uninstall '{pkg}'?"):
                        self.delete_installed_package(env_name, pkg)
                elif col == "#4":  # Update
                    self.update_installed_package(env_name, pkg)
                

            self.pkg_tree.bind("<Button-1>", on_pkg_click)

        except Exception as e:
            self.packages_list_frame.grid_remove()
            show_error(f"Failed to list packages: {str(e)}")

    # ===== PACKAGE OPS =====
    def _install_package_workflow(self, env_name, package_name, confirm=True, on_complete=None, entry_widget=None, button_widget=None):
        """Reusable install package workflow for both tab and menubar."""
        if not env_name or not package_name:
            show_error("Please select an environment and enter a package name.")
            return
        if confirm and not messagebox.askyesno(
            "Confirm", f"Install '{package_name}' in '{env_name}'?"):
            return
        if button_widget:
            button_widget.configure(state="disabled")
        self.run_async(
            lambda: install_package(env_name, package_name,
                                    log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' installed in '{env_name}'.",
            error_msg="Failed to install package",
            callback=lambda: [
                entry_widget.delete(0, tkinter.END) if entry_widget else None,
                button_widget.configure(state="normal") if button_widget else None,
                self.view_installed_packages() if on_complete is None else on_complete()
            ],
            py_tonic_action="install_package",
        )

    def install_package(self):
        env_name = self.selected_env_var.get().strip()
        package_name = self.entry_package_name.get().strip()
        self._install_package_workflow(
            env_name,
            package_name,
            confirm=bool(self.checkbox_confirm_install.get()),
            entry_widget=self.entry_package_name,
            button_widget=self.btn_install_package
        )

    def delete_installed_package(self, env_name, package_name):
        if self.checkbox_confirm_install.get() and not messagebox.askyesno(
            "Confirm", f"Uninstall '{package_name}' from '{env_name}'?"):
            return
        self.run_async(
            lambda: uninstall_package(env_name, package_name,
                                      log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' uninstalled from '{env_name}'.",
            error_msg="Failed to uninstall package",
            callback=lambda: self.view_installed_packages(),
            py_tonic_action="uninstall_package",
        )

    def update_installed_package(self, env_name, package_name):
        self.run_async(
            lambda: update_package(env_name, package_name,
                                   log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' updated in '{env_name}'.",
            error_msg="Failed to update package",
            callback=lambda: self.view_installed_packages(),
            py_tonic_action="update_package",
        )

    def batch_update_packages(self, env_name, package_names, parent_window=None):
        """Update multiple packages and show a summary of results.
        
        Args:
            env_name: Name of the environment
            package_names: List of package names to update
            parent_window: Parent window to close after update
        """
        if not package_names:
            show_error("No packages to update.")
            return

        def task():
            """Execute updates and collect results"""
            successful = []
            failed = []
            
            for pkg_name in package_names:
                try:
                    update_package(env_name, pkg_name,
                                 log_callback=lambda msg: self.env_log_queue.put(msg))
                    successful.append(pkg_name)
                except Exception as e:
                    failed.append((pkg_name, str(e)))
                    logging.error(f"Failed to update {pkg_name}: {e}")
            
            return successful, failed

        def on_complete(result):
            """Show summary after all updates complete"""
            if result:
                successful, failed = result
                
                # Build summary message
                summary = "Update Summary:\n\n"
                
                if successful:
                    summary += f"✓ Updated Successfully ({len(successful)}):\n"
                    for pkg in successful:
                        summary += f"  • {pkg}\n"
                
                if failed:
                    summary += f"\n✗ Failed ({len(failed)}):\n"
                    for pkg, error in failed:
                        summary += f"  • {pkg}\n"
                
                # Close parent window if provided
                if parent_window:
                    parent_window.destroy()
                
                # Show summary
                messagebox.showinfo("Update Summary", summary)
                
                # Refresh package list
                self.view_installed_packages()

        self.run_async(
            task,
            success_msg=None,
            error_msg=None,
            callback=on_complete
        )

    # ===== BULK OPS =====
    def install_requirements(self):
        env_name = self.selected_env_var.get().strip()
        if not is_valid_env_selected(env_name):
            show_error("Please select a valid environment.")
            return
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.btn_install_requirements.configure(state="disabled")
            self.run_async(
                lambda: import_requirements(env_name, file_path,
                                            log_callback=lambda msg: self.env_log_queue.put(msg)),
                success_msg=f"Requirements from '{file_path}' installed in '{env_name}'.",
                error_msg="Failed to install requirements",
                callback=lambda: self.btn_install_requirements.configure(state="normal"),
                py_tonic_action="import_requirements",
            )

    def export_packages(self):
        env_name = self.selected_env_var.get().strip()
        if not is_valid_env_selected(env_name):
            show_error("Please select a valid environment.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            self.run_async(
                lambda: export_requirements(env_name, file_path),
                success_msg=f"Packages exported to {file_path}.",
                error_msg="Failed to export packages",
                py_tonic_action="export_requirements",
            )

    # ===== ENV OPS =====
    def activate_with_dir(self):
        env = self.selected_env_var.get()
        directory = self.dir_var.get().strip() or None
        open_with = self.open_with_var.get() or ""

        if not env:
            show_error("Please select an environment to activate.")
            return
        self.activate_button.configure(state="disabled")
        self.run_async(
            lambda: activate_env(env, directory, open_with, log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Environment '{env}' activated successfully in {open_with}.",
            error_msg="Failed to activate environment",
            callback=lambda: self.activate_button.configure(state="normal"),
            py_tonic_action="activate_env",
        )


    def show_detected_version(self, path):
        version = is_valid_python_version_detected(path)
        if not version:
            detected_version = "Please choose valid python or leave empty for default"
            # Set error color here for immediate feedback
            self.python_version_info.configure(
                text=f"USING PYTHON: {detected_version}",
                text_color=self.theme.ERROR_COLOR,
            )
            self.entry_python_path.delete(0, tkinter.END)
            self.entry_python_path.insert(0, "")
        else:
            detected_version = version
            # Set highlight color for success
            self.python_version_info.configure(
                text=f"USING PYTHON: {detected_version}",
                text_color=self.theme.HIGHLIGHT_COLOR,
            )
        return detected_version

    def browse_python_path(self, choice=None):
        if choice:
            self.entry_python_path.delete(0, tkinter.END)
            self.entry_python_path.insert(0, choice)
            self.choosen_python_var.set("")
            self.show_detected_version(choice)
            return
        selected = filedialog.askopenfilename(
            title="Select Python Interpreter",
            filetypes=[("Python Executable", "python.exe"), ("All Files", "*")]
        )
        if selected:
            self.entry_python_path.delete(0, tkinter.END)
            self.entry_python_path.insert(0, selected)
            self.choosen_python_var.set("")
            self.show_detected_version(selected)

    def browse_dir(self):
        selected = filedialog.askdirectory()
        if selected:
            self.dir_var.set(selected)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        try:
            self.app_config.set_param("settings", "appearance_mode", new_appearance_mode)
            self.preferences = self.configuration_service.load_preferences()
        except Exception as exc:
            logging.warning(f"Failed to save appearance mode: {exc}")
        self.update_treeview_style()
        self.refresh_env_list()

    def change_scaling_event(self, new_scaling: str):
        ctk.set_widget_scaling(int(new_scaling.replace("%", "")) / 100)
        try:
            self.app_config.set_param("settings", "ui_scaling", new_scaling)
            self.preferences = self.configuration_service.load_preferences()
        except Exception as exc:
            logging.warning(f"Failed to save UI scaling: {exc}")

    def on_tab_changed(self):
        if self.tabview.get() == "Packages":
            env_name = self.selected_env_var.get().strip()
            if is_valid_env_selected(env_name):
                self.selected_env_label.configure(
                    text=f"Selected Environment: {env_name}",
                    text_color=self.theme.HIGHLIGHT_COLOR,
                    image=self.icons.get("selected-env"),
                    compound="left"
                )
            else:
                self.selected_env_label.configure(
                    text="No valid environment selected.",
                    text_color=self.theme.ERROR_COLOR
                )
            self.packages_list_frame.grid_remove()

    def _on_env_runtime_selected(self):
        """Reflect the runtime choice in the info label; explicit path wins."""
        if getattr(self, "entry_python_path", None) and self.entry_python_path.get().strip():
            return
        choice = self.env_runtime_var.get().strip() if hasattr(self, "env_runtime_var") else ""
        if choice and choice not in ("System Default", "Loading..."):
            self.python_version_info.configure(
                text=f"USING PYTHON: Python {choice} (managed runtime)",
                text_color=self.theme.HIGHLIGHT_COLOR,
            )
        else:
            self.python_version_info.configure(
                text="USING PYTHON: Default",
                text_color=self.theme.HIGHLIGHT_COLOR,
            )

    def _set_env_runtime_hint(self, text, color=None):
        if not hasattr(self, "env_runtime_hint"):
            return
        try:
            self.env_runtime_hint.configure(
                text=text, text_color=color or self.theme.SECONDARY_COLOR
            )
        except Exception:
            pass

    def refresh_env_runtime_choices(self):
        """Refresh managed Python runtime choices without blocking the GUI."""
        if not hasattr(self, "env_runtime_menu"):
            return

        provider_name = (self.preferences.runtime_provider if self.preferences else "Python Install Manager")
        try:
            provider = self._get_runtime_provider(provider_name)
        except Exception as exc:
            logging.warning("Invalid runtime provider %r: %s", provider_name, exc)
            provider = self._get_runtime_provider("System")

        self.env_runtime_menu.configure(values=["Loading..."])
        self.env_runtime_var.set("Loading...")
        self._set_env_runtime_hint(f"Loading {provider.NAME} runtimes...")

        def task():
            try:
                installed = provider.list_installed() if provider.is_available() else []
                provider_error = None
            except Exception as exc:
                logging.warning("Failed to load managed Python runtimes: %s", exc)
                installed = []
                provider_error = str(exc)

            values = ["System Default"] + [rt.version for rt in installed]
            preferred = (self.preferences.default_python if self.preferences else "").strip()

            def apply():
                try:
                    if not self.winfo_exists():
                        return
                    self.env_runtime_menu.configure(values=values)
                    current = self.env_runtime_var.get().strip()
                    if current and current not in ("Loading...", "") and current in values:
                        self.env_runtime_var.set(current)
                    elif preferred and preferred in values:
                        self.env_runtime_var.set(preferred)
                    else:
                        self.env_runtime_var.set("System Default")
                    if provider_error:
                        self._set_env_runtime_hint(
                            "Could not load runtimes; using System Default.",
                            self.theme.WARNING_COLOR,
                        )
                    elif not installed:
                        if provider.NAME == "Python Install Manager":
                            self._set_env_runtime_hint(
                                "Install Manager not found; using system Python.",
                                self.theme.WARNING_COLOR,
                            )
                        elif provider.NAME == "Custom":
                            self._set_env_runtime_hint(
                                "Set an explicit interpreter in Configuration > Python.",
                                self.theme.WARNING_COLOR,
                            )
                        else:
                            self._set_env_runtime_hint(
                                f"{len(installed)} system runtime(s) found.",
                            )
                    else:
                        self._set_env_runtime_hint(
                            f"{len(installed)} runtime(s) via {provider.NAME}.",
                        )
                    self._on_env_runtime_selected()
                except Exception:
                    pass

            self._safe_after(0, apply)

        threading.Thread(target=task, daemon=True).start()

    def create_env(self):
        env_name = self.entry_env_name.get().strip()
        python_path = self.entry_python_path.get().strip() or None
        if not env_name:
            messagebox.showerror("Error", "Please enter an environment name.")
            return
        if is_valid_env_selected(env_name):
            messagebox.showerror("Error", f"Environment '{env_name}' already exists.")
            return

        # Get selected package manager from create env section
        selected_pkg_mgr = self.create_env_pkg_mgr.get()

        # Temporarily set the preference to use in create_env function
        from py_env_studio.core.env_manager import set_preferred_package_manager
        set_preferred_package_manager(selected_pkg_mgr)

        requested_version = self._version_from_python_path(python_path)
        runtime_choice = self.env_runtime_var.get().strip() if hasattr(self, "env_runtime_var") else "System Default"
        if runtime_choice in ("", "Loading..."):
            runtime_choice = "System Default"

        # An explicit interpreter path wins. Otherwise use the selected managed
        # runtime, falling back to the configured default runtime.
        if not python_path and runtime_choice not in ("", "System Default"):
            requested_version = runtime_choice
        elif not python_path:
            configured_default = (self.preferences.default_python if self.preferences else "").strip()
            if configured_default and configured_default.lower() != "system default":
                requested_version = configured_default

        if requested_version:
            try:
                provider = self._get_runtime_provider(
                    self.preferences.runtime_provider if self.preferences else "Python Install Manager"
                )
            except Exception as exc:
                logging.warning("Invalid runtime provider; using system Python: %s", exc)
                provider = self._get_runtime_provider("System")
            self._resolve_env_runtime_then_create(
                env_name=env_name,
                python_path=python_path,
                upgrade_pip=bool(self.checkbox_upgrade_pip.get()),
                requested_version=requested_version,
                provider=provider,
            )
            return

        self._start_env_creation(env_name, python_path, bool(self.checkbox_upgrade_pip.get()))

    @staticmethod
    def _version_from_python_path(python_path) -> str | None:
        """Return a bare version token (3.11.11) when a chosen path reveals one."""
        if not python_path:
            return None
        detected = is_valid_python_version_detected(python_path)
        if detected and detected.startswith("Python "):
            return detected.split(" ", 1)[1].strip()
        return None

    def _start_env_creation(self, env_name: str, python_path, upgrade_pip: bool) -> None:
        """Begin async environment creation using the existing workflow/helpers."""
        self.btn_create_env.configure(state="disabled")
        self.run_async(
            lambda: create_env(env_name, python_path, upgrade_pip,
                               log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Environment '{env_name}' created successfully.",
            error_msg="Failed to create environment",
            callback=lambda: [
                self.entry_env_name.delete(0, tkinter.END),
                self.entry_python_path.delete(0, tkinter.END),
                self.btn_create_env.configure(state="normal"),
                self.refresh_env_list()
            ],
            py_tonic_action="create_env",
        )


    def _resolve_env_runtime_then_create(self, env_name: str, python_path,
                                         upgrade_pip: bool, requested_version: str,
                                         provider) -> None:
        """Resolve the requested runtime off-thread; install when missing, then create."""
        self.btn_create_env.configure(state="disabled")
        self.env_log_queue.put(f"Checking Python {requested_version}...")

        def task():
            executable = None
            lookup_error = None
            try:
                if provider.is_available():
                    executable = provider.get_executable(requested_version)
            except Exception as exc:
                lookup_error = exc
            if executable:
                self._safe_after(
                    0,
                    lambda: self._start_env_creation(env_name, executable, upgrade_pip),
                )
                return
            if lookup_error is not None:
                self._safe_after(0, lambda: self._on_env_runtime_check_failed(
                    lookup_error, env_name, python_path, upgrade_pip))
                return
            # Not installed (or provider cannot supply it).
            if python_path:
                # Explicit path was given: continue with it instead of stalling.
                self._safe_after(
                    0,
                    lambda: self._start_env_creation(env_name, python_path, upgrade_pip),
                )
                return

            def ask_install():
                try:
                    can_install = provider.NAME == "Python Install Manager" and provider.is_available()
                except Exception:
                    can_install = False
                if not can_install:
                    self.env_log_queue.put(
                        f"Python {requested_version} is not available via {provider.NAME}; "
                        "creating with system Python."
                    )
                    self._start_env_creation(env_name, None, upgrade_pip)
                    return
                answer = messagebox.askyesno(
                    "Python Not Installed",
                    f"Python {requested_version} is required but is not installed.\n\n"
                    f"{provider.NAME} can install it now.",
                )
                if not answer:
                    self.btn_create_env.configure(state="normal")
                    return
                self._install_runtime_for_env(
                    env_name, python_path, upgrade_pip, requested_version, provider)

            self._safe_after(0, ask_install)

        threading.Thread(target=task, daemon=True).start()

    def _on_env_runtime_check_failed(self, exc: Exception, env_name=None,
                                     python_path=None, upgrade_pip=False) -> None:
        """Keep UI responsive when runtime lookup fails; fall back to saved Python."""
        logging.warning("Runtime lookup during env creation failed: %s", exc)
        self.env_log_queue.put("Runtime lookup failed; creating with configured Python.")
        if env_name:
            self._start_env_creation(env_name, python_path, bool(upgrade_pip))
        else:
            self.btn_create_env.configure(state="normal")

    def _install_runtime_for_env(self, env_name, python_path, upgrade_pip,
                                 requested_version, provider) -> None:
        """Install the requested runtime without blocking the UI, then continue."""
        self.env_log_queue.put(f"Installing Python {requested_version}...")

        def task():
            try:
                result = provider.install(
                    requested_version,
                    log_callback=lambda msg: self.env_log_queue.put(msg),
                )
            except Exception as exc:
                logging.warning("Python %s installation failed: %s", requested_version, exc)
                self._safe_after(0, lambda: self._on_env_runtime_install_failed(
                    env_name, requested_version, str(exc)))
                return
            if not result:
                self._safe_after(0, lambda: self._on_env_runtime_install_failed(
                    env_name, requested_version, "installation reported failure"))
                return
            # Verify off the UI thread: listing/installation may take seconds.
            try:
                executable = provider.get_executable(requested_version)
            except Exception as exc:
                self._safe_after(0, lambda: self._on_env_runtime_install_failed(
                    env_name, requested_version, str(exc)))
                return
            if not executable:
                self._safe_after(0, lambda: self._on_env_runtime_install_failed(
                    env_name, requested_version,
                    "installed runtime not found after install"))
                return
            self._safe_after(
                0,
                lambda: self._on_env_runtime_installed(
                    env_name, requested_version, executable, upgrade_pip),
            )

        threading.Thread(target=task, daemon=True).start()

    def _on_env_runtime_installed(self, env_name, requested_version,
                                  executable, upgrade_pip) -> None:
        self.env_log_queue.put(f"Python {requested_version} installed")
        self.refresh_env_runtime_choices()
        self._start_env_creation(env_name, executable, upgrade_pip)

    def _on_env_runtime_install_failed(self, env_name: str, requested_version: str,
                                       details: str) -> None:
        """Report install failure and offer retry while staying in the create flow."""
        logging.warning("Python %s install for env %s failed: %s",
                        requested_version, env_name, details)
        try:
            retry = messagebox.askretrycancel(
                "Python Installation Failed",
                f"Python {requested_version} installation failed.\n\n"
                f"Details: {details}",
            )
        except Exception:
            retry = False
        if retry:
            try:
                provider = self._get_runtime_provider(
                    self.preferences.runtime_provider if self.preferences else "Python Install Manager"
                )
            except Exception:
                provider = None
            if provider is not None and provider.NAME == "Python Install Manager":
                self._install_runtime_for_env(
                    self.entry_env_name.get().strip() or env_name,
                    self.entry_python_path.get().strip() or None,
                    bool(self.checkbox_upgrade_pip.get()),
                    requested_version, provider)
                return
        self.btn_create_env.configure(state="normal")

    def _resolve_python_for_env(self, version: str, log_queue) -> tuple[bool, str]:
        """Deprecated synchronous helper retained only for backward compatibility."""
        logging.warning("_resolve_python_for_env is deprecated; env creation now uses the async flow.")
        return False, ""

    def show_about_dialog(self):
        show_info(f"PyEnvStudio: Manage Python virtual environments and packages.\n\n"
                  f"Created by: Wasim Shaikh\nVersion: {self.version}\n\nVisit: https://github.com/contactshaikhwasim")

    def show_preferences_dialog(self):
        """Show configuration dialog for PES defaults."""
        from py_env_studio.core import uv_tools

        current = self.configuration_service.load_preferences()

        top = ctk.CTkToplevel(self)
        top.title("Configuration")
        top.geometry("880x640")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 230}+{self.winfo_rooty() + 90}")

        header = ctk.CTkLabel(top, text="Configuration", font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        body = ctk.CTkScrollableFrame(top)
        body.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        default_venv_var = tkinter.StringVar(value=current.default_venv_path)
        package_manager_var = tkinter.StringVar(value=current.default_package_manager)
        project_tool_var = tkinter.StringVar(value=current.default_project_tool or "Default")
        create_venv_var = tkinter.IntVar(value=1 if current.template_create_venv_default else 0)
        init_git_var = tkinter.IntVar(value=1 if current.template_initialize_git_default else 0)
        appearance_var = tkinter.StringVar(value=current.appearance_mode)
        scaling_var = tkinter.StringVar(value=current.ui_scaling)
        runtime_provider_var = tkinter.StringVar(value=current.runtime_provider)
        default_python_rt_var = tkinter.StringVar(
            value=current.default_python.strip() or "System Default"
        )

        python_map: dict[str, tuple[str, str]] = {"System Default": ("", "")}
        python_labels = ["System Default"]
        for interpreter in list_pythons():
            detected_version = is_valid_python_version_detected(interpreter)
            version = ""
            if detected_version and detected_version.startswith("Python "):
                version = detected_version.split(" ", 1)[1]
            label = f"{detected_version or 'Python (unknown)'} - {interpreter}"
            python_labels.append(label)
            python_map[label] = (interpreter, version)

        default_python_label = "System Default"
        for label, (path_value, version_value) in python_map.items():
            if current.default_python_path and path_value == current.default_python_path:
                default_python_label = label
                break
            if not current.default_python_path and current.default_python_version and version_value.startswith(current.default_python_version):
                default_python_label = label

        default_python_var = tkinter.StringVar(value=default_python_label)

        available_tools = discover_project_open_tools(self.open_with_tools, include_default=True)
        tool_display_to_id = {tool["display_name"]: tool["tool_id"] for tool in available_tools}
        tool_id_to_display = {tool["tool_id"]: tool["display_name"] for tool in available_tools}
        tool_labels = list(tool_display_to_id.keys())

        if current.default_project_tool in tool_id_to_display:
            project_tool_var.set(tool_id_to_display[current.default_project_tool])
        elif tool_labels:
            project_tool_var.set(tool_labels[0])

        self.lbl(body, "General", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, padx=8, pady=(6, 4), sticky="w")
        self.lbl(body, "Appearance Mode:", font=self.theme.FONT_BOLD).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.optmenu(body, ["Light", "Dark", "System"], var=appearance_var).grid(row=1, column=1, padx=8, pady=6, sticky="w")
        self.lbl(body, "UI Scaling:", font=self.theme.FONT_BOLD).grid(row=2, column=0, padx=8, pady=6, sticky="w")
        self.optmenu(body, ["80%", "90%", "100%", "110%", "120%"], var=scaling_var).grid(row=2, column=1, padx=8, pady=6, sticky="w")

        self.lbl(body, "Environment", font=("Segoe UI", 14, "bold")).grid(row=3, column=0, columnspan=2, padx=8, pady=(14, 4), sticky="w")
        self.lbl(body, "Default Virtual Environment Location:", font=self.theme.FONT_BOLD).grid(row=4, column=0, padx=8, pady=6, sticky="w")
        venv_row = ctk.CTkFrame(body, fg_color="transparent")
        venv_row.grid(row=4, column=1, padx=8, pady=6, sticky="ew")
        venv_row.grid_columnconfigure(0, weight=1)
        self.entry(venv_row, var=default_venv_var, width=420).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.btn(
            venv_row,
            "Browse",
            lambda: default_venv_var.set(filedialog.askdirectory() or default_venv_var.get()),
            width=90,
        ).grid(row=0, column=1, padx=0, pady=0)

        self.lbl(body, "Python", font=("Segoe UI", 14, "bold")).grid(row=5, column=0, columnspan=2, padx=8, pady=(14, 4), sticky="w")
        self.lbl(body, "Explicit Interpreter Override:", font=self.theme.FONT_BOLD).grid(row=6, column=0, padx=8, pady=6, sticky="w")
        self.optmenu(body, python_labels, var=default_python_var, width=620).grid(row=6, column=1, padx=8, pady=6, sticky="ew")

        # ---- Python Runtime section ----
        self.lbl(body, "Python Runtime", font=("Segoe UI", 14, "bold")).grid(row=7, column=0, columnspan=2, padx=8, pady=(14, 4), sticky="w")
        self.lbl(body, "Runtime Provider:", font=self.theme.FONT_BOLD).grid(row=8, column=0, padx=8, pady=6, sticky="w")
        self.runtime_provider_menu = self.optmenu(
            body, list(self.configuration_service.SUPPORTED_RUNTIME_PROVIDERS),
            var=runtime_provider_var, width=250,
            cmd=lambda value: self._populate_runtime_ui(runtime_provider_var, default_python_rt_var, status_label),
        )
        self.runtime_provider_menu.grid(row=8, column=1, padx=8, pady=6, sticky="ew")
        self.lbl(body, "Default Python:", font=self.theme.FONT_BOLD).grid(row=9, column=0, padx=8, pady=6, sticky="w")
        self.default_python_rt_menu = self.optmenu(body, ["Loading..."], var=default_python_rt_var, width=250)
        self.default_python_rt_menu.grid(row=9, column=1, padx=8, pady=6, sticky="ew")
        self.lbl(body, "Installed Runtimes", font=("Segoe UI", 11, "bold")).grid(row=10, column=0, columnspan=2, padx=8, pady=(10, 2), sticky="w")
        self.installed_runtimes_frame = ctk.CTkScrollableFrame(body, height=120)
        self.installed_runtimes_frame.grid(row=11, column=0, columnspan=2, padx=8, pady=2, sticky="nsew")
        self.lbl(body, "Available to Install", font=("Segoe UI", 11, "bold")).grid(row=12, column=0, columnspan=2, padx=8, pady=(10, 2), sticky="w")
        self.available_runtimes_frame = ctk.CTkScrollableFrame(body, height=120)
        self.available_runtimes_frame.grid(row=13, column=0, columnspan=2, padx=8, pady=2, sticky="nsew")
        refresh_row = ctk.CTkFrame(body, fg_color="transparent")
        refresh_row.grid(row=14, column=0, columnspan=2, padx=8, pady=(8, 0), sticky="ew")
        self.btn(refresh_row, "Refresh", lambda: self._refresh_runtime_ui(top, runtime_provider_var, default_python_rt_var, status_label), width=100).pack(side="left")
        self._runtime_cache_label = self.lbl(refresh_row, "Last checked: never", font=("Segoe UI", 10), text_color=self.theme.SECONDARY_COLOR)
        self._runtime_cache_label.pack(side="left", padx=(12, 0))
        self.lbl(body, "Package Manager", font=("Segoe UI", 14, "bold")).grid(row=15, column=0, columnspan=2, padx=8, pady=(14, 4), sticky="w")
        pm_row = ctk.CTkFrame(body, fg_color="transparent")
        pm_row.grid(row=16, column=0, columnspan=2, padx=8, pady=6, sticky="w")
        pip_radio = ctk.CTkRadioButton(pm_row, text="pip", variable=package_manager_var, value="pip")
        pip_radio.grid(row=0, column=0, padx=(0, 18), pady=4, sticky="w")
        uv_text = "uv" if uv_tools.is_uv_installed() else "uv (Not Installed)"
        uv_radio = ctk.CTkRadioButton(pm_row, text=uv_text, variable=package_manager_var, value="uv")
        uv_radio.grid(row=0, column=1, padx=0, pady=4, sticky="w")

        self.lbl(body, "Project / Templates", font=("Segoe UI", 14, "bold")).grid(row=17, column=0, columnspan=2, padx=8, pady=(14, 4), sticky="w")
        self.lbl(body, "Default Project Tool:", font=self.theme.FONT_BOLD).grid(row=18, column=0, padx=8, pady=6, sticky="w")
        self.optmenu(body, tool_labels, var=project_tool_var, width=320).grid(row=18, column=1, padx=8, pady=6, sticky="w")
        self.chk(body, "Create virtual environment automatically", variable=create_venv_var).grid(row=19, column=0, columnspan=2, padx=8, pady=6, sticky="w")
        self.chk(body, "Initialize Git repository", variable=init_git_var).grid(row=20, column=0, columnspan=2, padx=8, pady=6, sticky="w")

        status_label = self.lbl(body, "", text_color=self.theme.HIGHLIGHT_COLOR)
        status_label.grid(row=21, column=0, columnspan=2, padx=8, pady=(4, 8), sticky="w")

        def collect_preferences() -> AppPreferences:
            selected_python_label = default_python_var.get().strip() or "System Default"
            python_path, python_version = python_map.get(selected_python_label, ("", ""))
            selected_tool_display = project_tool_var.get().strip()
            selected_tool_id = tool_display_to_id.get(selected_tool_display, "default")
            default_python_value = default_python_rt_var.get().strip()
            if default_python_value.lower() == "system default":
                default_python_value = ""
            return AppPreferences(
                default_venv_path=default_venv_var.get().strip(),
                default_python_path=python_path,
                default_python_version=python_version,
                default_package_manager=package_manager_var.get().strip().lower(),
                default_project_tool=selected_tool_id,
                open_with_tools=current.open_with_tools,
                template_create_venv_default=bool(create_venv_var.get()),
                template_initialize_git_default=bool(init_git_var.get()),
                appearance_mode=appearance_var.get().strip() or "System",
                ui_scaling=scaling_var.get().strip() or "100%",
                runtime_provider=runtime_provider_var.get().strip() or "Python Install Manager",
                default_python=default_python_value,
            )

        def apply_runtime_preferences(saved: AppPreferences) -> None:
            refresh_runtime_config()
            refresh_runtime_paths()
            self.preferences = saved
            self.open_with_tools = self._load_open_with_tools()
            self.open_with_dropdown.configure(values=self.open_with_tools)
            if self.open_with_var.get() not in self.open_with_tools:
                self.open_with_var.set(self.open_with_tools[0])

            ctk.set_appearance_mode(saved.appearance_mode)
            ctk.set_widget_scaling(int(saved.ui_scaling.replace("%", "")) / 100)
            self.create_env_pkg_mgr.set(saved.default_package_manager)

            self.entry_python_path.delete(0, tkinter.END)
            if saved.default_python_path:
                self.entry_python_path.insert(0, saved.default_python_path)

            self.refresh_env_runtime_choices()
            self.refresh_env_list()
            self.env_log_queue.put("[Configuration] Settings updated")

        def persist(close_after_save: bool) -> None:
            try:
                new_preferences = collect_preferences()
                valid_tool_ids = [tool["tool_id"] for tool in available_tools]
                self.configuration_service.validate_preferences(
                    new_preferences,
                    available_project_tools=valid_tool_ids,
                )
                self.configuration_service.save_preferences(new_preferences)
                apply_runtime_preferences(new_preferences)
                status_label.configure(
                    text="Configuration saved successfully.",
                    text_color=self.theme.HIGHLIGHT_COLOR,
                )
                if close_after_save:
                    top.destroy()
            except ConfigurationError as exc:
                status_label.configure(text=str(exc), text_color=self.theme.ERROR_COLOR)
                show_error(str(exc))
            except Exception as exc:
                status_label.configure(text="Failed to save configuration.", text_color=self.theme.ERROR_COLOR)
                show_error(f"Failed to save configuration: {exc}")

        def reset_defaults() -> None:
            if not messagebox.askyesno(
                "Reset Configuration?",
                "This will restore Py Env Studio defaults.\n\nContinue?",
            ):
                return
            try:
                defaults = self.configuration_service.reset_to_defaults()
                apply_runtime_preferences(defaults)
                status_label.configure(text="Configuration reset to defaults.", text_color=self.theme.HIGHLIGHT_COLOR)
                show_info("Configuration reset to defaults.")
                top.destroy()
            except Exception as exc:
                show_error(f"Failed to reset configuration: {exc}")

        footer = ctk.CTkFrame(top)
        footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        self.btn(footer, "Reset to Defaults", reset_defaults, width=150).pack(side="left", padx=8, pady=8)
        self.btn(footer, "Cancel", top.destroy, width=100).pack(side="right", padx=8, pady=8)
        self.btn(footer, "Save", lambda: persist(close_after_save=True), width=100).pack(side="right", padx=8, pady=8)
        self.btn(footer, "Apply", lambda: persist(close_after_save=False), width=100).pack(side="right", padx=8, pady=8)

        # Load runtime provider data asynchronously
        self._populate_runtime_ui(runtime_provider_var, default_python_rt_var, status_label)

    def _get_runtime_provider(self, provider_name: str) -> "RuntimeProvider":
        """Return the configured runtime provider instance (never None)."""
        normalized = (provider_name or "").strip() or "Python Install Manager"
        if normalized == "Custom":
            custom_path = ""
            try:
                custom_path = (self.preferences.default_python_path or "").strip()
            except Exception:
                custom_path = ""
            return get_runtime_provider(normalized, custom_path=custom_path)
        return get_runtime_provider(normalized)

    def _populate_runtime_ui(self, provider_var, default_python_var, status_label, force_refresh: bool = False) -> None:
        """Load runtime information without unnecessary network access.

        Normal flow (Configuration open): installed runtimes are read
        locally, official releases come from the DB cache, and the UI
        renders immediately. The online catalogue (``py list --online``)
        runs at most once, only when the cache is missing/expired or the
        user explicitly clicks Refresh (``force_refresh=True``). Expired
        caches render stale data first, then refresh in the background.
        """
        from py_env_studio.core.runtime_cache import RuntimeCache

        provider_name = provider_var.get().strip() or "Python Install Manager"
        installed_frame = self.installed_runtimes_frame
        available_frame = self.available_runtimes_frame
        default_menu = self.default_python_rt_menu
        generation = getattr(self, "_runtime_ui_generation", 0) + 1
        self._runtime_ui_generation = generation
        self._clear_frame(installed_frame)
        self._clear_frame(available_frame)
        self.lbl(
            installed_frame,
            "Loading installed runtimes...",
            text_color=self.theme.SECONDARY_COLOR,
        ).pack(anchor="w", padx=8, pady=4)
        self.lbl(
            available_frame,
            "Loading official Python releases..." if provider_name == "Python Install Manager" else "Loading runtimes...",
            text_color=self.theme.SECONDARY_COLOR,
        ).pack(anchor="w", padx=8, pady=4)
        status_label.configure(
            text=f"Loading {provider_name}...",
            text_color=self.theme.SECONDARY_COLOR,
        )

        def task():
            try:
                provider = self._get_runtime_provider(provider_name)
            except Exception as exc:
                self._safe_after(0, lambda: self._show_runtime_unavailable(
                    provider_var, default_python_var, status_label,
                    message=str(exc), generation=generation))
                return

            cache = RuntimeCache()
            error = None
            installed: list = []
            cached: list = []
            available_flag = False
            last_checked = None
            stale = True
            cache_present = False
            usage: dict = {}
            updates: dict = {}
            background_pending = False
            try:
                available_flag = provider.is_available()
                if not available_flag:
                    error = f"{provider_name} is not available on this system."
                elif getattr(provider, "NAME", "") != "Python Install Manager":
                    installed = provider.list_installed()
                else:
                    # Local state first: no network on this path.
                    try:
                        installed = provider.list_installed()
                    except Exception as exc:
                        logging.warning("Local installed-runtime query failed: %s", exc)
                        installed = []
                    cached, last_updated = cache.load_cached(provider.NAME)
                    last_checked = last_updated
                    cache_present = bool(cached)
                    stale = not cache.is_fresh(last_updated)
                    available = RuntimeCache.filter_available(cached, installed)
                    from py_env_studio.core.runtime_cache import map_runtime_usage
                    try:
                        usage = map_runtime_usage(installed)
                    except Exception:
                        usage = {}
                    try:
                        updates = cache.update_candidates(installed, cached)
                    except Exception:
                        updates = {}
                    needs_online = force_refresh or not cache_present or stale
                    if needs_online:
                        if cache_present and stale and not force_refresh:
                            # Stale-while-revalidate: render stale now,
                            # refresh in this same background thread.
                            background_pending = True
                            self._safe_after(0, lambda _i=list(installed), _a=list(available), _u=dict(usage), _up=dict(updates), _lc=last_checked: self._update_runtime_ui(
                                provider_name, _i, _a,
                                available_flag, default_python_var, status_label,
                                error=None, generation=generation,
                                last_checked=_lc, stale=True,
                                cache_present=cache_present, usage=_u,
                                updates=_up, refreshing=True,
                            ))
                        try:
                            fresh = cache.refresh_online(provider, provider_name=provider.NAME)
                            cached = fresh
                            _, last_updated = cache.load_cached(provider.NAME)
                            last_checked = last_updated
                            cache_present = bool(cached)
                            stale = False
                            available = RuntimeCache.filter_available(cached, installed)
                            try:
                                updates = cache.update_candidates(installed, cached)
                            except Exception:
                                updates = {}
                        except Exception as exc:
                            logging.warning("Online metadata refresh failed; using cache: %s", exc)
                            if not cache_present:
                                error = (
                                    "No online release information is currently available. "
                                    "Check your connection and click Refresh to retry."
                                )
                                cached = []
                                available = []
                            else:
                                error = (
                                    "⚠ Unable to refresh Python release information. "
                                    "Showing cached data."
                                )
                    else:
                        available = RuntimeCache.filter_available(cached, installed)
                    if not background_pending:
                        shown_available = available if getattr(provider, "NAME", "") == "Python Install Manager" else []
                        if getattr(provider, "NAME", "") != "Python Install Manager":
                            cached = []
                        self._safe_after(0, lambda _i=list(installed), _a=list(shown_available), _c=list(cached), _u=dict(usage), _up=dict(updates), _lc=last_checked, _e=error, _s=stale, _cp=cache_present: self._update_runtime_ui(
                            provider_name, _i, _a,
                            available_flag, default_python_var, status_label,
                            error=_e, generation=generation,
                            last_checked=_lc, stale=_s,
                            cache_present=_cp, usage=_u,
                            updates=_up, refreshing=False,
                        ))
                        return
                    # Stale was already rendered; now render the refreshed state.
                    shown_available = available if getattr(provider, "NAME", "") == "Python Install Manager" else []
                    self._safe_after(0, lambda _i=list(installed), _a=list(shown_available), _c=list(cached), _u=dict(usage), _up=dict(updates), _lc=last_checked, _e=error, _s=stale, _cp=cache_present: self._update_runtime_ui(
                        provider_name, _i, _a,
                        available_flag, default_python_var, status_label,
                        error=_e, generation=generation,
                        last_checked=_lc, stale=_s,
                        cache_present=_cp, usage=_u,
                        updates=_up, refreshing=False,
                    ))
                    return
            except Exception as exc:
                error = str(exc)
                logging.warning("Failed to load runtime data from %s: %s", provider_name, exc)

            # Fallthrough: non-PyManager providers, unavailable providers, or
            # unexpected errors. (The PyManager path always renders above.)
            _installed = list(installed) if isinstance(installed, list) else []
            self._safe_after(0, lambda: self._update_runtime_ui(
                provider_name, _installed, [],
                available_flag, default_python_var, status_label,
                error=error, generation=generation,
            ))

        threading.Thread(target=task, daemon=True).start()

    def _show_runtime_unavailable(self, provider_var, default_python_var, status_label,
                                  message=None, generation=None) -> None:
        """Display the provider-unavailable state."""
        if generation is not None and generation != getattr(self, "_runtime_ui_generation", generation):
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._clear_frame(self.installed_runtimes_frame)
        self._clear_frame(self.available_runtimes_frame)
        self.lbl(
            self.installed_runtimes_frame,
            message or "Runtime provider is not available on this system.",
            text_color=self.theme.WARNING_COLOR,
        ).pack(anchor="w", padx=8, pady=4)
        self.lbl(
            self.available_runtimes_frame,
            "Choose 'System' to use interpreters already on PATH, or "
            "'Python Install Manager' on Windows to install official releases.",
            text_color=self.theme.SECONDARY_COLOR,
        ).pack(anchor="w", padx=8, pady=2)
        default_python_var.set("System Default")
        self.default_python_rt_menu.configure(values=["System Default"])
        try:
            status_label.configure(
                text=message or "Selected runtime provider is not available.",
                text_color=self.theme.WARNING_COLOR,
            )
        except Exception:
            pass

    def _update_runtime_ui(
        self,
        provider_name: str,
        installed: list,
        available: list,
        available_flag: bool,
        default_python_var,
        status_label,
        *,
        error: str | None = None,
        generation=None,
        last_checked=None,
        stale: bool = False,
        cache_present: bool = False,
        usage: dict | None = None,
        updates: dict | None = None,
        refreshing: bool = False,
    ) -> None:
        """Render runtime data (cached official releases minus installed)."""
        if generation is not None and generation != getattr(self, "_runtime_ui_generation", generation):
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            from py_env_studio.core.runtime_cache import _format_age
            if last_checked is not None and getattr(self, "_runtime_cache_label", None) is not None:
                try:
                    if self._runtime_cache_label.winfo_exists():
                        prefix = "⚠ Last checked: " if stale else "Last checked: "
                        self._runtime_cache_label.configure(
                            text=f"{prefix}{_format_age(last_checked)}" + (" (updating…)" if refreshing else ""),
                            text_color=self.theme.WARNING_COLOR if stale else self.theme.SECONDARY_COLOR,
                        )
                except Exception:
                    pass
        except Exception:
            pass
        if not available_flag:
            self._clear_frame(self.installed_runtimes_frame)
            self._clear_frame(self.available_runtimes_frame)
            message = error or f"{provider_name} is not available on this system."
            self.lbl(
                self.installed_runtimes_frame,
                message,
                text_color=self.theme.WARNING_COLOR,
            ).pack(anchor="w", padx=8, pady=4)
            hint = (
                "Use 'System' to work with interpreters already on PATH."
                if provider_name == "Python Install Manager"
                else "Set an explicit interpreter path in Configuration > Python."
                if provider_name == "Custom"
                else "Install a Python interpreter so it can be discovered on PATH."
            )
            self.lbl(
                self.installed_runtimes_frame,
                hint,
                text_color=self.theme.SECONDARY_COLOR,
            ).pack(anchor="w", padx=8, pady=2)
            default_python_var.set("System Default")
            self.default_python_rt_menu.configure(values=["System Default"])
            try:
                status_label.configure(text=message, text_color=self.theme.ERROR_COLOR)
            except Exception:
                pass
            return

        self._clear_frame(self.installed_runtimes_frame)
        if not installed:
            self.lbl(
                self.installed_runtimes_frame,
                "No Python runtimes found for this provider.",
                text_color=self.theme.SECONDARY_COLOR,
            ).pack(anchor="w", padx=8, pady=4)
        else:
            usage = usage or {}
            updates = updates or {}
            for rt in installed:
                details = []
                if rt.implementation:
                    details.append(rt.implementation.upper() if rt.implementation == "cpython" else rt.implementation)
                if rt.architecture:
                    details.append(rt.architecture)
                suffix = f"  ({', '.join(details)})" if details else ""
                row = ctk.CTkFrame(self.installed_runtimes_frame, fg_color="transparent")
                row.pack(fill="x", padx=6, pady=1)
                row.grid_columnconfigure(0, weight=1)
                self.lbl(row, f"✓ Python {rt.version}{suffix}").grid(
                    row=0, column=0, padx=2, pady=1, sticky="w"
                )
                sub_row = 1
                if rt.path:
                    self.lbl(row, rt.path, font=("Segoe UI", 10),
                             text_color=self.theme.SECONDARY_COLOR).grid(
                        row=sub_row, column=0, padx=2, pady=(0, 1), sticky="w"
                    )
                    sub_row += 1
                used_by = list(usage.get(rt.version, []))
                used_label = (
                    f"Used by: {', '.join(used_by)}"
                    if used_by else "Used by: no environments"
                )
                self.lbl(row, used_label, font=("Segoe UI", 10),
                         text_color=self.theme.SECONDARY_COLOR).grid(
                    row=sub_row, column=0, padx=2, pady=(0, 1), sticky="w"
                )
                sub_row += 1
                candidate = updates.get(rt.version)
                if candidate is not None:
                    self.lbl(row, f"Update available → {candidate.version}",
                             font=("Segoe UI", 10),
                             text_color=self.theme.WARNING_COLOR).grid(
                        row=sub_row, column=0, padx=2, pady=(0, 1), sticky="w"
                    )
                    sub_row += 1
                btn_row = ctk.CTkFrame(row, fg_color="transparent")
                btn_row.grid(row=sub_row, column=0, padx=2, pady=(0, 2), sticky="w")
                if candidate is not None:
                    upd_btn = self.btn(btn_row, f"Update → {candidate.version}", lambda: None, width=150)
                    upd_btn.configure(
                        command=lambda r=rt, c=candidate, b=upd_btn: self._update_python(
                            r, c, default_python_var, status_label, install_button=b
                        )
                    )
                    upd_btn.pack(side="left", padx=(0, 6))
                rm_btn = self.btn(btn_row, "Remove", lambda: None, width=85)
                rm_btn.configure(
                    command=lambda r=rt, b=rm_btn: self._uninstall_python(
                        r, default_python_var, status_label, install_button=b
                    )
                )
                rm_btn.pack(side="left")

        self._clear_frame(self.available_runtimes_frame)
        if provider_name != "Python Install Manager":
            self.lbl(
                self.available_runtimes_frame,
                "Only Python Install Manager (Windows) can install official releases here. "
                "'System' lists interpreters already on PATH; 'Custom' uses your explicit path.",
                text_color=self.theme.SECONDARY_COLOR,
            ).pack(anchor="w", padx=8, pady=4)
        elif not available:
            if provider_name == "Python Install Manager" and not cache_present:
                self.lbl(
                    self.available_runtimes_frame,
                    "No online release information is currently available.\n"
                    "Check your connection, then click Refresh to retry.",
                    text_color=self.theme.WARNING_COLOR,
                ).pack(anchor="w", padx=8, pady=4)
            else:
                self.lbl(
                    self.available_runtimes_frame,
                    "Everything installable is already installed, or the online index is unreachable.",
                    text_color=self.theme.SECONDARY_COLOR,
                ).pack(anchor="w", padx=8, pady=4)
        else:
            try:
                provider = self._get_runtime_provider(provider_name)
            except Exception:
                provider = None
            for rt in available:
                row = ctk.CTkFrame(self.available_runtimes_frame, fg_color="transparent")
                row.pack(fill="x", padx=6, pady=2)
                row.grid_columnconfigure(0, weight=1)
                display = f"Python {rt.version}"
                if rt.release_status:
                    display += f"  [{rt.release_status}]"
                self.lbl(row, display).grid(row=0, column=0, padx=(2, 8), pady=2, sticky="w")
                install_btn = self.btn(row, "Install", lambda: None, width=85)
                install_btn.configure(
                    command=lambda r=rt, p=provider, b=install_btn: self._install_python(
                        r, p, default_python_var, status_label, install_button=b
                    )
                )
                install_btn.grid(row=0, column=1, padx=(0, 2), pady=2)

        default_opts = ["System Default"] + [rt.version for rt in installed]
        self.default_python_rt_menu.configure(values=default_opts)
        current_val = default_python_var.get().strip()
        if current_val not in default_opts:
            if self.preferences and self.preferences.default_python in default_opts:
                default_python_var.set(self.preferences.default_python)
            else:
                default_python_var.set("System Default")

        try:
            if error:
                status_label.configure(text=error, text_color=self.theme.WARNING_COLOR)
            elif provider_name == "Python Install Manager":
                stale_note = " (may be outdated)" if stale else ""
                status_label.configure(
                    text=f"Loaded {len(installed)} installed, {len(available)} official releases available to install.{stale_note}",
                    text_color=self.theme.WARNING_COLOR if stale else self.theme.HIGHLIGHT_COLOR,
                )
            else:
                status_label.configure(
                    text=f"Loaded {len(installed)} runtime(s) via {provider_name}.",
                    text_color=self.theme.HIGHLIGHT_COLOR,
                )
        except Exception:
            pass

    def _refresh_runtime_ui(self, top, provider_var, default_python_var, status_label) -> None:
        """Explicit Refresh: permitted to query online metadata (cache policy)."""
        try:
            if top is not None and not top.winfo_exists():
                return
        except Exception:
            return
        self._populate_runtime_ui(provider_var, default_python_var, status_label, force_refresh=True)

    def _install_python(
        self,
        runtime: "PythonRuntime",
        provider: "RuntimeProvider | None",
        default_python_var,
        status_label,
        install_button=None,
    ) -> None:
        """Install a runtime asynchronously and refresh the complete runtime UI."""
        if provider is None or provider.NAME != "Python Install Manager":
            try:
                status_label.configure(
                    text="Install is only supported via Python Install Manager.",
                    text_color=self.theme.ERROR_COLOR,
                )
            except Exception:
                pass
            return

        if install_button is not None:
            try:
                install_button.configure(state="disabled", text="Installing...")
            except Exception:
                pass
        try:
            status_label.configure(
                text=f"Installing Python {runtime.version}...",
                text_color=self.theme.HIGHLIGHT_COLOR,
            )
        except Exception:
            pass
        self.env_log_queue.put(f"Installing Python {runtime.version}...")

        provider_name = provider.NAME
        generation = getattr(self, "_runtime_ui_generation", 0)

        def task():
            try:
                result = provider.install(
                    runtime.version,
                    log_callback=lambda msg: self.env_log_queue.put(msg),
                )
                # Verify with a local query, then recalculate the available
                # list from the DB cache: no online request after install.
                installed = provider.list_installed()
                from py_env_studio.core.runtime_cache import RuntimeCache
                cache = RuntimeCache()
                cached, last_checked = cache.load_cached(provider.NAME)
                available = RuntimeCache.filter_available(cached, installed)
                from py_env_studio.core.runtime_cache import map_runtime_usage
                try:
                    usage = map_runtime_usage(installed)
                except Exception:
                    usage = {}
                try:
                    updates = cache.update_candidates(installed, cached)
                except Exception:
                    updates = {}
                stale = not cache.is_fresh(last_checked)
                available_flag = provider.is_available()
                matched = provider.find_best_match(runtime.version, installed)
                if matched is None:
                    raise RuntimeError(
                        f"Python {runtime.version} was not found after installation."
                    )
                error = None if result else "Installation reported no result."
            except Exception as exc:
                installed = []
                available = []
                cached = []
                usage = {}
                updates = {}
                last_checked = None
                stale = False
                available_flag = False
                error = str(exc)
                logging.warning("Python %s installation failed: %s", runtime.version, exc)

            def on_done():
                try:
                    if not self.winfo_exists():
                        return
                except Exception:
                    return
                if error:
                    if install_button is not None:
                        try:
                            if install_button.winfo_exists():
                                install_button.configure(state="normal", text="Retry")
                        except Exception:
                            pass
                    try:
                        status_label.configure(
                            text=f"Python {runtime.version} installation failed: {error}",
                            text_color=self.theme.ERROR_COLOR,
                        )
                    except Exception:
                        pass
                    return

                if install_button is not None:
                    try:
                        if install_button.winfo_exists():
                            install_button.configure(state="normal", text="Installed")
                    except Exception:
                        pass
                self._update_runtime_ui(
                    provider_name,
                    installed,
                    available,
                    available_flag,
                    default_python_var,
                    status_label,
                    generation=generation,
                    last_checked=last_checked,
                    stale=stale,
                    cache_present=bool(cached),
                    usage=usage,
                    updates=updates,
                )
                self.refresh_env_runtime_choices()

            self._safe_after(0, on_done)

        threading.Thread(target=task, daemon=True).start()

    def _update_python(
        self,
        runtime: "PythonRuntime",
        candidate: "PythonRuntime",
        default_python_var,
        status_label,
        install_button=None,
    ) -> None:
        """Update an installed runtime to a newer cached patch (via manager)."""
        try:
            provider = self._get_runtime_provider("Python Install Manager")
        except Exception as exc:
            try:
                status_label.configure(text=str(exc), text_color=self.theme.ERROR_COLOR)
            except Exception:
                pass
            return
        if install_button is not None:
            try:
                install_button.configure(state="disabled", text="Updating...")
            except Exception:
                pass
        try:
            status_label.configure(
                text=f"Updating Python {runtime.version} → {candidate.version}...",
                text_color=self.theme.HIGHLIGHT_COLOR,
            )
        except Exception:
            pass
        self.env_log_queue.put(f"Updating Python {runtime.version} → {candidate.version}...")

        provider_name = provider.NAME
        generation = getattr(self, "_runtime_ui_generation", 0)

        def task():
            try:
                result = provider.update(
                    runtime.version,
                    log_callback=lambda msg: self.env_log_queue.put(msg),
                )
                installed = provider.list_installed()
                from py_env_studio.core.runtime_cache import RuntimeCache, map_runtime_usage
                cache = RuntimeCache()
                cached, last_checked = cache.load_cached(provider.NAME)
                available = RuntimeCache.filter_available(cached, installed)
                try:
                    usage = map_runtime_usage(installed)
                except Exception:
                    usage = {}
                try:
                    updates = cache.update_candidates(installed, cached)
                except Exception:
                    updates = {}
                stale = not cache.is_fresh(last_checked)
                error = None if result else "Update reported no result."
            except Exception as exc:
                installed, available, cached, usage, updates = [], [], [], {}, {}
                last_checked, stale = None, False
                error = str(exc)
                logging.warning("Python %s update failed: %s", runtime.version, exc)

            def on_done():
                try:
                    if not self.winfo_exists():
                        return
                except Exception:
                    return
                if error:
                    if install_button is not None:
                        try:
                            if install_button.winfo_exists():
                                install_button.configure(state="normal", text="Retry")
                        except Exception:
                            pass
                    try:
                        status_label.configure(
                            text=f"Python {runtime.version} update failed: {error}",
                            text_color=self.theme.ERROR_COLOR,
                        )
                    except Exception:
                        pass
                    return
                if install_button is not None:
                    try:
                        if install_button.winfo_exists():
                            install_button.configure(state="normal", text="Updated")
                    except Exception:
                        pass
                self._update_runtime_ui(
                    provider_name, installed, available, True,
                    default_python_var, status_label, generation=generation,
                    last_checked=last_checked, stale=stale,
                    cache_present=bool(cached), usage=usage, updates=updates,
                )
                self.refresh_env_runtime_choices()

            self._safe_after(0, on_done)

        threading.Thread(target=task, daemon=True).start()

    def _uninstall_python(
        self,
        runtime: "PythonRuntime",
        default_python_var,
        status_label,
        install_button=None,
    ) -> None:
        """Safely remove an installed runtime (blocked when in use without confirm)."""
        from py_env_studio.core.runtime_cache import find_runtime_usage
        try:
            used_by = find_runtime_usage(runtime.version)
        except Exception:
            used_by = []
        if used_by:
            confirm = messagebox.askyesno(
                "Runtime In Use",
                f"Python {runtime.version} is used by environment(s):\n"
                f"{', '.join(used_by)}\n\n"
                "Removing it may break those environments.\n\n"
                "Remove anyway?",
            )
            if not confirm:
                return
        else:
            confirm = messagebox.askyesno(
                "Remove Runtime",
                f"Remove Python {runtime.version} via Python Install Manager?",
            )
            if not confirm:
                return
        try:
            provider = self._get_runtime_provider("Python Install Manager")
        except Exception as exc:
            try:
                status_label.configure(text=str(exc), text_color=self.theme.ERROR_COLOR)
            except Exception:
                pass
            return
        if install_button is not None:
            try:
                install_button.configure(state="disabled", text="Removing...")
            except Exception:
                pass
        try:
            status_label.configure(
                text=f"Removing Python {runtime.version}...",
                text_color=self.theme.HIGHLIGHT_COLOR,
            )
        except Exception:
            pass
        self.env_log_queue.put(f"Removing Python {runtime.version}...")

        provider_name = provider.NAME
        generation = getattr(self, "_runtime_ui_generation", 0)

        def task():
            try:
                result = provider.uninstall(
                    runtime.version,
                    log_callback=lambda msg: self.env_log_queue.put(msg),
                )
                installed = provider.list_installed()
                from py_env_studio.core.runtime_cache import RuntimeCache, map_runtime_usage
                cache = RuntimeCache()
                cached, last_checked = cache.load_cached(provider.NAME)
                available = RuntimeCache.filter_available(cached, installed)
                try:
                    usage = map_runtime_usage(installed)
                except Exception:
                    usage = {}
                try:
                    updates = cache.update_candidates(installed, cached)
                except Exception:
                    updates = {}
                stale = not cache.is_fresh(last_checked)
                if provider.find_best_match(runtime.version, installed) is not None:
                    raise RuntimeError(
                        f"Python {runtime.version} is still present after removal."
                    )
                error = None if result else "Removal reported no result."
            except Exception as exc:
                installed, available, cached, usage, updates = [], [], [], {}, {}
                last_checked, stale = None, False
                error = str(exc)
                logging.warning("Python %s removal failed: %s", runtime.version, exc)

            def on_done():
                try:
                    if not self.winfo_exists():
                        return
                except Exception:
                    return
                if error:
                    if install_button is not None:
                        try:
                            if install_button.winfo_exists():
                                install_button.configure(state="normal", text="Retry")
                        except Exception:
                            pass
                    try:
                        status_label.configure(
                            text=f"Python {runtime.version} removal failed: {error}",
                            text_color=self.theme.ERROR_COLOR,
                        )
                    except Exception:
                        pass
                    return
                self._update_runtime_ui(
                    provider_name, installed, available, True,
                    default_python_var, status_label, generation=generation,
                    last_checked=last_checked, stale=stale,
                    cache_present=bool(cached), usage=usage, updates=updates,
                )
                self.refresh_env_runtime_choices()

            self._safe_after(0, on_done)

        threading.Thread(target=task, daemon=True).start()

    def _clear_frame(self, frame) -> None:
        """Remove all widgets from a frame."""
        try:
            for child in frame.winfo_children():
                child.destroy()
        except Exception:
            pass

    def show_install_package_dialog(self):
        """Show a dialog to install a package in the selected environment."""
        env_name = self.selected_env_var.get().strip()
        if not env_name or not is_valid_env_selected(env_name):
            show_error("Please select a valid environment before installing a package.")
            return

        dialog = ctk.CTkInputDialog(
            text=f"Enter package name to install in '{env_name}':",
            title="Install Package"
        )
        dialog.geometry("+%d+%d" % (self.winfo_rootx() + 600, self.winfo_rooty() + 300))
        package_name = dialog.get_input()
        if package_name:
            self._install_package_workflow(
                env_name,
                package_name,
                confirm=True,
                on_complete=self.view_installed_packages
            )

    def show_plugins_dialog(self):
        """Show plugin management dialog."""
        top = ctk.CTkToplevel(self)
        top.title("Plugin Manager")
        top.geometry("700x500")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 300}+{self.winfo_rooty() + 150}")

        # Title
        title = ctk.CTkLabel(
            top,
            text="Plugin Manager",
            font=("Segoe UI", 16, "bold")
        )
        title.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")

        # Plugin list frame
        list_frame = ctk.CTkScrollableFrame(top)
        list_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)

        # Discover plugins
        discovered = self.plugin_manager.discover_plugins()
        loaded = self.plugin_manager.get_all_plugins()

        if not discovered and not loaded:
            label = ctk.CTkLabel(
                list_frame,
                text="No plugins found.\n\nPlace plugins in: ~/.py_env_studio/plugins/",
                text_color=self.theme.TEXT_COLOR_LIGHT
            )
            label.pack(padx=20, pady=20)
        else:
            # Show loaded plugins
            for plugin_name, plugin in loaded.items():
                self._create_plugin_item(
                    list_frame,
                    plugin_name,
                    plugin,
                    is_loaded=True
                )

            # Show discovered but not loaded plugins
            for plugin_name in discovered:
                if plugin_name not in loaded:
                    self._create_plugin_item(
                        list_frame,
                        plugin_name,
                        None,
                        is_loaded=False
                    )

        # Footer buttons
        footer = ctk.CTkFrame(top)
        footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        footer.grid_columnconfigure(1, weight=1)

        reload_btn = self.btn(footer, "Reload", lambda: self._reload_plugins_dialog(top))
        reload_btn.grid(row=0, column=0, padx=4)

        docs_btn = self.btn(
            footer,
            "View Docs",
            lambda: open_link("https://py-env-studio.readthedocs.io/en/latest/plugin-development/")
        )
        docs_btn.grid(row=0, column=1, padx=4)

        close_btn = self.btn(footer, "Close", top.destroy, width=120)
        close_btn.grid(row=0, column=2, padx=4, sticky="e")

    def _reload_template_registry(self) -> None:
        registry = refresh_default_registry()
        self.template_engine.registry = registry
        self.template_creation_workflow.engine = self.template_engine
        self._setup_menubar()

    def show_community_templates_dialog(self) -> None:
        """Browse GitHub repository candidates and import them as user templates."""
        top = ctk.CTkToplevel(self)
        top.title("Community Templates")
        top.geometry("980x700")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(2, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 150}+{self.winfo_rooty() + 70}")

        query_var = tkinter.StringVar()
        category_var = tkinter.StringVar(value="All")
        sort_var = tkinter.StringVar(value="Popular")
        state = {"page": 1, "results": [], "busy": False, "error": None}

        ctk.CTkLabel(top, text="Community Templates", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, padx=16, pady=(16, 2), sticky="w"
        )
        ctk.CTkLabel(
            top,
            text="Discover untrusted third-party Python project templates from GitHub. Preview before importing.",
            text_color=self.theme.TEXT_COLOR_LIGHT,
        ).grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

        controls = ctk.CTkFrame(top)
        controls.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")
        controls.grid_columnconfigure(0, weight=1)
        self.entry(controls, var=query_var, width=360).grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        self.optmenu(controls, list(self.community_template_service.CATEGORIES), var=category_var).grid(row=0, column=1, padx=8, pady=8)
        self.optmenu(controls, ["Popular", "Recently Updated", "Recently Added"], var=sort_var).grid(row=0, column=2, padx=8, pady=8)

        status_label = self.lbl(top, "Ready to search GitHub community templates.", text_color=self.theme.HIGHLIGHT_COLOR)
        status_label.grid(row=3, column=0, padx=16, pady=(0, 4), sticky="w")
        list_frame = ctk.CTkScrollableFrame(top)
        list_frame.grid(row=4, column=0, padx=16, pady=4, sticky="nsew")
        top.grid_rowconfigure(4, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(top)
        footer.grid(row=5, column=0, padx=16, pady=(8, 16), sticky="ew")

        def use_candidate(candidate: CommunityTemplateCandidate) -> None:
            existing = self.community_template_service.find_existing_import(candidate.url)
            if existing:
                top.destroy()
                self.open_template_wizard(existing)
                return
            inspect_candidate(candidate, use_after_import=True)

        def render_results() -> None:
            for child in list_frame.winfo_children():
                child.destroy()
            if state["error"]:
                ctk.CTkLabel(list_frame, text=state["error"], justify="left", wraplength=860, text_color=self.theme.ERROR_COLOR).pack(padx=16, pady=24)
                return
            if not state["results"] and not state["busy"]:
                ctk.CTkLabel(list_frame, text="No community templates found. Try a different search or category.").pack(padx=16, pady=24)
                return
            for candidate in state["results"]:
                card = ctk.CTkFrame(list_frame, corner_radius=8, border_width=1, border_color=self.theme.BORDER_COLOR)
                card.pack(fill="x", padx=4, pady=6)
                card.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(card, text=f"Community Template: {candidate.name}", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
                ctk.CTkLabel(card, text=candidate.full_name, text_color=self.theme.HIGHLIGHT_COLOR).grid(row=1, column=0, padx=12, pady=2, sticky="w")
                ctk.CTkLabel(card, text=candidate.description, justify="left", wraplength=660).grid(row=2, column=0, padx=12, pady=2, sticky="w")
                topics = " | ".join(candidate.topics[:5]) or "Other"
                metadata = (
                    f"Stars: {candidate.stars}   Updated: {candidate.updated_at[:10]}   "
                    f"Language: {candidate.language or 'Unknown'}   License: {candidate.license_name or 'Unknown'}\n"
                    f"Topics: {topics}"
                )
                ctk.CTkLabel(card, text=metadata, justify="left").grid(row=3, column=0, padx=12, pady=(2, 10), sticky="w")
                actions = ctk.CTkFrame(card, fg_color="transparent")
                actions.grid(row=0, column=1, rowspan=4, padx=12, pady=10, sticky="ne")
                self.btn(actions, "Preview", lambda item=candidate: inspect_candidate(item), width=110).pack(pady=3)
                self.btn(actions, "Use Template", lambda item=candidate: use_candidate(item), width=110).pack(pady=3)
                self.btn(actions, "Open GitHub", lambda item=candidate: open_link(item.url), width=110).pack(pady=3)

        def search(reset: bool = True) -> None:
            if state["busy"]:
                return
            if reset:
                state["page"] = 1
                state["results"] = []
            state["busy"] = True
            state["error"] = None
            status_label.configure(text="Searching GitHub community templates...")
            render_results()

            def task() -> None:
                try:
                    found = self.community_template_service.search(
                        query=query_var.get(),
                        category=category_var.get(),
                        sort=sort_var.get(),
                        page=state["page"],
                    )
                    state["found"] = found
                except Exception as exc:
                    state["error"] = str(exc)

            def on_complete() -> None:
                state["busy"] = False
                if not top.winfo_exists():
                    return
                if not state["error"]:
                    found = state.pop("found", [])
                    state["results"] = found if reset else state["results"] + found
                    status_label.configure(text=f"Showing {len(state['results'])} community template candidates.")
                else:
                    status_label.configure(text="Unable to retrieve community templates.", text_color=self.theme.ERROR_COLOR)
                render_results()

            self.run_async(task, callback=on_complete)

        def inspect_candidate(candidate: CommunityTemplateCandidate, use_after_import: bool = False) -> None:
            if state["busy"]:
                return
            state["busy"] = True
            status_label.configure(text=f"Inspecting {candidate.full_name} without executing repository code...")

            def task() -> None:
                try:
                    state["inspection"] = self.community_template_service.inspect(candidate)
                    state["inspection_error"] = None
                except Exception as exc:
                    state["inspection"] = None
                    state["inspection_error"] = exc

            def on_complete() -> None:
                state["busy"] = False
                if not top.winfo_exists():
                    inspection = state.get("inspection")
                    if inspection:
                        self.community_template_service.cleanup_inspection(inspection)
                    return
                inspection = state.get("inspection")
                error = state.get("inspection_error")
                if error or inspection is None:
                    status_label.configure(text=f"Inspection failed: {error}", text_color=self.theme.ERROR_COLOR)
                    return
                status_label.configure(text=f"Inspection complete: {candidate.full_name}")
                show_preview(inspection, use_after_import)

            self.run_async(task, callback=on_complete)

        def show_preview(inspection: CommunityTemplateInspection, use_after_import: bool) -> None:
            preview = ctk.CTkToplevel(top)
            preview.title(f"Community Template Preview - {inspection.candidate.name}")
            preview.geometry("900x700")
            preview.transient(top)
            preview.grab_set()
            preview.grid_columnconfigure(0, weight=1)
            preview.grid_rowconfigure(1, weight=1)

            ctk.CTkLabel(preview, text="Community Template (Untrusted Third-Party Source)", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")
            details = ctk.CTkTextbox(preview)
            details.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
            concerns = []
            if inspection.source_inspection.sensitive_files:
                concerns.append("Sensitive files detected and excluded: " + ", ".join(path.as_posix() for path in inspection.source_inspection.sensitive_files[:8]))
            if inspection.has_workflows:
                concerns.append("GitHub workflows detected. Workflows are not executed or imported.")
            lines = [
                f"Name: {inspection.candidate.name}",
                f"GitHub: {inspection.candidate.full_name}",
                f"Stars: {inspection.candidate.stars}",
                f"Language: {inspection.candidate.language or 'Unknown'}",
                f"License: {inspection.candidate.license_name or 'Unknown'}",
                f"Topics: {', '.join(inspection.candidate.topics) or 'Other'}",
                "",
                "Description:", inspection.candidate.description,
                "",
                "Detected:",
                f"- Python project: {'yes' if inspection.has_python_project else 'no'}",
                f"- Tests: {'yes' if inspection.has_tests else 'no'}",
                f"- Environment files: {'yes' if inspection.has_environment_files else 'no'}",
                "",
                "Relevant files:",
            ]
            lines.extend(f"- {path}" for path in inspection.detected_files)
            lines.extend(["", "Project structure:"])
            lines.extend(f"- {path.as_posix()}" for path in inspection.source_inspection.included_files[:160])
            if concerns:
                lines.extend(["", "Potential concerns:"])
                lines.extend(f"- {item}" for item in concerns)
            if inspection.readme_excerpt:
                lines.extend(["", "README excerpt:", inspection.readme_excerpt])
            details.insert("1.0", "\n".join(lines))
            details.configure(state="disabled")

            def close_preview() -> None:
                self.community_template_service.cleanup_inspection(inspection)
                preview.destroy()

            def import_template() -> None:
                existing = self.community_template_service.find_existing_import(inspection.candidate.url)
                if existing:
                    choice = messagebox.askyesnocancel(
                        "Template Already Imported",
                        "This GitHub repository is already in My Templates.\n\n"
                        "Yes: use the existing template\nNo: import another copy\nCancel: return to preview",
                        parent=preview,
                    )
                    if choice is None:
                        return
                    if choice:
                        close_preview()
                        top.destroy()
                        self.open_template_wizard(existing)
                        return
                preview.destroy()
                self._show_template_metadata_dialog(
                    source_dir=inspection.source_dir,
                    source_type="github",
                    origin=inspection.candidate.url,
                    cleanup_dir=inspection.cleanup_dir,
                    refresh_callback=lambda: None,
                    suggested_template_name=inspection.candidate.name,
                    on_saved_template=(lambda template_id: self.open_template_wizard(template_id)) if use_after_import else None,
                )

            footer = ctk.CTkFrame(preview)
            footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
            self.btn(footer, "Import as Template", import_template, width=150).pack(side="left", padx=8, pady=8)
            self.btn(footer, "Open GitHub", lambda: open_link(inspection.candidate.url), width=120).pack(side="left", padx=8, pady=8)
            self.btn(footer, "Back", close_preview, width=100).pack(side="right", padx=8, pady=8)
            preview.protocol("WM_DELETE_WINDOW", close_preview)

        self.btn(controls, "Search", search, width=100).grid(row=0, column=3, padx=8, pady=8)
        self.btn(footer, "Load More", lambda: [state.__setitem__("page", state["page"] + 1), search(reset=False)], width=120).pack(side="left", padx=8, pady=8)
        self.btn(footer, "My Templates", lambda: self.show_manage_templates_dialog(), width=130).pack(side="left", padx=8, pady=8)
        self.btn(footer, "Close", top.destroy, width=100).pack(side="right", padx=8, pady=8)
        top.protocol("WM_DELETE_WINDOW", top.destroy)
        search()

    def show_manage_templates_dialog(self):
        """Manage built-in and user-created templates."""
        top = ctk.CTkToplevel(self)
        top.title("Manage Templates")
        top.geometry("900x640")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 250}+{self.winfo_rooty() + 120}")

        title = ctk.CTkLabel(top, text="Manage Templates", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        list_frame = ctk.CTkScrollableFrame(top)
        list_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)

        def refresh_sections():
            for child in list_frame.winfo_children():
                child.destroy()

            templates = self.template_engine.list_templates()
            builtins = [template for template in templates if template.source == "built-in"]
            users = [template for template in templates if template.source == "user"]

            ctk.CTkLabel(list_frame, text="Built-in Templates", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
            for template in builtins:
                card = ctk.CTkFrame(list_frame, corner_radius=8, border_width=1, border_color=self.theme.BORDER_COLOR)
                card.pack(fill="x", padx=4, pady=4)
                ctk.CTkLabel(card, text=template.name, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
                ctk.CTkLabel(card, text=template.description, justify="left", wraplength=620).grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")
                self.btn(card, "Use", lambda template_id=template.id: [top.destroy(), self.open_template_wizard(template_id)], width=90).grid(row=0, column=1, rowspan=2, padx=10, pady=8)

            ctk.CTkLabel(list_frame, text="My Templates", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=8, pady=(14, 2))
            if not users:
                ctk.CTkLabel(list_frame, text="No user templates yet.", text_color=self.theme.TEXT_COLOR_LIGHT).pack(anchor="w", padx=10, pady=6)
            for template in users:
                card = ctk.CTkFrame(list_frame, corner_radius=8, border_width=1, border_color=self.theme.BORDER_COLOR)
                card.pack(fill="x", padx=4, pady=4)
                ctk.CTkLabel(card, text=template.name, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
                ctk.CTkLabel(card, text=f"{template.description}\nCategory: {template.category}", justify="left", wraplength=620).grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")
                actions = ctk.CTkFrame(card, fg_color="transparent")
                actions.grid(row=0, column=1, rowspan=2, padx=10, pady=8)
                self.btn(actions, "Use", lambda template_id=template.id: [top.destroy(), self.open_template_wizard(template_id)], width=90).grid(row=0, column=0, padx=4)
                self.btn(actions, "Delete", lambda template_id=template.id: self._delete_user_template(template_id, refresh_sections), width=90).grid(row=0, column=1, padx=4)

        refresh_sections()

        footer = ctk.CTkFrame(top)
        footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        self.btn(footer, "+ Add Template", lambda: self._show_add_template_dialog(refresh_sections), width=140).pack(side="left", padx=8, pady=8)
        self.btn(footer, "Refresh", refresh_sections, width=100).pack(side="left", padx=8, pady=8)
        self.btn(footer, "Close", top.destroy, width=110).pack(side="right", padx=8, pady=8)

    def _show_add_template_dialog(self, refresh_callback) -> None:
        top = ctk.CTkToplevel(self)
        top.title("Add Template")
        top.geometry("520x280")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 330}+{self.winfo_rooty() + 180}")

        ctk.CTkLabel(top, text="How would you like to add it?", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, padx=16, pady=(18, 10), sticky="w")

        body = ctk.CTkFrame(top)
        body.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        body.grid_columnconfigure((0, 1), weight=1)

        self.btn(
            body,
            "Local Project",
            lambda: [top.destroy(), self._import_template_from_local(refresh_callback)],
            width=200,
            height=40,
        ).grid(row=0, column=0, padx=8, pady=12)

        self.btn(
            body,
            "GitHub Repository",
            lambda: [top.destroy(), self._import_template_from_github(refresh_callback)],
            width=200,
            height=40,
        ).grid(row=0, column=1, padx=8, pady=12)

        self.btn(top, "Cancel", top.destroy, width=100).grid(row=2, column=0, padx=16, pady=(8, 16), sticky="e")

    def _import_template_from_local(self, refresh_callback) -> None:
        source = filedialog.askdirectory(title="Select project directory")
        if not source:
            return
        self._show_template_metadata_dialog(
            source_dir=Path(source),
            source_type="local",
            origin=source,
            cleanup_dir=None,
            refresh_callback=refresh_callback,
            suggested_template_name=Path(source).name,
        )

    def _import_template_from_github(self, refresh_callback) -> None:
        dialog = ctk.CTkInputDialog(
            text="Enter GitHub repository URL:\nExample: https://github.com/user/project",
            title="Import from GitHub",
        )
        dialog.geometry("+%d+%d" % (self.winfo_rootx() + 580, self.winfo_rooty() + 260))
        repo_url = dialog.get_input()
        if not repo_url:
            return

        progress = ctk.CTkToplevel(self)
        progress.title("Importing Repository")
        progress.geometry("520x190")
        progress.transient(self)
        progress.grab_set()
        progress.grid_columnconfigure(0, weight=1)
        progress.geometry(f"+{self.winfo_rootx() + 340}+{self.winfo_rooty() + 190}")

        title = ctk.CTkLabel(progress, text="Importing repository...", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, padx=16, pady=(18, 8), sticky="w")
        status_label = ctk.CTkLabel(progress, text="Validating repository URL...", justify="left", wraplength=480)
        status_label.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        state = {"error": None, "source_dir": None, "cleanup_dir": None, "origin": None, "repo_name": None}

        def set_status(message: str) -> None:
            self._safe_after(0, lambda: status_label.configure(text=message))

        def task():
            try:
                set_status("Validating repository URL...")
                normalized_url = validate_github_repository_url(repo_url)
                state["origin"] = normalized_url
                state["repo_name"] = extract_github_repository_name(repo_url)

                temp_root = Path(tempfile.mkdtemp(prefix="pes-template-import-"))
                source_dir = temp_root / "repo"
                state["cleanup_dir"] = temp_root

                set_status("Cloning repository...")
                clone_github_repository(
                    normalized_url,
                    source_dir,
                    timeout_seconds=240,
                    log_callback=lambda msg: self.env_log_queue.put(f"[Templates] {msg}"),
                )
                set_status("Inspecting project...")
                self.user_template_store.inspect_source(source_dir)
                state["source_dir"] = source_dir
                set_status("Template ready.")
            except Exception as exc:
                state["error"] = exc
                if state.get("cleanup_dir"):
                    shutil.rmtree(state["cleanup_dir"], ignore_errors=True)
                raise

        def on_complete():
            progress.destroy()
            if state["error"]:
                show_error(f"GitHub import failed: {state['error']}")
                return
            self._show_template_metadata_dialog(
                source_dir=state["source_dir"],
                source_type="github",
                origin=state["origin"],
                cleanup_dir=state["cleanup_dir"],
                refresh_callback=refresh_callback,
                suggested_template_name=state["repo_name"],
            )

        self.run_async(task, success_msg=None, error_msg=None, callback=on_complete)

    def _show_template_metadata_dialog(self, source_dir: Path, source_type: str, origin: str, cleanup_dir: Path | None, refresh_callback, suggested_template_name: str | None = None, on_saved_template=None) -> None:
        try:
            inspection = self.user_template_store.inspect_source(source_dir)
        except Exception as exc:
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)
            show_error(f"Unable to inspect template source: {exc}")
            return

        top = ctk.CTkToplevel(self)
        top.title("Create Template")
        top.geometry("880x700")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 220}+{self.winfo_rooty() + 80}")

        default_name = (suggested_template_name or source_dir.name).strip()
        name_var = tkinter.StringVar(value=default_name)
        generated_id = generate_template_id(name_var.get())
        template_id_var = tkinter.StringVar(value=generated_id)
        desc_var = tkinter.StringVar(value="User-created template")
        author_var = tkinter.StringVar(value="")
        version_var = tkinter.StringVar(value="1.0.0")
        category_var = tkinter.StringVar(value="General")
        python_var = tkinter.StringVar(value="3.11")
        replace_name_var = tkinter.IntVar(value=0)
        state = {"last_generated": generated_id}

        header = ctk.CTkLabel(top, text="Create Template", font=("Segoe UI", 16, "bold"))
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        body = ctk.CTkScrollableFrame(top)
        body.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        self.lbl(body, "Template Name:", font=self.theme.FONT_BOLD).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=name_var, width=320).grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        self.lbl(body, "Template ID:", font=self.theme.FONT_BOLD).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=template_id_var, width=320).grid(row=1, column=1, padx=8, pady=6, sticky="ew")

        self.lbl(body, "Description:", font=self.theme.FONT_BOLD).grid(row=2, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=desc_var, width=520).grid(row=2, column=1, padx=8, pady=6, sticky="ew")

        self.lbl(body, "Author:", font=self.theme.FONT_BOLD).grid(row=3, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=author_var, width=260).grid(row=3, column=1, padx=8, pady=6, sticky="w")

        self.lbl(body, "Version:", font=self.theme.FONT_BOLD).grid(row=4, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=version_var, width=200).grid(row=4, column=1, padx=8, pady=6, sticky="w")

        self.lbl(body, "Category:", font=self.theme.FONT_BOLD).grid(row=5, column=0, padx=8, pady=6, sticky="w")
        self.optmenu(body, ["General", "Web/API", "CLI", "Package", "Data Science", "Custom"], var=category_var).grid(row=5, column=1, padx=8, pady=6, sticky="w")

        self.lbl(body, "Python Version:", font=self.theme.FONT_BOLD).grid(row=6, column=0, padx=8, pady=6, sticky="w")
        self.optmenu(body, ["3.10", "3.11", "3.12", "3.13"], var=python_var).grid(row=6, column=1, padx=8, pady=6, sticky="w")

        self.chk(body, "Replace source project-name occurrences with {{ project_name }}", variable=replace_name_var).grid(row=7, column=0, columnspan=2, padx=8, pady=6, sticky="w")

        if inspection.sensitive_files:
            names = "\n".join(str(path) for path in inspection.sensitive_files[:10])
            warn = ctk.CTkLabel(
                body,
                text=(
                    "Potential sensitive files detected. They will be excluded:\n"
                    f"{names}"
                ),
                justify="left",
                text_color=self.theme.ERROR_COLOR,
            )
            warn.grid(row=8, column=0, columnspan=2, padx=8, pady=(4, 10), sticky="w")
            preview_row = 9
        else:
            preview_row = 8

        preview_label = ctk.CTkLabel(body, text="Template Preview", font=("Segoe UI", 13, "bold"))
        preview_label.grid(row=preview_row, column=0, columnspan=2, padx=8, pady=(8, 4), sticky="w")
        preview = ctk.CTkTextbox(body, height=260)
        preview.grid(row=preview_row + 1, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="nsew")

        lines = [
            f"Source: {source_type}",
            f"Origin: {origin}",
            "",
            "Included files:",
        ]
        lines.extend([f"- {path.as_posix()}" for path in inspection.included_files[:200]])
        if len(inspection.included_files) > 200:
            lines.append(f"... and {len(inspection.included_files) - 200} more files")
        preview.insert("1.0", "\n".join(lines))
        preview.configure(state="disabled")

        def on_name_change(*_):
            current_id = template_id_var.get().strip()
            if current_id == state["last_generated"] or not current_id:
                new_value = generate_template_id(name_var.get())
                state["last_generated"] = new_value
                template_id_var.set(new_value)

        name_var.trace_add("write", on_name_change)

        def close_dialog():
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)
            top.destroy()

        def save_template_action():
            all_ids = [template.id for template in self.template_engine.list_templates()]
            try:
                self.user_template_store.save_template(
                    source_dir=source_dir,
                    template_name=name_var.get().strip(),
                    template_id=template_id_var.get().strip(),
                    description=desc_var.get().strip(),
                    author=author_var.get().strip(),
                    version=version_var.get().strip(),
                    category=category_var.get().strip(),
                    python_version=python_var.get().strip(),
                    source_type=source_type,
                    origin=origin,
                    reserved_template_ids=all_ids,
                    replace_project_name=bool(replace_name_var.get()),
                )
                self._reload_template_registry()
                refresh_callback()
                show_info("Template saved successfully.")
                close_dialog()
                if on_saved_template:
                    on_saved_template(template_id_var.get().strip())
            except UserTemplateError as exc:
                show_error(str(exc))
            except Exception as exc:
                show_error(f"Template save failed: {exc}")

        footer = ctk.CTkFrame(top)
        footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        self.btn(footer, "Save Template", save_template_action, width=140).pack(side="right", padx=8, pady=8)
        self.btn(footer, "Cancel", close_dialog, width=100).pack(side="right", padx=8, pady=8)

        top.protocol("WM_DELETE_WINDOW", close_dialog)

    def _delete_user_template(self, template_id: str, refresh_callback) -> None:
        if not messagebox.askyesno(
            "Delete Template?",
            f"'{template_id}' will be removed from your templates.\n\n"
            "Existing projects created from this template will NOT be affected.",
        ):
            return
        try:
            self.user_template_store.delete_template(template_id)
            self._reload_template_registry()
            refresh_callback()
            show_info("Template deleted successfully.")
        except Exception as exc:
            show_error(f"Failed to delete template: {exc}")

    def show_templates_dialog(self):
        """Show templates landing page with metadata and create actions."""
        top = ctk.CTkToplevel(self)
        top.title("Project Templates")
        top.geometry("900x620")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 260}+{self.winfo_rooty() + 120}")

        title = ctk.CTkLabel(top, text="Templates", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, padx=16, pady=(16, 10), sticky="w")

        list_frame = ctk.CTkScrollableFrame(top)
        list_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)

        for spec in self.template_engine.list_templates():
            item = ctk.CTkFrame(list_frame, corner_radius=8, border_width=1, border_color=self.theme.BORDER_COLOR)
            item.pack(fill="x", pady=8)
            item.grid_columnconfigure(0, weight=1)

            header = ctk.CTkLabel(item, text=f"{spec.name} ({spec.id})", font=("Segoe UI", 13, "bold"))
            header.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

            desc = ctk.CTkLabel(item, text=spec.description, wraplength=640, justify="left")
            desc.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")

            meta_text = (
                f"Python: {', '.join(spec.supported_python_versions)}\n"
                f"Architecture: {spec.architecture} ({spec.style})\n"
                f"Tooling: {', '.join(spec.included_tooling)}"
            )
            meta = ctk.CTkLabel(item, text=meta_text, justify="left", text_color=self.theme.HIGHLIGHT_COLOR)
            meta.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="w")

            preview_title = ctk.CTkLabel(item, text="Structure Preview", font=("Segoe UI", 11, "bold"))
            preview_title.grid(row=3, column=0, padx=12, pady=(0, 2), sticky="w")

            preview = ctk.CTkTextbox(item, height=90, width=760)
            preview.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="ew")
            preview.insert("1.0", "\n".join(spec.structure_preview))
            preview.configure(state="disabled")

            create_btn = self.btn(item, "Create Project", lambda template_id=spec.id: [top.destroy(), self.open_template_wizard(template_id)], width=150)
            create_btn.grid(row=0, column=1, rowspan=2, padx=12, pady=10, sticky="ne")

        footer = ctk.CTkFrame(top)
        footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        close_btn = self.btn(footer, "Close", top.destroy, width=120)
        close_btn.pack(side="right", padx=8, pady=8)

    def open_template_wizard(self, template_id: str):
        """Open configuration and preview dialog for selected template."""
        spec = self.template_engine.get_template(template_id)

        top = ctk.CTkToplevel(self)
        top.title(f"Create Project - {spec.name}")
        top.geometry("860x720")
        top.transient(self)
        top.grab_set()
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)
        top.geometry(f"+{self.winfo_rootx() + 220}+{self.winfo_rooty() + 90}")

        title = ctk.CTkLabel(top, text=f"{spec.name} Template", font=("Segoe UI", 17, "bold"))
        title.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        body = ctk.CTkScrollableFrame(top)
        body.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        project_name_var = tkinter.StringVar(value="my-project")
        project_location_var = tkinter.StringVar(value=os.path.expanduser("~"))
        default_python_version = (self.preferences.default_python_version or "").strip()
        if default_python_version and default_python_version in spec.supported_python_versions:
            initial_python_version = default_python_version
        else:
            initial_python_version = spec.supported_python_versions[0]
        python_version_var = tkinter.StringVar(value=initial_python_version)
        create_venv_var = tkinter.IntVar(value=1 if self.preferences.template_create_venv_default else 0)
        init_git_var = tkinter.IntVar(value=1 if self.preferences.template_initialize_git_default else 0)
        package_name_var = tkinter.StringVar(value="")
        cli_command_name_var = tkinter.StringVar(value="")
        author_var = tkinter.StringVar(value="")
        license_var = tkinter.StringVar(value=spec.default_license)

        self.lbl(body, "Project Name:", font=self.theme.FONT_BOLD).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=project_name_var, width=300).grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        self.lbl(body, "Project Location:", font=self.theme.FONT_BOLD).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        location_row = ctk.CTkFrame(body, fg_color="transparent")
        location_row.grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        location_row.grid_columnconfigure(0, weight=1)
        self.entry(location_row, var=project_location_var, width=420).grid(row=0, column=0, padx=(0, 6), pady=0, sticky="ew")
        self.btn(
            location_row,
            "Browse",
            lambda: project_location_var.set(filedialog.askdirectory() or project_location_var.get()),
            width=90,
        ).grid(row=0, column=1, padx=0, pady=0)

        self.lbl(body, "Python Version:", font=self.theme.FONT_BOLD).grid(row=2, column=0, padx=8, pady=6, sticky="w")
        self.optmenu(body, spec.supported_python_versions, var=python_version_var).grid(row=2, column=1, padx=8, pady=6, sticky="w")

        self.lbl(body, "Package Name (optional):", font=self.theme.FONT_BOLD).grid(row=3, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=package_name_var, width=300).grid(row=3, column=1, padx=8, pady=6, sticky="ew")

        self.lbl(body, "CLI Command Name (optional):", font=self.theme.FONT_BOLD).grid(row=4, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=cli_command_name_var, width=300).grid(row=4, column=1, padx=8, pady=6, sticky="ew")

        self.lbl(body, "Author (optional):", font=self.theme.FONT_BOLD).grid(row=5, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=author_var, width=300).grid(row=5, column=1, padx=8, pady=6, sticky="ew")

        self.lbl(body, "License:", font=self.theme.FONT_BOLD).grid(row=6, column=0, padx=8, pady=6, sticky="w")
        self.entry(body, var=license_var, width=200).grid(row=6, column=1, padx=8, pady=6, sticky="w")

        self.chk(body, "Create Virtual Environment", variable=create_venv_var).grid(row=7, column=0, columnspan=2, padx=8, pady=6, sticky="w")
        self.chk(body, "Initialize Git", variable=init_git_var).grid(row=8, column=0, columnspan=2, padx=8, pady=6, sticky="w")

        preview_label = self.lbl(body, "Template Preview", font=("Segoe UI", 13, "bold"))
        preview_label.grid(row=9, column=0, columnspan=2, padx=8, pady=(12, 4), sticky="w")
        preview_box = ctk.CTkTextbox(body, height=230)
        preview_box.grid(row=10, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="nsew")

        status_label = self.lbl(body, "", text_color=self.theme.HIGHLIGHT_COLOR)
        status_label.grid(row=11, column=0, columnspan=2, padx=8, pady=6, sticky="w")
        request_state = {"result": None, "error": None, "busy": False}

        def build_request() -> TemplateCreationRequest:
            package_name = package_name_var.get().strip() or sanitize_module_name(project_name_var.get().strip() or "my-project")
            cli_cmd = cli_command_name_var.get().strip() or package_name
            return TemplateCreationRequest(
                template_id=template_id,
                project_name=project_name_var.get().strip(),
                project_location=project_location_var.get().strip(),
                python_version=python_version_var.get().strip(),
                create_virtual_environment=bool(create_venv_var.get()),
                initialize_git=bool(init_git_var.get()),
                package_name=package_name,
                cli_command_name=cli_cmd,
                author=author_var.get().strip() or None,
                license_name=license_var.get().strip() or None,
                install_dev_dependencies=True,
            )

        def refresh_preview(*_):
            preview_box.configure(state="normal")
            preview_box.delete("1.0", "end")
            try:
                req = build_request()
                data = self.template_engine.preview(template_id, req)
                lines = [
                    f"Template: {data['name']} ({data['template_id']})",
                    "",
                    f"Description: {data['description']}",
                    f"Architecture: {data['architecture']} ({data['style']})",
                    f"Python: {', '.join(data['supported_python_versions'])}",
                    "",
                    "Included tooling:",
                ]
                lines.extend([f"  - {item}" for item in data["included_tooling"]])
                lines.append("")
                lines.append("Runtime dependencies:")
                if data["runtime_dependencies"]:
                    lines.extend([f"  - {item}" for item in data["runtime_dependencies"]])
                else:
                    lines.append("  - none")
                lines.append("")
                lines.append("Dev dependencies:")
                lines.extend([f"  - {item}" for item in data["dev_dependencies"]])
                lines.append("")
                lines.append("Structure:")
                lines.extend([f"  - {item}" for item in data["structure_preview"]])
                preview_box.insert("1.0", "\n".join(lines))
                status_label.configure(text="Preview updated")
            except Exception as exc:
                preview_box.insert("1.0", f"Preview unavailable: {exc}")
                status_label.configure(text="")
            preview_box.configure(state="disabled")

        for var in [project_name_var, project_location_var, python_version_var, package_name_var, cli_command_name_var, author_var, license_var]:
            var.trace_add("write", refresh_preview)

        def create_project_action():
            if request_state["busy"]:
                return

            if not messagebox.askyesno("Confirm", "Create project from this template?"):
                return

            try:
                req = build_request()
            except Exception as exc:
                show_error(f"Invalid template configuration: {exc}")
                return

            status_label.configure(text="Creating project...")
            request_state["result"] = None
            request_state["error"] = None
            request_state["busy"] = True
            create_project_btn.configure(state="disabled")

            project_status = (
                f"Project: {req.project_name}\n"
                "Status: Creating project...\n"
                f"Template: {spec.name}\n"
                f"Location: {Path(req.project_location) / req.project_name}"
            )
            status_label.configure(text=project_status)
            self.env_log_queue.put(f"[Templates] Project creation started: {req.project_name}")

            try:
                top.iconify()
                self.env_log_queue.put("[Templates] Project creation minimized UI")
            except Exception:
                pass

            def task():
                try:
                    request_state["result"] = self.template_creation_workflow.create_project(
                        req,
                        log_callback=lambda msg: self.env_log_queue.put(f"[Templates] {msg}"),
                    )
                except Exception as exc:
                    request_state["error"] = exc
                    raise

            def on_complete():
                request_state["busy"] = False
                create_project_btn.configure(state="normal")

                state = self.template_creation_workflow.state
                if state.status == ProjectCreationStatus.FAILED or request_state["error"]:
                    self.env_log_queue.put("[Templates] Project creation failed")
                    try:
                        top.deiconify()
                        top.lift()
                    except Exception:
                        pass
                    status_label.configure(
                        text=(
                            f"Project: {state.project_name}\n"
                            "Status: Project creation failed"
                        ),
                        text_color=self.theme.ERROR_COLOR,
                    )
                    self._show_project_creation_failed_dialog(state.project_name, request_state["error"])
                    return

                result = request_state["result"]
                if result is None:
                    return

                status_label.configure(text="Project created successfully.", text_color=self.theme.SUCCESS_COLOR)
                self.env_log_queue.put("[Templates] Project creation completed")
                try:
                    self.plugin_manager.execute_hook(
                        "after_template_created",
                        {
                            "template_id": result.template_id,
                            "project_path": str(result.project_path),
                            "created_environment": result.created_environment_name,
                            "dependencies": result.installed_dependencies,
                        },
                    )
                except Exception as hook_error:
                    self.env_log_queue.put(f"[Templates] Plugin hook error: {hook_error}")

                action = self._show_project_created_prompt(result.project_path.name, result.project_path)
                if action == "open":
                    self._open_created_project_workflow(result.project_path)
                top.destroy()

            self.run_async(
                task,
                success_msg=None,
                error_msg=None,
                callback=on_complete,
            )

        actions = ctk.CTkFrame(top)
        actions.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        self.btn(actions, "Refresh Preview", refresh_preview, width=140).grid(row=0, column=0, padx=6, pady=8, sticky="w")
        create_project_btn = self.btn(actions, "Create Project", create_project_action, width=150)
        create_project_btn.grid(row=0, column=1, padx=6, pady=8, sticky="e")
        self.btn(actions, "Cancel", top.destroy, width=120).grid(row=0, column=2, padx=6, pady=8, sticky="e")

        refresh_preview()

    def _show_project_created_prompt(self, project_name: str, project_path: Path) -> str:
        """Show completion prompt and ask whether to open the new project."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Project Created Successfully")
        dialog.geometry("520x260")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.geometry(f"+{self.winfo_rootx() + 350}+{self.winfo_rooty() + 180}")

        message = (
            f"{project_name} has been created successfully.\n\n"
            f"Location:\n{project_path}\n\n"
            "Would you like to open the project?"
        )
        ctk.CTkLabel(dialog, text=message, justify="left", wraplength=480).grid(
            row=0, column=0, padx=16, pady=(20, 12), sticky="w"
        )

        response = {"action": "not_now"}

        row = ctk.CTkFrame(dialog)
        row.grid(row=1, column=0, padx=16, pady=(4, 16), sticky="e")
        self.btn(row, "Open Project", lambda: [response.update({"action": "open"}), dialog.destroy()], width=130).grid(row=0, column=0, padx=6)
        self.btn(row, "Not Now", dialog.destroy, width=110).grid(row=0, column=1, padx=6)

        self.wait_window(dialog)
        return response["action"]

    def _show_open_with_dialog(self, project_path: Path, tools) -> str | None:
        """Show tool selection dialog and return selected tool id."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Open Project With")
        dialog.geometry("500x380")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)
        dialog.geometry(f"+{self.winfo_rootx() + 360}+{self.winfo_rooty() + 170}")

        ctk.CTkLabel(dialog, text="Detected applications", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )

        preferred = self._get_preferred_project_editor()
        available_ids = {tool["tool_id"] for tool in tools}
        if preferred in available_ids:
            default_selection = preferred
        elif len(tools) == 1:
            default_selection = tools[0]["tool_id"]
        elif "vscode" in available_ids:
            default_selection = "vscode"
        else:
            default_selection = tools[0]["tool_id"]

        selected_tool = tkinter.StringVar(value=default_selection)

        list_frame = ctk.CTkScrollableFrame(dialog)
        list_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)

        for tool in tools:
            radio = ctk.CTkRadioButton(
                list_frame,
                text=tool["display_name"],
                variable=selected_tool,
                value=tool["tool_id"],
            )
            radio.pack(anchor="w", padx=8, pady=6)

        result = {"tool_id": None}

        footer = ctk.CTkFrame(dialog)
        footer.grid(row=2, column=0, padx=16, pady=(6, 16), sticky="e")
        self.btn(
            footer,
            "Open",
            lambda: [result.update({"tool_id": selected_tool.get()}), dialog.destroy()],
            width=100,
        ).grid(row=0, column=0, padx=6)
        self.btn(footer, "Cancel", dialog.destroy, width=100).grid(row=0, column=1, padx=6)

        self.wait_window(dialog)
        return result["tool_id"]

    def _show_project_open_failed_prompt(self, tool_name: str, error_text: str) -> str:
        """Return one of: try_again, choose_another, done."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Unable to Open Project")
        dialog.geometry("520x280")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.geometry(f"+{self.winfo_rootx() + 340}+{self.winfo_rooty() + 170}")

        text = (
            "Project created successfully, but the selected application could not be opened.\n\n"
            f"Application: {tool_name}\n\n"
            f"Reason: {error_text}"
        )
        ctk.CTkLabel(dialog, text=text, justify="left", wraplength=480).grid(
            row=0, column=0, padx=16, pady=(20, 12), sticky="w"
        )

        response = {"action": "done"}
        row = ctk.CTkFrame(dialog)
        row.grid(row=1, column=0, padx=16, pady=(6, 16), sticky="e")
        self.btn(row, "Try Again", lambda: [response.update({"action": "try_again"}), dialog.destroy()], width=110).grid(row=0, column=0, padx=5)
        self.btn(row, "Choose Another", lambda: [response.update({"action": "choose_another"}), dialog.destroy()], width=130).grid(row=0, column=1, padx=5)
        self.btn(row, "Done", dialog.destroy, width=90).grid(row=0, column=2, padx=5)

        self.wait_window(dialog)
        return response["action"]

    def _show_project_creation_failed_dialog(self, project_name: str, error: Exception | None) -> None:
        message = (
            "Unable to create the project.\n\n"
            f"Project: {project_name}\n"
            "Use 'View Details' for technical information."
        )
        if messagebox.askyesno("Project Creation Failed", f"{message}\n\nView details?"):
            show_error(f"Project creation failed:\n{error}")

    def _get_preferred_project_editor(self) -> str | None:
        try:
            cfg = AppConfig()
            value = cfg.get_param("settings", "preferred_project_editor", fallback="") or ""
            return value.strip() or None
        except Exception:
            return None

    def _set_preferred_project_editor(self, tool_id: str) -> None:
        try:
            cfg = AppConfig()
            cfg.set_param("settings", "preferred_project_editor", tool_id)
        except Exception as exc:
            logging.warning(f"Failed to save preferred project editor: {exc}")

    def _open_created_project_workflow(self, project_path: Path) -> None:
        tools = discover_project_open_tools(self.open_with_tools, include_default=True)
        tool_names = [tool["display_name"] for tool in tools]
        self.env_log_queue.put(f"[Templates] Detected project tools: {tool_names}")

        if not tools:
            show_error("No supported applications were detected to open this project.")
            return

        selected_tool_id = self._show_open_with_dialog(project_path, tools)
        if not selected_tool_id:
            self.env_log_queue.put("[Templates] Project open canceled by user")
            return

        while selected_tool_id:
            selected = find_tool_by_id(selected_tool_id, tools)
            if selected is None:
                show_error("Selected tool is no longer available.")
                return

            self.env_log_queue.put(f"[Templates] Selected project tool: {selected['display_name']}")
            logging.info("Project opening requested with tool: %s", selected["display_name"])
            try:
                open_project_with_tool(selected, project_path)
                self._set_preferred_project_editor(selected["tool_id"])
                self.env_log_queue.put("[Templates] Project opened successfully")
                show_info(f"Project opened with {selected['display_name']}.")
                return
            except Exception as exc:
                self.env_log_queue.put(f"[Templates] Project opening failed: {exc}")
                action = self._show_project_open_failed_prompt(selected["display_name"], str(exc))
                if action == "try_again":
                    continue
                if action == "choose_another":
                    selected_tool_id = self._show_open_with_dialog(project_path, tools)
                    continue
                return

    def _create_plugin_item(self, parent, plugin_name, plugin, is_loaded):
        """Create a plugin list item.
        
        Args:
            parent: Parent frame
            plugin_name: Name of plugin
            plugin: Plugin instance or None
            is_loaded: Whether plugin is currently loaded
        """
        # Get metadata
        if is_loaded:
            metadata = plugin.get_metadata()
            status = "✓ Loaded"
            status_color = self.theme.SUCCESS_COLOR
        else:
            # Try to load metadata from manifest
            manifest_file = Path.home() / ".py_env_studio" / "plugins" / plugin_name / "plugin.json"
            if manifest_file.exists():
                try:
                    import json
                    manifest = json.loads(manifest_file.read_text())
                    metadata = self.plugin_manager._manifest_to_metadata(manifest)
                    status = "○ Not Loaded"
                    status_color = self.theme.TEXT_COLOR_LIGHT
                except Exception as e:
                    logging.error(f"Failed to load metadata for {plugin_name}: {e}")
                    return
            else:
                return

        # Create item frame
        item_frame = ctk.CTkFrame(parent, corner_radius=8, border_width=1, border_color=self.theme.BORDER_COLOR)
        item_frame.pack(padx=0, pady=8, fill="x")
        item_frame.grid_columnconfigure(1, weight=1)

        # Plugin info
        info_text = f"{metadata.name} v{metadata.version}"
        info_label = ctk.CTkLabel(
            item_frame,
            text=info_text,
            font=("Segoe UI", 12, "bold")
        )
        info_label.grid(row=0, column=0, columnspan=3, padx=12, pady=(8, 4), sticky="w")

        # Description
        desc_label = ctk.CTkLabel(
            item_frame,
            text=metadata.description,
            text_color=self.theme.TEXT_COLOR_LIGHT
        )
        desc_label.grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 4), sticky="ew")

        # Author and status
        author_status = f"by {metadata.author} • {status}"
        author_label = ctk.CTkLabel(
            item_frame,
            text=author_status,
            text_color=status_color,
            font=("Segoe UI", 10)
        )
        author_label.grid(row=2, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")

        # Buttons
        if is_loaded:
            unload_btn = self.btn(
                item_frame,
                "Disable",
                lambda: self._unload_plugin_and_refresh(plugin_name, top=parent.winfo_toplevel()),
                width=80
            )
            unload_btn.grid(row=0, column=3, rowspan=3, padx=(12, 8), pady=8)
        else:
            load_btn = self.btn(
                item_frame,
                "Enable",
                lambda: self._load_plugin_and_refresh(plugin_name, top=parent.winfo_toplevel()),
                width=80
            )
            load_btn.grid(row=0, column=3, rowspan=3, padx=(12, 8), pady=8)

    def _load_plugin_and_refresh(self, plugin_name, top):
        """Load plugin and refresh dialog."""
        try:
            self.plugin_manager.load_plugin(plugin_name)
            self.plugin_manager.set_plugin_enabled(plugin_name, True)
            self.env_log_queue.put(f"[Plugin] Loaded plugin: {plugin_name}")
            show_info(f"Plugin '{plugin_name}' loaded successfully")
            self._reload_plugins_dialog(top)
        except Exception as e:
            show_error(f"Failed to load plugin '{plugin_name}':\n{str(e)}")

    def _unload_plugin_and_refresh(self, plugin_name, top):
        """Unload plugin and refresh dialog."""
        try:
            self.plugin_manager.unload_plugin(plugin_name)
            self.plugin_manager.set_plugin_enabled(plugin_name, False)
            self.env_log_queue.put(f"[Plugin] Unloaded plugin: {plugin_name}")
            show_info(f"Plugin '{plugin_name}' unloaded successfully")
            self._reload_plugins_dialog(top)
        except Exception as e:
            show_error(f"Failed to unload plugin '{plugin_name}':\n{str(e)}")

    def _reload_plugins_dialog(self, top):
        """Reload the plugins dialog."""
        top.destroy()
        self.show_plugins_dialog()

    def on_closing(self):
        """Handle application shutdown - cleanup plugins."""
        try:
            # Execute on_app_shutdown hook for all loaded plugins
            self.plugin_manager.execute_hook("on_app_shutdown", {
                "version": self.version
            })
            logging.info("✓ Executed on_app_shutdown hook for all plugins")
        except Exception as e:
            logging.error(f"Error executing on_app_shutdown hook: {e}")
        
        self.destroy()

# ===== RUN APP =====
if __name__ == "__main__":
    app = PyEnvStudio()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
