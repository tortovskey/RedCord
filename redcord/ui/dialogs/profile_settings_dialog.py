from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from redcord.app.theme import key_by_name, theme_names, display_name_by_key
from redcord.services.account_service import AccountService
from redcord.services.settings_service import SettingsService, UserSettings


class ProfileSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Профиль и настройки")
        self.resize(500, 280)

        self.settings_service = SettingsService()
        self.account_service = AccountService()
        self.current = self.settings_service.load()

        self.account_combo = QComboBox()
        self.reload_accounts()

        self.new_account_btn = QPushButton("Новый аккаунт")
        self.delete_account_btn = QPushButton("Удалить аккаунт")
        self.new_account_btn.clicked.connect(self.create_account)
        self.delete_account_btn.clicked.connect(self.delete_account)

        account_buttons = QHBoxLayout()
        account_buttons.addWidget(self.new_account_btn)
        account_buttons.addWidget(self.delete_account_btn)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(theme_names())
        self.theme_combo.setCurrentText(display_name_by_key(self.current.theme))
        self.autosave_checkbox = QCheckBox("Включить автосохранение")
        self.autosave_checkbox.setChecked(self.current.autosave_enabled)

        hint = QLabel(
            "Локальные аккаунты хранятся в data/accounts.json. "
            "Тема и автосохранение сохраняются в data/settings.json."
        )
        hint.setWordWrap(True)
        hint.setObjectName("MutedLabel")

        form = QFormLayout()
        form.addRow("Аккаунт", self.account_combo)
        form.addRow("", account_buttons)
        form.addRow("Тема", self.theme_combo)
        form.addRow("", self.autosave_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def reload_accounts(self) -> None:
        self.account_combo.clear()
        active_id = self.account_service.active_account().id
        for account in self.account_service.list_accounts():
            self.account_combo.addItem(f"{account.display_name} @{account.username}", account.id)
            if account.id == active_id:
                self.account_combo.setCurrentIndex(self.account_combo.count() - 1)

    def create_account(self) -> None:
        username, ok = QInputDialog.getText(self, "Новый аккаунт", "Логин:")
        if not ok or not username.strip():
            return
        display_name, ok = QInputDialog.getText(
            self,
            "Новый аккаунт",
            "Имя профиля:",
            text=username.strip(),
        )
        if not ok:
            return
        account = self.account_service.create_account(username.strip(), display_name.strip(), set_active=True)
        self.reload_accounts()
        for i in range(self.account_combo.count()):
            if self.account_combo.itemData(i) == account.id:
                self.account_combo.setCurrentIndex(i)
                break

    def delete_account(self) -> None:
        account_id = self.account_combo.currentData()
        if not account_id:
            return
        self.account_service.delete_account(str(account_id))
        self.reload_accounts()

    def values(self) -> tuple[UserSettings, str]:
        account_id = str(self.account_combo.currentData() or "")
        display_name = self.account_combo.currentText().split(" @")[0] or "Автор"
        return (
            UserSettings(
                profile_name=display_name,
                theme=key_by_name(self.theme_combo.currentText()),
                autosave_enabled=self.autosave_checkbox.isChecked(),
            ),
            account_id,
        )
