"""Virtual keyboard for shortcut actions (Alt+Tab, media keys...).

Linux: a second uinput device, so it works on Wayland and X11 alike. Windows/macOS: pynput.
Chords are tuples of backend-neutral key names; presses are queued to a worker thread so the
recognition loop never blocks on key timing.
"""
from __future__ import annotations

import fcntl
import os
import queue
import struct
import threading
import time

from .base import MouseUnavailable

# backend-neutral name -> Linux evdev key code
LINUX_KEYS = {
    "alt": 56, "shift": 42, "ctrl": 29, "super": 125, "tab": 15, "esc": 1,
    "left": 105, "right": 106, "up": 103, "down": 108, "f4": 62,
    "c": 46, "d": 32, "v": 47, "z": 44,
    "playpause": 164, "nexttrack": 163, "prevtrack": 165,
    "mute": 113, "volup": 115, "voldown": 114, "prtsc": 99,
}
STEP = 0.012  # s between key events: some compositors drop chords that arrive in one burst


class Keyboard:
    live = False

    def chord(self, keys) -> None: ...
    def close(self) -> None: ...


class NullKeyboard(Keyboard):
    pass


class UInputKeyboard(Keyboard):
    live = True

    def __init__(self):
        try:
            fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        except OSError as e:
            raise MouseUnavailable(f"keyboard: {e.strerror}") from e
        io = lambda req, arg=0: fcntl.ioctl(fd, req, arg)
        io(0x40045564, 1)  # EV_KEY
        for code in set(LINUX_KEYS.values()):
            io(0x40045565, code)
        io(0x405C5503, struct.pack("HHHH80sI", 0x03, 0x1234, 0x567A, 1, b"aircursor-keyboard", 0))
        io(0x5501)
        self.fd = fd
        self._q: "queue.Queue" = queue.Queue()
        time.sleep(0.3)
        threading.Thread(target=self._worker, daemon=True).start()

    def _send(self, code: int, down: bool) -> None:
        t = time.time()
        sec, usec = int(t), int((t % 1) * 1e6)
        buf = struct.pack("llHHi", sec, usec, 1, code, int(down)) + struct.pack("llHHi", sec, usec, 0, 0, 0)
        try:
            os.write(self.fd, buf)
        except OSError:
            pass

    def chord(self, keys) -> None:
        codes = [LINUX_KEYS[k] for k in keys if k in LINUX_KEYS]
        if codes:
            self._q.put(codes)

    def _worker(self) -> None:
        while True:
            codes = self._q.get()
            if codes is None:
                return
            for c in codes:
                self._send(c, True); time.sleep(STEP)
            for c in reversed(codes):
                self._send(c, False); time.sleep(STEP)

    def close(self) -> None:
        self._q.put(None)
        time.sleep(0.05)
        fd, self.fd = self.fd, None
        if fd is not None:
            fcntl.ioctl(fd, 0x5502)
            os.close(fd)


class PynputKeyboard(Keyboard):
    """Windows / macOS (experimental)."""
    live = True

    def __init__(self):
        try:
            from pynput.keyboard import Controller, Key
        except Exception as e:
            raise MouseUnavailable(f"pynput is required on this platform: {e}") from e
        self._c = Controller()
        self._map = {
            "alt": Key.alt, "shift": Key.shift, "ctrl": Key.ctrl, "super": Key.cmd, "tab": Key.tab,
            "esc": Key.esc, "left": Key.left, "right": Key.right, "up": Key.up, "down": Key.down,
            "f4": Key.f4, "playpause": Key.media_play_pause, "nexttrack": Key.media_next,
            "prevtrack": Key.media_previous, "mute": Key.media_volume_mute,
            "volup": Key.media_volume_up, "voldown": Key.media_volume_down, "prtsc": Key.print_screen,
        }

    def chord(self, keys) -> None:
        ks = [self._map.get(k, k) for k in keys]
        for k in ks:
            self._c.press(k)
        for k in reversed(ks):
            self._c.release(k)
