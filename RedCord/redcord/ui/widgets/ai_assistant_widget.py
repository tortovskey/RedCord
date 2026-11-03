from PyQt6.QtWidgets import QPushButton, QTextEdit, QVBoxLayout, QWidget


class AIAssistantWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.improve_btn = QPushButton("AI: Improve text")
        self.suggest_btn = QPushButton("AI: Suggest ideas")
        layout = QVBoxLayout(self)
        layout.addWidget(self.improve_btn)
        layout.addWidget(self.suggest_btn)
        layout.addWidget(self.output)
