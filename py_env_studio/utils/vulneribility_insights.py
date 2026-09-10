import json
import logging
import queue
import re
import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
from datetime import datetime
from .handlers import DBHelper
from .version_utils import version_key, vuln_status
from .db_status import ensure_vulnerability_statuses, mark_package_fixed
from py_env_studio.core.package_manager import install_package

# Set customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VulnerabilityInsightsApp:
    """Dashboard application for exploring vulnerability insights."""

    def __init__(self, root, env_name):
        self.root = root
        self.env_name = env_name
        # Make sure every vulnerability in the DB carries a persisted
        # 'status' (fixed/not fixed) before rendering the report.
        ensure_vulnerability_statuses(self.env_name)
        self.data = DBHelper.get_vulnerability_info(self.env_name)

        # State
        self.current_pkg_key = None
        self.current_pkg_data = None
        self.vulnerabilities = []
        self.current_vuln = None
        self.current_update_button = None
        self._updating = False
        self._update_queue = queue.Queue()

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
        """Extract vulnerabilities with a 'current_version' and 'status'.

        The status (fixed/not fixed) comes from the DB when present and is
        otherwise computed from installed vs fixed versions.
        """
        meta = pkg_data.get("metadata", {})
        current_versions = {}
        if meta.get("package"):
            current_versions[str(meta["package"]).split("[")[0].strip()] = meta.get("version", "?")
        for entry in meta.get("index_insights", []):
            name = str(entry.get("package", "")).split("[")[0].strip()
            ver = entry.get("version")
            if name and ver:
                current_versions[name] = ver

        vulnerabilities = []
        for vuln in pkg_data.get("developer_view", []):
            package = (vuln.get("affected_components") or ["Unknown"])[0]
            package_key = str(package).split("[")[0].strip()
            raw_fixed = vuln.get("fixed_versions", []) or []
            current_version = current_versions.get(package_key, "?")
            status = vuln.get("status")
            if status not in ("fixed", "not fixed"):
                status = vuln_status(current_version, raw_fixed)
            vulnerabilities.append({
                "id": vuln.get("vulnerability_id", "Unknown"),
                "package": package,
                "current_version": current_version,
                "status": status,
                "summary": vuln.get("summary", "—"),
                "severity": vuln.get("severity", {}).get("level", "Unknown"),
                "fixed_versions": ", ".join(raw_fixed) or "None",
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
        self.tree = ttk.Treeview(
            frame,
            columns=("ID", "Severity", "Current", "Fixed", "Status"),
            show="headings",
        )
        for col, text, width in [
            ("ID", "Vulnerability ID", 170),
            ("Severity", "Severity", 90),
            ("Current", "Current Version", 110),
            ("Fixed", "Fixed Versions", 150),
            ("Status", "Status", 90),
        ]:
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=width, anchor="w")
        self.tree.tag_configure("fixed", foreground="#388E3C")
        self.tree.tag_configure("notfixed", foreground="#C62828")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)

    def _setup_right_panel(self, parent):
        frame = ctk.CTkFrame(parent, width=420)
        frame.pack(side="right", fill="y", padx=5)
        self.details_notebook = ctk.CTkTabview(frame)
        self.details_notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs: Dependencies, Basic Details, Scan Details
        self.index_details_text = self._create_details_tab("Dependencies", "Select a package for details")
        self.developer_details_text = self._create_details_tab(
            "Basic Details", "Select a vulnerability for details", with_action=True
        )
        self.enterprise_details_text = self._create_details_tab("Scan Details", "Select a package to see scan details")

    def _create_details_tab(self, name, default="", with_action=False):
        tab = self.details_notebook.add(name)
        textbox = ctk.CTkTextbox(tab, width=380, height=350)
        textbox.pack(fill="both", expand=True, padx=5, pady=5)
        textbox.configure(state="disabled")
        self._set_text(textbox, default)

        if with_action:
            # Action bar so the user can remediate directly from the report
            action_frame = ctk.CTkFrame(tab)
            action_frame.pack(fill="x", padx=5, pady=(2, 5))
            self.update_now_button = ctk.CTkButton(
                action_frame,
                text="⬆ Upgrade all Packages",
                width=180,
                height=32,
                state="disabled",
                command=self.upgrade_all_packages,
            )
            self.update_now_button.pack(side="left", padx=(0, 8))
            self.update_status_label = ctk.CTkLabel(
                action_frame,
                text="Upgrade all packages to their recommended fixed versions.",
                text_color="#7F8B9A",
                anchor="w",
            )
            self.update_status_label.pack(side="left", fill="x", expand=True)

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
        self._refresh_upgrade_all_button()

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
        self.current_vuln = None
        self.current_update_button = None
        if hasattr(self, "update_now_button"):
            self.update_now_button.configure(text="⬆ Upgrade all Packages", state="disabled")
        if hasattr(self, "update_status_label"):
            self.update_status_label.configure(
                text="Upgrade all packages to their recommended fixed versions."
            )

    def populate_treeview(self):
        for vuln in self.vulnerabilities:
            status = vuln.get("status", "not fixed")
            tag = "fixed" if status == "fixed" else "notfixed"
            self.tree.insert(
                "",
                "end",
                values=(
                    vuln["id"],
                    vuln["severity"],
                    vuln.get("current_version", "?"),
                    vuln["fixed_versions"],
                    status,
                ),
                tags=(tag,),
            )

    def show_details(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vid = self.tree.item(sel[0])["values"][0]
        vuln = next((v for v in self.vulnerabilities if v["id"] == vid), None)
        if not vuln:
            return
        self.current_vuln = vuln
        target = self._parse_target_version(vuln)
        current_version = vuln.get("current_version", "?")
        status = vuln.get("status", "not fixed")
        up_to_date = status == "fixed"
        lines = [
            f"ID: {vuln['id']}",
            f"Package: {vuln['package']}",
            f"Current Version: {current_version}",
            f"Status: {status}",
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
        if target:
            self._embed_update_now_button(target, up_to_date=up_to_date)
        else:
            self.current_update_button = None
        self._refresh_upgrade_all_button()

    # ---------------------- Remediation Action ----------------------

    @staticmethod
    def _parse_target_version(vuln):
        """Extract the fixed version the remediation recommends.

        Example: "Upgrade to 26.2.0" -> "26.2.0".
        Returns None when no actionable fix is available.
        """
        if not vuln:
            return None
        remediation = vuln.get("remediation", "") or ""
        match = re.search(r"[Uu]pgrade to\s+(\d[\w.\-]*)", remediation)
        if match:
            return match.group(1).strip()
        fixed = vuln.get("fixed_versions", "") or ""
        first = fixed.split(",")[0].strip()
        if first and first.lower() not in ("none", "no fix available", "—"):
            return first
        return None

    def _is_vuln_up_to_date(self, vuln):
        """True when the vulnerability is already fixed (installed version meets
        or exceeds the recommended fix). Prefers the DB-persisted status."""
        if not vuln:
            return False
        status = vuln.get("status")
        if status in ("fixed", "not fixed"):
            return status == "fixed"
        # Fallback for records built without a status field.
        target = self._parse_target_version(vuln)
        if not target:
            return False
        current = (vuln.get("current_version") or "").strip()
        if not current or current in ("?", "—", "None", "Unknown"):
            return False
        return self._version_key(current) >= self._version_key(target)

    def _embed_update_now_button(self, target, up_to_date=False):
        """Embed a real 'Update Now' button inline at the end of the Remediation line.

        When the installed version already meets the fix (current >= target), the
        button is embedded disabled and labelled 'Up to date'.
        """
        textbox = self.developer_details_text
        content = textbox.get("0.0", "end")
        rem_line = None
        for line in content.splitlines():
            if line.startswith("Remediation:"):
                rem_line = line
                break
        if rem_line is None:
            self.current_update_button = None
            return

        start = content.index(rem_line)
        index = f"1.0 + {start + len(rem_line)} chars"

        btn = ctk.CTkButton(
            textbox._textbox,
            text="Up to date" if up_to_date else "Update Now",
            width=88 if not up_to_date else 100,
            height=24,
            state="disabled" if up_to_date else "normal",
            command=self.update_now,
        )
        textbox.configure(state="normal")
        textbox._textbox.window_create(index, window=btn)
        textbox.configure(state="disabled")
        self.current_update_button = btn

    def _refresh_upgrade_all_button(self):
        """Enable 'Upgrade all Packages' when any package in the environment has a fix."""
        has_fix = bool(self._collect_upgrade_plan())
        if has_fix and not self._updating:
            self.update_now_button.configure(text="⬆ Upgrade all Packages", state="normal")
        else:
            self.update_now_button.configure(text="⬆ Upgrade all Packages", state="disabled")

    def update_now(self):
        """Upgrade the currently selected vulnerable package to its fixed version."""
        if self._updating or not self.current_vuln:
            return
        vuln = self.current_vuln
        target = self._parse_target_version(vuln)
        if not target:
            messagebox.showinfo(
                "No Action",
                "No fixed version is available for the selected vulnerability.",
            )
            return
        if self._is_vuln_up_to_date(vuln):
            messagebox.showinfo(
                "Already Up to Date",
                f"'{vuln['package']}' is already at version "
                f"{vuln.get('current_version', '?')}, which meets or exceeds the "
                f"recommended fixed version {target}.",
            )
            return
        package = vuln["package"].split("[")[0].strip()
        if not package:
            return
        if not messagebox.askyesno(
            "Confirm Update",
            f"Upgrade '{package}' to version {target} in environment '{self.env_name}'?\n\n"
            "This installs the fixed version recommended by the remediation "
            "and resolves this vulnerability.",
        ):
            return

        btn = getattr(self, "current_update_button", None)
        self._updating = True
        if btn is not None:
            try:
                if btn.winfo_exists():
                    btn.configure(state="disabled", text="Updating...")
            except Exception:
                pass
        self.update_status_label.configure(
            text=f"Upgrading {package} to {target}..."
        )
        threading.Thread(
            target=self._do_update,
            args=(package, target, btn),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_update_result)

    def _do_update(self, package, target, btn=None):
        # Runs in a worker thread: NEVER touch tkinter here.
        try:
            install_package(
                self.env_name,
                f"{package}=={target}",
                log_callback=lambda msg: None,
            )
            self._update_queue.put(("single_success", (btn, package, target)))
        except Exception as e:
            self._update_queue.put(("single_failure", (btn, package, target, str(e))))

    def _poll_update_result(self):
        """Main-thread poller that reads the worker thread's result safely."""
        if not self._updating:
            return
        try:
            outcome, payload = self._update_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_update_result)
            return
        if outcome == "single_success":
            self._on_update_success(*payload)
        elif outcome == "single_failure":
            self._on_update_failure(*payload)
        elif outcome == "upgrade_all_done":
            self._on_upgrade_all_done(*payload)

    def _configure_embedded_buttons(self, text, state):
        """Update every live embedded 'Update Now' button instance."""
        candidates = {getattr(self, "current_update_button", None)}
        for btn in candidates:
            if btn is None:
                continue
            try:
                if btn.winfo_exists():
                    btn.configure(text=text, state=state)
            except Exception:
                pass

    def _on_update_success(self, btn, package, target):
        self._updating = False
        self._configure_embedded_buttons("✓ Updated", "disabled")
        self.current_vuln = None
        self.current_update_button = None
        self.update_status_label.configure(
            text=f"{package} upgraded to {target} successfully."
        )
        messagebox.showinfo(
            "Update Successful",
            f"'{package}' has been upgraded to {target}.\n\n"
            "The vulnerability remediation has been applied.",
        )
        # Persist the fixed status + new version in the DB, then refresh the
        # report so the status column and locks reflect the resolution.
        try:
            mark_package_fixed(self.env_name, package, target)
        except Exception as e:
            logging.warning(f"Failed to persist fixed status for {package}: {e}")
        self._refresh_from_db()

    def _on_update_failure(self, btn, package, target, error):
        self._updating = False
        self._configure_embedded_buttons("Update Now", "normal")
        self.update_status_label.configure(
            text=f"Failed — {package} was not upgraded to {target}."
        )
        self._refresh_upgrade_all_button()
        messagebox.showerror(
            "Update Failed",
            f"Failed to upgrade '{package}' to {target}:\n\n{error}",
        )

    # ---------------------- Upgrade All Packages ----------------------

    @staticmethod
    def _version_key(version):
        """Turn a version string into a comparable numeric tuple."""
        return version_key(version)

    def _collect_upgrade_plan(self):
        """Build {package: recommended_fixed_version} from ALL packages scanned in
        the environment — NOT just the currently selected package.

        For every vulnerability across every package, the remediation-recommended
        fixed version is picked (highest wins when duplicates exist).
        """
        plan = {}
        for pkg_data in self.packages_map.values():
            for vuln in self._extract_vulnerabilities(pkg_data):
                target = self._parse_target_version(vuln)
                if not target or self._is_vuln_up_to_date(vuln):
                    # No fix, or the installed version already meets the fix.
                    continue
                package = vuln["package"].split("[")[0].strip()
                if not package:
                    continue
                if package not in plan or self._version_key(target) > self._version_key(plan[package]):
                    plan[package] = target
        return plan

    def upgrade_all_packages(self):
        """Upgrade every vulnerable package across the whole environment to its
        recommended fixed version."""
        if self._updating or not self.packages_map:
            return
        plan = self._collect_upgrade_plan()
        if not plan:
            messagebox.showinfo(
                "No Action",
                "No vulnerabilities with a recommended fixed version were found "
                f"in environment '{self.env_name}'.\n"
                "Rescan the environment to refresh the report.",
            )
            return
        plan_text = "\n".join(f"  • {p} -> {v}" for p, v in plan.items())
        if not messagebox.askyesno(
            "Confirm Upgrade",
            f"Upgrade all {len(plan)} package(s) to the recommended fixed versions "
            f"in environment '{self.env_name}'?\n\n{plan_text}",
        ):
            return

        self._updating = True
        self.update_now_button.configure(state="disabled", text="⏳ Upgrading...")
        self.update_status_label.configure(
            text=f"Upgrading {len(plan)} package(s) to recommended versions..."
        )
        threading.Thread(
            target=self._do_upgrade_all,
            args=(plan,),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_update_result)

    def _do_upgrade_all(self, plan):
        # Runs in a worker thread: NEVER touch tkinter here.
        successful, failed = [], []
        for package, target in plan.items():
            try:
                install_package(
                    self.env_name,
                    f"{package}=={target}",
                    log_callback=lambda msg: None,
                )
                successful.append((package, target))
            except Exception as e:
                failed.append((package, target, str(e)))
        self._update_queue.put(("upgrade_all_done", (successful, failed)))

    def _on_upgrade_all_done(self, successful, failed):
        self._updating = False
        parts = []
        if successful:
            parts.append(f"✓ Upgraded ({len(successful)}):")
            parts.extend(f"  • {p} -> {v}" for p, v in successful)
        if failed:
            parts.append(f"✗ Failed ({len(failed)}):")
            parts.extend(f"  • {p} -> {v}: {err}" for p, v, err in failed)
        summary = "\n".join(parts) or "No packages were updated."

        if failed:
            self.update_status_label.configure(
                text=f"Upgrade finished: {len(successful)} ok, {len(failed)} failed."
            )
            messagebox.showerror("Upgrade Summary", summary)
        else:
            self.update_status_label.configure(
                text=f"All {len(successful)} package(s) upgraded to recommended versions."
            )
            messagebox.showinfo("Upgrade Summary", summary)

        # Persist the upgraded versions + fixed statuses, then refresh the report.
        for package, new_version in successful:
            try:
                mark_package_fixed(self.env_name, package, new_version)
            except Exception as e:
                logging.warning(f"Failed to persist fixed status for {package}: {e}")
        self._refresh_from_db()

    def _refresh_from_db(self):
        """Reload the latest scan data from the DB (e.g., after a successful
        upgrade persisted a fixed status) and rebuild the current view."""
        self.data = DBHelper.get_vulnerability_info(self.env_name)
        new_map = self._packages_map()
        selected = (
            self.current_pkg_key
            if self.current_pkg_key in new_map
            else (list(new_map)[0] if new_map else None)
        )
        self.packages_map = new_map
        self.pkg_combo.configure(values=list(new_map.keys()))
        if selected:
            self.pkg_combo.set(selected)
            self.on_package_selected(None)
        else:
            self._clear_ui()

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