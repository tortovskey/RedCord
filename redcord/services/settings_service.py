from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from redcord.app.config import get_settings


@dataclass
class UserSettings:
    profile_name: str = "Автор"
    theme: str = "dark_crimson"
    autosave_enabled: bool = True


class SettingsService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.settings.settings_file

    def load(self) -> UserSettings:
        if not self.path.exists():
            value = UserSettings(theme=self.settings.default_theme)
            self.save(value)
            return value
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return UserSettings(
                profile_name=str(data.get("profile_name") or "Автор"),
                theme=str(data.get("theme") or self.settings.default_theme),
                autosave_enabled=bool(data.get("autosave_enabled", True)),
            )
        except Exception:
            value = UserSettings(theme=self.settings.default_theme)
            self.save(value)
            return value

    def save(self, value: UserSettings) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(value), ensure_ascii=False, indent=2), encoding="utf-8")

    def update_theme(self, theme: str) -> UserSettings:
        value = self.load()
        value.theme = theme
        self.save(value)
        return value

    def update_profile(self, profile_name: str, theme: str, autosave_enabled: bool) -> UserSettings:
        value = UserSettings(
            profile_name=profile_name.strip() or "Автор",
            theme=theme,
            autosave_enabled=autosave_enabled,
        )
        self.save(value)
        return value
