from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "dark_red": {
        "name": "Dark Red",
        "bg": "#080607",
        "panel": "#121012",
        "panel2": "#1b1416",
        "text": "#f3ecee",
        "muted": "#b9a9ad",
        "accent": "#7e1b29",
        "accent2": "#b93649",
        "border": "#2c1d21",
        "selection": "#45111b",
        "success": "#8fe388",
        "danger": "#ff6b6b",
    },
    "dark_green": {
        "name": "Dark Green",
        "bg": "#07100c",
        "panel": "#101a15",
        "panel2": "#17251d",
        "text": "#e8f2ed",
        "muted": "#9fb6aa",
        "accent": "#197146",
        "accent2": "#26a365",
        "border": "#20382b",
        "selection": "#12452d",
        "success": "#8fe388",
        "danger": "#ff8a8a",
    },
    "dark_blue": {
        "name": "Dark Blue",
        "bg": "#080d15",
        "panel": "#111827",
        "panel2": "#172033",
        "text": "#e8edf7",
        "muted": "#9daecb",
        "accent": "#1f4f91",
        "accent2": "#2f75d6",
        "border": "#24324f",
        "selection": "#173969",
        "success": "#8fe388",
        "danger": "#ff8a8a",
    },
    "dark": {
        "name": "Dark",
        "bg": "#090909",
        "panel": "#151515",
        "panel2": "#202020",
        "text": "#f0f0f0",
        "muted": "#a8a8a8",
        "accent": "#626262",
        "accent2": "#8d8d8d",
        "border": "#303030",
        "selection": "#3a3a3a",
        "success": "#8fe388",
        "danger": "#ff7777",
    },
    "white": {
        "name": "White",
        "bg": "#f4f1eb",
        "panel": "#ffffff",
        "panel2": "#f7f3ed",
        "text": "#1d1719",
        "muted": "#756a70",
        "accent": "#a73b4a",
        "accent2": "#c84a5b",
        "border": "#ded2d6",
        "selection": "#f0cdd4",
        "success": "#197146",
        "danger": "#b42333",
    },
    "dark_purple": {
        "name": "Dark Purple",
        "bg": "#0d0914",
        "panel": "#171021",
        "panel2": "#21162f",
        "text": "#f0e8ff",
        "muted": "#b8a7d1",
        "accent": "#6b3fa0",
        "accent2": "#9b63d4",
        "border": "#342447",
        "selection": "#3d2361",
        "success": "#8fe388",
        "danger": "#ff7aa8",
    },
    "dark_rose": {
        "name": "Dark Rose",
        "bg": "#14090d",
        "panel": "#211016",
        "panel2": "#301722",
        "text": "#ffe8ee",
        "muted": "#d1a7b4",
        "accent": "#9f3157",
        "accent2": "#d04a78",
        "border": "#472434",
        "selection": "#61233d",
        "success": "#8fe388",
        "danger": "#ff7777",
    },
}


def theme_names() -> list[str]:
    return [THEMES[key]["name"] for key in THEMES]


def key_by_name(name: str) -> str:
    for key, theme in THEMES.items():
        if theme["name"] == name:
            return key
    return "dark_red"


def display_name_by_key(key: str) -> str:
    return THEMES.get(key, THEMES["dark_red"])["name"]


