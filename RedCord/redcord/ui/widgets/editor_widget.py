from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class EditorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.editor = QPlainTextEdit()
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)

    def get_text(self) -> str:
        return self.editor.toPlainText()

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text)
