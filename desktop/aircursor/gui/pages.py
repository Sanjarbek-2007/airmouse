"""The five pages of the main window."""
from __future__ import annotations

import threading
import time
from collections import deque

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QPushButton, QRadioButton, QScrollArea, QTextBrowser,
                               QVBoxLayout, QWidget, QButtonGroup)

from .. import camera as cam
from ..config import SLIDERS, TOGGLES, Config
from ..gestures import (ACTION_INFO, COMMAND_INFO, DEFAULT_COMMANDS, DEFAULT_MAPPING, GESTURE_INFO,
                        ONE_SHOT_ACTIONS, Action, Command, Gesture)
from . import theme
from .widgets import (Banner, Card, Meter, NoWheelComboBox, Pill, SliderRow, Switch, VideoView,
                      page_header)


def _scroll(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(inner)
    sa.setFrameShape(QFrame.NoFrame)
    return sa


def _page_layout(page: QWidget) -> QVBoxLayout:
    page.setObjectName("page")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(28, 24, 28, 20)
    lay.setSpacing(12)
    return lay


# ---------------------------------------------------------------------------- Live
class LivePage(QWidget):
    resume_requested = Signal()

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.recent: deque = deque(maxlen=8)
        root = _page_layout(self)

        top = QHBoxLayout()
        top.addWidget(page_header("Live", "Your camera, with the hand AirCursor sees. Point to move; pinch to click."), 1)
        self.pill_state = Pill("STARTING")
        self.pill_cam = Pill("no camera")
        self.pill_fps = Pill("– fps")
        for w in (self.pill_state, self.pill_cam, self.pill_fps):
            top.addWidget(w, 0, Qt.AlignTop)
        root.addLayout(top)

        self.banner = Banner("warn")
        root.addWidget(self.banner)

        body = QHBoxLayout()
        body.setSpacing(18)
        self.video = VideoView()
        body.addWidget(self.video, 1)

        side = QVBoxLayout()
        side.setSpacing(14)
        card = Card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(8)
        row = QHBoxLayout()
        self.emoji = QLabel("✋"); self.emoji.setObjectName("emoji")
        self.command = QLabel("NO HAND"); self.command.setObjectName("command")
        row.addWidget(self.emoji); row.addWidget(self.command, 1)
        cl.addLayout(row)
        self.sub = QLabel("Show your hand to the camera"); self.sub.setObjectName("muted"); self.sub.setWordWrap(True)
        cl.addWidget(self.sub)
        cl.addSpacing(6)
        self.m_confirm = Meter("Recognising…")
        self.m_pinch = Meter("Pinch")
        self.m_tuck = Meter("Thumb tuck")
        self.m_bend = Meter("Index bend (C-shape)")
        self.m_vol = Meter("Volume")
        self.m_boost = Meter("Reach boost")
        for m in (self.m_confirm, self.m_pinch, self.m_tuck, self.m_bend, self.m_vol, self.m_boost):
            cl.addWidget(m)
        side.addWidget(card)

        rc = Card()
        rl = QVBoxLayout(rc)
        rl.setContentsMargins(20, 14, 20, 14)
        t = QLabel("Recent commands"); t.setObjectName("h2")
        rl.addWidget(t)
        self.list = QListWidget()
        self.list.setMaximumHeight(190)
        rl.addWidget(self.list)
        side.addWidget(rc)
        side.addStretch(1)
        wrap = QWidget(); wrap.setLayout(side); wrap.setFixedWidth(330)
        body.addWidget(wrap)
        root.addLayout(body, 1)

        tip = QLabel("💡  Open palm = lift the mouse. Move your hand freely, then point again to carry on from where the cursor is.")
        tip.setObjectName("muted")
        tip.setWordWrap(True)
        root.addWidget(tip)

        ctx.tick.connect(self.on_tick)
        ctx.event.connect(self.on_event)

    def on_event(self, text: str) -> None:
        self.list.insertItem(0, f"{time.strftime('%H:%M:%S')}   {text}")
        while self.list.count() > 8:
            self.list.takeItem(self.list.count() - 1)

    def on_tick(self, img, st) -> None:
        if img is not None:
            self.video.set_image(img)
        # status pills + overlays
        if st.paused:
            self.pill_state.setText("PAUSED"); self.pill_state.set_kind("warn")
            self.video.set_overlay("⏸  PAUSED\n" + (st.pause_reason or "") + "\nPress Resume to continue", "warn")
        elif st.status == "running":
            self.pill_state.setText("LIVE" if st.live else "DRY RUN")
            self.pill_state.set_kind("ok" if st.live else "")
            self.video.set_overlay("")
        elif st.status in ("starting", "connecting"):
            self.pill_state.setText(st.status.upper()); self.pill_state.set_kind("")
            self.video.set_overlay(st.message or "Starting…")
        else:
            self.pill_state.setText("NO CAMERA" if st.status == "no_camera" else "ERROR")
            self.pill_state.set_kind("danger")
            self.video.set_overlay(st.message, "danger")
        self.pill_cam.setText(st.source or "no camera")
        self.pill_fps.setText(f"{st.fps:.0f} fps" if st.fps else "– fps")
        if st.warning:
            self.banner.show_message("⚠  Cursor control is not active (preview only).\n" + st.warning, "warn")
        else:
            self.banner.hide()

        # command card
        g = Gesture(st.gesture) if st.gesture in {x.value for x in Gesture} else Gesture.NONE
        info = GESTURE_INFO.get(g)
        self.emoji.setText(info[0] if info else "👋")
        self.command.setText(st.label or "…")
        color = theme.AMBER if st.paused else (theme.GREEN if "CLICK" in st.label or "HOLD" in st.label else theme.TEXT)
        self.command.setStyleSheet(f"color:{color};")
        if st.paused:
            self.sub.setText("Control is paused — nothing you do will act.")
        elif info:
            self.sub.setText(f"{info[1]}  →  {ACTION_INFO[Action(st.action)]}")
        else:
            self.sub.setText("Show your hand to the camera")
        if st.pending and st.pending != "none":
            pi = GESTURE_INFO.get(Gesture(st.pending))
            self.m_confirm.title.setText(f"Recognising {pi[1] if pi else st.pending}…")
            self.m_confirm.set(st.progress, "warn", "")
        else:
            self.m_confirm.title.setText("Recognised")
            self.m_confirm.set(1.0 if st.hand else 0.0, "ok" if st.hand else "", "")
        self.m_pinch.set((0.8 - st.pinch) / 0.5, "ok" if g == Gesture.PINCH else "", f"{st.pinch:.2f}" if st.hand else "")
        self.m_tuck.set((1.0 - st.tuck) / 0.5, "ok" if g == Gesture.TUCK else "", f"{st.tuck:.2f}" if st.hand else "")
        self.m_bend.set((st.bend - 60) / 120, "ok" if g == Gesture.HOOK else "", f"{st.bend:.0f}°" if st.hand else "")
        is_vol = st.action == Action.VOLUME.value
        self.m_vol.setVisible(is_vol)
        if is_vol:
            self.m_vol.set(st.volume, "", f"{round(st.volume * 100)}%")
        self.m_boost.setVisible(st.factor > 1.08)
        self.m_boost.set((st.factor - 1) / 3.0, "warn", f"×{st.factor:.1f}")


# ------------------------------------------------------------------------ Gestures
class GesturesPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.cards: dict[Gesture, Card] = {}
        self.combos: dict[Gesture, QComboBox] = {}
        self.cmd_cards: dict[Command, Card] = {}
        self.cmd_combos: dict[Command, QComboBox] = {}
        root = _page_layout(self)
        head = QHBoxLayout()
        head.addWidget(page_header("Gestures", "Choose what each hand gesture does. The current gesture lights up live."), 1)
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self.reset)
        head.addWidget(reset, 0, Qt.AlignTop)
        root.addLayout(head)

        inner = QWidget(); inner.setObjectName("page")
        grid = QGridLayout(inner)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 8, 0)
        for i, g in enumerate(DEFAULT_MAPPING):
            emoji, name, how = GESTURE_INFO[g]
            card = Card()
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 14, 18, 16)
            cl.setSpacing(8)
            row = QHBoxLayout()
            e = QLabel(emoji); e.setObjectName("emoji")
            t = QLabel(name); t.setObjectName("h2")
            row.addWidget(e); row.addWidget(t, 1)
            cl.addLayout(row)
            d = QLabel(how); d.setObjectName("muted"); d.setWordWrap(True)
            cl.addWidget(d)
            cb = NoWheelComboBox()
            for a, label in ACTION_INFO.items():
                cb.addItem(label, a.value)
            cb.currentIndexChanged.connect(lambda _i, g=g, cb=cb: self.on_pick(g, cb))
            cl.addWidget(cb)
            grid.addWidget(card, i // 2, i % 2)
            self.cards[g], self.combos[g] = card, cb
        # ---- motion commands
        base = (len(DEFAULT_MAPPING) + 1) // 2 + 1
        h = QLabel("Motion commands"); h.setObjectName("h1"); h.setStyleSheet("font-size:18px; margin-top:10px;")
        grid.addWidget(h, base, 0, 1, 2)
        sub = QLabel("Do these with an <b>open palm</b>: flick, wave or tilt your hand. Each can trigger a keyboard shortcut "
                     "(switch windows, workspaces, media keys…). Set to “Do nothing” to turn one off.")
        sub.setObjectName("muted"); sub.setWordWrap(True); sub.setTextFormat(Qt.RichText)
        grid.addWidget(sub, base + 1, 0, 1, 2)
        for i, c in enumerate(DEFAULT_COMMANDS):
            emoji, name, how = COMMAND_INFO[c]
            card = Card()
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 14, 18, 16)
            cl.setSpacing(8)
            row = QHBoxLayout()
            e = QLabel(emoji); e.setObjectName("emoji")
            t = QLabel(name); t.setObjectName("h2")
            row.addWidget(e); row.addWidget(t, 1)
            cl.addLayout(row)
            d = QLabel(how); d.setObjectName("muted"); d.setWordWrap(True)
            cl.addWidget(d)
            cb = NoWheelComboBox()
            cb.addItem(ACTION_INFO[Action.NONE], Action.NONE.value)
            for a in ONE_SHOT_ACTIONS:
                cb.addItem(ACTION_INFO[a], a.value)
            cb.currentIndexChanged.connect(lambda _i, c=c, cb=cb: self.on_pick_cmd(c, cb))
            cl.addWidget(cb)
            grid.addWidget(card, base + 2 + i // 2, i % 2)
            self.cmd_cards[c], self.cmd_combos[c] = card, cb
        grid.setRowStretch(grid.rowCount(), 1)
        root.addWidget(_scroll(inner), 1)
        self.load()
        ctx.tick.connect(self.on_tick)

    def load(self):
        for g, cb in self.combos.items():
            cb.blockSignals(True)
            cb.setCurrentIndex(cb.findData(self.ctx.cfg.action_for(g).value))
            cb.blockSignals(False)
        for c, cb in self.cmd_combos.items():
            cb.blockSignals(True)
            cb.setCurrentIndex(cb.findData(self.ctx.cfg.command_action(c).value))
            cb.blockSignals(False)

    def on_pick_cmd(self, c: Command, cb: QComboBox):
        self.ctx.cfg.commands[c.value] = cb.currentData()
        self.ctx.save()

    def on_pick(self, g: Gesture, cb: QComboBox):
        self.ctx.cfg.gestures[g.value] = cb.currentData()
        self.ctx.save()

    def reset(self):
        self.ctx.cfg.gestures = {g.value: a.value for g, a in DEFAULT_MAPPING.items()}
        self.ctx.cfg.commands = {c.value: a.value for c, a in DEFAULT_COMMANDS.items()}
        self.ctx.save()
        self.load()

    def on_tick(self, _img, st):
        for g, card in self.cards.items():
            card.set_active(not st.paused and st.hand and st.gesture == g.value)
        recent = st.command and time.time() - st.command_at < 1.2
        for c, card in self.cmd_cards.items():
            card.set_active(bool(recent) and st.command == c.value)


# ------------------------------------------------------------------------ Settings
class SettingsPage(QWidget):
    SECTIONS = [
        ("Pointer", ["speed", "accel_strength", "long_move_boost", "smoothing"], ["smart_motion"]),
        ("Recognition", ["hold_scale", "pinch_sensitivity", "tuck_sensitivity", "hook_sensitivity", "command_sensitivity"],
         ["motion_commands"]),
        ("Actions", ["scroll_speed", "volume_step"], []),
        ("Camera view & safety", [], ["mirror", "guard_enabled", "float_widget", "start_paused"]),
    ]

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.rows: dict[str, SliderRow] = {}
        self.switches: dict[str, Switch] = {}
        root = _page_layout(self)
        head = QHBoxLayout()
        head.addWidget(page_header("Settings", "Changes apply instantly and are saved automatically. The defaults are tuned to feel right."), 1)
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self.reset)
        head.addWidget(reset, 0, Qt.AlignTop)
        root.addLayout(head)

        inner = QWidget(); inner.setObjectName("page")
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 8, 0)
        col.setSpacing(14)
        meta = {s[0]: s for s in SLIDERS}
        tmeta = {t[0]: t for t in TOGGLES}
        for title, sliders, toggles in self.SECTIONS:
            card = Card()
            cl = QVBoxLayout(card)
            cl.setContentsMargins(22, 16, 22, 16)
            h = QLabel(title); h.setObjectName("h1"); h.setStyleSheet("font-size:17px;")
            cl.addWidget(h)
            for key in sliders:
                _k, label, lo, hi, step, fmt, help_text = meta[key]
                row = SliderRow(key, label, lo, hi, step, fmt, help_text, getattr(ctx.cfg, key))
                row.changed.connect(self.on_slider)
                cl.addWidget(row)
                self.rows[key] = row
            for key in toggles:
                _k, label, help_text = tmeta[key]
                line = QHBoxLayout()
                txt = QVBoxLayout(); txt.setSpacing(1)
                a = QLabel(label); a.setObjectName("h2")
                b = QLabel(help_text); b.setObjectName("muted"); b.setWordWrap(True)
                txt.addWidget(a); txt.addWidget(b)
                sw = Switch(getattr(ctx.cfg, key))
                sw.toggled.connect(lambda on, k=key: self.on_toggle(k, on))
                line.addLayout(txt, 1); line.addWidget(sw, 0, Qt.AlignVCenter)
                cl.addSpacing(6); cl.addLayout(line)
                self.switches[key] = sw
            if title.startswith("Camera view"):
                cl.addSpacing(10)
                sc = QLabel("<b>Global pause key.</b> Bind this command to any keyboard shortcut in your system "
                            "settings — it pauses/resumes AirCursor from anywhere, even if the window is lost:<br>"
                            f"<code>{ctx.ctl_command('toggle')}</code>")
                sc.setObjectName("muted"); sc.setWordWrap(True); sc.setTextInteractionFlags(Qt.TextSelectableByMouse)
                cl.addWidget(sc)
                if ctx.can_install_shortcuts:
                    btn = QPushButton("Add shortcuts:  Ctrl+Alt+P  pause   ·   Ctrl+Alt+Q  quit")
                    btn.clicked.connect(lambda: self._install(btn))
                    cl.addWidget(btn)
            col.addWidget(card)
        col.addStretch(1)
        root.addWidget(_scroll(inner), 1)

    def _install(self, btn):
        ok, msg = self.ctx.install_shortcuts()
        btn.setText(("✓ " if ok else "✗ ") + msg)

    def on_slider(self, key, v):
        setattr(self.ctx.cfg, key, v)
        self.ctx.save()

    def on_toggle(self, key, on):
        setattr(self.ctx.cfg, key, on)
        self.ctx.save()
        if key == "float_widget":
            self.ctx.apply_float_setting()

    def reset(self):
        self.ctx.cfg.reset_to_defaults()
        self.ctx.save()
        for key, row in self.rows.items():
            row.set_value(getattr(self.ctx.cfg, key))
        for key, sw in self.switches.items():
            sw.setChecked(getattr(self.ctx.cfg, key))
        self.ctx.apply_float_setting()
        self.ctx.reload_gestures.emit()


