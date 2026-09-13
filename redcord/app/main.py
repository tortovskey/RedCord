from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from redcord import __version__
from redcord.app.config import get_settings
from redcord.services.importer_07 import Legacy07Importer
from redcord.services.settings_service import SettingsService
from redcord.services.theme08 import build_qss_08, theme_key
from redcord.storage.sqlite_store import SQLiteStore
from redcord.ui.main_window_08 import MainWindow08
from redcord.ui.splash import create_splash


def configure_logging() -> None:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(settings.log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def ensure_runtime_dirs() -> None:
    settings = get_settings()
    for path in [settings.data_dir, settings.commit_dir, settings.assets_dir]:
        Path(path).mkdir(parents=True, exist_ok=True)


def _load_app_icon() -> QIcon:
    settings = get_settings()
    icon_path = settings.assets_dir / "redcord_icon.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    png_fallback = settings.assets_dir / "redcord_icon.png"
    if png_fallback.exists():
        return QIcon(str(png_fallback))
    return QIcon()


def bootstrap_08() -> tuple[SQLiteStore | None, str]:
    settings = get_settings()
    ensure_runtime_dirs()
    store = SQLiteStore(settings.client_db_file)
    try:
        store.initialize()
        importer = Legacy07Importer(
            store=store,
            legacy_db=settings.data_dir / "redcord.db",
            backup_dir=settings.data_dir / "migration_backups",
        )
        report = importer.import_once()
        logging.info("Legacy import: %s", report)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Failed to bootstrap RedCord 0.8.3")
        return None, f"Не удалось подготовить RedCord 0.8.3: {exc}"
    return store, "ok"


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("RedCord")
    app.setApplicationDisplayName(f"RedCord {__version__}")
    app.setWindowIcon(_load_app_icon())

    settings = get_settings()
    user_settings = SettingsService().load()
    app.setStyleSheet(build_qss_08(theme_key(user_settings.theme or settings.default_theme)))

    splash = create_splash()
    splash.show()
    app.processEvents()
    splash.showMessage("Инициализация локальной SQLite 0.8.3...")
    app.processEvents()

    store, message = bootstrap_08()
    if store is None:
        splash.close()
        QMessageBox.critical(None, f"RedCord {__version__}: ошибка запуска", message)
        logging.error("Startup failed: %s", message)
        return 1

    splash.showMessage("Загрузка HTML WYSIWYG редактора...")
    app.processEvents()
    window = MainWindow08(store)
    window.show()
    splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
