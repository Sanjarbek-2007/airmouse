"""GUI application: Qt setup, shared context, single-instance handling."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from ..platform_setup import prepare_qt

from PySide6.QtCore import QObject, QTimer, Signal  # noqa: E402  (after prepare_qt is imported, before use)
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from .. import APP_NAME
from ..config import Config
from ..engine import Engine, EngineState
from ..ipc import ControlServer, send_command
from . import shortcuts, theme
from .floating import FloatPanel
from .icon import app_icon, write_arrow
from .main_window import MainWindow

DESKTOP_DIR = Path(__file__).resolve().parents[2]


class AppContext(QObject):
    tick = Signal(object, object)        # (QImage | None, EngineState) ~30x/s, GUI thread
    event = Signal(str)                  # recognised command / notice, GUI thread
    reload_gestures = Signal()
    command = Signal(str)                # remote command (from `aircursor ctl`)

    def __init__(self, app: QApplication, cfg: Config, live: bool = True):
        super().__init__()
        self.app, self.cfg = app, cfg
        self._lock = threading.Lock()
        self._frame, self._state, self._seq, self._shown_seq = None, EngineState(live=live), 0, 0
        self.engine = Engine(cfg, live, on_frame=self._on_frame, on_state=self._on_state,
                             on_event=self._on_event)
        self.window: MainWindow | None = None
        self.panel: FloatPanel | None = None
        self.server = ControlServer(self._remote)
        self._quitting = False
        self.can_install_shortcuts = shortcuts.available()
        self.command.connect(self._handle_command)
        self._timer = QTimer(self, interval=33)
        self._timer.timeout.connect(self._poll)

    # ------------------------------------------------------------- engine side
    def _on_frame(self, frame, state):
        with self._lock:
            self._frame, self._state, self._seq = frame, state, self._seq + 1

    def _on_state(self, state):
        with self._lock:
            self._state = state

    def _on_event(self, text: str):
        self.event.emit(text)
        if text.startswith("Safety guard") and shutil.which("notify-send"):
            subprocess.Popen(["notify-send", "-u", "critical", f"{APP_NAME} paused", text])

    def _poll(self):
        with self._lock:
            frame, state, seq = self._frame, self._state, self._seq
        img = None
        if frame is not None and seq != self._shown_seq:
            self._shown_seq = seq
            h, w = frame.shape[:2]
            img = QImage(frame.data, w, h, frame.strides[0], QImage.Format_BGR888).copy()
        self.tick.emit(img, state)
        if self.panel:
            self.panel.set_state(state.paused, state.label, state.pause_reason)

    # --------------------------------------------------------------- user side
    def save(self):
        self.cfg.save()

    def toggle_pause(self):
        self.engine.toggle_pause()

    def apply_float_setting(self):
        if self.panel:
            self.panel.setVisible(self.cfg.float_widget)
            if self.cfg.float_widget:
                QTimer.singleShot(250, self.panel.make_sticky)

    def ctl_command(self, cmd: str) -> str:
        run = DESKTOP_DIR / "run.sh"
        return f"{run} ctl {cmd}" if run.exists() else f"aircursor ctl {cmd}"

    def install_shortcuts(self):
        return shortcuts.install([
            ("aircursor-toggle", "AirCursor pause/resume", self.ctl_command("toggle"), "<Ctrl><Alt>p"),
            ("aircursor-quit", "AirCursor quit", self.ctl_command("quit"), "<Ctrl><Alt>q"),
        ])

    def show_window(self):
        w = self.window
        if w:
            w.showNormal()
            w.raise_()
            w.activateWindow()

    def _remote(self, cmd: str) -> str:
        """Runs in the control-server thread; keep it quick and thread-safe."""
        if cmd in ("pause", "resume", "toggle"):
            if cmd == "pause" or (cmd == "toggle" and not self.engine.paused):
                self.engine.pause("Paused by shortcut")
            else:
                self.engine.resume()
            return "paused" if self.engine.paused else "running"
        if cmd in ("quit", "show"):
            self.command.emit(cmd)
            return "ok"
        if cmd == "status":
            s = self.engine.state
            return f"{s.status} {'paused' if self.engine.paused else 'active'} {s.label}"
        return "unknown command"

    def _handle_command(self, cmd: str):
        if cmd == "quit":
            self.quit()
        elif cmd == "show":
            self.show_window()

    def quit(self):
        if self._quitting:
            return
        self._quitting = True
        self._timer.stop()
        threading.Timer(4.0, lambda: os._exit(0)).start()  # failsafe if something hangs
        self.engine.stop()          # releases every button, drops queued motion
        self.server.stop()
        if self.panel:
            self.panel.hide()
        self.app.quit()

    def start(self):
        if self.cfg.start_paused:
            self.engine.pause("Start paused")
        self.engine.start()
        self._timer.start()


def run_gui(live: bool = True) -> int:
    if send_command("ping") == "pong":      # already running: just bring it to the front
        send_command("show")
        print(f"{APP_NAME} is already running - raised its window.")
        return 0
    prepare_qt()
    sys.argv[0] = "aircursor"   # becomes the window class (shows as AirCursor in the shell)
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())
    from ..config import config_dir
    arrow = write_arrow(config_dir() / "arrow.png") if config_dir().exists() or config_dir().mkdir(parents=True, exist_ok=True) is None else ""
    app.setStyleSheet(theme.QSS + f"QComboBox::down-arrow {{ image: url({arrow}); width: 16px; height: 16px; margin-right: 8px; }}")
    app.setQuitOnLastWindowClosed(False)

    cfg = Config.load()
    ctx = AppContext(app, cfg, live)
    if not ctx.server.start():
        print(f"{APP_NAME} is already running.", file=sys.stderr)
        return 1
    ctx.window = MainWindow(ctx)
    ctx.panel = FloatPanel()
    ctx.panel.pause_toggled.connect(ctx.toggle_pause)
    ctx.panel.show_requested.connect(ctx.show_window)
    ctx.panel.quit_requested.connect(ctx.quit)
    ctx.panel.moved.connect(lambda x, y: (setattr(cfg, "float_pos", [x, y]), ctx.save()))
    ctx.panel.place_at(*cfg.float_pos)
    if cfg.first_run:
        ctx.window.show_page(4)
        cfg.first_run = False
        ctx.save()
    ctx.window.show()
    ctx.panel.show()
    ctx.apply_float_setting()
    ctx.start()
    return app.exec()
