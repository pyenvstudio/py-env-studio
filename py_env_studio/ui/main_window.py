import tkinter
from tkinter import messagebox, filedialog
import ctypes
import customtkinter as ctk
import os
from PIL import Image, ImageTk
import importlib.resources as pkg_resources
from datetime import datetime as DT

from py_env_studio.core.env_manager import (
    create_env,rename_env , list_envs, delete_env, activate_env, get_env_data, search_envs,set_env_data,
    VENV_DIR
)

from py_env_studio.core.pip_tools import (
    list_packages, install_package, uninstall_package, update_package,
    export_requirements, import_requirements
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
        self.config = ConfigParser()
        self.config.read(get_config_path())
        self.VENV_DIR = os.path.expanduser(
            self.config.get('settings', 'venv_dir', fallback='~/.venvs')
        )

    def _setup_vars(self):
        self.env_search_var = tkinter.StringVar()
        self.selected_env_var = tkinter.StringVar()
        self.dir_var = tkinter.StringVar()
        self.open_with_var = tkinter.StringVar(value="CMD")
        self.env_log_queue = queue.Queue()
        self.pkg_log_queue = queue.Queue()

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
            with pkg_resources.path('py_env_studio.ui.static.icons', 'pes-icon-default.ico') as p:
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
        self._setup_sidebar()
        self._setup_tabview()
        self._setup_env_tab()
        self._setup_pkg_tab()

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
        self.btn(sb, "About", self.show_about_dialog, self.icons.get("about"), width=150).grid(row=4, column=0, padx=10, pady=(10, 20), sticky="ew")
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
        self._env_console_section(env_tab)

    def _env_create_section(self, parent):
        f = self.frame(parent, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        f.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        f.grid_columnconfigure(1, weight=1)
        self.lbl(f, "New Environment Name:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.entry_env_name = self.entry(f, "Enter environment name")
        self.entry_env_name.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        self.lbl(f, "Python Path (Optional):").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.entry_python_path = self.entry(f, "Enter Python interpreter path")
        self.entry_python_path.grid(row=1, column=1, padx=(0, 5), pady=5, sticky="ew")
        self.btn(f, "Browse", self.browse_python_path, width=80).grid(row=1, column=2, padx=(5, 10), pady=5)
        self.checkbox_upgrade_pip = self.chk(f, "Upgrade pip during creation")
        self.checkbox_upgrade_pip.select()
        self.checkbox_upgrade_pip.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        self.btn_create_env = self.btn(f, "Create Environment", self.create_env, self.icons.get("create-env"))
        self.btn_create_env.grid(row=3, column=0, columnspan=3, padx=10, pady=5)

    def _env_activate_section(self, parent):
        p = self.frame(parent, corner_radius=12, border_width=1, border_color=self.theme.BORDER_COLOR)
        p.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        p.grid_columnconfigure(1, weight=1)
        self.lbl(p, "Open At:", font=self.theme.FONT_BOLD).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="e")
        self.dir_entry = self.entry(p, "Directory", var=self.dir_var, width=150)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn(p, "Browse", self.browse_dir, width=80).grid(row=0, column=2, padx=5, pady=5)
        self.lbl(p, "Open With:", font=self.theme.FONT_BOLD).grid(row=0, column=3, padx=(10, 5), pady=5, sticky="e")
        self.open_with_dropdown = self.optmenu(p, ["CMD", "VS-Code", "PyCharm"], var=self.open_with_var, width=100)
        self.open_with_dropdown.grid(row=0, column=4, padx=5, pady=5)
        self.activate_button = self.btn(p, "Activate", self.activate_with_dir, self.icons.get("activate-env"), width=100)
        self.activate_button.grid(row=0, column=5, padx=(5, 10), pady=5)

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

    def _env_console_section(self, parent):
        self.env_console = ctk.CTkTextbox(parent, height=self.theme.CONSOLE_HEIGHT, state="disabled", font=self.theme.FONT_CONSOLE)
        self.env_console.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # === PKG TAB ===
    def _setup_pkg_tab(self):
        pkg_tab = self.tabview.tab("Packages")
        pkg_tab.grid_rowconfigure(4, weight=1)
        pkg_tab.grid_rowconfigure(5, weight=0)
        self._pkg_header(pkg_tab)
        self._pkg_install_section(pkg_tab)
        self._pkg_bulk_section(pkg_tab)
        self._pkg_manage_section(pkg_tab)
        self._pkg_console_section(pkg_tab)

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

    def _pkg_console_section(self, parent):
        self.pkg_console = ctk.CTkTextbox(parent, height=self.theme.CONSOLE_HEIGHT, state="disabled",
                                          font=self.theme.FONT_CONSOLE)
        self.pkg_console.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

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
        self._process_log_queue(self.env_log_queue, self.env_console)
        self._process_log_queue(self.pkg_log_queue, self.pkg_console)
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
        columns = ("ENVIRONMENT", "LAST_LOCATION", "SIZE", "RENAME", "DELETE", "LAST_SCANNED", "MORE")
        self.env_tree = ttk.Treeview(
            self.env_scrollable_frame, columns=columns, show="headings", height=8, selectmode="browse"
        )
        for col, text, width, anchor in [
            ("ENVIRONMENT", "Environment", 220, "w"),
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
            env_path = os.path.join(self.VENV_DIR, env)
            if col == "#4":  # Rename
                # ctk.CTkInputDialog
                dialog = ctk.CTkInputDialog(
                    text=f"Enter new name for '{env}':",
                    title="Environment Rename"
                )
                # center dialog
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
            elif col == "#5":  # Delete
                if messagebox.askyesno("Confirm", f"Delete environment '{env}'?"):
                    self.run_async(
                        lambda: delete_env(env, log_callback=lambda msg: self.env_log_queue.put(msg)),
                        success_msg=f"Environment '{env}' deleted successfully.",
                        error_msg="Failed to delete environment",
                        callback=self.refresh_env_list
                    )
            elif col == "#7":  # More (... column)
                # Show the More actions dialog
                self.show_more_actions_dialog(env)

        self.env_tree.bind("<Button-1>", on_tree_click)

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
    def install_package(self):
        env_name = self.selected_env_var.get().strip()
        package_name = self.entry_package_name.get().strip()
        if not env_name or not package_name:
            show_error("Please select an environment and enter a package name.")
            return
        if self.checkbox_confirm_install.get() and not messagebox.askyesno(
            "Confirm", f"Install '{package_name}' in '{env_name}'?"):
            return
        self.btn_install_package.configure(state="disabled")
        self.run_async(
            lambda: install_package(env_name, package_name,
                                    log_callback=lambda msg: self.pkg_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' installed in '{env_name}'.",
            error_msg="Failed to install package",
            callback=lambda: [
                self.entry_package_name.delete(0, tkinter.END),
                self.btn_install_package.configure(state="normal"),
                self.view_installed_packages()
            ]
        )

    def delete_installed_package(self, env_name, package_name):
        if self.checkbox_confirm_install.get() and not messagebox.askyesno(
            "Confirm", f"Uninstall '{package_name}' from '{env_name}'?"):
            return
        self.run_async(
            lambda: uninstall_package(env_name, package_name,
                                      log_callback=lambda msg: self.pkg_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' uninstalled from '{env_name}'.",
            error_msg="Failed to uninstall package",
            callback=lambda: self.view_installed_packages()
        )

    def update_installed_package(self, env_name, package_name):
        self.run_async(
            lambda: update_package(env_name, package_name,
                                   log_callback=lambda msg: self.pkg_log_queue.put(msg)),
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
                                            log_callback=lambda msg: self.pkg_log_queue.put(msg)),
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
        env = self.selected_env_var.get()
        directory = self.dir_var.get().strip() or None
        open_with = self.open_with_var.get() or None
        if not env:
            show_error("Please select an environment to activate.")
            return
        self.activate_button.configure(state="disabled")
        self.run_async(
            lambda: activate_env(env, directory, open_with),
            success_msg=f"Environment '{env}' activated successfully.",
            error_msg="Failed to activate environment",
            callback=lambda: self.activate_button.configure(state="normal")
        )

    def browse_python_path(self):
        selected = filedialog.askopenfilename(
            title="Select Python Interpreter",
            filetypes=[("Python Executable", "python.exe"), ("All Files", "*")]
        )
        if selected:
            self.entry_python_path.delete(0, tkinter.END)
            self.entry_python_path.insert(0, selected)

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
            lambda: create_env(env_name, python_path, self.checkbox_upgrade_pip.get(),
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
        show_info("PyEnvStudio: Manage Python virtual environments and packages.\n\n"
                  "Created by: Wasim Shaikh\nVersion: 2.0.2\n\nVisit: https://github.com/pyenvstudio")


# ===== RUN APP =====
if __name__ == "__main__":
    app = PyEnvStudio()
    app.mainloop()