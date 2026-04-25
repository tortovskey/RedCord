from PyQt6.QtWidgets import QListWidget, QVBoxLayout, QWidget


class VersionHistoryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)

    def set_versions(self, versions: list[str]):
        self.list.clear()
        self.list.addItems(versions)
