from PyQt6.QtWidgets import QListWidget, QPushButton, QVBoxLayout, QWidget


class ConceptVaultWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.list = QListWidget()
        self.create_btn = QPushButton("New Concept")
        layout = QVBoxLayout(self)
        layout.addWidget(self.create_btn)
        layout.addWidget(self.list)
