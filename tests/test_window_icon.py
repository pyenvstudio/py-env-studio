"""Standalone test for the shared Py Env Studio window icon.

Every PES window (main window, CustomTkinter dialogs, plugin windows and the
Vulnerability Insights Dashboard) must show the packaged PES icon instead of the
CustomTkinter default icon.

Covers:
  1. icon resolution (packaged resource + filesystem fallback)
  2. robustness of apply_window_icon (missing window / missing icon file)
  3. the global Tk hook that gives every window the PES icon
  4. the Vulnerability Insights Dashboard window

Run:
    python tests/test_window_icon.py
"""

import ctypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Keep the unicode check marks printable even when stdout is piped/redirected
# (the Windows default code page cannot encode them).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - very old Python / exotic stream
    pass

FAILURES = []


def check(name, condition, extra=""):
    status = "✓" if condition else "✗"
    print(f"{status} {name} {extra}")
    if not condition:
        FAILURES.append(name)


def skip(name, reason):
    print(f"⊘ {name} skipped ({reason})")


def pump(root, seconds=0.6):
    """Flush tkinter events for ``seconds`` so delayed `after` callbacks run."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        root.update()
        time.sleep(0.03)


WM_GETICON = 0x007F
ICON_BIG = 1


def icon_handle(window):
    """Return the Windows window-icon handle of ``window`` (0 when unset)."""
    if not sys.platform.startswith("win"):
        return 0
    user32 = ctypes.windll.user32
    hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
    return user32.SendMessageW(hwnd, WM_GETICON, ICON_BIG, 0)


# Minimal vulnerability payload so the dashboard can render without a database.
SAMPLE_DATA = {
    "vulnerability_insights": [
        {
            "123": {
                "metadata": {"package": "demo-pkg", "version": "1.0.0", "index_insights": []},
                "developer_view": [
                    {
                        "vulnerability_id": "GHSA-icon-1",
                        "affected_components": ["demo-pkg"],
                        "summary": "Demo vulnerability",
                        "severity": {"level": "High"},
                        "fixed_versions": ["2.0.0"],
                        "impact": "Impact text",
                        "remediation_steps": "Upgrade to 2.0.0",
                        "references": [],
                    }
                ],
                "tech_leader_view": {"total_vulnerabilities": 1, "severity_breakdown": {}},
                "enterprise_view": {},
            }
        }
    ]
}


from py_env_studio.utils import app_icon

# ---------------------------------------------------------------------------
# 1. Icon resolution
# ---------------------------------------------------------------------------
icon_path = app_icon.get_app_icon_path()
check("icon path resolved", icon_path is not None)
check("icon file exists", icon_path is not None and icon_path.is_file())
check(
    "resolved file is the packaged PES icon",
    icon_path is not None and icon_path.name == "pes-transparrent-icon-default.ico",
    f"({icon_path})",
)
check(
    "icon lives in the packaged static/icons folder",
    icon_path is not None
    and icon_path.parent.name == "icons"
    and icon_path.parent.parent.name == "static",
)
if icon_path is not None and icon_path.is_file():
    header = icon_path.read_bytes()[:4]
    check("icon has a valid ICO header", header == b"\x00\x00\x01\x00", f"(header={header!r})")

# Filesystem fallback must still work when the packaged lookup fails.
original_package = app_icon.ICON_PACKAGE
try:
    app_icon.ICON_PACKAGE = "py_env_studio.does_not_exist_icons"
    fallback_path = app_icon.get_app_icon_path()
finally:
    app_icon.ICON_PACKAGE = original_package
check(
    "filesystem fallback used when the packaged resource is missing",
    fallback_path is not None and fallback_path == icon_path,
    f"({fallback_path})",
)

# ---------------------------------------------------------------------------
# 2. Robustness: a missing window / icon must never raise
# ---------------------------------------------------------------------------
check("apply_window_icon(None) returns False", app_icon.apply_window_icon(None) is False)
check(
    "apply_window_icon(non-window) returns False",
    app_icon.apply_window_icon(object(), icon_path) is False,
)
check(
    "apply_window_icon(missing file) returns False",
    app_icon.apply_window_icon(None, Path("definitely-missing.ico")) is False,
)

# ---------------------------------------------------------------------------
# 3./4. GUI behaviour (needs a display)
# ---------------------------------------------------------------------------
gui_ready = True
try:
    import tkinter

    import customtkinter as ctk

    from py_env_studio.utils import vulneribility_insights as vi
except Exception as exc:  # pragma: no cover - environment without GUI deps
    skip("GUI window icon tests", f"import failed: {exc}")
    gui_ready = False

root = None
if gui_ready:
    try:
        root = ctk.CTk()
    except tkinter.TclError as exc:  # pragma: no cover - headless machine
        skip("GUI window icon tests", f"no display: {exc}")
        gui_ready = False
    else:
        root.withdraw()

        # Baseline: windows created before the hook only get the CustomTkinter
        # icon - this is exactly the bug that was reported.
        pre_hook_top = ctk.CTkToplevel(root)
        pre_hook_top.withdraw()
        pump(root)
        check(
            "baseline: pre-hook window has no PES icon (bug reproduced)",
            getattr(pre_hook_top, "_pes_window_icon_photo", None) is None
            and getattr(root, "_pes_window_icon_photo", None) is None,
        )

        original_tk_init = tkinter.Tk.__init__
        original_toplevel_init = tkinter.Toplevel.__init__
        app_icon.install_window_icon_hook()
        check("hook patches tkinter.Tk.__init__", tkinter.Tk.__init__ is not original_tk_init)
        check(
            "hook patches tkinter.Toplevel.__init__",
            tkinter.Toplevel.__init__ is not original_toplevel_init,
        )
        check(
            "hook keeps a reference to the original initializers",
            getattr(tkinter.Tk.__init__, "__wrapped__", None) is original_tk_init
            and getattr(tkinter.Toplevel.__init__, "__wrapped__", None) is original_toplevel_init,
        )
        patched_toplevel_init = tkinter.Toplevel.__init__
        app_icon.install_window_icon_hook()
        check(
            "installing the hook twice is a no-op",
            tkinter.Toplevel.__init__ is patched_toplevel_init,
        )

        # A CustomTkinter toplevel created after the hook is covered.
        ctk_top = ctk.CTkToplevel(root)
        ctk_top.withdraw()
        pump(root)
        check(
            "CTkToplevel created after the hook gets the PES icon",
            getattr(ctk_top, "_pes_window_icon_photo", None) is not None,
        )

        # A plain tkinter toplevel (non-CustomTkinter window) is covered too.
        plain_top = tkinter.Toplevel(root)
        plain_top.withdraw()
        pump(root)
        check(
            "plain tkinter.Toplevel created after the hook gets the PES icon",
            getattr(plain_top, "_pes_window_icon_photo", None) is not None,
        )

        # Explicitly applied icons (the dashboard path) win the race against
        # the CustomTkinter default icon thanks to the delayed re-apply.
        check(
            "schedule_window_icon applies the icon to an existing window",
            app_icon.schedule_window_icon(pre_hook_top) is None
            and getattr(pre_hook_top, "_pes_window_icon_photo", None) is not None,
        )
        pump(root)
        check(
            "icon survives the delayed CustomTkinter icon update",
            getattr(pre_hook_top, "_pes_window_icon_photo", None) is not None,
        )
        check(
            "apply_window_icon(main window) returns True",
            app_icon.apply_window_icon(root) is True,
        )

        # ---- 4. OS level verification (Windows) ---------------------------
        if sys.platform.startswith("win"):
            check(
                "Windows reports a window icon for the main window",
                icon_handle(root) > 0,
                f"(handle={icon_handle(root)})",
            )
            check(
                "Windows reports a window icon for the CTkToplevel",
                icon_handle(ctk_top) > 0,
                f"(handle={icon_handle(ctk_top)})",
            )
        else:
            skip("OS level window icon check", f"not Windows ({sys.platform})")

        # ---- 5. Vulnerability Insights Dashboard window --------------------
        check(
            "dashboard uses the shared icon helper",
            vi.schedule_window_icon is app_icon.schedule_window_icon,
        )
        dashboard_root = None
        original_get = vi.DBHelper.get_vulnerability_info
        original_ensure = vi.ensure_vulnerability_statuses
        try:
            dashboard_root = ctk.CTk()
            dashboard_root.withdraw()
            vi.DBHelper.get_vulnerability_info = staticmethod(lambda env: SAMPLE_DATA)
            vi.ensure_vulnerability_statuses = lambda env: None
            dashboard = vi.VulnerabilityInsightsApp(dashboard_root, "test_env")
            pump(dashboard_root)
            check(
                "dashboard window keeps its title",
                "Vulnerability Insights Dashboard" in dashboard_root.title(),
                f"({dashboard_root.title()})",
            )
            check(
                "dashboard window gets the PES icon",
                getattr(dashboard_root, "_pes_window_icon_photo", None) is not None,
            )
            if sys.platform.startswith("win"):
                check(
                    "Windows reports a window icon for the dashboard",
                    icon_handle(dashboard_root) > 0,
                    f"(handle={icon_handle(dashboard_root)})",
                )
        except Exception as exc:
            check("dashboard window builds with the shared icon", False, f"({exc})")
        finally:
            vi.DBHelper.get_vulnerability_info = original_get
            vi.ensure_vulnerability_statuses = original_ensure
            if dashboard_root is not None:
                try:
                    dashboard_root.destroy()
                except Exception:
                    pass

        try:
            root.destroy()
        except Exception:
            pass


print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)} check(s) failed -> {FAILURES}")
    sys.exit(1)
print("ALL CHECKS PASSED ✅")
