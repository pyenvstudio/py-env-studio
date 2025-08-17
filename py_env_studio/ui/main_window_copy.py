import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import os
from PIL import Image, ImageTk
import importlib.resources as pkg_resources
from py_env_studio.core.env_manager import create_env, list_envs, delete_env, activate_env, get_env_data, search_envs
from py_env_studio.core.pip_tools import list_packages, install_package, uninstall_package, update_package, export_requirements, import_requirements
import logging
from configparser import ConfigParser
import threading
import queue
import datetime
import tkinter.ttk as ttk

# Layout constants
PADDING = 10
BUTTON_HEIGHT = 32
ENTRY_WIDTH = 250
SIDEBAR_WIDTH = 200
LOGO_SIZE = (150, 150)
TABLE_ROW_HEIGHT = 35
TABLE_FONT_SIZE = 14

# Color constants
HIGHLIGHT_COLOR = "#F2A42D"  # Orange for accents
ERROR_COLOR = "red"
SUCCESS_COLOR = "#61D759"  # Green for success states

def get_config_path():
    try:
        with pkg_resources.path('py_env_studio', 'config.ini') as config_path:
            return str(config_path)
    except Exception:
        return os.path.join(os.path.dirname(__file__), 'config.ini')

config = ConfigParser()
config.read(get_config_path())
VENV_DIR = os.path.expanduser(config.get('settings', 'venv_dir', fallback='~/.venvs'))

class PyEnvStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.setup_window()
        self.icons = self.load_icons()
        self.setup_ui()
        self.env_log_queue = queue.Queue()
        self.pkg_log_queue = queue.Queue()
        self.after(100, self.process_env_log_queue)
        self.after(100, self.process_pkg_log_queue)

    def setup_window(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.title('PyEnvStudio')
        try:
            with pkg_resources.path('py_env_studio.ui.static.icons', 'pes-icon-default.png') as icon_path:
                icon_img = ImageTk.PhotoImage(Image.open(str(icon_path)))
                self.iconphoto(True, icon_img)
        except Exception as e:
            logging.warning(f"Could not set window icon: {e}")
        self.geometry('1100x580')
        self.minsize(800, 500)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def load_icons(self):
        icon_names = ["logo", "create-env", "delete-env", "selected-env", "activate-env",
                      "install", "uninstall", "requirements", "export", "packages", "update", "about"]
        icons = {}
        for name in icon_names:
            try:
                with pkg_resources.path('py_env_studio.ui.static.icons', f"{name}.png") as icon_path:
                    icons[name] = ctk.CTkImage(Image.open(str(icon_path)))
            except Exception:
                icons[name] = None
                logging.warning(f"Icon '{name}' not found.")
        return icons

    def setup_ui(self):
        self.setup_sidebar()
        self.setup_tabview()
        self.setup_env_tab()
        self.setup_pkg_tab()

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=SIDEBAR_WIDTH)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        try:
            with pkg_resources.path('py_env_studio.ui.static.icons', 'pes-default-transparrent.png') as logo_path:
                self.sidebar_logo_img = ctk.CTkImage(Image.open(str(logo_path)), size=LOGO_SIZE)
        except Exception:
            self.sidebar_logo_img = None
        self.logo_img_label = ctk.CTkLabel(self.sidebar_frame, text="", image=self.sidebar_logo_img)
        self.logo_img_label.grid(row=0, column=0, padx=PADDING, pady=(PADDING, 20))

        self.btn_about = ctk.CTkButton(
            self.sidebar_frame, text="About", image=self.icons.get("about"), command=self.show_about_dialog,
            height=BUTTON_HEIGHT, width=150, hover=True
        )
        self.btn_about.grid(row=4, column=0, padx=PADDING, pady=(PADDING, 20), sticky="ew")

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=PADDING, pady=(PADDING, 0))
        self.appearance_mode_optionmenu = ctk.CTkOptionMenu(
            self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event,
            height=BUTTON_HEIGHT, width=150
        )
        self.appearance_mode_optionmenu.grid(row=6, column=0, padx=PADDING, pady=(5, PADDING))
        self.appearance_mode_optionmenu.set("System")

        self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=PADDING, pady=(PADDING, 0))
        self.scaling_optionmenu = ctk.CTkOptionMenu(
            self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"], command=self.change_scaling_event,
            height=BUTTON_HEIGHT, width=150
        )
        self.scaling_optionmenu.grid(row=8, column=0, padx=PADDING, pady=(5, PADDING))
        self.scaling_optionmenu.set("100%")

    def setup_tabview(self):
        self.tabview = ctk.CTkTabview(self, command=self.on_tab_changed)
        self.tabview.grid(row=0, column=1, padx=PADDING, pady=PADDING, sticky="nsew")
        self.tabview.add("Environments")
        self.tabview.add("Packages")
        self.tabview.tab("Environments").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Packages").grid_columnconfigure(0, weight=1)

    def setup_env_tab(self):
        env_tab = self.tabview.tab("Environments")
        env_tab.grid_rowconfigure(9, weight=1)

        self.env_search_var = tkinter.StringVar()
        self.env_search_var.trace_add('write', lambda *args: self.refresh_env_list())

        # Input Section
        # ----------------------------Environment Creation start------------------------------------------
        input_frame = ctk.CTkFrame(env_tab)
        input_frame.grid(row=0, column=0, columnspan=2, padx=PADDING, pady=(PADDING, 5), sticky="ew")
        self.label_env_name = ctk.CTkLabel(input_frame, text="New Environment Name:")
        self.label_env_name.grid(row=0, column=0, padx=(0, PADDING), pady=5, sticky="w")
        self.entry_env_name = ctk.CTkEntry(input_frame, placeholder_text="Enter environment name", width=ENTRY_WIDTH, takefocus=True)
        self.entry_env_name.grid(row=0, column=1, padx=(0, PADDING), pady=5, sticky="ew")
        self.label_python_path = ctk.CTkLabel(input_frame, text="Python Path (Optional):")
        self.label_python_path.grid(row=1, column=0, padx=(0, PADDING), pady=5, sticky="w")
        self.entry_python_path = ctk.CTkEntry(input_frame, placeholder_text="Enter Python interpreter path", width=ENTRY_WIDTH, takefocus=True)
        self.entry_python_path.grid(row=1, column=1, padx=(0, PADDING), pady=5, sticky="ew")
        self.browse_python_btn = ctk.CTkButton(
            input_frame, text="Browse", width=80, height=BUTTON_HEIGHT, command=self.browse_python_path, hover=True
        )
        self.browse_python_btn.grid(row=1, column=2, padx=(5, 0), pady=5)

        self.checkbox_upgrade_pip = ctk.CTkCheckBox(input_frame, text="Upgrade pip during creation")
        self.checkbox_upgrade_pip.grid(row=2, column=0, columnspan=3, padx=(0, PADDING), pady=5, sticky="w")
        self.checkbox_upgrade_pip.select()

        # Action Buttons
        action_frame = ctk.CTkFrame(env_tab)
        action_frame.grid(row=1, column=0, columnspan=2, padx=PADDING, pady=5, sticky="ew")
        self.btn_create_env = ctk.CTkButton(
            action_frame, text="Create Environment", command=self.create_env, image=self.icons.get("create-env"),
            width=150, height=BUTTON_HEIGHT, hover=True
        )
        self.btn_create_env.grid(row=0, column=0, padx=(0, PADDING), pady=5)
        # ----------------------------Environment Creation end------------------------------------------

        # ----------------------------Activation Section start------------------------------------------
        # Environment Picker
        self.env_picker_panel = ctk.CTkFrame(env_tab, corner_radius=10)
        self.env_picker_panel.grid(row=2, column=0, columnspan=2, padx=PADDING, pady=(PADDING, 0), sticky="ew")
        self.env_picker_panel.grid_columnconfigure(0, weight=1)
        self.env_picker_panel.grid_columnconfigure((1, 2, 3, 4, 5), weight=0)

        self.selected_env_var = tkinter.StringVar()
        self.dir_var = tkinter.StringVar()
        self.open_with_var = tkinter.StringVar(value="CMD")

        self.open_at_label = ctk.CTkLabel(self.env_picker_panel, text="Open At:", font=ctk.CTkFont(size=12, weight="bold"))
        self.open_at_label.grid(row=0, column=0, padx=(PADDING, 5), pady=5, sticky="e")
        self.dir_entry = ctk.CTkEntry(self.env_picker_panel, width=150, textvariable=self.dir_var, placeholder_text="Directory", takefocus=True)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5)
        self.browse_btn = ctk.CTkButton(
            self.env_picker_panel, text="Browse", width=80, height=BUTTON_HEIGHT, command=self.browse_dir, hover=True
        )
        self.browse_btn.grid(row=0, column=2, padx=5, pady=5)
        self.open_with_label = ctk.CTkLabel(self.env_picker_panel, text="Open With:", font=ctk.CTkFont(size=12, weight="bold"))
        self.open_with_label.grid(row=0, column=3, padx=(PADDING, 5), pady=5, sticky="e")
        self.open_with_dropdown = ctk.CTkOptionMenu(
            self.env_picker_panel, values=["CMD", "VS Code", "PyCharm"], variable=self.open_with_var, width=100, height=BUTTON_HEIGHT
        )
        self.open_with_dropdown.grid(row=0, column=4, padx=5, pady=5)
        self.activate_button = ctk.CTkButton(
            self.env_picker_panel, text="Activate", width=100, height=BUTTON_HEIGHT, command=self.activate_with_dir,
            image=self.icons.get("activate-env"), hover=True
        )
        self.activate_button.grid(row=0, column=5, padx=(5, PADDING), pady=5)
        # ----------------------------Activation Section end------------------------------------------

        # ----------------------------Search Section start------------------------------------------
        # Search Section
        self.label_env_search = ctk.CTkLabel(env_tab, text="Search Environments:")
        self.label_env_search.grid(row=8, column=0, padx=PADDING, pady=(5, 0), sticky="w")
        self.entry_env_search = ctk.CTkEntry(env_tab, textvariable=self.env_search_var, placeholder_text="Search environments...", width=ENTRY_WIDTH, takefocus=True)
        self.entry_env_search.grid(row=8, column=1, padx=PADDING, pady=(5, 0), sticky="ew")
        # ----------------------------Search Section end------------------------------------------

        # ----------------------------Environment Table Section start------------------------------------------
        # Environment List
        self.env_scrollable_frame = ctk.CTkScrollableFrame(env_tab, label_text="Available Environments")
        self.env_scrollable_frame.grid(row=9, column=0, columnspan=2, padx=PADDING, pady=PADDING, sticky="nsew")
        self.env_scrollable_frame.grid_columnconfigure(0, weight=1)
        self.env_labels = []
        self.refresh_env_list()
        # ----------------------------Environment Table Section end------------------------------------------

        # ---------------------------Environment Console Section start------------------------------------------

        self.env_console = ctk.CTkTextbox(env_tab, height=120, state="disabled", font=ctk.CTkFont(family="Courier", size=12))
        self.env_console.grid(row=10, column=0, columnspan=2, padx=PADDING, pady=PADDING, sticky="nsew")
        # ---------------------------Environment Console Section end------------------------------------------

    def setup_pkg_tab(self):
        pkg_tab = self.tabview.tab("Packages")
        pkg_tab.grid_rowconfigure(7, weight=1)

        self.selected_env_label = ctk.CTkLabel(pkg_tab, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.selected_env_label.grid(row=0, column=0, columnspan=2, padx=PADDING, pady=(PADDING, 5), sticky="ew")
        # ----------------------------New Package Installation Section start------------------------------------------
        # Input Section
        input_frame = ctk.CTkFrame(pkg_tab)
        input_frame.grid(row=1, column=0, columnspan=2, padx=PADDING, pady=5, sticky="ew")
        self.label_package_name = ctk.CTkLabel(input_frame, text="Package Name:")
        self.label_package_name.grid(row=0, column=0, padx=(0, PADDING), pady=5, sticky="w")
        self.entry_package_name = ctk.CTkEntry(input_frame, placeholder_text="Enter package name", width=ENTRY_WIDTH, takefocus=True)
        self.entry_package_name.grid(row=0, column=1, padx=(0, PADDING), pady=5, sticky="ew")

        self.checkbox_confirm_install = ctk.CTkCheckBox(input_frame, text="Confirm package actions")
        self.checkbox_confirm_install.grid(row=1, column=0, columnspan=2, padx=(0, PADDING), pady=5, sticky="w")
        self.checkbox_confirm_install.select()

        # Action Buttons
        action_frame = ctk.CTkFrame(pkg_tab)
        action_frame.grid(row=2, column=0, columnspan=2, padx=PADDING, pady=5, sticky="ew")
        self.btn_install_package = ctk.CTkButton(
            action_frame, text="Install Package", command=self.install_package, image=self.icons.get("install"),
            width=150, height=BUTTON_HEIGHT, hover=True
        )
        self.btn_install_package.grid(row=0, column=0, padx=(0, PADDING), pady=5)
        # ----------------------------New Package Installation Section end------------------------------------------

       
        # ----------------------------Bulk Package Action Section start------------------------------------------

        action_frame2 = ctk.CTkFrame(pkg_tab)
        action_frame2.grid(row=3, column=0, columnspan=2, padx=PADDING, pady=5, sticky="ew")
        self.btn_install_requirements = ctk.CTkButton(
            action_frame2, text="Install Requirements", command=self.install_requirements, image=self.icons.get("requirements"),
            width=150, height=BUTTON_HEIGHT, hover=True
        )
        self.btn_install_requirements.grid(row=0, column=0, padx=(0, PADDING), pady=5)
        self.btn_export_packages = ctk.CTkButton(
            action_frame2, text="Export Packages", command=self.export_packages, image=self.icons.get("export"),
            width=150, height=BUTTON_HEIGHT, hover=True
        )
        self.btn_export_packages.grid(row=0, column=1, padx=(0, PADDING), pady=5)
        # ----------------------------Bulk Package Action Section end------------------------------------------

        # ---------------------------Manage Packages Section start------------------------------------------

        self.btn_view_packages = ctk.CTkButton(
            pkg_tab, text="Manage Packages", command=self.view_installed_packages, image=self.icons.get("packages"),
            width=300, height=BUTTON_HEIGHT, hover=True
        )
        self.btn_view_packages.grid(row=4, column=0, columnspan=2, padx=PADDING, pady=5, sticky="ew")

        self.packages_list_frame = ctk.CTkScrollableFrame(pkg_tab, label_text="Installed Packages")
        self.packages_list_frame.grid(row=7, column=0, columnspan=2, padx=PADDING, pady=PADDING, sticky="nsew")
        self.packages_list_frame.grid_remove()
        # ---------------------------Manage Packages Section end------------------------------------------
        
        # ---------------------------Package Console Section start------------------------------------------
        self.pkg_console = ctk.CTkTextbox(pkg_tab, height=120, state="disabled", font=ctk.CTkFont(family="Courier", size=12))
        self.pkg_console.grid(row=8, column=0, columnspan=2, padx=PADDING, pady=PADDING, sticky="nsew")
        # ---------------------------Package Console Section end------------------------------------------


    def browse_python_path(self):
        selected = filedialog.askopenfilename(title="Select Python Interpreter", filetypes=[("Python Executable", "python.exe"), ("All Files", "*")])
        if selected:
            self.entry_python_path.delete(0, tkinter.END)
            self.entry_python_path.insert(0, selected)

    def browse_dir(self):
        selected = filedialog.askdirectory()
        if selected:
            self.dir_var.set(selected)

    def activate_with_dir(self):
        env = self.selected_env_var.get()
        directory = self.dir_var.get().strip() or None
        open_with = self.open_with_var.get() or None
        if not env:
            messagebox.showerror("Error", "Please select an environment to activate.")
            return
        self.activate_button.configure(state="disabled")
        threading.Thread(target=lambda: self.run_async(
            lambda: activate_env(env, directory, open_with),
            success_msg=f"Environment '{env}' activated successfully.",
            error_msg="Failed to activate environment",
            callback=lambda: self.activate_button.configure(state="normal")
        )).start()

    def update_treeview_style(self):
        mode = ctk.get_appearance_mode()
        bg_color = "white" if mode == "Light" else "#343638"
        fg_color = "black" if mode == "Light" else "white"
        style = ttk.Style()
        style.configure("Treeview", background=bg_color, foreground=fg_color, fieldbackground=bg_color, rowheight=TABLE_ROW_HEIGHT, font=("Segoe UI", TABLE_FONT_SIZE))
        style.map("Treeview", background=[('selected', HIGHLIGHT_COLOR)], foreground=[('selected', fg_color)])
        style.configure("Treeview.Heading", font=("Segoe UI", TABLE_FONT_SIZE, "bold"))

    def refresh_env_list(self):
        for widget in self.env_scrollable_frame.winfo_children():
            widget.destroy()

        query = self.env_search_var.get()
        envs = search_envs(query)

        columns = ("ENVIRONMENT", "RECENT USED LOCATION", "SIZE", "ACTION")
        self.env_tree = ttk.Treeview(
            self.env_scrollable_frame, columns=columns, show="headings", height=8, selectmode="browse"
        )
        self.env_tree.heading("ENVIRONMENT", text="Environment")
        self.env_tree.heading("RECENT USED LOCATION", text="Recent Location")
        self.env_tree.heading("SIZE", text="Size")
        self.env_tree.heading("ACTION", text="Action")
        self.env_tree.column("ENVIRONMENT", width=220, anchor="w", minwidth=120, stretch=True)
        self.env_tree.column("RECENT USED LOCATION", width=160, anchor="center", minwidth=80, stretch=True)
        self.env_tree.column("SIZE", width=100, anchor="center", minwidth=60, stretch=True)
        self.env_tree.column("ACTION", width=80, anchor="center", minwidth=60, stretch=False)
        self.env_tree.grid(row=0, column=0, columnspan=2, padx=PADDING, pady=(0, PADDING), sticky="nsew")

        self.update_treeview_style()

        for env in envs:
            env_info = get_env_data(env)
            recent = env_info.get("recent_location", "-")
            size = env_info.get("size", "-")
            item_id = self.env_tree.insert("", "end", values=(env, recent, size, ""))
            self.env_tree.tag_configure(item_id, font=("Segoe UI", TABLE_FONT_SIZE))

        def on_tree_click(event):
            region = self.env_tree.identify("region", event.x, event.y)
            if region == "cell":
                col = self.env_tree.identify_column(event.x)
                row = self.env_tree.identify_row(event.y)
                if col == "#4" and row:
                    env = self.env_tree.item(row)['values'][0]
                    if messagebox.askyesno("Confirm", f"Delete environment '{env}'?"):
                        self.run_async(
                            lambda: delete_env(env, log_callback=lambda msg: self.env_log_queue.put(msg)),
                            success_msg=f"Environment '{env}' deleted successfully.",
                            error_msg="Failed to delete environment",
                            callback=self.refresh_env_list
                        )

        self.env_tree.bind("<Button-1>", on_tree_click)

        def on_tree_select(event):
            selected = self.env_tree.selection()
            for iid in self.env_tree.get_children():
                self.env_tree.item(iid, tags=())
            if selected:
                env = self.env_tree.item(selected[0])['values'][0]
                self.selected_env_var.set(env)
                self.dir_var.set("")
                self.open_with_var.set("CMD")
                self.env_tree.item(selected[0], tags=("selected",))
                self.activate_button.configure(state="normal")
            else:
                self.selected_env_var.set("")
                self.dir_var.set("")
                self.open_with_var.set("CMD")
                self.activate_button.configure(state="disabled")

        self.env_tree.bind("<<TreeviewSelect>>", on_tree_select)

        children = self.env_tree.get_children()
        if children:
            self.env_tree.selection_set(children[0])
            env = self.env_tree.item(children[0])['values'][0]
            self.selected_env_var.set(env)
            self.activate_button.configure(state="normal")

    def run_async(self, func, success_msg=None, error_msg=None, callback=None):
        def target():
            try:
                func()
                if success_msg:
                    self.after(0, lambda: messagebox.showinfo("Success", success_msg))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"{error_msg}: {str(e)}"))
            if callback:
                self.after(0, callback)
        threading.Thread(target=target).start()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        self.update_treeview_style()
        self.refresh_env_list()

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def create_env(self):
        env_name = self.entry_env_name.get().strip()
        python_path = self.entry_python_path.get().strip() or None
        if not env_name:
            messagebox.showerror("Error", "Please enter an environment name.")
            return
        if os.path.exists(os.path.join(VENV_DIR, env_name)):
            messagebox.showerror("Error", f"Environment '{env_name}' already exists.")
            return
        self.btn_create_env.configure(state="disabled")
        self.run_async(
            lambda: create_env(env_name, python_path, self.checkbox_upgrade_pip.get(), log_callback=lambda msg: self.env_log_queue.put(msg)),
            success_msg=f"Environment '{env_name}' created successfully.",
            error_msg="Failed to create environment",
            callback=lambda: [self.entry_env_name.delete(0, tkinter.END), self.entry_python_path.delete(0, tkinter.END), self.btn_create_env.configure(state="normal"), self.refresh_env_list()]
        )

    def install_package(self):
        env_name = self.selected_env_var.get().strip()
        package_name = self.entry_package_name.get().strip()
        if not env_name or not package_name:
            messagebox.showerror("Error", "Please select an environment and enter a package name.")
            return
        if self.checkbox_confirm_install.get() and not messagebox.askyesno("Confirm", f"Install '{package_name}' in '{env_name}'?"):
            return
        self.btn_install_package.configure(state="disabled")
        self.run_async(
            lambda: install_package(env_name, package_name, log_callback=lambda msg: self.pkg_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' installed in '{env_name}'.",
            error_msg="Failed to install package",
            callback=lambda: [self.entry_package_name.delete(0, tkinter.END), self.btn_install_package.configure(state="normal"), self.view_installed_packages()]
        )

    def delete_package(self):
        env_name = self.selected_env_var.get().strip()
        package_name = self.entry_package_name.get().strip()
        if not env_name or not package_name:
            messagebox.showerror("Error", "Please select an environment and enter a package name.")
            return
        if self.checkbox_confirm_install.get() and not messagebox.askyesno("Confirm", f"Uninstall '{package_name}' from '{env_name}'?"):
            return
        self.btn_delete_package.configure(state="disabled")
        self.run_async(
            lambda: uninstall_package(env_name, package_name, log_callback=lambda msg: self.pkg_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' uninstalled from '{env_name}'.",
            error_msg="Failed to uninstall package",
            callback=lambda: [self.entry_package_name.delete(0, tkinter.END), self.btn_delete_package.configure(state="normal"), self.view_installed_packages()]
        )

    def install_requirements(self):
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
            messagebox.showerror("Error", "Please select a valid environment.")
            return
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.btn_install_requirements.configure(state="disabled")
            self.run_async(
                lambda: import_requirements(env_name, file_path, log_callback=lambda msg: self.pkg_log_queue.put(msg)),
                success_msg=f"Requirements from '{file_path}' installed in '{env_name}'.",
                error_msg="Failed to install requirements",
                callback=lambda: self.btn_install_requirements.configure(state="normal")
            )

    def export_packages(self):
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
            messagebox.showerror("Error", "Please select a valid environment.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            self.run_async(
                lambda: export_requirements(env_name, file_path),
                success_msg=f"Packages exported to {file_path}.",
                error_msg="Failed to export packages"
            )

    def view_installed_packages(self):
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
            self.selected_env_label.configure(text="No valid environment selected.", text_color=ERROR_COLOR)
            self.packages_list_frame.grid_remove()
            return

        for widget in self.packages_list_frame.winfo_children():
            widget.destroy()

        try:
            packages = list_packages(env_name)
            self.packages_list_frame.grid()

            headers = ["Package", "Version", "Delete", "Update"]
            for col, header in enumerate(headers):
                ctk.CTkLabel(self.packages_list_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=col, padx=10, pady=5, sticky="nsew")

            for row, (pkg_name, pkg_version) in enumerate(packages, start=1):
                ctk.CTkLabel(self.packages_list_frame, text=pkg_name).grid(row=row, column=0, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(self.packages_list_frame, text=pkg_version).grid(row=row, column=1, padx=10, pady=5, sticky="w")
                delete_btn = ctk.CTkButton(
                    self.packages_list_frame, text="Delete", command=lambda pn=pkg_name: self.delete_installed_package(env_name, pn),
                    image=self.icons.get("uninstall"), width=80, height=BUTTON_HEIGHT, hover=True
                ) if pkg_name != "pip" else ctk.CTkButton(
                    self.packages_list_frame, text="Delete", state="disabled", image=self.icons.get("uninstall"), width=80, height=BUTTON_HEIGHT
                )
                delete_btn.grid(row=row, column=2, padx=10, pady=5)
                update_btn = ctk.CTkButton(
                    self.packages_list_frame, text="Update", command=lambda pn=pkg_name: self.update_installed_package(env_name, pn),
                    image=self.icons.get("update"), width=80, height=BUTTON_HEIGHT, hover=True
                )
                update_btn.grid(row=row, column=3, padx=10, pady=5)
        except Exception as e:
            self.packages_list_frame.grid_remove()
            messagebox.showerror("Error", f"Failed to list packages: {str(e)}")

    def delete_installed_package(self, env_name, package_name):
        if self.checkbox_confirm_install.get() and not messagebox.askyesno("Confirm", f"Uninstall '{package_name}' from '{env_name}'?"):
            return
        self.btn_view_packages.configure(state="disabled")
        self.run_async(
            lambda: uninstall_package(env_name, package_name, log_callback=lambda msg: self.pkg_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' uninstalled from '{env_name}'.",
            error_msg="Failed to uninstall package",
            callback=lambda: [self.btn_view_packages.configure(state="normal"), self.view_installed_packages()]
        )

    def update_installed_package(self, env_name, package_name):
        self.btn_view_packages.configure(state="disabled")
        self.run_async(
            lambda: update_package(env_name, package_name, log_callback=lambda msg: self.pkg_log_queue.put(msg)),
            success_msg=f"Package '{package_name}' updated in '{env_name}'.",
            error_msg="Failed to update package",
            callback=lambda: [self.btn_view_packages.configure(state="normal"), self.view_installed_packages()]
        )

    def on_tab_changed(self):
        if self.tabview.get() == "Packages":
            env_name = self.selected_env_var.get().strip()
            if env_name and os.path.exists(os.path.join(VENV_DIR, env_name)):
                self.selected_env_label.configure(
                    text=f"Selected Environment: {env_name}", text_color=HIGHLIGHT_COLOR,
                    image=self.icons.get("selected-env"), compound="left"
                )
            else:
                self.selected_env_label.configure(text="No valid environment selected.", text_color=ERROR_COLOR)
            self.packages_list_frame.grid_remove()

    def show_about_dialog(self):
        messagebox.showinfo("About PyEnvStudio", "PyEnvStudio: Manage Python virtual environments and packages.\n\n"
                                                  "Created by: Wasim Shaikh\nVersion: 1.0.0\n\n"
                                                  "Visit: https://github.com/pyenvstudio", icon='info')

    def process_env_log_queue(self):
        try:
            while True:
                msg = self.env_log_queue.get_nowait()
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                full_msg = f"[{timestamp}] {msg}"
                self.env_console.configure(state="normal")
                if "error" in msg.lower():
                    self.env_console.insert("end", full_msg + "\n", "error")
                else:
                    self.env_console.insert("end", full_msg + "\n")
                self.env_console.configure(state="disabled")
                self.env_console.see("end")
        except queue.Empty:
            pass
        self.after(100, self.process_env_log_queue)

    def process_pkg_log_queue(self):
        try:
            while True:
                msg = self.pkg_log_queue.get_nowait()
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                full_msg = f"[{timestamp}] {msg}"
                self.pkg_console.configure(state="normal")
                if "error" in msg.lower():
                    self.pkg_console.insert("end", full_msg + "\n", "error")
                else:
                    self.pkg_console.insert("end", full_msg + "\n")
                self.pkg_console.configure(state="disabled")
                self.pkg_console.see("end")
        except queue.Empty:
            pass
        self.after(100, self.process_pkg_log_queue)

if __name__ == "__main__":
    app = PyEnvStudio()
    app.mainloop()