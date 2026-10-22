"""Synthetic hands + fake devices so gesture logic can be tested without a camera."""
import math

import numpy as np

from aircursor.config import Config
from aircursor.controller import Controller

W, H = 1280, 720  # webcam-shaped frame


class FakeMouse:
    live = True

    def __init__(self):
        self.log, self.mv, self.held = [], np.zeros(2), set()

    def move_rel(self, dx, dy): self.mv += (dx, dy)
    def cancel_motion(self): self.log.append("cancel")
    def button(self, name, down):
        if (name in self.held) == down:
            return
        (self.held.add if down else self.held.discard)(name)
        self.log.append((name, "down" if down else "up"))
    def scroll(self, n, horizontal=False): self.log.append(("scroll", "H" if horizontal else "V", n))
    def release_all(self):
        for n in list(self.held):
            self.button(n, False)
    def close(self): pass


class FakeKeyboard:
    def __init__(self): self.chords = []
    def chord(self, keys): self.chords.append(tuple(keys))
    def close(self): pass


class FakeVolume:
    def __init__(self): self.sets = []
    def get(self): return 0.30
    def set(self, v): self.sets.append(round(v, 3))


def hand(up, ox=0.5, oy=0.75, thumb="out", tip_off=(0, 0), hook=False):
    """Normalised landmarks of an upright hand. `up` = indices of extended fingers
    (0 index, 1 middle, 2 ring, 3 pinky). Sized ~ a real hand in a 16:9 frame."""
    s = 0.17  # hand length as a fraction of frame height (aspect-corrected below)
    p = np.zeros((21, 2))
    p[0] = (ox, oy)
    sx = H / W  # x offsets are fractions of width
    for f, (k, dx) in enumerate({5: -0.05, 9: 0.0, 13: 0.045, 17: 0.09}.items()):
        b = np.array([ox + dx * sx, oy - s])
        p[k] = b
        p[k + 1] = b + (0, -0.06)
        if f in up:
            p[k + 2] = b + (0, -0.11); p[k + 3] = b + (0, -0.16)
        else:
            p[k + 2] = b + (0, -0.03); p[k + 3] = b
    p[1:5] = [(ox - 0.06 * sx, oy - 0.05), (ox - 0.10 * sx, oy - 0.10),
              (ox - 0.13 * sx, oy - 0.13), (ox - 0.17 * sx, oy - 0.17)]
    if thumb == "pinch":
        p[4] = p[8] + (0.004 * sx, 0.004)
    elif thumb == "tuck":
        p[4] = p[13] + (0.0, 0.04)
    if hook:  # index half-bent: ~125 degrees at the PIP joint, like a "C"
        b = p[5]
        p[6] = b + (0, -0.06)
        p[7] = p[6] + (0.05 * math.sin(math.radians(55)) * sx, -0.05 * math.cos(math.radians(55)))
        p[8] = p[7] + (0.04 * math.sin(math.radians(110)) * sx, -0.04 * math.cos(math.radians(110)))
    p[8] = p[8] + tip_off
    return p


def rotated(p, deg):
    """Rotate a hand about its wrist, clockwise on screen (+deg)."""
    px = p * (W, H)
    d = px - px[0]
    a = math.radians(deg)
    out = np.stack([d[:, 0] * math.cos(a) - d[:, 1] * math.sin(a),
                    d[:, 0] * math.sin(a) + d[:, 1] * math.cos(a)], axis=1) + px[0]
    return out / (W, H)


OPEN = hand({0, 1, 2, 3})
FIST = hand(set(), thumb="pinch")      # thumb resting on index: must NOT count as a click
POINT = hand({0})
PINCH = hand({1, 2, 3}, thumb="pinch")
TUCK = hand({0, 1, 2, 3}, thumb="tuck")


HOOK = hand(set(), hook=True)


def make(cfg=None):
    m, v, kb = FakeMouse(), FakeVolume(), FakeKeyboard()
    c = Controller(cfg or Config(), m, v, kb)
    return c, m, v


def run(c, seq, dt=1 / 15, t0=1000.0):
    """Feed frames (None = no hand). Returns the label after each frame."""
    t, labels = t0, []
    for g in seq:
        t += dt
        labels.append(c.lost(t) if g is None else c.update(g, W, H, t))
    return labels


def circle(turns, n_per=14, cw=True, up={0, 3}):
    out = []
    for i in range(int(turns * n_per)):
        a = 2 * math.pi * i / n_per * (1 if cw else -1)
        out.append(hand(up, tip_off=(0.06 * math.cos(a) * H / W, 0.06 * math.sin(a))))
    return out
