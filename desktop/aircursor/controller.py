"""Turns a stream of hand poses into mouse actions.

Safety design (everything here exists because hands shake and cameras glitch):

* **Confirmation** - a new gesture must persist for a short time (and at least
  two frames) before it replaces the current one. Single-frame glitches never act.
* **Freeze while uncertain** - while a different gesture is being confirmed the
  cursor holds still, so pinching doesn't drag the cursor off its target.
* **Dropout tolerance** - a hand briefly lost during a drag keeps the button held;
  a hand missing for 0.3 s releases everything.
* **Pause / panic** - ``pause()`` instantly releases every button and drops queued
  cursor motion. Nothing acts while paused.
* **Click-storm guard** - too many button presses in a short window means the
  camera is misreading fingers: auto-pause.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Callable, Optional

import numpy as np

from .config import Config
from .backends.keyboard import Keyboard, NullKeyboard
from .commands import CommandDetector, hand_tilt
from .gestures import (ACTION_INFO, Action, BUTTON_ACTIONS, COMMAND_INFO, Command, Gesture,
                       ONE_SHOT_ACTIONS, POINTING_ACTIONS, Pose, PoseClassifier, SHORTCUTS, palm_point)
from .motion import Dial, OneEuro, SmartMotion

CONFIRM = {Action.MOVE: 0.10, Action.LEFT: 0.10, Action.RIGHT: 0.15, Action.MIDDLE: 0.15,
           Action.SCROLL: 0.12, Action.FAST_SCROLL: 0.12, Action.VOLUME: 0.25, Action.NONE: 0.10}
NO_HAND_CONFIRM = 0.30
MIN_FRAMES = 2
CLICK_FREEZE = 0.15   # s the cursor stays put right after a button goes down
HOLD_LABEL = 0.35     # s after which a held button is called a drag
SCROLL_PER_HAND = 4.0  # wheel notches per hand-length of motion at scroll speed 1.0
SCROLL_DEADZONE = 0.03
FAST_SCROLL = 3
BUTTON_NAME = {Action.LEFT: "left", Action.RIGHT: "right", Action.MIDDLE: "middle"}
CLICK_WORD = {Action.LEFT: "LEFT", Action.RIGHT: "RIGHT", Action.MIDDLE: "MIDDLE"}


class Controller:
    def __init__(self, cfg: Config, mouse, volume, keyboard: Optional[Keyboard] = None,
                 on_trip: Optional[Callable[[str], None]] = None):
        self.cfg, self.mouse, self.volume = cfg, mouse, volume
        self.keyboard = keyboard or NullKeyboard()
        self.commands = CommandDetector()
        self.last_command = ("", 0.0)   # (command id, time) for the UI
        self.on_trip = on_trip
        self.classifier = PoseClassifier()
        self.fx, self.fy = OneEuro(), OneEuro()
        self.motion = SmartMotion()
        self.dial = Dial()
        self.paused = False
        self.pause_reason = ""
        self.press_times: deque = deque()
        self.pose: Optional[Pose] = None
        self._reset_state(time.time())

    # ------------------------------------------------------------------ state
    def _reset_state(self, now: float):
        self.stable, self.since = Gesture.NONE, now
        self.cand, self.cand_t, self.cand_n = None, 0.0, 0
        self.raw = Gesture.NONE
        self.freeze_until = 0.0
        self.flash = ("", 0.0)
        self.prev_pt, self.prev_t = None, now
        self.scroll_prev = None
        self.scroll_acc = np.zeros(2)
        self.slide_axis = ""
        self.vol = 0.5
        self.fx.reset(); self.fy.reset()
        self.motion.reset(); self.dial.reset(); self.commands.reset()

    def pause(self, reason: str = "") -> None:
        """Instant stop: release every button and drop queued cursor motion."""
        self.paused, self.pause_reason = True, reason
        self.mouse.release_all()
        self.mouse.cancel_motion()
        self._reset_state(time.time())

    def resume(self) -> None:
        self.paused, self.pause_reason = False, ""
        self.press_times.clear()
        self._reset_state(time.time())

    def shutdown(self) -> None:
        self.mouse.release_all()
        self.mouse.cancel_motion()

    # -------------------------------------------------------------- confirmation
    @property
    def action(self) -> Action:
        return Action.NONE if self.stable == Gesture.NONE else self.cfg.action_for(self.stable)

    def _confirm_time(self, g: Gesture) -> float:
        if g == Gesture.NONE:
            return NO_HAND_CONFIRM
        return CONFIRM.get(self.cfg.action_for(g), 0.20) * self.cfg.hold_scale

    def cand_progress(self, now: float) -> Optional[float]:
        if self.cand is None:
            return None
        return min((now - self.cand_t) / self._confirm_time(self.cand), 1.0)

    def _advance(self, raw: Gesture, now: float) -> None:
        self.raw = raw
        if raw == self.stable:
            self.cand = None
            return
        if raw != self.cand:
            self.cand, self.cand_t, self.cand_n = raw, now, 1
        else:
            self.cand_n += 1
        if now - self.cand_t >= self._confirm_time(raw) and self.cand_n >= MIN_FRAMES:
            self._switch(raw, now)

    def _switch(self, new: Gesture, now: float) -> None:
        old_action = self.action
        held = now - self.since
        if old_action in BUTTON_ACTIONS:
            self.mouse.button(BUTTON_NAME[old_action], False)
            if held < HOLD_LABEL:
                self.flash = (f"{CLICK_WORD[old_action]} CLICK", now + 0.4)
        self.stable, self.since, self.cand = new, now, None
        new_action = self.action
        if new_action in BUTTON_ACTIONS:
            self.mouse.button(BUTTON_NAME[new_action], True)
            self.freeze_until = now + CLICK_FREEZE
            self._record_press(now)
        elif new_action == Action.VOLUME:
            self.vol = self.volume.get()
            self.dial.reset()
        elif new_action in ONE_SHOT_ACTIONS:
            self._shortcut(new_action, now)
        self.scroll_prev = None

    @staticmethod
    def short_label(action: Action) -> str:
        return ACTION_INFO[action].split(" (")[0]

    def _shortcut(self, action: Action, now: float, prefix: str = "") -> None:
        """Fire a keyboard shortcut once. Counts toward the click-storm guard."""
        self.keyboard.chord(SHORTCUTS[action][1])
        self.flash = (f"{prefix}{self.short_label(action).upper()}", now + 0.9)
        self._record_press(now)

    def _record_press(self, now: float) -> None:
        cfg = self.cfg
        self.press_times.append(now)
        while self.press_times and now - self.press_times[0] > cfg.guard_window:
            self.press_times.popleft()
        if cfg.guard_enabled and len(self.press_times) >= cfg.guard_clicks:
            reason = f"Safety guard: {len(self.press_times)} clicks in {cfg.guard_window:.0f}s"
            self.pause(reason)
            if self.on_trip:
                self.on_trip(reason)

    # ------------------------------------------------------------------ frames
    def lost(self, now: float) -> str:
        """No hand in view this frame."""
        self.pose = None
        self.prev_pt = None
        self.fx.reset(); self.fy.reset()
        self.commands.update(now, np.zeros(2), 1.0, 0.0, False)  # lets the history time out
        if self.paused:
            return self.label(now)
        self._advance(Gesture.NONE, now)
        return self.label(now)

    def update(self, pts: np.ndarray, w: int, h: int, now: float, world: Optional[np.ndarray] = None) -> str:
        cfg = self.cfg
        pose = self.pose = self.classifier.classify(
            pts, w, h, self.stable, cfg.pinch_sensitivity, cfg.tuck_sensitivity, cfg.hook_sensitivity, world)
        if self.paused:
            return self.label(now)
        self._advance(pose.gesture, now)
        if cfg.motion_commands:
            cmd = self.commands.update(now, palm_point(pts) * (w, h), pose.motion_size, hand_tilt(pts, w, h),
                                       pose.gesture == Gesture.OPEN, cfg.command_sensitivity)
            if cmd:
                self._run_command(cmd, now)
            if self.paused:  # a command can trip the click-storm guard
                return self.label(now)

        cutoff = 0.4 + 2.0 * (1 - cfg.smoothing)
        self.fx.min_cutoff = self.fy.min_cutoff = cutoff
        ptr = palm_point(pts) * (w, h)
        fp = np.array([self.fx(float(ptr[0]), now), self.fy(float(ptr[1]), now)])
        active = self.raw == self.stable  # a pending gesture change freezes the action
        act = self.action

        if act in POINTING_ACTIONS and active and now >= self.freeze_until and self.prev_pt is not None:
            d = self.motion.map(fp - self.prev_pt, now - self.prev_t, pose.motion_size, cfg)
            if d.any():
                self.mouse.move_rel(float(d[0]), float(d[1]))
        if act in (Action.SCROLL, Action.FAST_SCROLL) and active:
            self._slide(fp, pose.motion_size, FAST_SCROLL if act == Action.FAST_SCROLL else 1)
        else:
            self.scroll_prev = None
        if act == Action.VOLUME and active:
            turns = self.dial.update(pts[8] * (w, h), pose.size)
            if turns:
                self.vol = min(max(self.vol + cfg.volume_step / 100 * turns, 0.0), 1.0)
                self.volume.set(self.vol)

        self.prev_pt, self.prev_t = fp, now
        return self.label(now)

    def _run_command(self, cmd: Command, now: float) -> None:
        action = self.cfg.command_action(cmd)
        if action != Action.NONE:
            self.last_command = (cmd.value, now)
            self._shortcut(action, now, prefix=f"{COMMAND_INFO[cmd][1].upper()} → ")

    def _slide(self, fp: np.ndarray, size: float, speed: int) -> None:
        """Scroll along whichever axis the hand is mostly moving on."""
        self.slide_axis = ""
        if self.scroll_prev is not None:
            d = (fp - self.scroll_prev) / size
            if abs(d).max() > SCROLL_DEADZONE:
                axis = int(abs(d[1]) > abs(d[0]))
                self.scroll_acc[axis] += (d[0] if axis == 0 else -d[1]) * SCROLL_PER_HAND \
                    * self.cfg.scroll_speed * speed
                self.slide_axis = " ⇄" if axis == 0 else " ⇅"
            for axis in (0, 1):
                n = int(self.scroll_acc[axis])
                if n:
                    self.mouse.scroll(n, horizontal=(axis == 0))
                    self.scroll_acc[axis] -= n
        self.scroll_prev = fp.copy()

    # ------------------------------------------------------------------- label
    def label(self, now: float) -> str:
        if self.paused:
            return "PAUSED"
        st, act = self.stable, self.action
        if st == Gesture.NONE:
            return self.flash[0] if now < self.flash[1] else "NO HAND"
        if act not in BUTTON_ACTIONS and now < self.flash[1]:
            return self.flash[0]
        held = now - self.since
        if act in BUTTON_ACTIONS:
            word = CLICK_WORD[act]
            return f"{word} HOLD (drag)" if held > HOLD_LABEL else f"{word} CLICK"
        return {
            Action.MOVE: "MOVE",
            Action.SCROLL: "SLIDE" + self.slide_axis,
            Action.FAST_SCROLL: "FAST SLIDE" + self.slide_axis,
            Action.VOLUME: f"VOLUME {round(self.vol * 100)}%",
            Action.NONE: "IDLE",
        }.get(act) or self.short_label(act).upper()