# -------------------------------------------------------------------------- Camera
class CameraPage(QWidget):
    scanned = Signal(list)
    tested = Signal(object, str)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.local_radios: list[tuple[QRadioButton, int]] = []
        root = _page_layout(self)
        root.addWidget(page_header("Camera", "Use your computer's camera, or stream from a phone. Auto picks the built-in camera."))
        self.group = QButtonGroup(self)

        card = Card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 18, 22, 18)
        cl.setSpacing(10)
        self.auto = QRadioButton("Automatic (recommended)")
        sub = QLabel("Uses the first working camera on this computer. If there is none, uses the phone stream below.")
        sub.setObjectName("muted"); sub.setWordWrap(True)
        self.group.addButton(self.auto)
        cl.addWidget(self.auto); cl.addWidget(sub)
        self.local_box = QVBoxLayout(); self.local_box.setSpacing(6)
        cl.addLayout(self.local_box)
        self.scan_label = QLabel("Looking for cameras…"); self.scan_label.setObjectName("muted")
        self.local_box.addWidget(self.scan_label)
        root.addWidget(card)

        pc = Card()
        pl = QVBoxLayout(pc)
        pl.setContentsMargins(22, 18, 22, 18)
        pl.setSpacing(10)
        self.phone = QRadioButton("Phone or network camera")
        self.group.addButton(self.phone)
        hint = QLabel("Install <b>IP Webcam</b> on Android, tap <i>Start server</i>, then enter the address it shows "
                      "(for example <code>192.168.1.50:8080</code>). Phone and computer must be on the same Wi-Fi. "
                      "Any MJPEG stream URL works.")
        hint.setObjectName("muted"); hint.setWordWrap(True); hint.setTextFormat(Qt.RichText)
        self.url = QLineEdit(ctx.cfg.phone_url)
        self.url.setPlaceholderText("192.168.1.50:8080   or   https://192.168.1.50:8080/video")
        self.url.textChanged.connect(self.on_url)
        row = QHBoxLayout()
        self.test_btn = QPushButton("Test connection")
        self.test_btn.clicked.connect(self.test)
        self.test_label = QLabel(""); self.test_label.setObjectName("muted"); self.test_label.setWordWrap(True)
        row.addWidget(self.test_btn); row.addWidget(self.test_label, 1)
        self.thumb = QLabel(); self.thumb.setFixedHeight(0)
        pl.addWidget(self.phone); pl.addWidget(hint); pl.addWidget(self.url); pl.addLayout(row); pl.addWidget(self.thumb)
        root.addWidget(pc)

        self.status = QLabel(""); self.status.setObjectName("muted")
        root.addWidget(self.status)
        root.addStretch(1)

        self.group.buttonClicked.connect(self.on_choice)
        self.scanned.connect(self.on_scanned)
        self.tested.connect(self.on_tested)
        ctx.tick.connect(lambda _i, st: self.status.setText(
            f"Now using:  {st.source}" if st.source else "Not connected"))
        self.rescan()

    # -- local cameras
    def rescan(self):
        threading.Thread(target=lambda: self.scanned.emit(cam.list_local_cameras()), daemon=True).start()

    def on_scanned(self, cams):
        while self.local_box.count():
            w = self.local_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.local_radios = []
        if not cams:
            l = QLabel("No local cameras detected."); l.setObjectName("muted")
            self.local_box.addWidget(l)
        for c in cams:
            rb = QRadioButton(c.label)
            self.group.addButton(rb)
            self.local_box.addWidget(rb)
            self.local_radios.append((rb, c.index))
        refresh = QPushButton("Rescan"); refresh.setFixedWidth(100)
        refresh.clicked.connect(self.rescan)
        self.local_box.addWidget(refresh)
        self.sync_selection()

    def sync_selection(self):
        src = self.ctx.cfg.camera_source
        if src == "auto":
            self.auto.setChecked(True)
        elif src == "url":
            self.phone.setChecked(True)
        else:
            for rb, idx in self.local_radios:
                if src == f"local:{idx}":
                    rb.setChecked(True)

    def on_choice(self, btn):
        if btn is self.auto:
            src = "auto"
        elif btn is self.phone:
            src = "url"
        else:
            src = next((f"local:{i}" for rb, i in self.local_radios if rb is btn), "auto")
        if src != self.ctx.cfg.camera_source:
            self.ctx.cfg.camera_source = src
            self.ctx.save()
            self.ctx.engine.restart_source()

    # -- phone
    def on_url(self, text):
        self.ctx.cfg.phone_url = text.strip()
        self.ctx.save()
        self._url_timer = getattr(self, "_url_timer", None) or QTimer(self, singleShot=True, interval=900)
        if self.ctx.cfg.camera_source == "url":
            self._url_timer.timeout.connect(self.ctx.engine.restart_source, Qt.UniqueConnection)
            self._url_timer.start()

    def test(self):
        url = cam.normalize_stream_url(self.url.text())
        if not url:
            self.test_label.setText("Enter an address first.")
            return
        self.test_btn.setEnabled(False)
        self.test_label.setText("Connecting…")

        def work():
            s = cam.MjpegStream(url)
            ok = s.wait_first_frame(6.0)
            frame = s.latest()[0]
            err = s.error
            s.stop()
            self.tested.emit(frame if ok else None, err or "No video received (check the address and Wi-Fi).")
        threading.Thread(target=work, daemon=True).start()

    def on_tested(self, frame, err):
        self.test_btn.setEnabled(True)
        if frame is None:
            self.test_label.setText("✗ " + err)
            self.thumb.setFixedHeight(0)
            return
        h, w = frame.shape[:2]
        self.test_label.setText(f"✓ Connected — {w}×{h}")
        small = cv2.resize(frame, (int(160 * w / h), 160))
        img = QImage(small.data, small.shape[1], small.shape[0], 3 * small.shape[1], QImage.Format_BGR888).copy()
        self.thumb.setPixmap(QPixmap.fromImage(img))
        self.thumb.setFixedHeight(166)


