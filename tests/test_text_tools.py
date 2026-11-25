from __future__ import annotations

import unittest

from redcord.services.text_tools import number_lines, prefix_lines, replace_all, text_statistics, wrap_text


class TextToolsTests(unittest.TestCase):
    def test_wrap_text_uses_placeholder_for_empty_selection(self):
        self.assertEqual(wrap_text("", "**", "**"), "**текст**")

    def test_number_lines_numbers_only_content_lines(self):
        self.assertEqual(number_lines("alpha\n\nbeta"), "1. alpha\n\n2. beta")

    def test_replace_all_returns_count(self):
        result, count = replace_all("one two one", "one", "three")
        self.assertEqual(result, "three two three")
        self.assertEqual(count, 2)

    def test_formatting_keeps_the_final_paragraph_boundary(self):
        for separator in ("\n", "\r\n", "\r", "\u2028", "\u2029"):
            with self.subTest(separator=separator):
                selected = separator.join(["first", "second", "", ""])
                self.assertEqual(number_lines(selected), "1. first\n2. second\n\n")
                self.assertEqual(prefix_lines(selected, "> "), "> first\n> second\n\n")

    def test_text_statistics_counts_words_and_reading_time(self):
        stats = text_statistics("Глава первая\n\nГерой идет домой.")
        self.assertEqual(stats.words, 5)
        self.assertEqual(stats.paragraphs, 2)
        self.assertEqual(stats.reading_minutes, 1)
