from __future__ import annotations

import json
import re
from pathlib import Path

from redcord.app.config import get_settings

CUSTOM_THEME_KEY = "custom_dark"

THEMES_08: dict[str, dict[str, str]] = {
    "dark_crimson": {"name": "Dark Crimson", "bg": "#080608", "panel": "#141012", "surface": "#1f1518", "text": "#f5eef0", "muted": "#b9a9ad", "accent": "#b93649", "border": "#352026"},
    "dark_emerald": {"name": "Dark Emerald", "bg": "#050b08", "panel": "#0e1712", "surface": "#14251b", "text": "#eef7f2", "muted": "#9fbaaa", "accent": "#27a66b", "border": "#20382b"},
    "dark_cobalt": {"name": "Dark Cobalt", "bg": "#050912", "panel": "#0d1320", "surface": "#151f34", "text": "#edf3ff", "muted": "#a6b6d1", "accent": "#3b82f6", "border": "#24324f"},
    "dark_violet": {"name": "Dark Violet", "bg": "#090612", "panel": "#130e1f", "surface": "#201633", "text": "#f3ecff", "muted": "#b8a7d1", "accent": "#9b63d4", "border": "#342447"},
    "dark_rose": {"name": "Dark Rose", "bg": "#10060a", "panel": "#1b0f14", "surface": "#2a1620", "text": "#ffeef3", "muted": "#d1a7b4", "accent": "#d04a78", "border": "#472434"},
    "dark_amber": {"name": "Dark Amber", "bg": "#0d0904", "panel": "#171107", "surface": "#251a0a", "text": "#fff6e8", "muted": "#c3ae8c", "accent": "#d9902f", "border": "#403017"},
    "dark_cyan": {"name": "Dark Cyan", "bg": "#041012", "panel": "#0a181b", "surface": "#10262a", "text": "#eaffff", "muted": "#9fc1c7", "accent": "#22b8cf", "border": "#1d3a40"},
    "dark_graphite": {"name": "Dark Graphite", "bg": "#070707", "panel": "#121212", "surface": "#1d1d1d", "text": "#f0f0f0", "muted": "#ababab", "accent": "#8a8f98", "border": "#303030"},
    "dark_teal": {"name": "Dark Teal", "bg": "#04100f", "panel": "#0b1917", "surface": "#102923", "text": "#ecfffb", "muted": "#9bbdb6", "accent": "#2dd4bf", "border": "#1e3d38"},
    "dark_magenta": {"name": "Dark Magenta", "bg": "#100512", "panel": "#1a0d1d", "surface": "#291532", "text": "#fdeeff", "muted": "#c7a4ce", "accent": "#c026d3", "border": "#43214b"},
    "dark_copper": {"name": "Dark Copper", "bg": "#0f0704", "panel": "#1a100b", "surface": "#2a1a12", "text": "#fff0e8", "muted": "#c4a294", "accent": "#b86b3a", "border": "#43271a"},
    "dark_ice": {"name": "Dark Ice", "bg": "#061014", "panel": "#0f181f", "surface": "#172733", "text": "#f0fbff", "muted": "#a8bdc8", "accent": "#7dd3fc", "border": "#2b4250"},
}

DEFAULT_CUSTOM_THEME = {
    "name": "Custom Dark",
    "bg": "#080608",
    "panel": "#141012",
    "surface": "#1f1518",
    "text": "#f5eef0",
    "muted": "#b9a9ad",
    "accent": "#b93649",
    "border": "#352026",
}

LEGACY_THEME_ALIASES = {
    "dark_red": "dark_crimson",
    "dark_green": "dark_emerald",
    "dark_blue": "dark_cobalt",
    "dark": "dark_graphite",
    "white": "dark_ice",
    "dark_purple": "dark_violet",
}

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def custom_theme_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    return get_settings().data_dir / "custom_theme.json"


def normalize_color(value: str, fallback: str) -> str:
    value = str(value).strip()
    if HEX_RE.match(value):
        return value.lower()
    return fallback


def load_custom_theme(path: str | Path | None = None) -> dict[str, str]:
    target = custom_theme_path(path)
    if not target.exists():
        return dict(DEFAULT_CUSTOM_THEME)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CUSTOM_THEME)
    if not isinstance(data, dict):
        return dict(DEFAULT_CUSTOM_THEME)
    theme = dict(DEFAULT_CUSTOM_THEME)
    for key in ["bg", "panel", "surface", "text", "muted", "accent", "border"]:
        theme[key] = normalize_color(str(data.get(key, "")), theme[key])
    theme["name"] = str(data.get("name") or "Custom Dark")
    return theme


def save_custom_theme(theme: dict[str, str], path: str | Path | None = None) -> dict[str, str]:
    clean = dict(DEFAULT_CUSTOM_THEME)
    clean["name"] = str(theme.get("name") or "Custom Dark")
    for key in ["bg", "panel", "surface", "text", "muted", "accent", "border"]:
        clean[key] = normalize_color(str(theme.get(key, "")), clean[key])
    target = custom_theme_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return clean


def theme_key(key: str | None) -> str:
    if not key:
        return "dark_crimson"
    if key == CUSTOM_THEME_KEY:
        return CUSTOM_THEME_KEY
    return key if key in THEMES_08 else LEGACY_THEME_ALIASES.get(key, "dark_crimson")


def resolve_theme(key: str | None, custom_theme: dict[str, str] | None = None) -> dict[str, str]:
    resolved = theme_key(key)
    if resolved == CUSTOM_THEME_KEY:
        return dict(custom_theme or load_custom_theme())
    return THEMES_08[resolved]


