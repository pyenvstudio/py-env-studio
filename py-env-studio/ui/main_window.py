import tkinter
from tkinter import messagebox, filedialog
import customtkinter as ctk
import os
from PIL import Image, ImageTk
from core.env_manager import create_env, list_envs, delete_env, get_env_python, activate_env, get_env_data, search_envs
from core.pip_tools import list_packages, install_package, uninstall_package, update_package, export_requirements, import_requirements
import logging
from configparser import ConfigParser

# Load configuration
config = ConfigParser()
config.read('config.ini')

VENV_DIR = os.path.expanduser(config.get('settings', 'venv_dir', fallback='~/.venvs'))
# Get the current script's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
class PyEnvStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        ctk.set_appearance_mode("System")  # Theme
        ctk.set_default_color_theme("blue")  # Enterprise blue theme
        self.title('PyEnvStudio')
        try:
            icon_path =  os.path.join(BASE_DIR, "static", "icons","logo.png")
            self.wm_iconbitmap(r"{icon_path}")
        except Exception as e:
            logging.warning(f"Could not set window icon: {e}")
        self.geometry('1100x580')
        self.minsize(800, 500)

        

        # Configure grid for responsiveness
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Load icons
        try:
            self.icons = {
                # full path to the logo image
                "logo": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","logo.png"))),
                 
                # https://icon-sets.iconify.design/solar/?icon-filter=home-
                "create-env": ctk.CTkImage(Image.open( os.path.join(BASE_DIR, "static", "icons","create-env.png"))),
                "delete-env": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","delete-env.png"))),
                "selected-env": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","selected-env.png"))),
                "activate-env": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","activate-env.png"))),
                "install": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","install.png"))),
                "uninstall": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","uninstall.png"))),
                "requirements": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","requirements.png"))),
                "export": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","export.png"))),
                "packages": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","packages.png"))),
                "update": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","update.png"))),
                "about": ctk.CTkImage(Image.open(os.path.join(BASE_DIR, "static", "icons","about.png"))),
            }
        except FileNotFoundError:
            self.icons = {}
            logging.warning("Icon files not found. Running without icons.")

        # Sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        
        # Logo and appearance settings (256x256 logo below the app name)
        logo_path = os.path.join(BASE_DIR, "static", "icons","logo.png")
        self.sidebar_logo_img = ctk.CTkImage(Image.open(logo_path), size=(256, 256))
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PyEnvStudio",text_color="#00797A",fg_color="#CDD3D3", font=ctk.CTkFont(size=30, weight="bold"))
        self.logo_label.grid(row=1, column=0, padx=20, pady=(10, 10))
        self.logo_img_label = ctk.CTkLabel(self.sidebar_frame, text="", image=self.sidebar_logo_img)
        self.logo_img_label.grid(row=2, column=0, padx=20, pady=(0, 10))

        # About button
        self.btn_about = ctk.CTkButton(
            self.sidebar_frame,
            text="About",
            image=self.icons.get("about"),
            command=self.show_about_dialog,
            
        )
        self.btn_about.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")

        # Appearance settings
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionmenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                           command=self.change_appearance_mode_event)
        self.appearance_mode_optionmenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionmenu.set("System")

        self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionmenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                   command=self.change_scaling_event)
        self.scaling_optionmenu.grid(row=8, column=0, padx=20, pady=(10, 20))
        self.scaling_optionmenu.set("100%")

        # Tabview for Environments and Packages
        self.tabview = ctk.CTkTabview(self, command=self.on_tab_changed)
        self.tabview.grid(row=0, column=1, columnspan=3, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.tabview.add("Environments")
        self.tabview.add("Packages")
        self.tabview.tab("Environments").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Packages").grid_columnconfigure(0, weight=1)


        # Environments Tab
        env_tab = self.tabview.tab("Environments")

        # SEARCH FIELD for environments (to be placed below Available Environments label, above the table)
        self.env_search_var = tkinter.StringVar()
        self.env_search_var.trace_add('write', lambda *args: self.refresh_env_list())

        # Environment Name as input field for new environment only
        self.label_env_name = ctk.CTkLabel(env_tab, text="New Environment Name:")
        self.label_env_name.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="w")
        self.entry_env_name = ctk.CTkEntry(env_tab, placeholder_text="Enter new environment name", width=200)
        self.entry_env_name.grid(row=1, column=1, padx=20, pady=(5, 5), sticky="ew")
        self.entry_env_name.bind("<KeyRelease>", self.on_env_name_change)

        self.label_python_path = ctk.CTkLabel(env_tab, text="Python Path (optional):")
        self.label_python_path.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.entry_python_path = ctk.CTkEntry(env_tab, placeholder_text="Enter Python interpreter path")
        self.entry_python_path.grid(row=2, column=1, padx=(20, 0), pady=5, sticky="ew")

        def browse_python_path_callback():
            selected = filedialog.askopenfilename(
                title="Select Python Interpreter",
                filetypes=[("Python Executable", "python.exe"), ("All Files", "*")]
            )
            if selected:
                self.entry_python_path.delete(0, tkinter.END)
                self.entry_python_path.insert(0, selected)

        self.browse_python_btn = ctk.CTkButton(
            env_tab,
            text="...📂",
            width=28,
            height=28,
            command=browse_python_path_callback
        )
        self.browse_python_btn.grid(row=1, column=2, padx=(2, 20), pady=5)

        # Radio buttons for Python version : ##for future use##
        # self.python_version_frame = ctk.CTkFrame(env_tab)
        # self.python_version_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        # self.python_version_label = ctk.CTkLabel(self.python_version_frame, text="Python Version:")
        # self.python_version_label.grid(row=0, column=0, padx=10, pady=5)
        # self.python_version_var = tkinter.StringVar(value="default")
        # self.radio_python_default = ctk.CTkRadioButton(self.python_version_frame, text="Default",
        #                                              variable=self.python_version_var, value="default",state="disabled")
        

        # Checkbox for upgrading pip
        self.checkbox_upgrade_pip = ctk.CTkCheckBox(env_tab, text="Upgrade pip during creation")
        self.checkbox_upgrade_pip.grid(row=3, column=0, columnspan=2, padx=20, pady=5, sticky="w")
        self.checkbox_upgrade_pip.select()

        # Environment buttons
        self.btn_create_env = ctk.CTkButton(env_tab, text="Create Environment", command=self.create_env,
                                           image=self.icons.get("create-env"))
        self.btn_create_env.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        # Remove Delete Environment button from its old position

        # Picker panel (control panel) at the top, not inside scrollable
        self.env_picker_panel = ctk.CTkFrame(env_tab, fg_color="#F8FAFB", corner_radius=10, border_width=1, border_color="#D0D7DE")
        self.env_picker_panel.grid(row=7, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 0))
        self.env_picker_panel.grid_columnconfigure(0, weight=2)
        self.env_picker_panel.grid_columnconfigure(1, weight=1)
        self.env_picker_panel.grid_columnconfigure(2, weight=0)
        self.env_picker_panel.grid_columnconfigure(3, weight=1)
        self.env_picker_panel.grid_columnconfigure(4, weight=1)

        # Variables for controls
        self.selected_env_var = tkinter.StringVar()
        self.dir_var = tkinter.StringVar()
        self.open_with_var = tkinter.StringVar(value="CMD")


        # OPEN AT label
        self.open_at_label = ctk.CTkLabel(
            self.env_picker_panel,
            text="OPEN AT:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="e"
        )
        self.open_at_label.grid(row=0, column=1, padx=(5, 0), pady=8, sticky="e")

        # Directory entry and browse button (minimal, modern)
        self.dir_entry = ctk.CTkEntry(
            self.env_picker_panel,
            width=180,
            textvariable=self.dir_var,
            placeholder_text="Directory (optional)"
        )
        self.dir_entry.grid(row=0, column=2, padx=(2, 0), pady=8)
        def browse_dir_callback():
            selected = filedialog.askdirectory()
            if selected:
                self.dir_var.set(selected)
        self.browse_btn = ctk.CTkButton(
            self.env_picker_panel,
            text="...📂",
            width=28,
            height=28,
            command=browse_dir_callback
        )
        self.browse_btn.grid(row=0, column=3, padx=(2, 0), pady=8)

        # OPEN WITH label
        self.open_with_label = ctk.CTkLabel(
            self.env_picker_panel,
            text="OPEN WITH:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="e"
        )
        self.open_with_label.grid(row=0, column=4, padx=(5, 0), pady=8, sticky="e")

        # OPEN WITH dropdown (minimal, modern)
        self.open_with_dropdown = ctk.CTkOptionMenu(
            self.env_picker_panel,
            values=["CMD", "VS-Code", "PyCharm(Beta)"],
            variable=self.open_with_var,
            width=90
        )
        self.open_with_dropdown.grid(row=0, column=5, padx=(2, 0), pady=8)

        # Activate Button
        def activate_with_dir():
            env = self.selected_env_var.get()
            directory = self.dir_var.get().strip() or None
            open_with = self.open_with_var.get() or None
            print(f"Activating {env} in directory: {directory} with IDE: {open_with}")
            activate_env(env, directory, open_with)
        self.activate_button = ctk.CTkButton(
            self.env_picker_panel,
            text="Activate",
            width=80,
            height=28,
            command=activate_with_dir,
            image=self.icons.get("activate-env")
        )
        self.activate_button.grid(row=0, column=6, padx=(5, 10), pady=8)

        # Environment list (scrollable)
        self.env_scrollable_frame = ctk.CTkScrollableFrame(env_tab, label_text="Available Environments")
        self.env_scrollable_frame.grid(row=8, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.env_scrollable_frame.grid_columnconfigure(0, weight=1)
        # Add SEARCH field below the label, above the table
        self.label_env_search = ctk.CTkLabel(self.env_scrollable_frame, text="SEARCH:")
        self.label_env_search.grid(row=0, column=0, padx=(10, 5), pady=(5, 5), sticky="w")
        self.entry_env_search = ctk.CTkEntry(self.env_scrollable_frame, textvariable=self.env_search_var, placeholder_text="Search environments...", width=200)
        self.entry_env_search.grid(row=0, column=1, padx=(0, 10), pady=(5, 5), sticky="ew")
        self.env_labels = []
        self.refresh_env_list()

        # Packages Tab
        pkg_tab = self.tabview.tab("Packages")

        # Highlighted selected environment label
        self.selected_env_label = ctk.CTkLabel(pkg_tab, text="", text_color="green", font=ctk.CTkFont(size=16, weight="bold"))
        self.selected_env_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 5), sticky="ew")

        self.label_package_name = ctk.CTkLabel(pkg_tab, text="Package Name:")
        self.label_package_name.grid(row=1, column=0, padx=20, pady=(20, 5), sticky="w")
        self.entry_package_name = ctk.CTkEntry(pkg_tab, placeholder_text="Enter package name")
        self.entry_package_name.grid(row=1, column=1, padx=20, pady=(20, 5), sticky="ew")

        # Checkbox for package confirmation
        self.checkbox_confirm_install = ctk.CTkCheckBox(pkg_tab, text="Confirm package installation")
        self.checkbox_confirm_install.grid(row=2, column=0, columnspan=2, padx=20, pady=5, sticky="w")
        self.checkbox_confirm_install.select()


        # Package buttons
        self.btn_install_package = ctk.CTkButton(pkg_tab, text="Install Package", command=self.install_package,
                                               image=self.icons.get("install"))
        self.btn_install_package.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        self.btn_delete_package = ctk.CTkButton(pkg_tab, text="Delete Package", command=self.delete_package,
                                              image=self.icons.get("uninstall"))
        self.btn_delete_package.grid(row=4, column=1, padx=20, pady=5, sticky="ew")

        self.btn_install_requirements = ctk.CTkButton(pkg_tab, text="Install requirements.txt",
                                                    command=self.install_requirements,
                                                    image=self.icons.get("requirements"))
        self.btn_install_requirements.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        self.btn_export_packages = ctk.CTkButton(pkg_tab, text="Export Packages List", command=self.export_packages,
                                               image=self.icons.get("export"))
        self.btn_export_packages.grid(row=5, column=1, padx=20, pady=5, sticky="ew")

        self.btn_view_packages = ctk.CTkButton(pkg_tab, text="Manage Installed Packages",
                                       command=self.view_installed_packages,
                                       image=self.icons.get("packages"))
        self.btn_view_packages.grid(row=6, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

        # Add the dynamic packages list frame (initially empty)
        self.packages_list_frame = ctk.CTkScrollableFrame(pkg_tab, label_text="Installed Packages")
        self.packages_list_frame.grid(row=7, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.packages_list_frame.grid_remove()  # Hide initially

        # Bind environment name entry to update Packages tab availability
        self.entry_env_name.bind("<KeyRelease>", self.on_env_name_change)

        # Set window icon
        icon_path = os.path.join(BASE_DIR, "static", "icons","logo.png")
        icon_img = tkinter.PhotoImage(file=icon_path)
        self.iconphoto(True, icon_img)





    def refresh_env_list(self):
        """Refresh the list of environments in the scrollable frame and update ComboBox. Now uses ttk.Treeview for table alignment. Picker panel is at the top."""
        import tkinter.ttk as ttk

        # Remove previous widgets in env_scrollable_frame except the search widgets (row 0)
        for widget in self.env_scrollable_frame.winfo_children():
            info = widget.grid_info()
            if info.get('row', None) != 0:
                widget.destroy()

        # Use search if search field is present
        query = self.env_search_var.get() if hasattr(self, 'env_search_var') else ''
        envs = search_envs(query)

        # Create Treeview for environments (ENVIRONMENT, RECENT USED LOCATION, SIZE, ACTION columns)
        columns = ("ENVIRONMENT", "RECENT USED LOCATION", "SIZE", "ACTION")
        self.env_tree = ttk.Treeview(
            self.env_scrollable_frame,
            columns=columns,
            show="headings",
            height=12,
            selectmode="browse"
        )
        self.env_tree.heading("ENVIRONMENT", text="ENVIRONMENT")
        self.env_tree.heading("RECENT USED LOCATION", text="RECENT USED LOCATION")
        self.env_tree.heading("SIZE", text="SIZE")
        self.env_tree.heading("ACTION", text="ACTION")
        self.env_tree.column("ENVIRONMENT", width=220, anchor="w", minwidth=120, stretch=True)
        self.env_tree.column("RECENT USED LOCATION", width=160, anchor="center", minwidth=80, stretch=True)
        self.env_tree.column("SIZE", width=100, anchor="center", minwidth=60, stretch=True)
        self.env_tree.column("ACTION", width=80, anchor="center", minwidth=60, stretch=False)
        self.env_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 8))

        # Insert environments into the table (recent usage and size from get_env_data)
        for env in envs:
            env_info = get_env_data(env)
            recent = env_info.get("recent_location", "-")
            size = env_info.get("size", "-")
            self.env_tree.insert("", "end", values=(env, recent, size, "🗑"))

        # Add delete button click event (only on delete icon column)
        def on_tree_click(event):
            region = self.env_tree.identify("region", event.x, event.y)
            if region == "cell":
                col = self.env_tree.identify_column(event.x)
                row = self.env_tree.identify_row(event.y)
                # ACTION column is the 4th column (index starts at 1, so "#4")
                if col == "#4" and row:
                    env = self.env_tree.item(row)['values'][0]
                    if messagebox.askyesno("Confirm", f"Delete environment '{env}'?"):
                        try:
                            delete_env(env)
                            self.refresh_env_list()
                            messagebox.showinfo("Success", f"Environment '{env}' deleted successfully.")
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to delete environment: {e}")
        self.env_tree.bind("<Button-1>", on_tree_click)

        # Make row height bigger (ttk.Treeview style)
        style = ttk.Style()
        style.configure("Treeview", rowheight=50, font=("Segoe UI", 15))
        style.map("Treeview", background=[('selected', "#61D759")])

        # When a row is selected, update the picker panel, ComboBox, and highlight row
        def on_tree_select(event):
            selected = self.env_tree.selection()
            # Remove highlight from all rows
            for iid in self.env_tree.get_children():
                self.env_tree.item(iid, tags=())
            if selected:
                env = self.env_tree.item(selected[0])['values'][0]
                self.selected_env_var.set(env)
                self.dir_var.set("")
                self.open_with_var.set("CMD")
                # Highlight selected row
                self.env_tree.item(selected[0], tags=("selected",))
                self.activate_button.configure(state="normal")
                # Only update ComboBox display, not the selected env logic
                if hasattr(self, 'entry_env_name') and hasattr(self.entry_env_name, 'set'):
                    self.entry_env_name.set(env)
            else:
                self.selected_env_var.set("")
                self.dir_var.set("")
                self.open_with_var.set("CMD")
                self.activate_button.configure(state="disabled")
                
                


        self.env_tree.bind("<<TreeviewSelect>>", on_tree_select)

        # Select the first row by default if available
        children = self.env_tree.get_children()
        if children:
            self.env_tree.selection_set(children[0])
            env = self.env_tree.item(children[0])['values'][0]
            self.selected_env_var.set(env)
            self.dir_var.set("")
            self.open_with_var.set("CMD")
            self.activate_button.configure(state="normal")
            # Sync ComboBox (Create Env Input select)
            if hasattr(self, 'entry_env_name') and hasattr(self.entry_env_name, 'set'):
                self.entry_env_name.set(env)
        else:
            self.activate_button.configure(state="disabled")

        # No ComboBox: do not update values for entry field


        # When a row is selected, update the control panel, ComboBox, and highlight row
        def on_tree_select(event):
            selected = self.env_tree.selection()
            # Remove highlight from all rows
            for iid in self.env_tree.get_children():
                self.env_tree.item(iid, tags=())
            if selected:
                env = self.env_tree.item(selected[0])['values'][0]
                self.selected_env_var.set(env)
                self.dir_var.set("")
                self.open_with_var.set("CMD")
                # Highlight selected row
                self.env_tree.item(selected[0], tags=("selected",))
                self.activate_button.configure(state="normal")
                # Sync ComboBox (Create Env Input select)
                if hasattr(self, 'entry_env_name') and hasattr(self.entry_env_name, 'set'):
                    self.entry_env_name.set(env)
            else:
                self.selected_env_var.set("")
                self.dir_var.set("")
                self.open_with_var.set("CMD")
                self.activate_button.configure(state="disabled")
        self.env_tree.bind("<<TreeviewSelect>>", on_tree_select)

        # Style for selected row highlight
        style = ttk.Style()
        style.map("Treeview", background=[('selected', '#B7E0F7')])

        # Select the first row by default if available
        children = self.env_tree.get_children()
        if children:
            self.env_tree.selection_set(children[0])
            env = self.env_tree.item(children[0])['values'][0]
            self.selected_env_var.set(env)
            self.dir_var.set("")
            self.open_with_var.set("CMD")
            self.activate_button.configure(state="normal")
            # Sync ComboBox (Create Env Input select)
            if hasattr(self, 'entry_env_name') and hasattr(self.entry_env_name, 'set'):
                self.entry_env_name.set(env)
        else:
            self.activate_button.configure(state="disabled")



    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def create_env(self):
        """Create a new virtual environment."""
        env_name = self.entry_env_name.get().strip()
        python_path = self.entry_python_path.get().strip() or None
        if not env_name:
            messagebox.showerror("Error", "Please enter a new environment name.")
            return
        # Ensure the env does not already exist
        if os.path.exists(os.path.join(VENV_DIR, env_name)):
            messagebox.showerror("Error", f"Environment '{env_name}' already exists.")
            return
        try:
            self.btn_create_env.configure(state="disabled")
            self.update()
            if self.checkbox_upgrade_pip.get():
                create_env(env_name, python_path=None, upgrade_pip=True)
            else:
                create_env(env_name, python_path=None)
            self.refresh_env_list()
            self.entry_env_name.delete(0, tkinter.END)
            self.entry_python_path.delete(0, tkinter.END)
            messagebox.showinfo("Success", f"Environment '{env_name}' created successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create environment: {e}")
        finally:
            self.btn_create_env.configure(state="normal")

    def delete_env(self):
        """Delete the selected environment."""
        env_name = self.entry_env_name.get().strip()
        if not env_name or env_name == "Create new environment":
            messagebox.showerror("Error", "Please select a valid environment name.")
            return
        if messagebox.askyesno("Confirm", f"Delete environment '{env_name}'?"):
            try:
                self.btn_delete_env.configure(state="disabled")
                self.update()
                delete_env(env_name)
                self.refresh_env_list()
                messagebox.showinfo("Success", f"Environment '{env_name}' deleted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete environment: {e}")
            finally:
                self.btn_delete_env.configure(state="normal")


    def install_package(self):
        """Install a package in the selected environment."""
        env_name = self.selected_env_var.get().strip()
        package_name = self.entry_package_name.get().strip()
        if not env_name or not package_name:
            messagebox.showerror("Error", "Please enter a valid environment and package name.")
            return
        if self.checkbox_confirm_install.get() and not messagebox.askyesno("Confirm", f"Install '{package_name}' in '{env_name}'?"):
            return
        try:
            self.btn_install_package.configure(state="disabled")
            self.update()
            install_package(env_name, package_name)
            self.entry_package_name.delete(0, tkinter.END)
            messagebox.showinfo("Success", f"Package '{package_name}' installed in '{env_name}'.")
            self.view_installed_packages()  # <-- Auto-refresh the package list
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install package: {e}")
        finally:
            self.btn_install_package.configure(state="normal")

    def delete_package(self):
        """Uninstall a package from the selected environment."""
        env_name = self.selected_env_var.get().strip()
        package_name = self.entry_package_name.get().strip()
        if not env_name or not package_name:
            messagebox.showerror("Error", "Please enter a valid environment and package name.")
            return
        if self.checkbox_confirm_install.get() and not messagebox.askyesno("Confirm", f"Uninstall '{package_name}' from '{env_name}'?"):
            return
        try:
            self.btn_delete_package.configure(state="disabled")
            self.update()
            uninstall_package(env_name, package_name)
            self.entry_package_name.delete(0, tkinter.END)
            messagebox.showinfo("Success", f"Package '{package_name}' uninstalled from '{env_name}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to uninstall package: {e}")
        finally:
            self.btn_delete_package.configure(state="normal")

    def install_requirements(self):
        """Install packages from a requirements.txt file."""
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
            messagebox.showerror("Error", "Please select a valid environment name.")
            return
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                self.btn_install_requirements.configure(state="disabled")
                self.update()
                import_requirements(env_name, file_path)
                messagebox.showinfo("Success", f"Requirements({file_path}) installed in '{env_name}'.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to install requirements: {e}")
            finally:
                self.btn_install_requirements.configure(state="normal")

    def export_packages(self):
        """Export installed packages to a requirements.txt file."""
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
            messagebox.showerror("Error", "Please select a valid environment name.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                export_requirements(env_name, file_path)
                messagebox.showinfo("Success", f"Packages exported to {file_path}.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export packages: {e}")

    def view_installed_packages(self):
        """Display installed packages in the embedded list below the button."""
        env_name = self.selected_env_var.get().strip()
        if not env_name or not os.path.exists(os.path.join(VENV_DIR, env_name)):
            self.selected_env_label.configure(text="")  # Clear label if invalid
            messagebox.showerror("Error", "Please select a valid environment name.")
            self.packages_list_frame.grid_remove()
            return

        # Clear previous content
        for widget in self.packages_list_frame.winfo_children():
            widget.destroy()

        try:
            packages = list_packages(env_name)
            self.packages_list_frame.grid()  # Show the frame

            # Properly align headers
            headers = ["PACKAGE", "VERSION", "DELETE", "UPDATE"]
            for col, header in enumerate(headers):
                ctk.CTkLabel(
                    self.packages_list_frame,
                    text=header,
                    font=ctk.CTkFont(weight="bold"),
                    anchor="center"
                ).grid(row=0, column=col, padx=10, pady=5, sticky="nsew")

            for row, (pkg_name, pkg_version) in enumerate(packages, start=1):
                ctk.CTkLabel(self.packages_list_frame, text=pkg_name).grid(row=row, column=0, padx=10, pady=5, sticky="w")
                ctk.CTkLabel(self.packages_list_frame, text=pkg_version).grid(row=row, column=1, padx=10, pady=5, sticky="w")
                if pkg_name == "pip":
                    delete_btn = ctk.CTkButton(
                        self.packages_list_frame,
                        text="Delete",
                        state="disabled",
                        image=self.icons.get("uninstall")
                    )
                else:
                    delete_btn = ctk.CTkButton(
                        self.packages_list_frame,
                        text="Delete",
                        command=lambda pn=pkg_name: self.delete_installed_package(env_name, pn),
                        image=self.icons.get("uninstall")
                    )
                delete_btn.grid(row=row, column=2, padx=10, pady=5)
                update_btn = ctk.CTkButton(
                    self.packages_list_frame,
                    text="Update",
                    command=lambda pn=pkg_name: self.update_installed_package(env_name, pn),
                    image=self.icons.get("update")
                )
                update_btn.grid(row=row, column=3, padx=10, pady=5)
        except Exception as e:
            self.packages_list_frame.grid_remove()
            messagebox.showerror("Error", f"Failed to list packages: {e}")

    def delete_installed_package(self, env_name, package_name):
        """Delete a package from the package table."""
        if self.checkbox_confirm_install.get() and not messagebox.askyesno("Confirm", f"Uninstall '{package_name}' from '{env_name}'?"):
            return
        try:
            self.btn_view_packages.configure(state="disabled")
            self.update()
            uninstall_package(env_name, package_name)
            messagebox.showinfo("Success", f"Package '{package_name}' uninstalled from '{env_name}'.")
            self.view_installed_packages()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to uninstall package: {e}")
        finally:
            self.btn_view_packages.configure(state="normal")

    def update_installed_package(self, env_name, package_name):
        """Update a package from the package table."""
        try:

            self.btn_view_packages.configure(state="disabled")
            self.update()
            update_package(env_name, package_name)
            messagebox.showinfo("Success", f"Package '{package_name}' updated in '{env_name}'.")
            self.view_installed_packages()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update package: {e}")
        finally:

            self.btn_view_packages.configure(state="normal")

    def on_tab_changed(self):
        """Handle tab change events."""
        selected_tab = self.tabview.get()
        if selected_tab == "Packages":
            env_name = self.selected_env_var.get().strip()
            if env_name and os.path.exists(os.path.join(VENV_DIR, env_name)):
                self.selected_env_label.configure(
                    text=f"  Selected Environment: {env_name}",
                    text_color="green",
                    image=self.icons.get("selected-env"),
                    compound="left",
                )
            else:
                self.selected_env_label.configure(
                    text="No valid environment selected.",
                    text_color="red"
                )
            self.packages_list_frame.grid_remove()  # Always hide the list on tab change


    def on_env_name_change(self, event=None):
        # Only update Packages tab visibility based on selected environment from table
        env_name = self.selected_env_var.get().strip()
        if env_name and os.path.exists(os.path.join(VENV_DIR, env_name)):
            self.tabview.tab("Packages").grid()
        else:
            self.tabview.tab("Packages").grid_remove()

    def show_about_dialog(self):
        """Show the About dialog."""
        messagebox.showinfo("About PyEnvStudio", "PyEnvStudio is a powerful yet simple GUI for managing Python virtual environments and packages.\n\n"
                                                  "Created by: Wasim Shaikh\n"
                                                  "Version: 1.0.0\n\n"
                                                  "For more information, visit: https://github.com/pyenvstudio",
                            icon='info')


if __name__ == "__main__":
    app = PyEnvStudio()
    app.mainloop()