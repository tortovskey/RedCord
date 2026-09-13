from __future__ import annotations

import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from redcord.services.theme08 import CUSTOM_THEME_KEY, THEMES_08, build_qss_08, load_custom_theme, save_custom_theme, theme_key, theme_names


TMP_ROOT = Path(__file__).resolve().parents[1] / ".redcord_test_tmp"


@contextmanager
def _temp_dir():
    TMP_ROOT.mkdir(exist_ok=True)
    path = TMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class Theme08Tests(unittest.TestCase):
    def test_has_twelve_dark_color_themes(self):
        self.assertEqual(len(THEMES_08), 12)
        self.assertIn("Dark Crimson", theme_names())
        self.assertIn("Dark Ice", theme_names())

    def test_legacy_theme_aliases_resolve(self):
        self.assertEqual(theme_key("dark_red"), "dark_crimson")
        self.assertEqual(theme_key("dark_green"), "dark_emerald")
        self.assertEqual(theme_key("unknown"), "dark_crimson")

    def test_qss_contains_editor_and_tab_styles(self):
        qss = build_qss_08("dark_cobalt")

        self.assertIn("QTextEdit#WriterEditor", qss)
        self.assertIn("QScrollArea#RibbonToolbar", qss)
        self.assertIn("QFrame#QuickBar", qss)
        self.assertIn("QFrame#RibbonTabs", qss)
        self.assertIn("QFrame#RibbonGroup", qss)
        self.assertIn("QTabBar::tab:selected", qss)
        self.assertIn("QSplitter::handle", qss)

    def test_custom_theme_can_be_saved_and_loaded(self):
        with _temp_dir() as raw:
            path = raw / "custom_theme.json"
            saved = save_custom_theme({"accent": "#12abef", "bg": "bad"}, path)
            loaded = load_custom_theme(path)

            self.assertEqual(saved["accent"], "#12abef")
            self.assertEqual(loaded["accent"], "#12abef")
            self.assertEqual(loaded["bg"], "#080608")
            self.assertEqual(theme_key(CUSTOM_THEME_KEY), CUSTOM_THEME_KEY)
            self.assertIn("#12abef", build_qss_08(CUSTOM_THEME_KEY, loaded))


if __name__ == "__main__":
    unittest.main()