# ---------------------------------------------------------------------------- Guide
GUIDE_HTML = f"""
<style>
 h2 {{ color:{theme.ACCENT}; margin-top:18px; }}
 td, th {{ padding: 6px 14px 6px 0; vertical-align: top; }}
 th {{ text-align:left; color:{theme.MUTED}; }}
 code {{ background:{theme.SURFACE2}; padding:2px 6px; }}
 .m {{ color:{theme.MUTED}; }}
</style>
<h2>Quick start</h2>
<ol>
<li><b>Place your camera</b> facing you so your hand is visible above the keyboard (arm's length works well). Good, even light helps a lot.</li>
<li><b>Raise your index finger</b> and move your hand. The cursor moves like a mouse: only the <i>motion</i> matters, not where your hand is in the picture.</li>
<li><b>Pinch</b> thumb and index finger to click. Hold the pinch and move to drag.</li>
</ol>
<p class="m">Run out of room? <b>Open your palm</b> (lift the mouse), move your hand back, and point again. Want faster corner reach? Raise <i>Long-reach boost</i> in Settings (off by default).</p>

<h2>Gestures (defaults)</h2>
<table>
<tr><th>Gesture</th><th>Action</th><th>How</th></tr>
<tr><td>☝️ Point</td><td>Move cursor</td><td>Only the index finger up</td></tr>
<tr><td>🤏 Pinch</td><td>Left click / drag</td><td>Thumb tip to index tip, other fingers open. Quick = click, hold + move = drag</td></tr>
<tr><td>🖐️ Thumb tuck</td><td>Right click / drag</td><td>Open hand, fold the thumb into your palm</td></tr>
<tr><td>✌️ Peace</td><td>Scroll</td><td>Move your hand up, down, left or right</td></tr>
<tr><td>🤟 Three fingers</td><td>Fast scroll</td><td>Same as scroll, 3× faster</td></tr>
<tr><td>🤘 Rock sign</td><td>Volume dial</td><td>Draw circles with your index fingertip: clockwise = louder, 10% per turn</td></tr>
<tr><td>🪝 C-shape</td><td>Middle button</td><td>Bend your index finger halfway (like a hook), other fingers curled</td></tr>
<tr><td>✊ Fist</td><td>Nothing</td><td>A safe resting pose — a fist never clicks</td></tr>
<tr><td>✋ Open palm</td><td>Nothing</td><td>Lift the mouse</td></tr>
</table>
<p class="m">Every gesture can be remapped on the <b>Gestures</b> page.</p>

<h2>Motion commands</h2>
<p>With an <b>open palm</b>, do a motion to trigger a shortcut:</p>
<table>
<tr><td>👉 Swipe right</td><td>Next window (Alt+Tab)</td></tr>
<tr><td>👈 Swipe left</td><td>Previous window (Alt+Shift+Tab)</td></tr>
<tr><td>👆 Swipe up</td><td>Overview (Super)</td></tr>
<tr><td>👇 Swipe down</td><td>Show desktop (Super+D)</td></tr>
<tr><td>👋 Wave (3 swings)</td><td>Play / pause media</td></tr>
<tr><td>↻ ↺ Twist (tilt) right / left</td><td>Next / previous workspace</td></tr>
</table>
<p class="m">Remap any of them on the <b>Gestures</b> page (windows, workspaces, tabs, browser back/forward,
copy/paste/undo, media, screenshot…). Make them easier or harder to trigger with <i>Motion command sensitivity</i>.
There is a 1-second cooldown after each command, and they never fire while you are pointing or clicking.</p>

<h2>Why it won't misfire</h2>
<ul>
<li>A gesture must be held steadily for a split second before it counts (adjust under <i>Settings → Gesture confirmation time</i>).</li>
<li>While a new gesture is being recognised, the cursor holds still, so clicks land where you aimed.</li>
<li>If the app sees a burst of clicks, the <b>safety guard</b> pauses it automatically.</li>
</ul>

<h2>Stopping it fast</h2>
<ul>
<li>The <b>floating panel</b> stays on top of every window: <b>⏸ Pause</b> or <b>✕ Quit</b> in one click.</li>
<li>Press <b>Space</b> in this window to pause or resume.</li>
<li>From any terminal or keyboard shortcut: <code>aircursor ctl toggle</code> (pause/resume) or <code>aircursor ctl quit</code>.</li>
<li>Lost the window? Launch AirCursor again — it just raises the one that's already running.</li>
<li>Your real mouse and keyboard always keep working.</li>
</ul>

<h2>Troubleshooting</h2>
<ul>
<li><b>“Cursor control is not active”</b> (Linux): the app needs access to <code>/dev/uinput</code>. Run <code>desktop/scripts/setup-linux.sh</code> once.</li>
<li><b>Hand not detected:</b> more light, hand fully in view, plain background helps. Check the <i>Recognised</i> meter on the Live page.</li>
<li><b>Pinch too hard/easy:</b> change <i>Pinch sensitivity</i> in Settings.</li>
<li><b>Cursor too fast/slow:</b> change <i>Pointer speed</i>.</li>
<li><b>Phone stream:</b> phone and computer must be on the same Wi-Fi; use the Test button on the Camera page.</li>
</ul>
"""


class GuidePage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        root = _page_layout(self)
        root.addWidget(page_header("Guide", "Everything you need to know in one minute."))
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setHtml(GUIDE_HTML)
        root.addWidget(tb, 1)
