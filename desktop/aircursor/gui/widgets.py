"""Small reusable widgets."""
from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy,
                               QSlider, QVBoxLayout, QWidget)

from . import theme


class NoWheelComboBox(QComboBox):
    """A dropdown that ignores the mouse wheel unless it has keyboard focus, so scrolling a page
    never silently changes a setting that happens to be under the cursor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class NoWheelSlider(QSlider):
    """Same protection for sliders."""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

    def set_active(self, on: bool) -> None:
        if self.property("active") != on:
            self.setProperty("active", on)
            repolish(self)


class Pill(QLabel):
    def __init__(self, text="", kind="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("pill")
        self.set_kind(kind)

    def set_kind(self, kind: str) -> None:
        if self.property("kind") != kind:
            self.setProperty("kind", kind)
            repolish(self)


class Banner(QFrame):
    """Coloured message strip (warning / danger)."""

    def __init__(self, kind="warn", parent=None):
        super().__init__(parent)
        self.setObjectName("banner")
        self.setProperty("kind", kind)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.label, 1)
        self.hide()

    def show_message(self, text: str, kind: str = "warn") -> None:
        self.setProperty("kind", kind)
        repolish(self)
        self.label.setText(text)
        self.show()


class Switch(QWidget):
    """iOS-style toggle."""
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, on: bool) -> None:
        if on != self._checked:
            self._checked = on
            self._anim.setEndValue(1.0 if on else 0.0)
            self._anim.start()

    def mouseReleaseEvent(self, e):
        self.setChecked(not self._checked)
        self.toggled.emit(self._checked)

    def _get(self): return self._pos
    def _set(self, v): self._pos = v; self.update()
    pos = Property(float, _get, _set)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        off, on = QColor(theme.BORDER), QColor(theme.ACCENT)
        mix = lambda a, b, t: QColor(int(a.red() + (b.red() - a.red()) * t),
                                     int(a.green() + (b.green() - a.green()) * t),
                                     int(a.blue() + (b.blue() - a.blue()) * t))
        p.setPen(Qt.NoPen)
        p.setBrush(mix(off, on, self._pos))
        p.drawRoundedRect(self.rect(), 12, 12)
        p.setBrush(QColor("#FFFFFF"))
        x = 3 + (self.width() - 24) * self._pos
        p.drawEllipse(QRectF(x, 3, 18, 18))


class SliderRow(QWidget):
    """Label + help text + slider + live value."""
    changed = Signal(str, float)

    def __init__(self, key, label, lo, hi, step, fmt, help_text, value, parent=None):
        super().__init__(parent)
        self.key, self.lo, self.step, self.fmt = key, lo, step, fmt
        self._n = round((hi - lo) / step)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(4)
        top = QHBoxLayout()
        title = QLabel(label); title.setObjectName("h2")
        self.value_label = QLabel(); self.value_label.setStyleSheet(f"color:{theme.ACCENT}; font-weight:700;")
        top.addWidget(title); top.addStretch(1); top.addWidget(self.value_label)
        lay.addLayout(top)
        h = QLabel(help_text); h.setObjectName("muted"); h.setWordWrap(True)
        lay.addWidget(h)
        self.slider = NoWheelSlider(Qt.Horizontal)
        self.slider.setRange(0, self._n)
        self.slider.valueChanged.connect(self._on_change)
        lay.addWidget(self.slider)
        self.set_value(value)

    def _val(self, i: int) -> float:
        return self.lo + i * self.step

    def _on_change(self, i: int) -> None:
        v = self._val(i)
        self.value_label.setText(self.fmt.format(v))
        self.changed.emit(self.key, v)

    def set_value(self, v: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(round((v - self.lo) / self.step))
        self.slider.blockSignals(False)
        self.value_label.setText(self.fmt.format(v))


class Meter(QWidget):
    """Labelled thin progress bar."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        row = QHBoxLayout()
        self.title = QLabel(title); self.title.setObjectName("muted")
        self.value = QLabel(""); self.value.setObjectName("muted")
        row.addWidget(self.title); row.addStretch(1); row.addWidget(self.value)
        lay.addLayout(row)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        lay.addWidget(self.bar)

    def set(self, frac: float, kind: str = "", text: str = "") -> None:
        self.bar.setValue(int(min(max(frac, 0), 1) * 100))
        if self.bar.property("kind") != kind:
            self.bar.setProperty("kind", kind)
            repolish(self.bar)
        self.value.setText(text)


class VideoView(QWidget):
    """Camera preview, aspect-correct, rounded corners, with an optional overlay message."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._img: QImage | None = None
        self._overlay = ""
        self._overlay_kind = ""
        self.setMinimumSize(480, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_image(self, img: QImage | None) -> None:
        self._img = img
        self.update()

    def set_overlay(self, text: str, kind: str = "") -> None:
        if (text, kind) != (self._overlay, self._overlay_kind):
            self._overlay, self._overlay_kind = text, kind
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath(); path.addRoundedRect(r, 18, 18)
        p.setClipPath(path)
        p.fillRect(r, QColor("#05080C"))
        if self._img is not None and not self._img.isNull():
            s = self._img.size().scaled(int(r.width()), int(r.height()), Qt.KeepAspectRatio)
            target = QRectF(r.x() + (r.width() - s.width()) / 2, r.y() + (r.height() - s.height()) / 2,
                            s.width(), s.height())
            p.drawImage(target, self._img)
        if self._overlay:
            col = {"warn": theme.AMBER, "danger": theme.RED}.get(self._overlay_kind, theme.ACCENT)
            p.fillRect(r, QColor(5, 8, 12, 190))
            p.setPen(QColor(col))
            f = p.font(); f.setPointSize(16); f.setBold(True); p.setFont(f)
            p.drawText(r.adjusted(24, 0, -24, 0), Qt.AlignCenter | Qt.TextWordWrap, self._overlay)
        p.setClipping(False)
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 18, 18)


def page_header(title: str, subtitle: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(2)
    t = QLabel(title); t.setObjectName("h1")
    s = QLabel(subtitle); s.setObjectName("muted"); s.setWordWrap(True)
    lay.addWidget(t); lay.addWidget(s)
    return w
