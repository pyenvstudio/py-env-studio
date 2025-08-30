
from .vulneribility_insights  import VulnerabilityInsightsApp
import customtkinter as ctk



class HoverButtonManager:
    def __init__(self, parent, treeview, theme, show_report_callback):
        self.parent = parent
        self.treeview = treeview
        self.theme = theme
        self.show_report_callback = show_report_callback
        self.hover_button = None
        self.treeview.bind("<Motion>", self.on_motion)
        self.treeview.bind("<Leave>", self.on_leave)

    def on_motion(self, event):
        col = self.treeview.identify_column(event.x)
        row = self.treeview.identify_row(event.y)
        # Last Scanned is column "#6"
        if col == "#6" and row:
            if self.hover_button:
                self.hover_button.destroy()
            x, y, width, height = self.treeview.bbox(row, col)
            env = self.treeview.item(row)['values'][0]
            self.hover_button = ctk.CTkButton(self.parent, text="SHOW REPORT",
                                              command=lambda: self.show_report_callback(env),
                                              width=100, height=self.theme.BUTTON_HEIGHT,
                                               fg_color=self.theme.HIGHLIGHT_COLOR)
            # Position button just above cell
            abs_x = self.treeview.winfo_rootx() + x
            abs_y = self.treeview.winfo_rooty() + y
            self.hover_button.place(x=x, y=y + height // 2)
        else:
            if self.hover_button:
                self.hover_button.destroy()
                self.hover_button = None

    def on_leave(self, event):
        if self.hover_button:
            self.hover_button.destroy()
            self.hover_button = None


class ReportManager:
    def __init__(self, parent):
        self.parent = parent

    def show_report(self, env_name):
        # You can expand or replace with `VulnerabilityInsightsApp(env_name)` logic
        win = ctk.CTkToplevel(self.parent)
        win.title(f"{env_name} - Vulnerability Report")
        win.geometry("800x500")
        insights_frame = VulnerabilityInsightsApp(win, env_name)
        # insights_frame.pack(expand=True, fill='both')


# HoverButtonManager