def build_qss(theme_key: str) -> str:
    t = THEMES.get(theme_key, THEMES["dark_red"])
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
        border-radius: 8px;
    }}
    QGroupBox {{
        margin-top: 10px;
        padding-top: 10px;
    }}
    QGroupBox::title {{
        color: {t['muted']};
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    QLabel#TitleLabel {{
        color: {t['text']};
        font-size: 12pt;
        font-weight: 700;
        background: transparent;
    }}
    QLabel#SectionLabel {{
        color: {t['muted']};
        font-size: 8.5pt;
        font-weight: 700;
        text-transform: uppercase;
        background: transparent;
    }}
    QLabel#MutedLabel {{
        color: {t['muted']};
        background: transparent;
    }}
    QLabel#SuccessLabel {{
        color: {t['success']};
        font-weight: 700;
        padding: 2px 6px;
        background: transparent;
    }}
    QPushButton {{
        background: {t['panel2']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 4px 8px;
        min-height: 22px;
        color: {t['text']};
    }}
    QPushButton:hover {{
        background: {t['selection']};
        border-color: {t['accent2']};
    }}
    QPushButton:pressed {{
        background: {t['selection']};
    }}
    QPushButton#AccentButton {{
        background: {t['accent']};
        border-color: {t['accent2']};
        font-weight: 700;
    }}
    QPushButton#DangerButton:hover {{
        background: {t['danger']};
        color: #ffffff;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListWidget {{
        background: {t['panel2']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {t['selection']};
        selection-color: {t['text']};
    }}
    QLineEdit, QComboBox {{
        min-height: 22px;
    }}
    QTextEdit {{
        line-height: 135%;
    }}
    QTextEdit#MainDocumentEditor {{
        background: {t['bg']};
        border-color: {t['border']};
        padding: 10px;
    }}
    QListWidget::item {{
        padding: 4px 6px;
        border-radius: 5px;
    }}
    QListWidget::item:hover {{
        background: {t['panel']};
    }}
    QListWidget::item:selected {{
        background: {t['selection']};
        border-left: 3px solid {t['accent2']};
    }}
    QTreeWidget {{
        background: {t['panel2']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {t['selection']};
    }}
    QTreeWidget::item {{
        padding: 4px 6px;
    }}
    QTreeWidget::item:selected {{
        background: {t['selection']};
        border-left: 3px solid {t['accent2']};
    }}
    QComboBox QAbstractItemView {{
        background: {t['panel2']};
        selection-background-color: {t['selection']};
    }}
    QMenuBar {{
        background: {t['bg']};
        color: {t['text']};
        border-bottom: 1px solid {t['border']};
    }}
    QMenuBar::item {{
        background: transparent;
        color: {t['text']};
        padding: 6px 10px;
    }}
    QMenuBar::item:selected {{
        background: {t['panel2']};
        color: {t['text']};
    }}
    QMenu {{
        background: {t['panel']};
        color: {t['text']};
        border: 1px solid {t['border']};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 5px 18px;
    }}
    QMenu::item:selected {{
        background: {t['selection']};
    }}
    QTabWidget::pane {{
        background: {t['bg']};
        border: 1px solid {t['border']};
        top: -1px;
    }}
    QTabWidget {{
        background: {t['bg']};
    }}
    QTabBar {{
        background: {t['bg']};
        color: {t['text']};
    }}
    QTabBar::tab {{
        background: {t['panel']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-bottom: none;
        padding: 5px 12px;
        min-width: 88px;
    }}
    QTabBar::tab:selected {{
        background: {t['panel2']};
        color: {t['text']};
        border-top: 2px solid {t['accent2']};
    }}
    QTabBar::tab:hover {{
        background: {t['selection']};
        color: {t['text']};
    }}
    QTabBar::tab:!selected {{
        background: {t['bg']};
        color: {t['muted']};
    }}
    QToolBar {{
        background: {t['panel']};
        border-bottom: 1px solid {t['border']};
        spacing: 4px;
        padding: 3px;
    }}
    QScrollArea#RibbonToolbar {{
        background: {t['panel']};
        border-bottom: 1px solid {t['border']};
    }}
    QWidget#RibbonContent {{
        background: {t['panel']};
    }}
    QFrame#RibbonGroup {{
        background: {t['panel2']};
        border: 1px solid {t['border']};
        border-radius: 7px;
    }}
    QLabel#RibbonGroupTitle {{
        color: {t['muted']};
        font-size: 8pt;
        font-weight: 700;
        background: transparent;
    }}
    QToolButton {{
        background: {t['panel']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        padding: 3px 6px;
        color: {t['text']};
    }}
    QToolButton:hover {{
        background: {t['selection']};
        border-color: {t['accent2']};
    }}
    QToolButton:pressed {{
        background: {t['accent']};
    }}
    QStatusBar {{
        background: {t['panel']};
        color: {t['muted']};
        border-top: 1px solid {t['border']};
        padding: 2px 6px;
    }}
    QSplitter::handle {{
        background: {t['border']};
        width: 3px;
        height: 3px;
    }}
    QScrollBar:vertical {{
        background: {t['bg']};
        width: 12px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']};
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['accent']};
    }}
    """
