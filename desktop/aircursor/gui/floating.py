"""Always-on-top floating panic panel: Pause/Resume, Show window, Quit. Draggable.

It is deliberately tiny and stays visible on every workspace so the app can never get
"lost" behind other windows while a hand is misbehaving."""
from __future__ import annotations

import sys

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from . import theme

QSS = f"""
QLabel#fstate {{ font-weight: 800; font-size: 12px; letter-spacing: 1px; }}
QLabel#fcmd {{ color: {theme.MUTED}; font-size: 11px; }}
QPushButton {{ border-radius: 9px; padding: 0 10px; font-weight: 800; font-size: 12px; min-height: 30px; }}
QPushButton#fpause {{ background: #2A2110; border: 1px solid {theme.AMBER}; color: {theme.AMBER}; }}
QPushButton#fresume {{ background: {theme.GREEN}; border: none; color: #04120A; }}
QPushButton#fshow {{ background: {theme.SURFACE2}; border: 1px solid {theme.BORDER}; color: {theme.TEXT}; }}
QPushButton#fquit {{ background: #2B1217; border: 1px solid {theme.RED}; color: {theme.RED}; }}
QPushButton:hover {{ border-color: #FFFFFF; }}
"""


class FloatPanel(QWidget):
    pause_toggled = Signal()
    show_requested = Signal()
    quit_requested = Signal()
    moved = Signal(int, int)

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle("AirCursor panic panel")
        self.setStyleSheet(QSS)
        self.setFixedSize(380, 52)
        self._paused = False
        self._active_color = QColor(theme.GREEN)
        self._drag: QPoint | None = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 10, 8)
        lay.setSpacing(8)
        self.state = QLabel("● ACTIVE"); self.state.setObjectName("fstate")
        self.cmd = QLabel(""); self.cmd.setObjectName("fcmd")
        self.cmd.setMinimumWidth(80)
        self.btn_pause = QPushButton("⏸ Pause"); self.btn_pause.setObjectName("fpause")
        self.btn_show = QPushButton("▣"); self.btn_show.setObjectName("fshow")
        self.btn_show.setToolTip("Show the AirCursor window"); self.btn_show.setFixedWidth(36)
        self.btn_quit = QPushButton("✕ Quit"); self.btn_quit.setObjectName("fquit")
        lay.addWidget(self.state)
        lay.addWidget(self.cmd, 1)
        for b in (self.btn_pause, self.btn_show, self.btn_quit):
            b.setCursor(Qt.PointingHandCursor)
            lay.addWidget(b)
        self.btn_pause.clicked.connect(self.pause_toggled)
        self.btn_show.clicked.connect(self.show_requested)
        self.btn_quit.clicked.connect(self.quit_requested)
        self.set_state(False, "", "")

    # ------------------------------------------------------------------ state
    def set_state(self, paused: bool, label: str, reason: str) -> None:
        self._paused = paused
        if paused:
            self.state.setText("⏸ PAUSED")
            self.state.setStyleSheet(f"color:{theme.AMBER};")
            self.btn_pause.setText("▶ Resume"); self.btn_pause.setObjectName("fresume")
            self.cmd.setText("tripped" if "guard" in reason.lower() else "")
            self.setToolTip(reason or "Paused")
        else:
            self.state.setText("● ACTIVE")
            self.state.setStyleSheet(f"color:{theme.GREEN};")
            self.btn_pause.setText("⏸ Pause"); self.btn_pause.setObjectName("fpause")
            self.cmd.setText(label[:16])
            self.setToolTip("")
        self.btn_pause.setStyleSheet("")  # re-evaluate object-name based style
        self.style().unpolish(self.btn_pause); self.style().polish(self.btn_pause)
        self.update()

    def place_default(self) -> None:
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.width() - 24, scr.top() + 24)

    def place_at(self, x: int, y: int) -> None:
        scr = QGuiApplication.primaryScreen().availableGeometry()
        if x < 0 or y < 0 or not scr.adjusted(-40, -40, 40, 40).contains(QPoint(x + 40, y + 20)):
            self.place_default()
        else:
            self.move(x, y)

    def make_sticky(self) -> None:
        """Ask the window manager to show this on every workspace (X11/XWayland)."""
        if sys.platform.startswith("linux"):
            try:
                from . import x11
                x11.make_sticky_above(int(self.winId()))
            except Exception:
                pass

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(QColor(10, 14, 20, 235))
        p.setPen(QPen(QColor(theme.AMBER if self._paused else theme.GREEN), 1.6))
        p.drawRoundedRect(r, 16, 16)

    # --------------------------------------------------------------- dragging
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.RightButton:
            m = QMenu(self)
            m.addAction("Show window", self.show_requested.emit)
            m.addAction("Resume" if self._paused else "Pause", self.pause_toggled.emit)
            m.addSeparator()
            m.addAction("Quit", self.quit_requested.emit)
            m.exec(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            self.moved.emit(self.x(), self.y())
