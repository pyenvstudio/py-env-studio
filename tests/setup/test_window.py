import tkinter as tk
from tkinter import ttk, messagebox

from setup.state import SetupStateManager, CURRENT_VERSION
from setup.db import DatabaseManager


# ---------------------------
# Setup Orchestrator
# ---------------------------

class SetupOrchestrator:
    """Handles installation orchestration: DB init + state management."""

    def __init__(self, state_manager: SetupStateManager):
        self.state_manager = state_manager
        self.db = DatabaseManager()

    def run_initial_setup(self):
        """Initialize DB and mark setup complete."""
        self.db.initialize_database()
        self.state_manager.mark_setup_complete()

    def repair(self):
        """Repair or reinitialize the setup."""
        self.db.initialize_database()
        self.state_manager.mark_setup_complete()


# ---------------------------
# Controller & UI
# ---------------------------

class AppController:
    """Controller that manages app state and navigation."""

    def __init__(self, root: tk.Tk, state_manager: SetupStateManager):
        self.root = root
        self.state_manager = state_manager
        self.orchestrator = SetupOrchestrator(state_manager)
        self.frames = {}

    def register_frame(self, name: str, frame: ttk.Frame) -> None:
        self.frames[name] = frame

    def show_frame(self, name: str) -> None:
        frame = self.frames.get(name)
        if not frame:
            raise ValueError(f"No frame named '{name}' registered")
        frame.tkraise()


class SetupWizard(ttk.Frame):
    """Parent container for setup wizard pages."""

    def __init__(self, parent: tk.Tk, controller: AppController):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True)

        self.controller.state_manager.create_installing_marker()

        for Page in (WelcomePage, ConfigPage, FinishPage):
            frame = Page(self, controller)
            frame.grid(row=0, column=0, sticky="nsew")
            controller.register_frame(Page.__name__, frame)

        controller.show_frame("WelcomePage")


# ---------------------------
# Pages
# ---------------------------

class WelcomePage(ttk.Frame):
    def __init__(self, parent, controller: AppController):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Welcome to the Setup Wizard!").pack(pady=10)
        ttk.Button(self, text="Next", command=self.on_next).pack(pady=5)

    def on_next(self):
        try:
            self.controller.orchestrator.db.initialize_database()
            self.controller.show_frame("ConfigPage")
        except Exception as e:
            messagebox.showerror("Error", f"Database initialization failed:\n{e}")


class ConfigPage(ttk.Frame):
    def __init__(self, parent, controller: AppController):
        super().__init__(parent)
        ttk.Label(self, text="Configuration Page").pack(pady=10)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("WelcomePage")).pack(pady=5)
        ttk.Button(self, text="Next", command=lambda: controller.show_frame("FinishPage")).pack(pady=5)


class FinishPage(ttk.Frame):
    def __init__(self, parent, controller: AppController):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Setup Complete!").pack(pady=10)
        ttk.Button(self, text="Finish", command=self.complete_setup).pack(pady=5)
        ttk.Button(self, text="Exit", command=self.abort_install).pack(pady=5)

    def complete_setup(self):
        try:
            self.controller.orchestrator.run_initial_setup()
            messagebox.showinfo("Setup Complete", f"Setup finished successfully (v{CURRENT_VERSION}).")
            self.controller.root.destroy()
            run_main_app()
        except Exception as e:
            self.controller.state_manager.mark_setup_failed(str(e))
            messagebox.showerror("Error", f"Setup failed: {e}")

    def abort_install(self):
        self.controller.state_manager.mark_setup_failed("User aborted setup")
        messagebox.showwarning("Aborted", "Setup was aborted by the user.")
        self.controller.root.quit()


# ---------------------------
# App Entry Points
# ---------------------------

class MainApp(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="This is the main application window.").pack(pady=20)
        ttk.Button(self, text="Exit", command=parent.quit).pack(pady=5)


def run_main_app():
    root = tk.Tk()
    root.title("Main Application")
    root.geometry("400x300")
    MainApp(root).pack(fill="both", expand=True)
    root.mainloop()


def run_setup_wizard():
    root = tk.Tk()
    root.title("Application Setup")
    root.geometry("400x300")

    state_manager = SetupStateManager()
    controller = AppController(root, state_manager)
    SetupWizard(root, controller)

    try:
        root.mainloop()
    except Exception as e:
        state_manager.mark_setup_failed(str(e))
        messagebox.showerror("Fatal Error", f"Setup terminated unexpectedly: {e}")


def run_migration(state_manager):
    messagebox.showinfo("Migration", "Performing version migration...")
    state_manager.mark_setup_complete()
    run_main_app()


def run_repair(state_manager):
    messagebox.showinfo("Repair", "Recovering from failed or incomplete setup...")
    orchestrator = SetupOrchestrator(state_manager)
    orchestrator.repair()
    run_main_app()


if __name__ == "__main__":
    state_manager = SetupStateManager()
    state = state_manager.check_installation_health()
    print(f"Detected install state: {state}")

    if state == "complete":
        run_main_app()
    elif state == "migrate":
        run_migration(state_manager)
    elif state in {"missing", "recover", "failed"}:
        run_setup_wizard()
    elif state == "installing":
        messagebox.showwarning("Setup in Progress", "An installation is currently in progress. Please wait or repair.")
