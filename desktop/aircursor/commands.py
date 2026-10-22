"""Motion commands: swipe, wave and twist of an open hand.

These are *events* (something your hand does) rather than poses (something it holds), so they are
detected from a short history of the palm's position and tilt, measured in hand-lengths so the
result doesn't depend on how far you sit from the camera. They only run while the hand is an open
palm, which is the "resting / lifted mouse" pose, so they never compete with pointing or clicking.

Anti-misfire: a cooldown after every command, history wiped during the cooldown (so the hand
coming back after a flick can't trigger the opposite command), and thresholds that a normal
"lift and reposition" movement doesn't reach.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Deque, Optional, Tuple

import numpy as np

from .gestures import Command

SWIPE_DIST = 2.6       # hand-lengths travelled ...
SWIPE_SPEED = 5.0      # ... at this average speed (hand-lengths / s)
SWIPE_WINDOW = 0.45    # s
SWIPE_STRAIGHT = 0.75  # net distance / path length
SWIPE_AXIS = 1.8       # dominant axis must beat the other by this factor
WAVE_MIN, WAVE_MAX = 0.5, 2.4   # swing amplitude range (hand-lengths); bigger = a swipe, not a wave
WAVE_SWINGS = 3
WAVE_WINDOW = 1.6
TWIST_DEG = 38.0
TWIST_SPEED = 60.0     # deg / s
TWIST_WINDOW = 0.6
TWIST_DRIFT = 1.4      # the hand must not also travel this far (that would be a swipe)
COOLDOWN = 1.0
MISS_TOLERANCE = 0.25  # s of "not an open palm" before the history is dropped


def _unwrap(prev: float, cur: float) -> float:
    d = (cur - prev + math.pi) % (2 * math.pi) - math.pi
    return prev + d


class CommandDetector:
    def __init__(self):
        self.hist: Deque[Tuple[float, float, float, float]] = deque()  # t, x, y (hand lengths), theta
        self.cooldown_until = 0.0
        self.miss = 0.0
        self.last_t = 0.0
        self.last_theta = 0.0
        self.last: Optional[Command] = None

    def reset(self) -> None:
        self.hist.clear()
        self.miss = 0.0

    def update(self, now: float, palm: np.ndarray, size: float, theta: float, open_hand: bool,
               sens: float = 1.0) -> Optional[Command]:
        """palm: palm position in camera px; size: hand size in px; theta: hand tilt in radians
        (0 = upright, + = clockwise). Returns a Command when one is recognised."""
        dt = now - self.last_t if self.last_t else 0.0
        self.last_t = now
        if not open_hand:
            self.miss += dt
            if self.miss > MISS_TOLERANCE:
                self.hist.clear()
            return None
        self.miss = 0.0
        if now < self.cooldown_until:
            self.hist.clear()
            return None
        theta = _unwrap(self.hist[-1][3], theta) if self.hist else theta
        self.hist.append((now, float(palm[0]) / size, float(palm[1]) / size, theta))
        while self.hist and now - self.hist[0][0] > WAVE_WINDOW:
            self.hist.popleft()

        cmd = self._wave() or self._swipe(sens) or self._twist(sens)
        if cmd:
            self.cooldown_until = now + COOLDOWN
            self.hist.clear()
            self.last = cmd
        return cmd

    # ------------------------------------------------------------------ swipe
    def _window(self, seconds: float):
        now = self.hist[-1][0]
        return [s for s in self.hist if now - s[0] <= seconds]

    def _swipe(self, sens: float) -> Optional[Command]:
        w = self._window(SWIPE_WINDOW)
        if len(w) < 3:
            return None
        dt = w[-1][0] - w[0][0]
        dx, dy = w[-1][1] - w[0][1], w[-1][2] - w[0][2]
        dist = math.hypot(dx, dy)
        if dt < 0.1 or dist < SWIPE_DIST / sens or dist / dt < SWIPE_SPEED / sens:
            return None
        path = sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(w, w[1:]))
        if path <= 0 or dist / path < SWIPE_STRAIGHT:
            return None
        if abs(dx) >= SWIPE_AXIS * abs(dy):
            return Command.SWIPE_RIGHT if dx > 0 else Command.SWIPE_LEFT
        if abs(dy) >= SWIPE_AXIS * abs(dx):
            return Command.SWIPE_DOWN if dy > 0 else Command.SWIPE_UP  # image y grows downward
        return None

    # ------------------------------------------------------------------- wave
    def _wave(self) -> Optional[Command]:
        xs = [s[1] for s in self.hist]
        ys = [s[2] for s in self.hist]
        if len(xs) < 6 or max(ys) - min(ys) > 1.2:
            return None
        series, mode, hi, lo = [xs[0]], None, xs[0], xs[0]
        for x in xs[1:]:
            hi, lo = max(hi, x), min(lo, x)
            if mode in (None, "up") and hi - x >= WAVE_MIN:
                series.append(hi); mode, hi, lo = "down", x, x
            elif mode in (None, "down") and x - lo >= WAVE_MIN:
                series.append(lo); mode, hi, lo = "up", x, x
        swings = [abs(b - a) for a, b in zip(series, series[1:])]
        if len(swings) >= WAVE_SWINGS and all(WAVE_MIN <= a <= WAVE_MAX for a in swings[-WAVE_SWINGS:]):
            return Command.WAVE
        return None

    # ------------------------------------------------------------------ twist
    def _twist(self, sens: float) -> Optional[Command]:
        w = self._window(TWIST_WINDOW)
        if len(w) < 3:
            return None
        dt = w[-1][0] - w[0][0]
        dtheta = math.degrees(w[-1][3] - w[0][3])
        drift = math.hypot(w[-1][1] - w[0][1], w[-1][2] - w[0][2])
        if dt < 0.1 or drift > TWIST_DRIFT or abs(dtheta) < TWIST_DEG / sens or abs(dtheta) / dt < TWIST_SPEED / sens:
            return None
        return Command.TWIST_CW if dtheta > 0 else Command.TWIST_CCW


def hand_tilt(pts: np.ndarray, w: int, h: int) -> float:
    """Tilt of the hand axis (wrist -> middle knuckle) in radians; 0 = upright, + = clockwise on screen."""
    dx = (pts[9][0] - pts[0][0]) * w
    dy = (pts[9][1] - pts[0][1]) * h
    return math.atan2(dx, -dy)
