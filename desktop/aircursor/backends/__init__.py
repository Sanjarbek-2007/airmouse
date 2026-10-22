"""Input backends: a virtual mouse and a volume control per platform."""
from __future__ import annotations

import sys

from .base import Mouse, MouseUnavailable, NullMouse
from .keyboard import Keyboard, NullKeyboard
from .volume import Volume

__all__ = ["Mouse", "NullMouse", "MouseUnavailable", "Volume", "Keyboard", "NullKeyboard",
           "create_mouse", "create_keyboard"]


def create_mouse(live: bool) -> Mouse:
    """Return a real virtual mouse (live=True) or a do-nothing one (dry run)."""
    if not live:
        return NullMouse()
    if sys.platform.startswith("linux"):
        from .uinput import UInputMouse
        return UInputMouse()
    from .pynput_backend import PynputMouse
    return PynputMouse()


def create_keyboard(live: bool) -> Keyboard:
    """Virtual keyboard for shortcut actions; a do-nothing one for dry runs."""
    if not live:
        return NullKeyboard()
    if sys.platform.startswith("linux"):
        from .keyboard import UInputKeyboard
        return UInputKeyboard()
    from .keyboard import PynputKeyboard
    return PynputKeyboard()
