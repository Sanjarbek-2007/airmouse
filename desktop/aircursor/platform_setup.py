"""Platform tweaks that must run before Qt starts."""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

VENDOR_LIB = Path(__file__).resolve().parents[1] / "vendor" / "lib"


def prepare_qt() -> str:
    """Pick the Qt platform. On Linux/Wayland we prefer XWayland (xcb): GNOME's Wayland
    ignores "always on top" from normal apps, but honours it for X11 windows, and the
    floating panic button must stay on top. Needs libxcb-cursor (apt install libxcb-cursor0,
    or run scripts/setup-linux.sh which fetches it into vendor/lib without root)."""
    os.environ.setdefault("QT_LOGGING_RULES", "*.warning=false;qt.qpa.*=false")
    if not sys.platform.startswith("linux") or "QT_QPA_PLATFORM" in os.environ:
        return os.environ.get("QT_QPA_PLATFORM", "")
    if not os.environ.get("DISPLAY"):
        return "wayland"  # no XWayland available
    try:
        ctypes.CDLL("libxcb-cursor.so.0", mode=ctypes.RTLD_GLOBAL)
    except OSError:
        try:
            ctypes.CDLL(str(VENDOR_LIB / "libxcb-cursor.so.0"), mode=ctypes.RTLD_GLOBAL)
        except OSError:
            return "wayland"  # fall back: widget may not stay on top
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    return "xcb"
