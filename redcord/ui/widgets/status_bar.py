from __future__ import annotations

from PyQt6.QtWidgets import QStatusBar


class RedCordStatusBar(QStatusBar):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("RedCordStatusBar")
        self.showMessage("Готово")
