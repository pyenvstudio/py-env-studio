import json
import webbrowser
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
        self.data = DBHelper.get_vulnerability_info(self.env_name)

        # State
        self.current_pkg_key = None
        self.current_pkg_data = None
        self.vulnerabilities = []

        # Precompute packages map once
        self.packages_map = self._packages_map()

        # Window setup
        self.root.title(f"Vulnerability Insights Dashboard - {self.env_name}")
        self.root.geometry("1400x800")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Build GUI
        self._setup_gui()

    # ---------------------- Core Methods ----------------------

    def _on_close(self):
        self.root.quit()
        self.root.destroy()

    def _packages_map(self):
        result = {}
        buckets = self.data.get("vulnerability_insights", [])
        if not buckets:
            return result
        for pkg_data in buckets[0].values():
            meta = pkg_data.get("metadata", {})
            key = f"{meta.get('package','Unknown')} ({meta.get('version','?')})"
            result[key] = pkg_data
        return result

    def _extract_vulnerabilities(self, pkg_data):
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
        self.pkg_combo = ttk.Combobox(
            row,
            values=list(self.packages_map.keys()),
            state="readonly",
            width=40
        )
        self.pkg_combo.pack(side="left", pady=5)
        self.pkg_combo.bind("<<ComboboxSelected>>", self.on_package_selected)

    def _setup_left_panel(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="left", fill="both", expand=True, padx=5)
        self.tree = ttk.Treeview(frame, columns=("ID", "Severity", "Fixed"), show="headings")
        for col, text, width in [
            ("ID", "Vulnerability ID", 220),
            ("Severity", "Severity", 120),
            ("Fixed", "Fixed Versions", 220),
        ]:
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)

    def _setup_right_panel(self, parent):
        frame = ctk.CTkFrame(parent, width=420)
        frame.pack(side="right", fill="y", padx=5)
        self.details_notebook = ctk.CTkTabview(frame)
        self.details_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs: Dependencies, Basic Details, Scan Details
        self.index_details_text = self._create_details_tab("Dependencies", "Select a package for details")
        self.developer_details_text = self._create_details_tab("Basic Details", "Select a vulnerability for details")
        self.enterprise_details_text = self._create_details_tab("Scan Details", "Select a package to see scan details")

    def _create_details_tab(self, name, default=""):
        tab = self.details_notebook.add(name)
        textbox = ctk.CTkTextbox(tab, width=380, height=350)
        textbox.pack(fill="both", expand=True, padx=5, pady=5)
        textbox.configure(state="disabled")
        self._set_text(textbox, default)
        return textbox

    def _setup_bottom_panel(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="bottom", fill="both", expand=True, pady=5)
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------------------- Text Helpers ----------------------

    def _set_text(self, textbox, text):
        textbox.configure(state="normal")
        textbox.delete("0.0", "end")
        textbox.insert("0.0", text)
        self._make_links_clickable(textbox)
        textbox.configure(state="disabled")

    def _make_links_clickable(self, textbox):
        import re
        url_pattern = re.compile(r"(https?://[^\s]+)")
        content = textbox.get("0.0", "end")
        for match in url_pattern.finditer(content):
            url = match.group(0)
            start = f"0.0 + {match.start()} chars"
            end   = f"0.0 + {match.end()} chars"
            tag_name = f"url_{match.start()}"
            textbox.tag_add(tag_name, start, end)
            textbox.tag_config(tag_name, foreground="blue", underline=True)
            textbox.tag_bind(
                tag_name, "<Button-1>",
                lambda e, link=url: webbrowser.open(link)
            )

    # ---------------------- Event Handlers ----------------------

    def on_package_selected(self, event):
        self._clear_ui()
        key = self.pkg_combo.get()
        pkg_data = self.packages_map.get(key)
        if not pkg_data:
            return
        self.current_pkg_key = key
        self.current_pkg_data = pkg_data
        self.vulnerabilities = self._extract_vulnerabilities(pkg_data)

        # Populate UI
        self.populate_treeview()
        self._set_text(self.enterprise_details_text, self.format_enterprise_details(pkg_data))
        self._set_text(self.index_details_text, self.format_index_details(pkg_data))
        self.update_charts()

        meta = pkg_data.get("metadata", {})
        pkg = meta.get("package", "Unknown")
        ver = meta.get("version", "?")
        self.root.title(f"Vulnerability Insights Dashboard - {self.env_name} [{pkg}:{ver}]")

    def _clear_ui(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for txt in (self.developer_details_text, self.enterprise_details_text, self.index_details_text):
            self._set_text(txt, "")
        self.ax1.clear()
        self.ax2.clear()
        self.canvas.draw()
        self.vulnerabilities.clear()
        self.current_pkg_data = None

    def populate_treeview(self):
        for vuln in self.vulnerabilities:
            self.tree.insert("", "end", values=(vuln["id"], vuln["severity"], vuln["fixed_versions"]))

    def show_details(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vid = self.tree.item(sel[0])["values"][0]
        vuln = next((v for v in self.vulnerabilities if v["id"] == vid), None)
        if not vuln:
            return
        lines = [
            f"ID: {vuln['id']}",
            f"Package: {vuln['package']}",
            f"Summary: {vuln['summary']}",
            f"Severity: {vuln['severity']}",
            f"Fixed Versions: {vuln['fixed_versions']}",
            f"Impact: {vuln.get('impact','—')}",
            f"Remediation: {vuln.get('remediation','—')}",
            "",
            "References:"
        ]
        for ref in vuln["references"]:
            url = ref.get("url","")
            lines.append(url)
            lines.append("────────────────────")
        self._set_text(self.developer_details_text, "\n".join(lines))

    # ---------------------- Details Formatters ----------------------

    def format_enterprise_details(self, pkg_data):
        ent = pkg_data.get("enterprise_view", {})
        cm = ent.get("centralized_management", {})
        lines = [
            "Centralized Management:",
            f"  Tool: {cm.get('tool','—')}",
            f"  Integration: {cm.get('integration_status','—')}",
            f"  Last Scan: {cm.get('last_scan','—')}",
            "",
            "Compliance:"
        ]
        for comp in ent.get("compliance", []):
            lines.append(
                f"  {comp.get('standard','—')}: "
                f"{comp.get('status','—')} (Last Audit: {comp.get('last_audit','—')})"
            )
        lines += [
            "",
            "Training:",
            f"  Last Session: {ent.get('training',{}).get('last_session','—')}",
            f"  Coverage: {ent.get('training',{}).get('coverage','—')}",
            f"  Next Scheduled: {ent.get('training',{}).get('next_scheduled','—')}",
            "",
            "Incident Response:",
            f"  Plan Status: {ent.get('incident_response',{}).get('plan_status','—')}",
            f"  Last Tested: {ent.get('incident_response',{}).get('last_tested','—')}",
            f"  Communication: {ent.get('incident_response',{}).get('stakeholder_communication','—')}"
        ]
        return "\n".join(lines)

    def format_index_details(self, pkg_data):
        meta = pkg_data.get("metadata", {})
        insights = meta.get("index_insights", [])
        if not insights:
            return "ℹ️ No index insights available.\n"
        lines = ["########## 📦 Package Index Insights ##########"]
        for idx, entry in enumerate(insights, 1):
            lines.append(f"\n🔹 {entry.get('package','—')} ({entry.get('version','?')})")
            if entry.get("deprecated", True):
                lines.append("   • Deprecated: ⚠️ Yes")
            if entry.get("yanked", True):
                lines.append("   • Yanked: ⚠️ Yes")
            if entry.get("eol", True):
                lines.append("   • End of Life: ⚠️ Yes")
            cl = entry.get("classifiers", [])
            if cl:
                lines.append("   • Classifiers:")
                for c in cl:
                    lines.append(f"     - {c}")
            if idx < len(insights):
                lines.append("────────────────────")
        return "\n".join(lines) + "\n"

    # ---------------------- Sorting ----------------------

    def sort_column(self, col, reverse):
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children()]
        data.sort(reverse=reverse)
        for i, (_, item) in enumerate(data):
            self.tree.move(item, "", i)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    # ---------------------- Charts ----------------------

    def update_charts(self):
        self.ax1.clear()
        self.ax2.clear()

        counts = defaultdict(int)
        for v in self.vulnerabilities:
            counts[v["severity"]] += 1

        severities = ["Critical", "High", "Medium", "Low", "Unknown"]
        colors = ["#ff0000", "#ff9900", "#ffcc00", "#00cc00", "#888888"]
        symbols = ["C", "H", "M", "L", "U"]
        counts_list = [counts[s] for s in severities]

        bars = self.ax1.bar(range(len(severities)), counts_list, color=colors)
        for i, bar in enumerate(bars):
            h = bar.get_height()
            self.ax1.text(bar.get_x()+bar.get_width()/2, h+0.2, symbols[i],
                          ha="center", va="bottom", fontsize=14)
        self.ax1.set_title("Vulnerability Severity Breakdown")
        self.ax1.set_xticks([])
        self.ax1.set_ylabel("Number of Vulnerabilities")

        # Trend chart
        if self.current_pkg_data:
            trend = self.current_pkg_data.get("tech_leader_view", {}).get("trend_data", [])
            if trend:
                dates = [datetime.fromisoformat(t["timestamp"]).strftime("%Y-%m-%d") for t in trend]
                totals = [t.get("total_vulnerabilities", 0) for t in trend]
                fixeds = [t.get("fixed_vulnerabilities", 0) for t in trend]
                self.ax2.plot(dates, totals, label="Total Vulnerabilities", marker="o")
                self.ax2.plot(dates, fixeds, label="Fixed Vulnerabilities", marker="o")
                self.ax2.set_title("Vulnerability Trends")
                self.ax2.set_xlabel("Date")
                self.ax2.set_ylabel("Count")
                self.ax2.legend()
                self.ax2.tick_params(axis="x", rotation=45)

        self.fig.tight_layout()
        self.canvas.draw()