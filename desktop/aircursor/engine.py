"""The recognition loop: camera -> hand tracking -> controller, in a background thread.

The GUI and the headless CLI both drive this class and only differ in what they do
with the ``on_frame`` / ``on_state`` / ``on_event`` callbacks.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

import cv2
import numpy as np

from .backends import MouseUnavailable, NullKeyboard, NullMouse, Volume, create_keyboard, create_mouse
from .camera import FrameSource, open_source
from .config import Config
from .controller import Controller
from .gestures import BUTTON_ACTIONS, Action, Gesture
from .overlay import draw_hand
from .tracker import HandTracker


@dataclass
class EngineState:
    status: str = "starting"        # starting | connecting | running | no_camera | error
    message: str = ""               # human readable detail for the status line
    source: str = ""                # name of the camera in use
    live: bool = False              # False = dry run (detect only)
    label: str = ""                 # big command text ("LEFT CLICK", "MOVE"...)
    gesture: str = Gesture.NONE.value
    raw_gesture: str = Gesture.NONE.value
    action: str = Action.NONE.value
    pending: Optional[str] = None   # gesture being confirmed
    progress: float = 0.0           # 0..1 confirmation progress
    pinch: float = 1.0
    tuck: float = 1.0
    bend: float = 180.0
    volume: float = 0.0
    factor: float = 1.0             # current smart-motion gain multiplier
    fps: float = 0.0
    hand: bool = False
    command: str = ""              # last motion command fired ...
    command_at: float = 0.0         # ... and when (epoch seconds)
    paused: bool = False
    pause_reason: str = ""
    warning: str = ""


class Engine:
    def __init__(self, cfg: Config, live: bool = True,
                 on_frame: Optional[Callable[[np.ndarray, EngineState], None]] = None,
                 on_state: Optional[Callable[[EngineState], None]] = None,
                 on_event: Optional[Callable[[str], None]] = None):
        self.cfg, self.live = cfg, live
        self.on_frame, self.on_state, self.on_event = on_frame, on_state, on_event
        self.state = EngineState(live=live)
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._reopen = threading.Event()
        self._want_paused = False
        self._want_reason = ""
        self._mouse = NullMouse()
        self._keyboard = NullKeyboard()
        self._ctl: Optional[Controller] = None

    # ----------------------------------------------------------------- control
    def start(self):
        self._thread = threading.Thread(target=self._run, name="aircursor-engine", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._mouse.release_all()  # immediately, even if the loop is mid-frame
        self._mouse.cancel_motion()
        if self._thread:
            self._thread.join(timeout=3)

    def restart_source(self):
        """Call after the camera setting changed."""
        self._reopen.set()

    def pause(self, reason: str = "Paused"):
        """Instant stop, safe to call from any thread (UI, hotkey, signal handler)."""
        self._want_reason, self._want_paused = reason, True
        self._mouse.release_all()
        self._mouse.cancel_motion()
        self.state.paused, self.state.pause_reason = True, reason

    def resume(self):
        self._want_paused = False
        self.state.paused, self.state.pause_reason = False, ""

    def toggle_pause(self) -> bool:
        """Returns True if now paused."""
        if self._want_paused:
            self.resume()
        else:
            self.pause("Paused by you")
        return self._want_paused

    @property
    def paused(self) -> bool:
        return self._want_paused

    # -------------------------------------------------------------------- loop
    def _emit_state(self):
        if self.on_state:
            self.on_state(EngineState(**asdict(self.state)))

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self.state, k, v)

    def _on_trip(self, reason: str):
        self._want_paused, self._want_reason = True, reason
        if self.on_event:
            self.on_event(reason)

    def _run(self):
        st = self.state
        try:
            self._mouse = create_mouse(self.live)
            self._keyboard = create_keyboard(self.live)
        except MouseUnavailable as e:
            self._mouse, self._keyboard = NullMouse(), NullKeyboard()
            self.live = st.live = False
            st.warning = str(e)
        volume = Volume(self.live)
        self._set(status="starting", message="Loading hand model…")
        self._emit_state()
        try:
            tracker = HandTracker(progress=lambda m: (self._set(message=m), self._emit_state()))
        except Exception as e:
            self._set(status="error", message=f"Could not load the hand model: {e}")
            self._emit_state()
            return
        ctl = self._ctl = Controller(self.cfg, self._mouse, volume, self._keyboard, on_trip=self._on_trip)
        src: Optional[FrameSource] = None
        last_seq, last_label, fps, t_prev, last_emit = -1, "", 0.0, time.time(), 0.0
        try:
            while not self._stop.is_set():
                if src is None or self._reopen.is_set():
                    self._reopen.clear()
                    if src:
                        src.stop()
                    self._set(status="connecting", message="Opening camera…", source="")
                    self._emit_state()
                    src = open_source(self.cfg)
                    last_seq = -1
                    if src is None:
                        self._set(status="no_camera", message=(
                            "No camera found. Plug in a webcam, or set up a phone stream on the Camera page."))
                        self._emit_state()
                        self._reopen.wait(1.0)
                        continue
                    self._set(source=src.name)

                frame, seq = src.latest()
                if frame is None or seq == last_seq:
                    now = time.time()
                    if src.error:
                        self._set(status="connecting", message=src.error)
                    if now - last_emit > 0.25:
                        self._emit_state(); last_emit = now
                    time.sleep(0.004)
                    continue
                last_seq = seq
                now = time.time()
                fps = 0.9 * fps + 0.1 / max(now - t_prev, 1e-3) if fps else 1 / max(now - t_prev, 1e-3)
                t_prev = now

                if self.cfg.mirror:
                    frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                pts, world = tracker.detect(frame)

                if self._want_paused and not ctl.paused:
                    ctl.pause(self._want_reason)
                elif not self._want_paused and ctl.paused:
                    ctl.resume()
                if ctl.paused and not self._want_paused:  # the guard tripped inside the controller
                    self._want_paused, self._want_reason = True, ctl.pause_reason

                label = ctl.update(pts, w, h, now, world) if pts is not None else ctl.lost(now)
                if label != last_label and self.on_event:
                    self.on_event(label)
                last_label = label

                pose = ctl.pose
                st.status, st.message = "running", ""
                st.label, st.gesture, st.raw_gesture = label, ctl.stable.value, ctl.raw.value
                st.action = ctl.action.value
                st.pending = ctl.cand.value if ctl.cand else None
                st.progress = ctl.cand_progress(now) or 0.0
                st.pinch, st.tuck = (pose.pinch, pose.tuck) if pose else (1.0, 1.0)
                st.bend = pose.bend if pose else 180.0
                st.command, st.command_at = ctl.last_command
                st.volume, st.factor, st.fps = ctl.vol, ctl.motion.factor, fps
                st.hand, st.paused, st.pause_reason = pts is not None, ctl.paused, ctl.pause_reason

                if self.on_frame:
                    draw_hand(frame, pts, pressed=ctl.action in BUTTON_ACTIONS and not ctl.paused)
                    self.on_frame(frame, EngineState(**asdict(st)))
                elif now - last_emit > 0.1:
                    self._emit_state(); last_emit = now
        finally:
            if src:
                src.stop()
            ctl.shutdown()
            self._mouse.close()
            self._keyboard.close()
            tracker.close()
