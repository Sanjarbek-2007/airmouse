"""Hand pose classification and the gesture / action vocabulary.

A *gesture* is something your hand does (point, pinch, fist...). An *action* is
what the computer does about it (move the cursor, left button, scroll...). The
user can map any gesture to any action; the defaults are the ones that were
tuned to be comfortable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np


class Gesture(str, Enum):
    POINT = "point"
    PINCH = "pinch"
    TUCK = "tuck"
    PEACE = "peace"
    THREE = "three"
    ROCK = "rock"
    HOOK = "hook"      # "C" shape: index finger half-bent
    FIST = "fist"
    OPEN = "open"
    NONE = "none"  # no hand in view


class Action(str, Enum):
    NONE = "none"
    MOVE = "move"
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    SCROLL = "scroll"
    FAST_SCROLL = "fast_scroll"
    VOLUME = "volume"
    # One-shot keyboard shortcuts (fire once when the gesture / command is recognised)
    WINDOW_NEXT = "window_next"
    WINDOW_PREV = "window_prev"
    OVERVIEW = "overview"
    SHOW_DESKTOP = "show_desktop"
    WORKSPACE_NEXT = "workspace_next"
    WORKSPACE_PREV = "workspace_prev"
    BROWSER_BACK = "browser_back"
    BROWSER_FORWARD = "browser_forward"
    TAB_NEXT = "tab_next"
    TAB_PREV = "tab_prev"
    COPY = "copy"
    PASTE = "paste"
    UNDO = "undo"
    PLAY_PAUSE = "play_pause"
    NEXT_TRACK = "next_track"
    PREV_TRACK = "prev_track"
    MUTE = "mute"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    SCREENSHOT = "screenshot"
    MAXIMIZE = "maximize"
    CLOSE_WINDOW = "close_window"


class Command(str, Enum):
    """Motion commands: things your hand *does* (as opposed to poses it *holds*)."""
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    WAVE = "wave"
    TWIST_CW = "twist_cw"
    TWIST_CCW = "twist_ccw"


# key names are backend-neutral; each keyboard backend translates them
SHORTCUTS: dict = {
    Action.WINDOW_NEXT: ("Next window (Alt+Tab)", ("alt", "tab")),
    Action.WINDOW_PREV: ("Previous window (Alt+Shift+Tab)", ("alt", "shift", "tab")),
    Action.OVERVIEW: ("Overview / Start menu (Super)", ("super",)),
    Action.SHOW_DESKTOP: ("Show desktop (Super+D)", ("super", "d")),
    Action.WORKSPACE_NEXT: ("Next workspace (Ctrl+Alt+→)", ("ctrl", "alt", "right")),
    Action.WORKSPACE_PREV: ("Previous workspace (Ctrl+Alt+←)", ("ctrl", "alt", "left")),
    Action.BROWSER_BACK: ("Back (Alt+←)", ("alt", "left")),
    Action.BROWSER_FORWARD: ("Forward (Alt+→)", ("alt", "right")),
    Action.TAB_NEXT: ("Next tab (Ctrl+Tab)", ("ctrl", "tab")),
    Action.TAB_PREV: ("Previous tab (Ctrl+Shift+Tab)", ("ctrl", "shift", "tab")),
    Action.COPY: ("Copy (Ctrl+C)", ("ctrl", "c")),
    Action.PASTE: ("Paste (Ctrl+V)", ("ctrl", "v")),
    Action.UNDO: ("Undo (Ctrl+Z)", ("ctrl", "z")),
    Action.PLAY_PAUSE: ("Play / pause media", ("playpause",)),
    Action.NEXT_TRACK: ("Next track", ("nexttrack",)),
    Action.PREV_TRACK: ("Previous track", ("prevtrack",)),
    Action.MUTE: ("Mute", ("mute",)),
    Action.VOLUME_UP: ("Volume up", ("volup",)),
    Action.VOLUME_DOWN: ("Volume down", ("voldown",)),
    Action.SCREENSHOT: ("Screenshot (Print Screen)", ("prtsc",)),
    Action.MAXIMIZE: ("Maximise window (Super+↑)", ("super", "up")),
    Action.CLOSE_WINDOW: ("Close window (Alt+F4)", ("alt", "f4")),
}
ONE_SHOT_ACTIONS = tuple(SHORTCUTS)


# Actions that also move the cursor while active (so a button can be dragged).
POINTING_ACTIONS = (Action.MOVE, Action.LEFT, Action.RIGHT, Action.MIDDLE)
BUTTON_ACTIONS = (Action.LEFT, Action.RIGHT, Action.MIDDLE)

DEFAULT_MAPPING = {
    Gesture.POINT: Action.MOVE,
    Gesture.PINCH: Action.LEFT,
    Gesture.TUCK: Action.RIGHT,
    Gesture.PEACE: Action.SCROLL,
    Gesture.THREE: Action.FAST_SCROLL,
    Gesture.ROCK: Action.VOLUME,
    Gesture.HOOK: Action.MIDDLE,
    Gesture.FIST: Action.NONE,
    Gesture.OPEN: Action.NONE,
}

DEFAULT_COMMANDS = {
    Command.SWIPE_RIGHT: Action.WINDOW_NEXT,
    Command.SWIPE_LEFT: Action.WINDOW_PREV,
    Command.SWIPE_UP: Action.OVERVIEW,
    Command.SWIPE_DOWN: Action.SHOW_DESKTOP,
    Command.WAVE: Action.PLAY_PAUSE,
    Command.TWIST_CW: Action.WORKSPACE_NEXT,
    Command.TWIST_CCW: Action.WORKSPACE_PREV,
}

COMMAND_INFO = {
    Command.SWIPE_RIGHT: ("👉", "Swipe right", "Open palm, flick your hand quickly to the right."),
    Command.SWIPE_LEFT: ("👈", "Swipe left", "Open palm, flick your hand quickly to the left."),
    Command.SWIPE_UP: ("👆", "Swipe up", "Open palm, flick your hand quickly upward."),
    Command.SWIPE_DOWN: ("👇", "Swipe down", "Open palm, flick your hand quickly downward."),
    Command.WAVE: ("👋", "Wave", "Open palm, wave side to side three times."),
    Command.TWIST_CW: ("↻", "Twist clockwise", "Open palm, tilt your hand to the right (like turning a knob)."),
    Command.TWIST_CCW: ("↺", "Twist counter-clockwise", "Open palm, tilt your hand to the left."),
}

GESTURE_INFO = {
    Gesture.POINT: ("☝️", "Point", "Raise only your index finger. Move your hand to move the cursor."),
    Gesture.PINCH: ("🤏", "Pinch", "Touch thumb tip to index tip, other fingers open. Quick = click, hold and move = drag."),
    Gesture.TUCK: ("🖐️", "Thumb tuck", "Open hand, then fold your thumb into your palm (the “signal for help” pose)."),
    Gesture.PEACE: ("✌️", "Peace", "Index and middle finger up, ring and pinky down."),
    Gesture.THREE: ("🤟", "Three fingers", "Index, middle and ring finger up, pinky down."),
    Gesture.ROCK: ("🤘", "Rock sign", "Index and pinky up, middle and ring down."),
    Gesture.HOOK: ("🪝", "C-shape", "Bend your index finger halfway, like a hook or a “C”. Other fingers curled."),
    Gesture.FIST: ("✊", "Fist", "Close your whole hand."),
    Gesture.OPEN: ("✋", "Open palm", "All fingers open. The natural “resting” pose, like lifting a mouse."),
}

ACTION_INFO = {
    Action.NONE: "Do nothing",
    Action.MOVE: "Move cursor",
    Action.LEFT: "Left button (click / drag)",
    Action.RIGHT: "Right button (click / drag)",
    Action.MIDDLE: "Middle button (click / drag)",
    Action.SCROLL: "Scroll (move hand up/down/left/right)",
    Action.FAST_SCROLL: "Fast scroll (3x)",
    Action.VOLUME: "Volume dial (circle your fingertip)",
    **{a: label for a, (label, _keys) in SHORTCUTS.items()},
}

TIPS, PIPS = (8, 12, 16, 20), (6, 10, 14, 18)
CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9),
               (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
               (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]

# Base thresholds (scaled by the user's sensitivity settings)
PINCH_ON, PINCH_OFF = 0.30, 0.42   # thumb-index distance / hand size
TUCK_ON, TUCK_OFF = 0.55, 0.75     # thumb-to-knuckles distance / hand size (low = tucked)
# C-shape: bend of the index finger's middle joint (PIP), degrees. 180 = straight, small = tightly curled.
HOOK_MIN, HOOK_MAX = 100.0, 150.0
HOOK_HYST = 10.0                   # extra tolerance once already in the shape


@dataclass
class Pose:
    gesture: Gesture
    size: float          # wrist -> middle knuckle, camera pixels
    motion_size: float   # steadier hand scale used to normalise motion
    pinch: float         # thumb-index distance / size  (meter for the UI)
    tuck: float          # thumb-to-knuckle distance / size
    bend: float = 180.0  # index PIP angle in degrees (meter for the UI)


def palm_point(pts: np.ndarray) -> np.ndarray:
    """Stable pointer anchor (index + middle knuckles): doesn't move when fingers curl."""
    return (pts[5] + pts[9]) / 2


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle at b (degrees) between the segments b->a and b->c."""
    u, v = a - b, c - b
    n = float(np.linalg.norm(u) * np.linalg.norm(v))
    if n < 1e-9:
        return 180.0
    return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / n, -1.0, 1.0))))


class PoseClassifier:
    """Turns 21 hand landmarks into a Gesture. Keeps per-finger hysteresis so a
    finger sitting on the edge of "extended" doesn't flicker frame to frame."""

    def __init__(self):
        self.ext = [False] * 4

    def classify(self, pts: np.ndarray, w: int, h: int, current: Gesture,
                 pinch_sens: float = 1.0, tuck_sens: float = 1.0, hook_sens: float = 1.0,
                 world: Optional[np.ndarray] = None) -> Pose:
        """pts: (21,2) normalised image landmarks. world: optional (21,3) metric hand-space
        landmarks (orientation-independent; used for finger-bend angles)."""
        px = pts * (w, h)
        dist = lambda a, b: float(np.linalg.norm(px[a] - px[b]))
        size = max(dist(0, 9), 1.0)
        motion_size = max((dist(0, 9) + dist(5, 17)) / 2, 1.0)
        for i, (t, p) in enumerate(zip(TIPS, PIPS)):
            ratio = dist(t, 0) / max(dist(p, 0), 1.0)
            self.ext[i] = ratio > (1.0 if self.ext[i] else 1.15)
        idx, mid, ring, pinky = self.ext
        pinch = dist(4, 8) / size
        tuck = min(dist(4, 9), dist(4, 13), dist(4, 17)) / size
        # index bend (PIP joint angle); world coordinates make it independent of hand orientation
        geo = world if world is not None else px
        bend = joint_angle(geo[5], geo[6], geo[7])
        spread = 30.0 * (hook_sens - 1.0)
        lo = HOOK_MIN - spread - (HOOK_HYST if current == Gesture.HOOK else 0.0)
        hi = HOOK_MAX + spread + (HOOK_HYST if current == Gesture.HOOK else 0.0)
        pinch_thr = (PINCH_OFF if current == Gesture.PINCH else PINCH_ON) * pinch_sens
        tuck_thr = (TUCK_OFF if current == Gesture.TUCK else TUCK_ON) * tuck_sens

        if not (mid or ring or pinky) and lo <= bend <= hi and pinch >= pinch_thr:
            g = Gesture.HOOK  # half-bent index, others curled: checked before FIST
        elif not any(self.ext):
            g = Gesture.FIST  # checked first: a fist can never count as a pinch
        elif pinch < pinch_thr:
            g = Gesture.PINCH
        elif all(self.ext) and tuck < tuck_thr:
            g = Gesture.TUCK
        elif idx and pinky and not mid and not ring:
            g = Gesture.ROCK
        elif idx and mid and ring and not pinky:
            g = Gesture.THREE
        elif idx and mid and not ring and not pinky:
            g = Gesture.PEACE
        elif idx and not mid:
            g = Gesture.POINT
        else:
            g = Gesture.OPEN
        return Pose(g, size, motion_size, pinch, tuck, bend)
