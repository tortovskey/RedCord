from __future__ import annotations

import unittest

from redcord.services.html_tools import plain_to_html


class HtmlToolsTests(unittest.TestCase):
    def test_plain_text_becomes_safe_paragraph_html(self):
        html = plain_to_html("Hello <world>\nline two\n\nNext")

        self.assertIn("<p>Hello &lt;world&gt;<br>line two</p>", html)
        self.assertIn("<p>Next</p>", html)


if __name__ == "__main__":
    unittest.main()
