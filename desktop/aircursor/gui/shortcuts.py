"""Optional: register global keyboard shortcuts on GNOME (the only place we can do it
without elevated rights on Wayland). Only runs when the user clicks the button."""
from __future__ import annotations

import os
import shutil
import subprocess

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
BASE = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"


def available() -> bool:
    return bool(shutil.which("gsettings")) and "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper()


def _gs(*args) -> str:
    return subprocess.run(["gsettings", *args], capture_output=True, text=True, timeout=5, check=True).stdout.strip()


def install(entries: list[tuple[str, str, str, str]]) -> tuple[bool, str]:
    """entries: (id, name, command, binding), e.g. ("aircursor-toggle", "AirCursor pause", "...", "<Ctrl><Alt>p")."""
    try:
        current = _gs("get", SCHEMA, "custom-keybindings")
        paths = [p.strip().strip("'") for p in current.strip("[]@as ").split(",") if p.strip().strip("'")]
        for ident, name, command, binding in entries:
            path = f"{BASE}{ident}/"
            if path not in paths:
                paths.append(path)
            key = f"{SCHEMA}.custom-keybinding:{path}"
            _gs("set", key, "name", name)
            _gs("set", key, "command", command)
            _gs("set", key, "binding", binding)
        _gs("set", SCHEMA, "custom-keybindings", "[" + ", ".join(f"'{p}'" for p in paths) + "]")
        return True, "Shortcuts added"
    except Exception as e:
        return False, f"Could not add shortcuts: {e}"
