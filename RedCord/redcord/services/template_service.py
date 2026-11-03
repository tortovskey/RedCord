from pathlib import Path

TEMPLATE_MAP = {
    "character": "character.md",
    "lore": "lore.md",
    "world": "world.md",
    "chapter": "chapter.md",
    "faction": "faction.md",
    "concept": "concept.md",
}


class TemplateService:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir

    def load_template(self, template_name: str) -> str:
        file_name = TEMPLATE_MAP.get(template_name.lower())
        if not file_name:
            return "# New Document\n"
        path = self.templates_dir / file_name
        return path.read_text(encoding="utf-8") if path.exists() else "# New Document\n"
