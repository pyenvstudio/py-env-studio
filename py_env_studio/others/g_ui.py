import json
import customtkinter as ctk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
from datetime import datetime

# Set customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VulnerabilityInsightsApp:
    def _on_close(self):
        """Cleanup handler to cancel scheduled callbacks and destroy window safely."""
        # Cancel any scheduled 'after' callbacks if you have their IDs stored
        # Example: if hasattr(self, 'after_id'): self.root.after_cancel(self.after_id)
        # Add more cleanup logic here if needed
        self.root.quit()
        self.root.destroy()
    def __init__(self, root, json_file):
        """Initialize the dashboard app."""
        self.root = root
        self.data = self._load_json(json_file)
        pkg = self.data["vulnerability_insights"]["metadata"]["package"]
        version = self.data["vulnerability_insights"]["metadata"]["version"]
        self.root.title(f"Vulnerability Insights Dashboard [{pkg}:{version}]")
        self.root.geometry("1400x800")
        self.vulnerabilities = self._extract_vulnerabilities()
        self._setup_gui()
        # Bind the window close event to the cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_json(self, json_file):
        """Load JSON data from file."""
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_vulnerabilities(self):
        """Extract vulnerabilities from JSON for display in the table."""
        vulnerabilities = []
        developer_view = self.data["vulnerability_insights"]["developer_view"]
        for vuln in developer_view:
            vulnerabilities.append({
                "id": vuln["vulnerability_id"],
                "package": vuln["affected_components"][0] if vuln["affected_components"] else "Unknown",
                "summary": vuln["summary"],
                "severity": vuln["severity"]["level"],
                "fixed_versions": ", ".join(vuln["fixed_versions"]) if vuln["fixed_versions"] else "None",
                "impact": vuln["impact"],
                "remediation": vuln["remediation_steps"],
                "references": vuln["references"],
                "discussions": vuln.get("discussions", [])
            })
        return vulnerabilities

    def _setup_gui(self):
        """Set up the main GUI layout."""
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # ...existing code...

        # Split main frame into left (treeview), right (details), and bottom (charts)
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=5)

        right_frame = ctk.CTkFrame(main_frame, width=400)
        right_frame.pack(side="right", fill="y", padx=5)

        bottom_frame = ctk.CTkFrame(main_frame)
        bottom_frame.pack(side="bottom", fill="both", expand=True, pady=5)

        # Treeview for developer view
        self.tree = ttk.Treeview(left_frame, columns=("ID", "Severity", "Fixed"), show="headings")
        self.tree.heading("ID", text="Vulnerability ID", command=lambda: self.sort_column("ID", False))
        self.tree.heading("Severity", text="Severity", command=lambda: self.sort_column("Severity", False))
        self.tree.heading("Fixed", text="Fixed Versions", command=lambda: self.sort_column("Fixed", False))
        self.tree.column("ID", width=150)
        self.tree.column("Severity", width=100)
        self.tree.column("Fixed", width=150)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)

        # Details pane (developer and enterprise view)
        self.details_notebook = ctk.CTkTabview(right_frame)
        self.details_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Developer details tab (scrollable)
        developer_tab = self.details_notebook.add("Basic Details")
        self.developer_details_frame = ctk.CTkScrollableFrame(developer_tab, width=380, height=350)
        self.developer_details_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.developer_details_label = ctk.CTkLabel(self.developer_details_frame, text="Select a vulnerability for details", wraplength=350, anchor="nw", justify="left")
        self.developer_details_label.pack(pady=10, padx=10, anchor="nw")

        # Enterprise details tab (scrollable)
        enterprise_tab = self.details_notebook.add("Scan Details")
        self.enterprise_details_frame = ctk.CTkScrollableFrame(enterprise_tab, width=380, height=350)
        self.enterprise_details_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.enterprise_details_label = ctk.CTkLabel(self.enterprise_details_frame, text=self.format_enterprise_details(), wraplength=350, anchor="nw", justify="left")
        self.enterprise_details_label.pack(pady=10, padx=10, anchor="nw")

        # Charts for tech leader view
        chart_frame = ctk.CTkFrame(bottom_frame)
        chart_frame.pack(fill="both", expand=True)

        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Populate treeview and charts
        self.populate_treeview()
        self.update_charts()

    def format_enterprise_details(self):
        """Format enterprise view details from JSON for display."""
        enterprise = self.data["vulnerability_insights"]["enterprise_view"]
        lines = ["Centralized Management:"]
        lines.append(f"  Tool: {enterprise['centralized_management']['tool']}")
        lines.append(f"  Integration: {enterprise['centralized_management']['integration_status']}")
        lines.append(f"  Last Scan: {enterprise['centralized_management']['last_scan']}")
        lines.append("")
        lines.append("Compliance:")
        for comp in enterprise["compliance"]:
            lines.append(f"  {comp['standard']}: {comp['status']} (Last Audit: {comp['last_audit']})")
        lines.append("")
        lines.append("Training:")
        lines.append(f"  Last Session: {enterprise['training']['last_session']}")
        lines.append(f"  Coverage: {enterprise['training']['coverage']}")
        lines.append(f"  Next Scheduled: {enterprise['training']['next_scheduled']}")
        lines.append("")
        lines.append("Incident Response:")
        lines.append(f"  Plan Status: {enterprise['incident_response']['plan_status']}")
        lines.append(f"  Last Tested: {enterprise['incident_response']['last_tested']}")
        lines.append(f"  Communication: {enterprise['incident_response']['stakeholder_communication']}")
        return "\n".join(lines)

    def populate_treeview(self):
        """Populate treeview with vulnerability data."""
        self.tree.delete(*self.tree.get_children())
        for vuln in self.vulnerabilities:
            self.tree.insert("", "end", values=(
                vuln["id"],
                vuln["severity"],
                vuln["fixed_versions"]
            ))

    # Removed filter_data method

    def sort_column(self, col, reverse):
        """Sort treeview by column."""
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children()]
        data.sort(reverse=reverse)
        for index, (_, item) in enumerate(data):
            self.tree.move(item, "", index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def show_details(self, event):
        """Show detailed vulnerability information in the details pane."""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item = self.tree.item(selected_item)
        vuln_id = item["values"][0]
        vuln = next((v for v in self.vulnerabilities if v["id"] == vuln_id), None)
        if vuln:
            details = [
                f"ID: {vuln['id']}",
                f"Package: {vuln['package']}",
                f"Summary: {vuln['summary']}",
                f"Severity: {vuln['severity']}",
                f"Fixed Versions: {vuln['fixed_versions']}",
                f"Impact: {vuln['impact']}",
                f"Remediation: {vuln['remediation']}",
                "",
                "References:",
                *(f"- {ref['url']}" for ref in vuln["references"]),
                "",
                "Discussions:",
                *(f"- {disc['title']} ({disc['url']})" for disc in vuln["discussions"])
            ]
            self.developer_details_label.configure(text="\n".join(details))

    def update_charts(self):
        """Update charts for tech leader view."""
        self.ax1.clear()
        self.ax2.clear()
        data = self.vulnerabilities

        # Bar chart: Severity breakdown
        severity_counts = defaultdict(int)
        for vuln in data:
            severity_counts[vuln["severity"]] += 1
        severities = ["Critical", "High", "Medium", "Low", "Unknown"]
        counts = [severity_counts[sev] for sev in severities]
        self.ax1.bar(severities, counts, color=["#ff0000", "#ff9900", "#ffcc00", "#00cc00", "#888888"])
        self.ax1.set_xlabel("Severity")
        self.ax1.set_ylabel("Number of Vulnerabilities")
        self.ax1.set_title("Vulnerability Severity Breakdown")

        # Line chart: Trend data (simplified, using single timestamp)
        trend_data = self.data["vulnerability_insights"]["tech_leader_view"]["trend_data"]
        if trend_data:
            timestamps = [datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m-%d") for t in trend_data]
            totals = [t["total_vulnerabilities"] for t in trend_data]
            fixed = [t["fixed_vulnerabilities"] for t in trend_data]
            self.ax2.plot(timestamps, totals, label="Total Vulnerabilities", marker="o")
            self.ax2.plot(timestamps, fixed, label="Fixed Vulnerabilities", marker="o")
            self.ax2.set_xlabel("Date")
            self.ax2.set_ylabel("Count")
            self.ax2.set_title("Vulnerability Trends")
            self.ax2.legend()
            self.ax2.tick_params(axis="x", rotation=45)

        self.fig.tight_layout()
        self.canvas.draw()

if __name__ == "__main__":
    root = ctk.CTk()
    app = VulnerabilityInsightsApp(root, "security_matrix.json")
    root.mainloop()