"""Windows / macOS virtual mouse using pynput (experimental - not tested by the author)."""
from __future__ import annotations

import threading

from .base import Mouse, MouseUnavailable


class PynputMouse(Mouse):
    live = True

    def __init__(self):
        try:
            from pynput.mouse import Button, Controller
        except Exception as e:  # missing package or no display
            raise MouseUnavailable(f"pynput is required on this platform: {e}") from e
        self._c = Controller()
        self._btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}
        self._down = {k: False for k in self._btn}
        self._rem = [0.0, 0.0]
        self._lock = threading.Lock()

    def move_rel(self, dx, dy):
        with self._lock:
            self._rem[0] += dx
            self._rem[1] += dy
            ix, iy = int(self._rem[0]), int(self._rem[1])
            self._rem[0] -= ix
            self._rem[1] -= iy
        if ix or iy:
            self._c.move(ix, iy)

    def cancel_motion(self):
        with self._lock:
            self._rem = [0.0, 0.0]

    def button(self, name, down):
        if self._down[name] == down:
            return
        self._down[name] = down
        (self._c.press if down else self._c.release)(self._btn[name])

    def scroll(self, notches, horizontal=False):
        if notches:
            self._c.scroll(notches if horizontal else 0, 0 if horizontal else notches)

    def release_all(self):
        for name in self._btn:
            self.button(name, False)

    def close(self):
        self.release_all()
