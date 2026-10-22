"""User settings, stored as JSON in the platform config directory."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .gestures import (DEFAULT_COMMANDS, DEFAULT_MAPPING, ONE_SHOT_ACTIONS, Action, Command, Gesture)


def config_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "aircursor"


CONFIG_PATH = config_dir() / "config.json"

# key, label, min, max, step, unit/format, help text  (drives the Settings page)
SLIDERS = [
    ("speed", "Pointer speed", 0.3, 3.0, 0.05, "{:.2f}×",
     "How far the cursor travels for a given hand movement. Hand-size aware, so it feels the same near or far from the camera."),
    ("accel_strength", "Speed-up on fast moves", 0.0, 2.0, 0.05, "{:.2f}",
     "Optional. Move fast and the cursor travels extra far. 0 = off: the cursor follows your hand 1:1."),
    ("long_move_boost", "Long-reach boost", 0.0, 2.0, 0.05, "{:.2f}",
     "Optional. Keep moving in one direction and the cursor gets faster, for reaching corners. 0 = off."),
    ("smoothing", "Smoothing", 0.0, 1.0, 0.05, "{:.0%}",
     "Higher = steadier cursor, slightly more lag. Lower = snappier but shakier."),
    ("hold_scale", "Gesture confirmation time", 0.5, 2.5, 0.1, "{:.1f}×",
     "How long a gesture must be held steadily before it counts. Raise it if you get accidental actions."),
    ("command_sensitivity", "Motion command sensitivity", 0.5, 2.0, 0.1, "{:.1f}×",
     "How easily swipes, waves and twists trigger. Raise it if they are hard to trigger; lower it if they fire by accident."),
    ("hook_sensitivity", "C-shape sensitivity", 0.6, 1.5, 0.05, "{:.2f}",
     "How much the index finger must bend for the C-shape. Higher = a wider range of bends counts."),
    ("pinch_sensitivity", "Pinch sensitivity", 0.6, 1.5, 0.05, "{:.2f}",
     "Higher = a looser pinch counts as a click."),
    ("tuck_sensitivity", "Thumb-tuck sensitivity", 0.6, 1.5, 0.05, "{:.2f}",
     "Higher = the thumb doesn't have to tuck as far."),
    ("scroll_speed", "Scroll speed", 0.3, 3.0, 0.1, "{:.1f}×", "How fast the page slides."),
    ("volume_step", "Volume per circle", 5, 25, 1, "{:.0f}%", "Volume change for one full finger circle."),
]

TOGGLES = [
    ("motion_commands", "Motion commands (swipe / wave / twist)",
     "Flick, wave or twist an open palm to trigger shortcuts like Alt+Tab. Configure them on the Gestures page."),
    ("smart_motion", "Smart motion (speed-up + long-reach boost)",
     "Master switch for the two optional boosts above. They are 0 (off) by default."),
    ("mirror", "Mirror image", "Show the camera like a mirror (recommended for webcams)."),
    ("guard_enabled", "Safety guard (auto-pause on click storms)",
     "If the app suddenly sees many clicks in a few seconds, it pauses itself."),
    ("float_widget", "Floating panic button (always on top)",
     "A small always-visible control with Pause and Quit."),
    ("start_paused", "Start paused",
     "Open the app with control paused. Press Resume when you are ready."),
]


@dataclass
class Config:
    # pointer
    speed: float = 1.0
    smart_motion: bool = True
    accel_strength: float = 0.0        # off by default: cursor follows the hand 1:1 (opt-in)
    long_move_boost: float = 0.0       # off by default (opt-in)
    smoothing: float = 0.5
    # recognition
    hold_scale: float = 1.0
    hook_sensitivity: float = 1.0
    command_sensitivity: float = 1.0
    motion_commands: bool = True
    pinch_sensitivity: float = 1.0
    tuck_sensitivity: float = 1.0
    # actions
    scroll_speed: float = 1.0
    volume_step: float = 10
    gestures: dict = field(default_factory=lambda: {g.value: a.value for g, a in DEFAULT_MAPPING.items()})
    commands: dict = field(default_factory=lambda: {c.value: a.value for c, a in DEFAULT_COMMANDS.items()})
    # camera
    camera_source: str = "auto"        # "auto" | "local:<index>" | "url"
    phone_url: str = ""                # e.g. https://192.168.1.50:8080/video
    mirror: bool = True
    # safety
    guard_enabled: bool = True
    guard_clicks: int = 6              # button presses ...
    guard_window: float = 2.0          # ... within this many seconds trips the guard
    float_widget: bool = True
    start_paused: bool = False
    float_pos: list = field(default_factory=lambda: [-1, -1])
    # misc
    first_run: bool = True
    config_version: int = 2            # bump when defaults change in a way old files must pick up

    # -- helpers -------------------------------------------------------------
    def action_for(self, gesture: Gesture) -> Action:
        try:
            return Action(self.gestures.get(gesture.value, DEFAULT_MAPPING.get(gesture, Action.NONE).value))
        except ValueError:
            return Action.NONE

    def command_action(self, command: Command) -> Action:
        try:
            a = Action(self.commands.get(command.value, DEFAULT_COMMANDS.get(command, Action.NONE).value))
        except ValueError:
            return Action.NONE
        return a if a in ONE_SHOT_ACTIONS else Action.NONE

    def clamp(self) -> "Config":
        for key, _l, lo, hi, _s, _f, _h in SLIDERS:
            setattr(self, key, min(max(float(getattr(self, key)), lo), hi))
        known = {g.value for g in DEFAULT_MAPPING}
        merged = {g.value: a.value for g, a in DEFAULT_MAPPING.items()}
        for k, v in (self.gestures or {}).items():
            if k in known and v in {a.value for a in Action}:
                merged[k] = v
        self.gestures = merged
        cmds = {c.value: a.value for c, a in DEFAULT_COMMANDS.items()}
        valid = {a.value for a in ONE_SHOT_ACTIONS} | {Action.NONE.value}
        for k, v in (self.commands or {}).items():
            if k in cmds and v in valid:
                cmds[k] = v
        self.commands = cmds
        return self

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2))
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        cfg = cls()
        try:
            data = json.loads(path.read_text())
            names = {f.name for f in fields(cls)}
            for k, v in data.items():
                if k in names:
                    setattr(cfg, k, v)
            if data.get("config_version", 1) < 2:
                # v1 shipped with speed-up + long-reach boost ON, which made fast moves lag and overshoot.
                cfg.accel_strength = cfg.long_move_boost = 0.0
                cfg.config_version = 2
        except FileNotFoundError:
            pass
        except (ValueError, OSError):
            pass  # corrupt file: fall back to defaults rather than crash
        return cfg.clamp()

    def reset_to_defaults(self) -> None:
        keep = (self.camera_source, self.phone_url, self.first_run, self.float_pos)
        fresh = Config()
        for f in fields(self):
            setattr(self, f.name, getattr(fresh, f.name))
        self.camera_source, self.phone_url, self.first_run, self.float_pos = keep
