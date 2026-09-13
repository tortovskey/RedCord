from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime

from redcord.app.config import get_settings


@dataclass
class LocalAccount:
    id: str
    username: str
    display_name: str
    created_at: str
    last_login_at: str = ""


class AccountService:
    """Local-only account storage.

    Accounts are stored in data/accounts.json and do not require network auth.
    """

    def __init__(self) -> None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.data_dir / "accounts.json"

    def _read(self) -> dict:
        if not self.path.exists():
            return {"active_account_id": "", "accounts": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"active_account_id": "", "accounts": []}

    def _write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_accounts(self) -> list[LocalAccount]:
        data = self._read()
        accounts = []
        for item in data.get("accounts", []):
            accounts.append(
                LocalAccount(
                    id=str(item.get("id", "")),
                    username=str(item.get("username", "")),
                    display_name=str(item.get("display_name", "")),
                    created_at=str(item.get("created_at", "")),
                    last_login_at=str(item.get("last_login_at", "")),
                )
            )
        return accounts

    def active_account_id(self) -> str:
        return str(self._read().get("active_account_id", ""))

    def active_account(self) -> LocalAccount:
        active_id = self.active_account_id()
        accounts = self.list_accounts()
        for account in accounts:
            if account.id == active_id:
                return account
        if accounts:
            self.set_active(accounts[0].id)
            return accounts[0]
        return self.create_account("author", "Автор", set_active=True)

    def create_account(self, username: str, display_name: str, set_active: bool = True) -> LocalAccount:
        data = self._read()
        now = datetime.now().isoformat(timespec="seconds")
        account = LocalAccount(
            id=str(uuid.uuid4()),
            username=username.strip() or "author",
            display_name=display_name.strip() or username.strip() or "Автор",
            created_at=now,
            last_login_at=now,
        )
        data.setdefault("accounts", []).append(asdict(account))
        if set_active:
            data["active_account_id"] = account.id
        self._write(data)
        return account

    def set_active(self, account_id: str) -> None:
        data = self._read()
        now = datetime.now().isoformat(timespec="seconds")
        for item in data.get("accounts", []):
            if item.get("id") == account_id:
                item["last_login_at"] = now
                data["active_account_id"] = account_id
                self._write(data)
                return
        raise ValueError("Локальный аккаунт не найден")

    def delete_account(self, account_id: str) -> None:
        data = self._read()
        accounts = [a for a in data.get("accounts", []) if a.get("id") != account_id]
        data["accounts"] = accounts
        if data.get("active_account_id") == account_id:
            data["active_account_id"] = accounts[0]["id"] if accounts else ""
        self._write(data)
