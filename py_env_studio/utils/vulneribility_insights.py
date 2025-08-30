import json
import customtkinter as ctk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
from datetime import datetime
from .handlers import DBHelper


# Set customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VulnerabilityInsightsApp:
    """Dashboard application for exploring vulnerability insights."""

    def __init__(self, root, env_name):
        self.root = root
        self.env_name = env_name

        # json_file = r"C:\Users\Lenovo\Desktop\Contribution\py_env_studio\py_env_studio\utils\security_matrix.json"
        # self.data = self._load_json(json_file)
        self.data = DBHelper.get_vulnerability_info(self.env_name)

        # state
        self.current_pkg_key = None           # key in packages_map: "name (version)"
        self.current_pkg_data = None          # actual package node from json
        self.vulnerabilities = []             # normalized list for tree

        # Precompute packages map once
        self.packages_map = self._packages_map()

        # Window setup
        self.root.title(f"Vulnerability Insights Dashboard - {self.env_name}")
        self.root.geometry("1400x800")

        # Setup GUI
        self._setup_gui()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------- Core Setup ----------------------
    def _load_json(self, json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _on_close(self):
        self.root.quit()
        self.root.destroy()

    # ---------------------- Data Helpers ----------------------
    def _packages_map(self):
        """
        Build a stable map of packages:
        {
          "django (2.1.0)": <pkg_data_obj>,
          "pandas (2.1.0)": <pkg_data_obj>,
          ...
        }
        JSON structure:
          { "vulnerability_insights": [ { "1": {...}, "2": {...} } ] }
        """
        result = {}
        root_obj = self.data.get("vulnerability_insights", [])
        if not root_obj:
            return result
        first_bucket = root_obj[0]
        for _, pkg_data in first_bucket.items():
            meta = pkg_data.get("metadata", {})
            key = f"{meta.get('package','Unknown')} ({meta.get('version','?')})"
            result[key] = pkg_data
        return result

    def _extract_vulnerabilities(self, pkg_data):
        """Extract and normalize vulnerabilities for a selected package."""
        vulnerabilities = []
        for vuln in pkg_data.get("developer_view", []):
            vulnerabilities.append({
                "id": vuln.get("vulnerability_id", "Unknown"),
                "package": (vuln.get("affected_components") or ["Unknown"])[0],
                "summary": vuln.get("summary", "—"),
                "severity": vuln.get("severity", {}).get("level", "Unknown"),
                "fixed_versions": ", ".join(vuln.get("fixed_versions", [])) or "None",
                "impact": vuln.get("impact", "—"),
                "remediation": vuln.get("remediation_steps", "—"),
                "references": vuln.get("references", []),
                "discussions": vuln.get("discussions", []),
            })
        return vulnerabilities

    # ---------------------- GUI Setup ----------------------
    def _setup_gui(self):
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._setup_dropdown(main_frame)
        self._setup_left_panel(main_frame)
        self._setup_right_panel(main_frame)
        self._setup_bottom_panel(main_frame)

    def _setup_dropdown(self, parent):
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", padx=5, pady=(0, 10))

        ctk.CTkLabel(row, text="Select Package:").pack(side="left", padx=(5, 10))

        # Use packages_map keys (dict) — no .values() problem
        self.pkg_combo = ttk.Combobox(row, values=list(self.packages_map.keys()), state="readonly", width=40)
        self.pkg_combo.pack(side="left", pady=5)
        self.pkg_combo.bind("<<ComboboxSelected>>", self.on_package_selected)

    def _setup_left_panel(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="left", fill="both", expand=True, padx=5)

        self.tree = self._create_treeview(frame)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)

    def _create_treeview(self, parent):
        tree = ttk.Treeview(parent, columns=("ID", "Severity", "Fixed"), show="headings")
        for col, text, width in [
            ("ID", "Vulnerability ID", 220),
            ("Severity", "Severity", 120),
            ("Fixed", "Fixed Versions", 220),
        ]:
            tree.heading(col, text=text, command=lambda c=col: self.sort_column(c, False))
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _setup_right_panel(self, parent):
        frame = ctk.CTkFrame(parent, width=420)
        frame.pack(side="right", fill="y", padx=5)

        self.details_notebook = ctk.CTkTabview(frame)
        self.details_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Index tab
        self.index_details_label = self._create_details_tab("Dependencies", default="Select a package for details")
        # Developer tab
        self.developer_details_label = self._create_details_tab("Basic Details", default="Select a vulnerability for details")
        # Enterprise tab
        self.enterprise_details_label = self._create_details_tab("Scan Details", default="Select a package to see scan details")

    def _create_details_tab(self, name, default=""):
        tab = self.details_notebook.add(name)
        frame = ctk.CTkScrollableFrame(tab, width=380, height=350)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        label = ctk.CTkLabel(
            frame, text=default or f"Select a {name.lower()} for details",
            wraplength=360, anchor="nw", justify="left"
        )
        label.pack(pady=10, padx=10, anchor="nw")
        return label

    def _setup_bottom_panel(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="bottom", fill="both", expand=True, pady=5)

        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------------------- Cleanup ----------------------
    def _clear_all_ui(self):
        """Reset UI before loading a new package."""
        self.tree.delete(*self.tree.get_children())
        self.developer_details_label.configure(text="Select a vulnerability for details")
        self.enterprise_details_label.configure(text="Select a package to see scan details")
        self.index_details_label.configure(text="Select a package to see index details")

        self.ax1.clear()
        self.ax2.clear()
        self.canvas.draw()

        self.vulnerabilities.clear()
        self.current_pkg_data = None

    # ---------------------- UI Updates ----------------------
    def on_package_selected(self, event):
        """Handle package selection from dropdown."""
        self._clear_all_ui()

        key = self.pkg_combo.get()
        pkg_data = self.packages_map.get(key)
        if not pkg_data:
            return

        self.current_pkg_key = key
        self.current_pkg_data = pkg_data
        self.vulnerabilities = self._extract_vulnerabilities(pkg_data)

        # Populate fresh UI
        self.populate_treeview()
        self.enterprise_details_label.configure(text=self.format_enterprise_details(pkg_data))
        self.index_details_label.configure(text=self.format_index_details(pkg_data))
        self.update_charts()

        # Update window title
        meta = pkg_data.get("metadata", {})
        pkg = meta.get("package", "Unknown")
        version = meta.get("version", "?")
        self.root.title(f"Vulnerability Insights Dashboard - {self.env_name} [{pkg}:{version}]")

    def populate_treeview(self):
        self.tree.delete(*self.tree.get_children())
        for vuln in self.vulnerabilities:
            self.tree.insert("", "end", values=(vuln["id"], vuln["severity"], vuln["fixed_versions"]))

    def format_enterprise_details(self, pkg_data):
        """Enterprise scan details into text."""
        enterprise = pkg_data.get("enterprise_view", {})
        cm = enterprise.get("centralized_management", {})
        lines = [
            "Centralized Management:",
            f"  Tool: {cm.get('tool', '—')}",
            f"  Integration: {cm.get('integration_status', '—')}",
            f"  Last Scan: {cm.get('last_scan', '—')}",
            "",
            "Compliance:",
        ]
        for comp in enterprise.get("compliance", []):
            lines.append(f"  {comp.get('standard','—')}: {comp.get('status','—')} (Last Audit: {comp.get('last_audit','—')})")
        lines.extend([
            "",
            "Training:",
            f"  Last Session: {enterprise.get('training', {}).get('last_session', '—')}",
            f"  Coverage: {enterprise.get('training', {}).get('coverage', '—')}",
            f"  Next Scheduled: {enterprise.get('training', {}).get('next_scheduled', '—')}",
            "",
            "Incident Response:",
            f"  Plan Status: {enterprise.get('incident_response', {}).get('plan_status', '—')}",
            f"  Last Tested: {enterprise.get('incident_response', {}).get('last_tested', '—')}",
            f"  Communication: {enterprise.get('incident_response', {}).get('stakeholder_communication', '—')}",
        ])
        return "\n".join(lines)

    def format_index_details(self, pkg_data):
            """Format index_insights metadata into a human-friendly report with separators."""
            meta = pkg_data.get("metadata", {})
            insights = meta.get("index_insights", [])
            if not insights:
                return "ℹ️ No index insights available.\n"

            lines = ["########## 📦 Package Index Insights ##########"]
            for i, entry in enumerate(insights, 1):
                lines.append(f"\n🔹 {entry.get('package','—')} ({entry.get('version','?')})")

                if entry.get('deprecated', True):
                    lines.append("   • Deprecated: ⚠️ Yes")
                if entry.get('yanked', True):
                    lines.append("   • Yanked: ⚠️ Yes")
                if entry.get('eol', True):
                    lines.append("   • End of Life: ⚠️ Yes")

                classifiers = entry.get("classifiers", [])
                if classifiers:
                    lines.append("   • Classifiers:")
                    for c in classifiers:
                        lines.append(f"     - {c}")

                # add horizontal line after each package (except the last)
                if i < len(insights):
                    lines.append("" + "─" * 20)

            return "\n".join(lines) + "\n"



    def sort_column(self, col, reverse):
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children()]
        data.sort(reverse=reverse)
        for index, (_, item) in enumerate(data):
            self.tree.move(item, "", index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def show_details(self, event):
        """Show developer details for selected vulnerability."""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item = self.tree.item(selected_item)
        vals = item.get("values", [])
        if not vals:
            return
        vuln_id = vals[0]
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
                *(f"- {ref.get('url','')}" for ref in vuln["references"]),
            ]
            self.developer_details_label.configure(text="\n".join(details))

    # ---------------------- Charts ----------------------
    def update_charts(self):
        self.ax1.clear()
        self.ax2.clear()

        # Severity breakdown
        severity_counts = self._count_severities()
        severities = ["Critical", "High", "Medium", "Low", "Unknown"]
        counts = [severity_counts[s] for s in severities]
        colors = ["#ff0000", "#ff9900", "#ffcc00", "#00cc00", "#888888"]
        symbols = ["C", "H", "M", "L", "U"]

        bars = self.ax1.bar(range(len(severities)), counts, color=colors)

        for i, bar in enumerate(bars):
            height = bar.get_height()
            self.ax1.text(bar.get_x() + bar.get_width() / 2, height + 0.2, symbols[i], ha="center", va="bottom", fontsize=14)

        self.ax1.set_title("Vulnerability Severity Breakdown")
        self.ax1.set_xticks([])
        self.ax1.set_ylabel("Number of Vulnerabilities")

        # Trends
        if self.current_pkg_data:
            self._plot_trends(self.current_pkg_data)

        self.fig.tight_layout()
        self.canvas.draw()

    def _count_severities(self):
        counts = defaultdict(int)
        for vuln in self.vulnerabilities:
            counts[vuln["severity"]] += 1
        return counts

    def _plot_trends(self, pkg_data):
        trend_data = pkg_data.get("tech_leader_view", {}).get("trend_data", [])
        if trend_data:
            timestamps = [datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m-%d") for t in trend_data]
            totals = [t.get("total_vulnerabilities", 0) for t in trend_data]
            fixed = [t.get("fixed_vulnerabilities", 0) for t in trend_data]
            self.ax2.plot(timestamps, totals, label="Total Vulnerabilities", marker="o")
            self.ax2.plot(timestamps, fixed, label="Fixed Vulnerabilities", marker="o")
            self.ax2.set_title("Vulnerability Trends")
            self.ax2.set_xlabel("Date")
            self.ax2.set_ylabel("Count")
            self.ax2.legend()
            self.ax2.tick_params(axis="x", rotation=45)


if __name__ == "__main__":
    root = ctk.CTk()
    app = VulnerabilityInsightsApp(root)
    root.mainloop()
