from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QSplashScreen

from redcord import __version__

SPLASH_TEXT = "Всё что тебе нужно — это лишь фантазия и ReC"


def build_splash_pixmap(width: int = 760, height: int = 430) -> QPixmap:
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#080608"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0, QColor("#080608"))
    gradient.setColorAt(0.45, QColor("#1f1518"))
    gradient.setColorAt(1, QColor("#551824"))
    painter.fillRect(0, 0, width, height, gradient)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(185, 54, 73, 180))
    painter.drawEllipse(width - 260, -80, 360, 360)
    painter.setBrush(QColor(125, 27, 41, 150))
    painter.drawEllipse(-100, height - 210, 330, 330)

    painter.setPen(QColor("#f5eef0"))
    title_font = QFont("Segoe UI", 46, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(54, 142, "RedCord")

    painter.setPen(QColor("#b9a9ad"))
    subtitle_font = QFont("Segoe UI", 17)
    painter.setFont(subtitle_font)
    painter.drawText(58, 186, f"Writer Desktop {__version__}")

    painter.setPen(QColor("#f5eef0"))
    quote_font = QFont("Segoe UI", 14)
    painter.setFont(quote_font)
    painter.drawText(58, 284, SPLASH_TEXT)

    painter.setPen(QColor("#b93649"))
    painter.setBrush(QColor("#b93649"))
    painter.drawRoundedRect(58, 322, width - 116, 5, 3, 3)

    painter.end()
    return pixmap


def create_splash() -> QSplashScreen:
    splash = QSplashScreen(build_splash_pixmap())
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    splash.showMessage(
        f"Запуск RedCord {__version__}...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#f5eef0"),
    )
    return splash
