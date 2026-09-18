"""Shared application-icon helpers for Py Env Studio windows.

This module is the single source of truth for the Py Env Studio window icon:

* :func:`get_app_icon_path` resolves the packaged ``.ico`` resource.
* :func:`apply_window_icon` applies the icon to one already created window.
* :func:`schedule_window_icon` applies the icon immediately and again after a
  short delay, because CustomTkinter overrides the icon of new windows
  (``CTk``/``CTkToplevel``) roughly 200 ms after they are created.
* :func:`install_window_icon_hook` patches the base ``tkinter`` window classes
  once, so every window created afterwards (dialogs, plugin windows, the
  Vulnerability Insights Dashboard, ...) automatically receives the PES icon.

The module deliberately keeps the GUI dependencies (Pillow, tkinter) out of the
import path of :func:`get_app_icon_path` so CLI/shortcut code can resolve the
icon without importing a GUI toolkit.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import importlib.resources as pkg_resources

LOGGER = logging.getLogger(__name__)

ICON_PACKAGE = "py_env_studio.ui.static.icons"
ICON_FILENAME = "pes-transparrent-icon-default.ico"

# CustomTkinter sets its own icon on new windows about 200 ms after creation,
# so the PES icon must be (re)applied after that delay to win the race.
ICON_APPLY_DELAY_MS = 300

# Attribute marking a patched initializer so the hook cannot be stacked twice.
_HOOK_MARKER = "_pes_window_icon_hooked"

_hook_installed = False


def get_app_icon_path() -> Path | None:
    """Return the resolved path of the packaged PES icon, or ``None``.

    Resolution order: packaged resource first (matches how the icon is shipped
    by ``pyproject.toml``), then a filesystem fallback for source checkouts.
    """
    try:
        with pkg_resources.path(ICON_PACKAGE, ICON_FILENAME) as icon_path:
            resolved = Path(icon_path).resolve()
            if resolved.exists():
                return resolved
    except Exception as exc:  # pragma: no cover - depends on the packaging layout
        LOGGER.debug("Packaged application icon lookup failed: %s", exc)

    fallback = Path(__file__).resolve().parent.parent / "ui" / "static" / "icons" / ICON_FILENAME
    if fallback.exists():
        return fallback

    LOGGER.warning("Py Env Studio window icon not found: %s", ICON_FILENAME)
    return None


def apply_window_icon(window: Any, icon_path: Path | None = None) -> bool:
    """Apply the PES icon to ``window`` and return ``True`` when it worked.

    ``iconbitmap`` gives the correct Windows titlebar/taskbar icon, while
    ``iconphoto`` covers platforms/situations where the bitmap form is not
    supported. Failures are logged and never raised: a missing icon must never
    break a window.
    """
    path = Path(icon_path) if icon_path is not None else get_app_icon_path()
    if path is None or not path.exists():
        return False

    applied = False

    try:
        window.iconbitmap(str(path))
        applied = True
    except Exception:
        # ``wm_iconbitmap`` is the primitive form; some window classes override
        # only one of the two aliases.
        try:
            window.wm_iconbitmap(str(path))
            applied = True
        except Exception as exc:
            LOGGER.debug("Could not set window bitmap icon: %s", exc)

    try:
        # Imported lazily so icon/path resolution stays free of GUI imports.
        from PIL import Image, ImageTk

        image = Image.open(str(path))
        try:
            # An explicit master keeps the photo bound to this window's
            # interpreter, which matters when several Tk roots exist.
            photo = ImageTk.PhotoImage(image, master=window)
        except TypeError:  # very old Pillow without a ``master`` option
            photo = ImageTk.PhotoImage(image)
        window.iconphoto(False, photo)
        # Tk drops the icon when the PhotoImage is garbage collected, so keep a
        # reference alive on the window itself.
        window._pes_window_icon_photo = photo
        applied = True
    except Exception as exc:
        LOGGER.debug("Could not set window photo icon: %s", exc)

    return applied


def schedule_window_icon(window: Any, delay_ms: int = ICON_APPLY_DELAY_MS) -> None:
    """Apply the PES icon now and again after ``delay_ms``.

    The delayed call is what makes the icon stick on CustomTkinter windows,
    which set their own default icon shortly after creation.
    """
    apply_window_icon(window)

    try:
        window.after(delay_ms, lambda: apply_window_icon(window))
    except Exception as exc:
        LOGGER.debug("Could not schedule window icon update: %s", exc)


def install_window_icon_hook() -> None:
    """Make every Tk window created afterwards use the PES icon.

    Both ``tkinter.Tk`` and ``tkinter.Toplevel`` are patched because
    CustomTkinter (``CTk``/``CTkToplevel``) derives from them, so the hook also
    covers newer windows that may be added later. Calling this repeatedly is
    safe.
    """
    global _hook_installed
    if _hook_installed:
        return

    import tkinter

    _patch_window_initializer(tkinter.Tk)
    _patch_window_initializer(tkinter.Toplevel)
    _hook_installed = True
    LOGGER.debug("Installed global Tk window icon hook.")


def _patch_window_initializer(window_class: type) -> None:
    """Wrap ``window_class.__init__`` so new windows get the PES icon."""
    original_init = window_class.__init__
    if getattr(original_init, _HOOK_MARKER, False):
        return

    def _pes_icon_initializer(self, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        schedule_window_icon(self)

    setattr(_pes_icon_initializer, _HOOK_MARKER, True)
    setattr(_pes_icon_initializer, "__wrapped__", original_init)
    window_class.__init__ = _pes_icon_initializer
