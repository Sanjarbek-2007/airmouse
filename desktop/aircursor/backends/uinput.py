"""Linux virtual mouse through /dev/uinput. Works on X11 *and* Wayland because the
compositor sees it as a real hardware mouse."""
from __future__ import annotations

import fcntl
import math
import os
import struct
import threading
import time

import numpy as np

from .base import Mouse, MouseUnavailable

EV_SYN, EV_KEY, EV_REL = 0, 1, 2
BTN = {"left": 0x110, "right": 0x111, "middle": 0x112}
REL_X, REL_Y, REL_HWHEEL, REL_WHEEL, REL_WHEEL_HI_RES, REL_HWHEEL_HI_RES = 0, 1, 6, 8, 0x0B, 0x0C
CURSOR_TAU = 0.025  # s: the cursor glides toward its target, smoothing low-fps video

HELP = (
    "Cannot open /dev/uinput.\n"
    "Fix once (takes effect immediately, survives reboot):\n"
    "  sudo setfacl -m u:$USER:rw /dev/uinput\n"
    "  echo 'KERNEL==\"uinput\", GROUP=\"input\", MODE=\"0660\"' | sudo tee /etc/udev/rules.d/99-uinput.rules\n"
    "  sudo usermod -aG input $USER   # then log out and in\n"
    "See desktop/scripts/setup-linux.sh"
)


class UInputMouse(Mouse):
    live = True

    def __init__(self):
        self.fd = None
        self._down = {k: False for k in BTN}
        self._wlock = threading.Lock()
        self._plock = threading.Lock()
        self._pend = np.zeros(2)
        self._rem = np.zeros(2)
        try:
            fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        except OSError as e:
            raise MouseUnavailable(f"{e.strerror}. {HELP}") from e
        io = lambda req, arg=0: fcntl.ioctl(fd, req, arg)
        io(0x40045564, EV_KEY)
        io(0x40045564, EV_REL)
        for code in BTN.values():
            io(0x40045565, code)
        for r in (REL_X, REL_Y, REL_WHEEL, REL_HWHEEL, REL_WHEEL_HI_RES, REL_HWHEEL_HI_RES):
            io(0x40045566, r)
        io(0x405C5503, struct.pack("HHHH80sI", 0x03, 0x1234, 0x5679, 1, b"aircursor-mouse", 0))
        io(0x5501)
        self.fd = fd
        time.sleep(0.4)  # let the compositor pick the device up
        threading.Thread(target=self._pump, daemon=True).start()

    def _send(self, *events):
        """Write events + a SYN_REPORT atomically (several threads send)."""
        if self.fd is None:
            return
        t = time.time()
        sec, usec = int(t), int((t % 1) * 1e6)
        buf = b"".join(struct.pack("llHHi", sec, usec, *e) for e in (*events, (EV_SYN, 0, 0)))
        with self._wlock:
            try:
                os.write(self.fd, buf)
            except OSError:
                pass

    def _pump(self):
        last = time.monotonic()
        while self.fd is not None:
            time.sleep(0.008)
            now = time.monotonic()
            k = 1 - math.exp(-(now - last) / CURSOR_TAU)
            last = now
            with self._plock:
                take = self._pend * k
                self._pend -= take
                self._rem += take
                ix, iy = int(self._rem[0]), int(self._rem[1])
                self._rem -= (ix, iy)
            if ix or iy:
                self._send((EV_REL, REL_X, ix), (EV_REL, REL_Y, iy))

    def move_rel(self, dx, dy):
        if self.fd is not None:
            with self._plock:
                self._pend += (dx, dy)

    def cancel_motion(self):
        with self._plock:
            self._pend[:] = 0
            self._rem[:] = 0

    def button(self, name, down):
        if self._down[name] == down:
            return
        self._down[name] = down
        self._send((EV_KEY, BTN[name], int(down)))

    def scroll(self, notches, horizontal=False):
        if notches:
            hi, lo = ((REL_HWHEEL_HI_RES, REL_HWHEEL) if horizontal else (REL_WHEEL_HI_RES, REL_WHEEL))
            self._send((EV_REL, hi, notches * 120), (EV_REL, lo, notches))

    def release_all(self):
        for name in BTN:
            self.button(name, False)

    def close(self):
        if self.fd is not None:
            self.release_all()
            fd, self.fd = self.fd, None
            time.sleep(0.05)
            fcntl.ioctl(fd, 0x5502)
            os.close(fd)
