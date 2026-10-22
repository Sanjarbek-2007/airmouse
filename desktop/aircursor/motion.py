"""Cursor motion: smoothing, hand-size normalisation, smart acceleration, dial."""
from __future__ import annotations

import math
from collections import deque

import numpy as np

BASE_PX = 700.0        # cursor px per hand-length of movement at speed 1.0 (before boosts)
DIAL_MIN_RADIUS = 0.18  # circle radius / hand size below which motion is ignored


class OneEuro:
    """One-euro filter: smooth when slow (no jitter), responsive when fast."""

    def __init__(self, min_cutoff=1.0, beta=0.02, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.reset()

    def reset(self):
        self.x = self.dx = self.t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self.t is None:
            self.x, self.dx, self.t = x, 0.0, t
            return x
        dt = max(t - self.t, 1e-3)
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx = a_d * (x - self.x) / dt + (1 - a_d) * self.dx
        a = self._alpha(self.min_cutoff + self.beta * abs(self.dx), dt)
        self.x = a * x + (1 - a) * self.x
        self.t = t
        return self.x


def _smoothstep(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


class SmartMotion:
    """Maps hand motion (camera px) to cursor motion (screen px).

    * Hand-size normalisation: moving your hand 10 cm moves the cursor the same
      whether you sit near or far from the camera.
    * Speed-up: fast flicks travel further, slow moves stay precise.
    * Long-reach boost: sustained movement in one direction ramps the gain up,
      so reaching a screen corner doesn't need a full arm swing. Stopping or
      reversing resets it.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.size = None
        self.run = 0.0       # distance travelled in a consistent direction (hand lengths)
        self.dir = None
        self.slow_t = 0.0
        self.factor = 1.0    # last total gain multiplier (for the UI)

    def map(self, d: np.ndarray, dt: float, hand_size: float, cfg) -> np.ndarray:
        """d: filtered hand displacement in camera px. Returns cursor displacement px."""
        self.size = hand_size if self.size is None else 0.9 * self.size + 0.1 * hand_size
        dt = max(dt, 1e-3)
        dn = d / self.size                    # in hand lengths
        dist = float(np.linalg.norm(dn))
        if dist * self.size < 0.6:            # sub-pixel tremor: no motion, but time still passes
            self.slow_t += dt
            if self.slow_t > 0.25:
                self.run = 0.0
            self.run *= math.exp(-dt / 2.0)
            self.factor = 1.0
            return np.zeros(2)
        speed = dist / dt                     # hand lengths / s
        gain = BASE_PX * cfg.speed
        factor = 1.0

        if cfg.smart_motion:
            factor *= 1 + cfg.accel_strength * _smoothstep((speed - 0.25) / 2.75)

            u = dn / dist
            if self.dir is None:
                self.dir = u
            elif float(np.dot(u, self.dir)) < 0.35:   # changed direction: restart the run
                self.run *= 0.25
                self.dir = u
            else:
                v = 0.7 * self.dir + 0.3 * u
                self.dir = v / max(float(np.linalg.norm(v)), 1e-6)
            if speed > 0.3:
                self.run += dist
                self.slow_t = 0.0
            else:
                self.slow_t += dt
                if self.slow_t > 0.25:                 # paused: the next move starts fresh
                    self.run = 0.0
            self.run *= math.exp(-dt / 2.0)
            factor *= 1 + cfg.long_move_boost * _smoothstep(self.run / 2.5)

        self.factor = factor
        return dn * gain * factor


class Dial:
    """Counts full circles drawn by a fingertip. Positive = clockwise on screen."""

    def __init__(self):
        self.win = deque(maxlen=10)
        self.prev = None

    def reset(self):
        self.win.clear()
        self.prev = None

    def update(self, tip: np.ndarray, size: float) -> float:
        """tip in pixels, size = hand size in pixels. Returns signed turns since last call."""
        self.win.append(tip)
        if len(self.win) < 5:
            return 0.0
        v = tip - np.mean(self.win, axis=0)
        if np.linalg.norm(v) < DIAL_MIN_RADIUS * size:  # too small: just hand jitter
            self.prev = None
            return 0.0
        ang = math.atan2(v[1], v[0])  # image y points down, so + = clockwise
        prev, self.prev = self.prev, ang
        if prev is None:
            return 0.0
        da = (ang - prev + math.pi) % (2 * math.pi) - math.pi
        return da / (2 * math.pi) if abs(da) < 2.0 else 0.0  # ignore tracking glitches