def theme_names(include_custom: bool = False) -> list[str]:
    names = [theme["name"] for theme in THEMES_08.values()]
    if include_custom:
        names.append(DEFAULT_CUSTOM_THEME["name"])
    return names


def build_qss_08(key: str | None, custom_theme: dict[str, str] | None = None) -> str:
    t = resolve_theme(key, custom_theme)
    return f"""
    QWidget {{
        background: {t['bg']};
        color: {t['text']};
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 10pt;
    }}
    QMainWindow, QDialog {{
        background: {t['bg']};
    }}
    QFrame#Panel, QGroupBox {{
        background: {t['panel']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        margin: 0px;
    }}
    QGroupBox {{
        padding: 8px;
        margin-top: 16px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: {t['muted']};
        background: {t['bg']};
    }}
    QScrollArea#RibbonToolbar {{
        background: {t['panel']};
        border: 0px;
        border-bottom: 1px solid {t['border']};
    }}
    QWidget#RibbonContent, QFrame#QuickBar, QFrame#RibbonTabs, QWidget#RibbonGroupRow {{
        background: {t['panel']};
    }}
    QFrame#QuickBar {{
        border: 0px;
        border-bottom: 1px solid {t['border']};
    }}
    QFrame#RibbonTabs {{
        border: 0px;
        border-bottom: 1px solid {t['border']};
    }}
    QLabel#QuickBarTitle {{
        color: {t['text']};
        background: transparent;
        font-weight: 700;
        font-size: 11pt;
    }}
    QLineEdit#RibbonCommandHint {{
        background: {t['bg']};
        color: {t['muted']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 2px 7px;
        min-height: 21px;
    }}
    QToolButton#QuickBarButton {{
        background: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 3px 6px;
        min-height: 22px;
    }}
    QToolButton#RibbonTabButton {{
        background: transparent;
        border: 0px;
        border-bottom: 2px solid transparent;
        border-radius: 0px;
        padding: 5px 12px;
        min-height: 24px;
        color: {t['muted']};
        font-weight: 600;
    }}
    QToolButton#RibbonTabButton:hover {{
        color: {t['text']};
        background: {t['accent']}22;
    }}
    QToolButton#RibbonTabButton:checked {{
        color: {t['text']};
        background: {t['surface']};
        border-bottom: 2px solid {t['accent']};
    }}
    QToolButton#QuickBarButton:hover, QToolButton#RibbonButton:hover {{
        background: {t['accent']}33;
        border-color: {t['accent']};
        color: #ffffff;
    }}
    QToolButton#QuickBarButton:checked, QToolButton#RibbonButton:checked {{
        background: {t['accent']}66;
        border-color: {t['accent']};
        color: #ffffff;
    }}
    QFrame#RibbonGroup {{
        background: {t['surface']};
        border: 1px solid {t['border']};
        border-left: 2px solid {t['accent']};
        border-radius: 6px;
    }}
    QLabel#RibbonGroupTitle {{
        color: {t['muted']};
        background: transparent;
        font-size: 8.5pt;
        font-weight: 600;
    }}
    QLabel#TitleLabel {{
        color: {t['text']};
        font-size: 12pt;
        font-weight: 700;
        background: transparent;
    }}
    QLabel#MutedLabel, QLabel#SectionLabel {{
        color: {t['muted']};
        background: transparent;
    }}
    QPushButton, QToolButton {{
        background: {t['surface']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        padding: 4px 7px;
        min-height: 23px;
    }}
    QPushButton:hover, QToolButton:hover {{
        background: {t['accent']}33;
        border-color: {t['accent']};
        color: #ffffff;
    }}
    QPushButton#AccentButton {{
        background: {t['accent']};
        color: #ffffff;
        border-color: {t['accent']};
        font-weight: 600;
    }}
    QPushButton#DangerButton {{
        color: #ffb4b4;
    }}
    QToolButton#RibbonButton {{
        min-width: 34px;
        max-width: 132px;
        text-align: left;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListWidget, QSpinBox, QSlider {{
        background: {t['surface']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        padding: 4px;
        selection-background-color: {t['accent']};
    }}
    QListWidget#CompactList::item {{
        min-height: 20px;
        padding: 3px 5px;
        border-left: 2px solid transparent;
    }}
    QListWidget#CompactList::item:selected {{
        background: {t['accent']}44;
        border-left: 2px solid {t['accent']};
    }}
    QTextEdit#WriterEditor, QTextEdit#MainDocumentEditor {{
        background: #f7f3ea;
        color: #181214;
        border: 1px solid #d0c7b8;
        border-radius: 4px;
        padding: 18px 22px;
        font-size: 12pt;
        selection-background-color: {t['accent']};
    }}
    QWidget#ArtCanvas {{
        background: #101010;
        border: 1px solid {t['border']};
        border-radius: 5px;
    }}
    QTabWidget::pane {{
        border: 0px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: {t['panel']};
        color: {t['muted']};
        border: 1px solid {t['border']};
        border-bottom: 0px;
        padding: 6px 13px;
        min-height: 22px;
    }}
    QTabBar::tab:selected {{
        color: {t['text']};
        background: {t['surface']};
        border-top: 2px solid {t['accent']};
    }}
    QTabBar::tab:hover {{
        color: {t['text']};
        background: {t['accent']}22;
    }}
    QSplitter::handle {{
        background: {t['border']};
        width: 3px;
        height: 3px;
    }}
    QMenuBar, QMenu {{
        background: {t['panel']};
        color: {t['text']};
        border: 1px solid {t['border']};
    }}
    QStatusBar {{
        background: {t['panel']};
        color: {t['muted']};
        border-top: 1px solid {t['border']};
    }}
    """
