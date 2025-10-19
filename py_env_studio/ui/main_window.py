import tkinter,json
from tkinter import messagebox, filedialog
import ctypes
import customtkinter as ctk
import os
from PIL import Image, ImageTk
import importlib.resources as pkg_resources
from datetime import datetime as DT
import webbrowser


from py_env_studio.core.env_manager import (
    create_env,rename_env , list_envs, delete_env, activate_env, get_env_data, search_envs,set_env_data,
    _extract_python_version,
    VENV_DIR
)

from py_env_studio.core.pip_tools import (
    list_packages, install_package, uninstall_package, update_package,
    export_requirements, import_requirements, check_outdated_packages
)

from py_env_studio.utils.vulneribility_scanner import DBHelper, SecurityMatrix
from  py_env_studio.utils.vulneribility_insights  import VulnerabilityInsightsApp

import logging
from configparser import ConfigParser
import threading
import queue
import datetime
import tkinter.ttk as ttk


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
        self._setup_ui()
        self._setup_logging()

    def _setup_config(self):
        self.app_config = ConfigParser()
        self.app_config.read(get_config_path())
        self.VENV_DIR = os.path.expanduser(
            self.app_config.get('settings', 'venv_dir', fallback='~/.venvs')
        )
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

    def _load_open_with_tools(self):
        # Use env_manager dynamic tool logic
        from py_env_studio.core.env_manager import get_available_tools
        tools = get_available_tools()
        names = [t["name"] for t in tools]
        if "Add Tool..." not in names:
            names.append("Add Tool...")
        return names

    def _save_open_with_tools(self):
        # Save current open_with_tools to config via env_manager
        from py_env_studio.core.env_manager import add_tool
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

        # === Help Menu ===
        help_menu = tkinter.Menu(menubar, tearoff=0)
        # read the docs link
        help_menu.add_command(label="Documentation", command=self.open_documentation)
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
        from py_env_studio.core.env_manager import list_pythons
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

        # show python version information label below checkbox
        self.python_version_info = self.lbl(f, "USING PYTHON: Default", font=self.theme.FONT_BOLD, text_color=self.theme.HIGHLIGHT_COLOR)
        self.python_version_info.grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky="w")

        # Create environment button below
        self.btn_create_env = self.btn(f, "Create Environment", self.create_env, self.icons.get("create-env"))
        self.btn_create_env.grid(row=4, column=0, columnspan=5, padx=10, pady=5)

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
                from py_env_studio.core.env_manager import add_tool
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

    # === Environment & Package Logic follows (using Treeview for Packages) ===
    # ===== LOGIC: Async, logging, events, environment ops, package ops =====
    def run_async(self, func, success_msg=None, error_msg=None, callback=None):
        def target():
            try:
                func()
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
        # Updated columns - replaced SCAN_NOW with MORE
        columns = ("ENVIRONMENT", "PYTHON_VERSION", "LAST_LOCATION", "SIZE", "RENAME", "DELETE", "LAST_SCANNED", "MORE")
        self.env_tree = ttk.Treeview(
            self.env_scrollable_frame, columns=columns, show="headings", height=8, selectmode="browse"
        )
        for col, text, width, anchor in [
            ("ENVIRONMENT", "Environment", 220, "w"),
            ("PYTHON_VERSION", "Python Version", 120, "center"),
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
            self.env_tree.insert("", "end", values=(
                env,
                data.get("python_version", "-"),
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
            if not row:
                return
            env = self.env_tree.item(row)['values'][0]

            if col == "#1" or col == "#2"  or col == "#4" or col == "#7":  # Name| Version | Size | Last Scanned
                recent_location = self.env_tree.item(row)['values'][2]
                if recent_location and recent_location != "-":
                    try:
                        self.env_tree.selection_set(row)
                    except Exception:
                        pass
                    self.selected_env_var.set(env)
                    self.activate_button.configure(state="normal")
                    self.dir_var.set(recent_location)
                return
            
            if col == "#3":  # Recent Location
                recent_location = self.env_tree.item(row)['values'][2]
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

            if col == "#5":  # Rename
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
                        callback=self.refresh_env_list
                    )
            elif col == "#6":  # Delete
                if messagebox.askyesno("Confirm", f"Delete environment '{env}'?"):
                    self.run_async(
                        lambda: delete_env(env, log_callback=lambda msg: self.env_log_queue.put(msg)),
                        success_msg=f"Environment '{env}' deleted successfully.",
                        error_msg="Failed to delete environment",
                        callback=self.refresh_env_list
                    )
            elif col == "#8":  # More (... column)
                self.show_more_actions_dialog(env)

        def on_tree_double_click(event):
            col = self.env_tree.identify_column(event.x)
            row = self.env_tree.identify_row(event.y)
            if not row:
                return

            # Double click on name,recent,size,more -> trigger Activate button
            if col in ("#1","#3","#4","#7"):
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
            callback=self.refresh_env_list
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

        def on_pkg_click(event):
            col = tree.identify_column(event.x)
            row = tree.identify_row(event.y)
            if not row:
                return
            if col == "#5":  # Action column
                pkg_name = tree.item(row)["values"][0]
                self.update_installed_package(self.selected_env_var.get().strip(), pkg_name)

        # select desired
        tree.bind("<Button-1>", on_pkg_click)
        # select all
        tree.bind("<Control-a>", lambda event: tree.selection_set(tree.get_children()))

        def update_selected_packages():
            selected_items = tree.selection()
            if not selected_items:
                show_info("No packages selected for update.")
                return
            for item in selected_items:
                pkg_name = tree.item(item)["values"][0]
                self.update_installed_package(self.selected_env_var.get().strip(), pkg_name)

        # Update Selected button
        btn_update = self.btn(top, "Update Selected", update_selected_packages)
        btn_update.grid(row=1, column=0, pady=(0, 10))

        # Close button
        btn_close = self.btn(top, "Close", top.destroy)
        btn_close.grid(row=2, column=0, pady=(0, 10))

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
        if not env_name or not os.path.exists(os.path.join(self.VENV_DIR, env_name)):
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
            ]
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
            callback=lambda: self.view_installed_packages()
        )

    def update_installed_package(self, env_name, package_name):
        self.run_async(
            lambda: update_package(env_name, package_name,
                                   log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' updated in '{env_name}'.",
            error_msg="Failed to update package",
            callback=lambda: self.view_installed_packages()
        )

    # ===== BULK OPS =====
    def install_requirements(self):
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(self.VENV_DIR, env_name)):
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
                callback=lambda: self.btn_install_requirements.configure(state="normal")
            )

    def export_packages(self):
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(self.VENV_DIR, env_name)):
            show_error("Please select a valid environment.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            self.run_async(
                lambda: export_requirements(env_name, file_path),
                success_msg=f"Packages exported to {file_path}.",
                error_msg="Failed to export packages"
            )

    # ===== ENV OPS =====
    def activate_with_dir(self):
        from py_env_studio.core.integration import activate_env
        env = self.selected_env_var.get()
        directory = self.dir_var.get().strip() or None
        open_with = self.open_with_var.get() or None

        if not env:
            show_error("Please select an environment to activate.")
            return
        self.activate_button.configure(state="disabled")
        self.run_async(
            lambda: activate_env(env, directory, open_with, log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Environment '{env}' activated successfully in {open_with}.",
            error_msg="Failed to activate environment",
            callback=lambda: self.activate_button.configure(state="normal")
        )


    def show_detected_version(self, path):
        version = _extract_python_version(path)
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
            if env_name and os.path.exists(os.path.join(self.VENV_DIR, env_name)):
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
        if os.path.exists(os.path.join(self.VENV_DIR, env_name)):
            messagebox.showerror("Error", f"Environment '{env_name}' already exists.")
            return
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
            ]
        )

    def show_about_dialog(self):
        show_info(f"PyEnvStudio: Manage Python virtual environments and packages.\n\n"
                  f"Created by: Wasim Shaikh\nVersion: {self.version}\n\nVisit: https://github.com/pyenvstudio")

    def open_documentation(self):
        webbrowser.open("https://py-env-studio.readthedocs.io/en/latest/")

    def show_preferences_dialog(self):
        """Show a dialog to set preferences"""
        # Load current preferences
        pass

    def show_install_package_dialog(self):
        """Show a dialog to install a package in the selected environment."""
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(self.VENV_DIR, env_name)):
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

# ===== RUN APP =====
if __name__ == "__main__":
    app = PyEnvStudio()
    app.mainloop()