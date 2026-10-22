"""System output volume. Linux: PipeWire (wpctl) or PulseAudio (pactl). macOS: osascript.
Windows: media keys via pynput (coarse, experimental). Writes are coalesced in a worker
thread so fast dialing never queues up subprocesses."""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading


class Volume:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        if sys.platform == "darwin":
            self.tool = "osascript"
        elif sys.platform.startswith("win"):
            self.tool = "keys"
        else:
            self.tool = "wpctl" if shutil.which("wpctl") else "pactl" if shutil.which("pactl") else None
        self._target = None
        self._current = 0.5
        self._ev = threading.Event()
        if enabled and self.tool:
            threading.Thread(target=self._run, daemon=True).start()

    def get(self) -> float:
        try:
            if self.tool == "wpctl":
                out = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                                     capture_output=True, text=True, timeout=2).stdout
                self._current = float(out.split()[1])
            elif self.tool == "pactl":
                out = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                                     capture_output=True, text=True, timeout=2).stdout
                self._current = int(out.split("%")[0].split()[-1]) / 100
            elif self.tool == "osascript":
                out = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"],
                                     capture_output=True, text=True, timeout=2).stdout
                self._current = int(out.strip()) / 100
        except Exception:
            pass
        return self._current

    def set(self, v: float) -> None:
        if self.enabled and self.tool:
            self._target = min(max(v, 0.0), 1.0)
            self._ev.set()

    def _run(self):
        while True:
            self._ev.wait()
            self._ev.clear()
            v = self._target
            try:
                if self.tool == "wpctl":
                    subprocess.run(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{v:.2f}"],
                                   timeout=2, capture_output=True)
                elif self.tool == "pactl":
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{round(v * 100)}%"],
                                   timeout=2, capture_output=True)
                elif self.tool == "osascript":
                    subprocess.run(["osascript", "-e", f"set volume output volume {round(v * 100)}"],
                                   timeout=2, capture_output=True)
                elif self.tool == "keys":
                    self._windows_keys(v)
            except Exception:
                pass

    def _windows_keys(self, v: float):
        from pynput.keyboard import Controller, Key
        kb, steps = Controller(), round((v - self._current) / 0.02)
        key = Key.media_volume_up if steps > 0 else Key.media_volume_down
        for _ in range(abs(steps)):
            kb.tap(key)
        self._current = v
