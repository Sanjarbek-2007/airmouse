"""Main window: sidebar navigation + pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from . import theme
from .icon import app_icon, make_pixmap
from .pages import CameraPage, GesturesPage, GuidePage, LivePage, SettingsPage
from .widgets import Pill


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1280, 780)
        self.setMinimumSize(1000, 640)

        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- sidebar
        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(232)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(16, 20, 16, 16)
        sl.setSpacing(4)
        brand = QHBoxLayout()
        ic = QLabel(); ic.setPixmap(make_pixmap(64).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        names = QVBoxLayout(); names.setSpacing(0)
        logo = QLabel(APP_NAME); logo.setObjectName("logo")
        ver = QLabel(f"v{__version__}"); ver.setObjectName("version")
        names.addWidget(logo); names.addWidget(ver)
        brand.addWidget(ic); brand.addLayout(names); brand.addStretch(1)
        sl.addLayout(brand)
        sl.addSpacing(18)

        self.stack = QStackedWidget()
        self.pages = [("◉   Live", LivePage(ctx)), ("✋   Gestures", GesturesPage(ctx)),
                      ("⚙   Settings", SettingsPage(ctx)), ("📷   Camera", CameraPage(ctx)),
                      ("📖   Guide", GuidePage(ctx))]
        self.group = QButtonGroup(self)
        self.nav = []
        for i, (title, page) in enumerate(self.pages):
            b = QPushButton(title); b.setObjectName("nav"); b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b, i)
            sl.addWidget(b)
            self.stack.addWidget(page)
            self.nav.append(b)
        self.group.idClicked.connect(self.stack.setCurrentIndex)
        self.show_page(0)
        ctx.reload_gestures.connect(self.pages[1][1].load)

        sl.addStretch(1)
        self.pill = Pill("STARTING")
        sl.addWidget(self.pill, 0, Qt.AlignLeft)
        sl.addSpacing(6)
        self.btn_pause = QPushButton("⏸  Pause")
        self.btn_pause.setObjectName("warn")
        self.btn_pause.setMinimumHeight(42)
        self.btn_pause.clicked.connect(ctx.toggle_pause)
        sl.addWidget(self.btn_pause)
        self.btn_quit = QPushButton("✕  Quit")
        self.btn_quit.setObjectName("danger")
        self.btn_quit.setMinimumHeight(38)
        self.btn_quit.clicked.connect(ctx.quit)
        sl.addWidget(self.btn_quit)
        hint = QLabel("Space = pause / resume")
        hint.setObjectName("version"); hint.setAlignment(Qt.AlignCenter)
        sl.addWidget(hint)

        outer.addWidget(side)
        outer.addWidget(self.stack, 1)

        QShortcut(QKeySequence(Qt.Key_Space), self, activated=ctx.toggle_pause)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=ctx.quit)
        ctx.tick.connect(self.on_tick)

    def show_page(self, i: int) -> None:
        self.nav[i].setChecked(True)
        self.stack.setCurrentIndex(i)

    def on_tick(self, _img, st) -> None:
        if st.paused:
            self.pill.setText("PAUSED"); self.pill.set_kind("warn")
            self.btn_pause.setText("▶  Resume"); self.btn_pause.setObjectName("primary")
        else:
            ok = st.status == "running"
            self.pill.setText(("LIVE" if st.live else "DRY RUN") if ok else st.status.upper().replace("_", " "))
            self.pill.set_kind("ok" if ok and st.live else ("danger" if st.status in ("no_camera", "error") else ""))
            self.btn_pause.setText("⏸  Pause"); self.btn_pause.setObjectName("warn")
        self.btn_pause.style().unpolish(self.btn_pause); self.btn_pause.style().polish(self.btn_pause)

    def closeEvent(self, e):
        e.accept()
        self.ctx.quit()  # closing the window quits: never leave a hidden app controlling the mouse
