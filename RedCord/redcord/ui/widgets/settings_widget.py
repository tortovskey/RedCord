from PyQt6.QtWidgets import QComboBox, QFormLayout, QSpinBox, QWidget


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light", "RedCord", "Matrix"])
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(3, 300)
        self.autosave_interval.setValue(10)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 48)
        self.font_size.setValue(12)

        layout = QFormLayout(self)
        layout.addRow("Theme", self.theme)
        layout.addRow("Autosave interval (s)", self.autosave_interval)
        layout.addRow("Font size", self.font_size)
