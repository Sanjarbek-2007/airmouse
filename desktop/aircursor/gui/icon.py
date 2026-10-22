"""App icon, drawn in code so there are no binary assets to ship."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from . import theme


def make_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor(theme.ACCENT))
    g.setColorAt(1, QColor(theme.ACCENT2))
    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92), size * 0.24, size * 0.24)
    # pointer arrow
    s = size
    path = QPainterPath()
    path.moveTo(QPointF(s * 0.34, s * 0.22))
    path.lineTo(QPointF(s * 0.34, s * 0.72))
    path.lineTo(QPointF(s * 0.47, s * 0.60))
    path.lineTo(QPointF(s * 0.57, s * 0.80))
    path.lineTo(QPointF(s * 0.65, s * 0.76))
    path.lineTo(QPointF(s * 0.55, s * 0.57))
    path.lineTo(QPointF(s * 0.72, s * 0.57))
    path.closeSubpath()
    p.setBrush(QColor("#04121A"))
    p.drawPath(path)
    # signal arcs
    pen = QPen(QColor("#04121A"), s * 0.035, Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(s * 0.52, s * 0.14, s * 0.30, s * 0.30), 20 * 16, 80 * 16)
    p.drawArc(QRectF(s * 0.46, s * 0.08, s * 0.42, s * 0.42), 20 * 16, 80 * 16)
    p.end()
    return pm


def app_icon() -> QIcon:
    return QIcon(make_pixmap(256))


def write_arrow(path) -> str:
    """Down-arrow glyph for combo boxes (Qt stylesheets need an image file)."""
    pm = QPixmap(24, 24)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(theme.MUTED), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline([QPointF(6, 9), QPointF(12, 15), QPointF(18, 9)])
    p.end()
    pm.save(str(path), "PNG")
    return str(path)
