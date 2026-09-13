from __future__ import annotations

import unittest

from redcord.services.command_registry import CommandRegistry


class CommandRegistryTests(unittest.TestCase):
    def test_registry_contains_core_word_like_commands(self):
        registry = CommandRegistry()

        for command_id in [
            "save",
            "import_file",
            "bold",
            "italic",
            "underline",
            "h1",
            "scene",
            "new_concept",
            "new_art",
            "save_art",
            "fill_tool",
            "toggle_art_grid",
            "apply_art_preset",
            "rollback_commit",
            "new_branch",
            "template_manager",
            "custom_theme",
            "compact",
            "focus",
            "help",
        ]:
            self.assertIn(command_id, registry.commands)

        self.assertEqual(registry.by_id("save").shortcut, "Ctrl+S")
        self.assertEqual(registry.by_id("focus").shortcut, "F11")

    def test_help_markdown_is_generated_from_registry(self):
        help_text = CommandRegistry().help_markdown()

        self.assertIn("File / Document", help_text)
        self.assertIn("Format", help_text)
        self.assertIn("Writer", help_text)
        self.assertIn("Art / BoC Lite", help_text)
        self.assertIn("Git / Versions", help_text)
        self.assertIn("Ctrl+S", help_text)


if __name__ == "__main__":
    unittest.main()
