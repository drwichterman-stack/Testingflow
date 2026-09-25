"""Product logo, app icon, and splash screen, drawn in code (no image files)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import QSplashScreen

from .. import config


def logo_pixmap(size: int = 128) -> QPixmap:
    """A shield (protection) with a clipboard check (assessment)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 100.0
    shield = QPainterPath()
    shield.moveTo(50 * s, 4 * s)
    shield.lineTo(90 * s, 18 * s)
    shield.cubicTo(90 * s, 58 * s, 74 * s, 82 * s, 50 * s, 96 * s)
    shield.cubicTo(26 * s, 82 * s, 10 * s, 58 * s, 10 * s, 18 * s)
    shield.closeSubpath()
    grad = QLinearGradient(QPointF(0, 0), QPointF(0, size))
    grad.setColorAt(0, QColor("#2f78c8"))
    grad.setColorAt(1, QColor("#14375f"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(shield)
    # Clipboard
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(31 * s, 26 * s, 38 * s, 46 * s), 5 * s, 5 * s)
    p.setBrush(QColor("#9fc3ea"))
    p.drawRoundedRect(QRectF(41 * s, 21 * s, 18 * s, 9 * s), 3 * s, 3 * s)
    # Check mark
    pen = QPen(QColor("#1b7a4b"), 6 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    check = QPainterPath()
    check.moveTo(39 * s, 50 * s)
    check.lineTo(47 * s, 58 * s)
    check.lineTo(61 * s, 41 * s)
    p.drawPath(check)
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for sz in (16, 32, 64, 128, 256, 512):
        icon.addPixmap(logo_pixmap(sz))
    return icon


def splash() -> QSplashScreen:
    w, h = 560, 320
    pm = QPixmap(w, h)
    pm.fill(QColor("#14253b"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawPixmap(40, 90, logo_pixmap(140))
    p.setPen(QColor("#ffffff"))
    f = QFont()
    f.setPointSize(30)
    f.setBold(True)
    p.setFont(f)
    p.drawText(200, 150, config.APP_NAME)
    f.setPointSize(12)
    f.setBold(False)
    p.setFont(f)
    p.setPen(QColor("#c5d1e0"))
    p.drawText(202, 182, config.APP_TAGLINE)
    p.drawText(202, 206, f"Version {config.APP_VERSION}")
    f.setPointSize(9)
    p.setFont(f)
    p.setPen(QColor("#8ea2bb"))
    p.drawText(40, 290, f"{config.COPYRIGHT}  |  Local-only. Encrypted with AES-256.")
    p.end()
    sp = QSplashScreen(pm)
    return sp
