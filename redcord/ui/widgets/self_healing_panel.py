from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from redcord.self_healing.backup_service import BackupService
from redcord.self_healing.event_log import SystemEventLog
from redcord.self_healing.health_checks import HealthCheckService
from redcord.self_healing.outbox import OutboxStore
from redcord.self_healing.recovery_manager import RecoveryManager


class SelfHealingPanel(QWidget):
    """Self-healing dashboard for the RedCord desktop core."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.health = HealthCheckService()
        self.recovery = RecoveryManager()
        self.backup = BackupService()
        self.events = SystemEventLog()
        self.outbox = OutboxStore()

        self.status_list = QListWidget()
        self.status_list.setObjectName("CompactList")
        self.event_view = QTextEdit()
        self.event_view.setReadOnly(True)

        self.check_btn = QPushButton("Проверить здоровье")
        self.repair_btn = QPushButton("Self-healing repair")
        self.backup_btn = QPushButton("Создать backup")
        self.outbox_btn = QPushButton("Тест outbox")
        self.refresh_events_btn = QPushButton("Обновить события")

        self.check_btn.clicked.connect(self.run_health_checks)
        self.repair_btn.clicked.connect(self.run_recovery)
        self.backup_btn.clicked.connect(self.create_backup)
        self.outbox_btn.clicked.connect(self.queue_outbox_test)
        self.refresh_events_btn.clicked.connect(self.refresh_events)

        header = QLabel("Self-Healing / Distributed-ready core")
        header.setObjectName("TitleLabel")
        hint = QLabel(
            "Health checks, retry-ready слой, circuit breaker, outbox, backups, event log и recovery manager. "
            "Это desktop-ядро, готовое к online beta sync."
        )
        hint.setWordWrap(True)
        hint.setObjectName("MutedLabel")

        buttons = QHBoxLayout()
        for button in [self.check_btn, self.repair_btn, self.backup_btn, self.outbox_btn, self.refresh_events_btn]:
            buttons.addWidget(button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(header)
        layout.addWidget(hint)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Health checks"))
        layout.addWidget(self.status_list, 1)
        layout.addWidget(QLabel("System events"))
        layout.addWidget(self.event_view, 1)
        self.run_health_checks()
        self.refresh_events()

    def run_health_checks(self) -> None:
        self.status_list.clear()
        for status in self.health.run_all():
            prefix = "[OK]" if status.ok else "[FAIL]"
            self.status_list.addItem(QListWidgetItem(f"{prefix} {status.name}: {status.message}"))

    def run_recovery(self) -> None:
        _statuses, actions = self.recovery.run_recovery()
        self.run_health_checks()
        self.refresh_events()
        if actions:
            QMessageBox.information(self, "Self-healing", "Выполнено:\n" + "\n".join(actions))
        else:
            QMessageBox.information(self, "Self-healing", "Проверка завершена. Исправления не потребовались.")

    def create_backup(self) -> None:
        path = self.backup.create_backup(reason="manual-ui")
        self.refresh_events()
        QMessageBox.information(self, "Backup", f"Backup создан:\n{path}")

    def queue_outbox_test(self) -> None:
        event = self.outbox.enqueue("diagnostic.ping", {"source": "self-healing-panel"})
        self.refresh_events()
        QMessageBox.information(self, "Outbox", f"Тестовое событие добавлено:\n{event.id}")

    def refresh_events(self) -> None:
        lines = []
        for event in self.events.tail(80):
            details = f" {event.details}" if event.details else ""
            lines.append(f"[{event.created_at}] {event.level} {event.source}: {event.message}{details}")
        self.event_view.setPlainText("\n".join(lines))
