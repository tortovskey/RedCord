from __future__ import annotations

import os
import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFont, QTextCursor  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from redcord.storage.sqlite_store import SQLiteStore  # noqa: E402
from redcord.ui.main_window_08 import MainWindow08  # noqa: E402


TMP_ROOT = Path(__file__).resolve().parents[1] / ".redcord_test_tmp"


@contextmanager
def _temp_dir():
    TMP_ROOT.mkdir(exist_ok=True)
    path = TMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir()
    old_data_dir = os.environ.get("DATA_DIR")
    os.environ["DATA_DIR"] = str(path / "data")
    try:
        yield path
    finally:
        if old_data_dir is None:
            os.environ.pop("DATA_DIR", None)
        else:
            os.environ["DATA_DIR"] = old_data_dir
        shutil.rmtree(path, ignore_errors=True)


class FormatToggleUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_bold_command_toggles_on_and_off(self):
        with _temp_dir() as tmp:
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            window = MainWindow08(store)
            window.editor.setPlainText("hello")
            cursor = window.editor.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            window.editor.setTextCursor(cursor)

            window.run_command("bold")
            self.assertGreaterEqual(window.editor.currentCharFormat().fontWeight(), QFont.Weight.Bold)

            window.run_command("bold")
            self.assertLess(window.editor.currentCharFormat().fontWeight(), QFont.Weight.Bold)
            window.close()


if __name__ == "__main__":
    unittest.main()
