from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class HealthDashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.status = QLabel("Health: unknown")
        self.sim_crash = QPushButton("Simulate editor crash")
        self.corrupt_doc = QPushButton("Corrupt current document")
        self.disable_db = QPushButton("Disable database connection mock")
        self.restore_autosave = QPushButton("Restore from autosave")
        self.restore_stable = QPushButton("Restore from stable version")
        self.create_backup = QPushButton("Create backup now")
        layout = QVBoxLayout(self)
        for w in [self.status, self.sim_crash, self.corrupt_doc, self.disable_db, self.restore_autosave, self.restore_stable, self.create_backup]:
            layout.addWidget(w)

    def set_status_text(self, text: str):
        self.status.setText(text)
