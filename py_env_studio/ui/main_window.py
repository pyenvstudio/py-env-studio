# standard libraries --------------------------------
import tkinter,json
from tkinter import messagebox, filedialog
import ctypes
import customtkinter as ctk
import os
from PIL import Image, ImageTk
import importlib.resources as pkg_resources
from datetime import datetime as DT
import webbrowser
import logging
from configparser import ConfigParser
import threading
import queue
import datetime
import tkinter.ttk as ttk

# project modules --------------------------------
from py_env_studio.core.env_manager import (
    create_env, rename_env, delete_env, activate_env, search_envs,
    get_env_data, set_env_data, is_valid_env_selected,
    list_pythons, is_valid_python_version_detected,
    get_available_tools, add_tool
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
from  py_env_studio.utils.vulneribility_insights  import VulnerabilityInsightsApp
from py_env_studio.core.plugins import PluginManager
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
        self._setup_ui()
        self._setup_logging()

    def _setup_config(self):
        self.app_config = ConfigParser()
        self.app_config.read(get_config_path())
        self.version = self.app_config.get('project', 'version', fallback='1.0.0')

    def _setup_vars(self):
        self.env_search_var = tkinter.StringVar()
        self.selected_env_var = tkinter.StringVar()
        self.dir_var = tkinter.StringVar()
        # Load open_with tools from config or default
        self.open_with_tools = self._load_open_with_tools()
        self.open_with_var = tkinter.StringVar(value=self.open_with_tools[0] if self.open_with_tools else "CMD")
        self.choosen_python_var = tkinter.StringVar()
        self.env_log_queue = queue.Queue()
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
        
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.title("PyEnvStudio")
        self.geometry('1100x700')
        self.minsize(800, 600)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        try:
            with pkg_resources.path('py_env_studio.ui.static.icons', 'pes-transparrent-icon-default.ico') as p:
                self.icon = ImageTk.PhotoImage(file=str(p))

            # Clear default icon and set new one with delay for reliability on Windows
            self.wm_iconbitmap()
            # Use iconbitmap for .ico files first, then iconphoto
            self.after(300, lambda: self.iconbitmap(str(p)))
            self.after(350, lambda: self.iconphoto(False, self.icon))
        except Exception as e:
            logging.warning(f"Could not set icon: {e}")


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
        tools_menu.add_separator()
        tools_menu.add_command(label="Plugins", command=self.show_plugins_dialog)

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
        self.lbl(sb, "Appearance Mode:", anchor="w").grid(row=5, column=0, padx=10, pady=(10, 0), sticky="w")
        opt = self.optmenu(sb, ["Light", "Dark", "System"], self.change_appearance_mode_event, width=150)
        opt.grid(row=6, column=0, padx=10, pady=5)
        opt.set("System")
        self.lbl(sb, "UI Scaling:", anchor="w").grid(row=7, column=0, padx=10, pady=(10, 0), sticky="w")
        scl = self.optmenu(sb, ["80%", "90%", "100%", "110%", "120%"], self.change_scaling_event, width=150)
        scl.grid(row=8, column=0, padx=10, pady=5)
        scl.set("100%")

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

        # Upgrade pip checkbox below, full width
        self.checkbox_upgrade_pip = self.chk(f, "Upgrade pip during creation")
        self.checkbox_upgrade_pip.select()
        self.checkbox_upgrade_pip.grid(row=2, column=0, columnspan=5, padx=10, pady=5, sticky="w")

        # Package manager selection
        self.lbl(f, "Package Manager:").grid(row=3, column=0, padx=(10, 5), pady=5, sticky="w")
        self.create_env_pkg_mgr = self.optmenu(
            f,
            ["pip", "uv"],
            var=None,
            width=150
        )
        self.create_env_pkg_mgr.grid(row=3, column=1, padx=(0, 5), pady=5, sticky="w")
        from py_env_studio.core.env_manager import get_preferred_package_manager
        self.create_env_pkg_mgr.set(get_preferred_package_manager())

        # show python version information label below checkbox
        self.python_version_info = self.lbl(f, "USING PYTHON: Default", font=self.theme.FONT_BOLD, text_color=self.theme.HIGHLIGHT_COLOR)
        self.python_version_info.grid(row=4, column=0, columnspan=5, padx=10, pady=5, sticky="w")

        # Create environment button below
        self.btn_create_env = self.btn(f, "Create Environment", self.create_env, self.icons.get("create-env"))
        self.btn_create_env.grid(row=5, column=0, columnspan=5, padx=10, pady=5)

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
                    self.after(0, lambda action=py_tonic_action: self.notify_py_tonic(action))
                if success_msg:
                    self.after(0, lambda: show_info(success_msg))
            except Exception as e:
                if error_msg:
                    self.after(0, lambda e=e: show_error(f"{error_msg}: {str(e)}"))
            if callback:
                self.after(0, callback)
        threading.Thread(target=target, daemon=True).start()

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
                data.get("recent_location", "heh"),
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
                self.after(0, lambda: self.show_updatable_packages(updatable_packages))
            except Exception as e:
                self.after(0, lambda: show_error(f"Failed to check for package updates: {str(e)}"))

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
        self.update_treeview_style()
        self.refresh_env_list()

    def change_scaling_event(self, new_scaling: str):
        ctk.set_widget_scaling(int(new_scaling.replace("%", "")) / 100)

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
        
        self.btn_create_env.configure(state="disabled")
        self.run_async(
            lambda: create_env(env_name, python_path, bool(self.checkbox_upgrade_pip.get()),
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

    def show_about_dialog(self):
        show_info(f"PyEnvStudio: Manage Python virtual environments and packages.\n\n"
                  f"Created by: Wasim Shaikh\nVersion: {self.version}\n\nVisit: https://github.com/contactshaikhwasim")

    def show_preferences_dialog(self):
        """Show a dialog to set preferences"""
        # Load current preferences
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
            from pathlib import Path
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
