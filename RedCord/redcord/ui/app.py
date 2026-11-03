import sys

from PyQt6.QtWidgets import QApplication

from redcord.ui.main_window import RedCordMainWindow


def run_app() -> int:
    app = QApplication(sys.argv)
    window = RedCordMainWindow()
    window.show()
    return app.exec()
