from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextStatistics:
    words: int
    characters: int
    characters_no_spaces: int
    paragraphs: int
    scene_markers: int
    reading_minutes: int

    def as_status_text(self) -> str:
        return (
            f"Слов: {self.words} | Символов: {self.characters} | "
            f"Без пробелов: {self.characters_no_spaces} | Абзацев: {self.paragraphs} | "
            f"Сцен: {self.scene_markers} | Чтение: ~{self.reading_minutes} мин."
        )


WRITER_BLOCKS: dict[str, str] = {
    "scene": (
        "\n---\n\n"
        "## Сцена\n\n"
        "**Цель сцены:** ...\n\n"
        "**Конфликт:** ...\n\n"
        "**Поворот:** ...\n\n"
        "**Последствие:** ...\n\n"
    ),
    "dialogue": "\n- Персонаж: ...\n- Другой персонаж: ...\n",
    "author_note": "\n> [!NOTE] Заметка автора: ...\n",
    "character_card": (
        "\n## Карточка персонажа\n\n"
        "**Имя:** ...\n"
        "**Роль в истории:** ...\n"
        "**Цель:** ...\n"
        "**Страх:** ...\n"
        "**Секрет:** ...\n"
        "**Арка:** ...\n"
    ),
    "chapter_plan": (
        "\n## План главы\n\n"
        "1. Крючок\n"
        "2. Цель героя\n"
        "3. Препятствие\n"
        "4. Выбор\n"
        "5. Последствие\n"
        "6. Переход к следующей главе\n"
    ),
    "beat_sheet": (
        "\n## Beat-sheet\n\n"
        "- Opening image:\n"
        "- Theme stated:\n"
        "- Catalyst:\n"
        "- Debate:\n"
        "- Break into two:\n"
        "- Midpoint:\n"
        "- Crisis:\n"
        "- Finale:\n"
    ),
}


def selection_to_plain_text(text: str) -> str:
    return text.replace("\u2029", "\n")


def wrap_text(text: str, before: str, after: str, placeholder: str = "текст") -> str:
    value = selection_to_plain_text(text)
    return f"{before}{value or placeholder}{after}"


def prefix_lines(text: str, prefix: str) -> str:
    value = selection_to_plain_text(text)
    if not value:
        return prefix
    return "\n".join(prefix + line if line.strip() else line for line in value.splitlines())


def number_lines(text: str) -> str:
    value = selection_to_plain_text(text)
    if not value:
        return "1. "
    counter = 1
    lines: list[str] = []
    for line in value.splitlines():
        if line.strip():
            lines.append(f"{counter}. {line.strip()}")
            counter += 1
        else:
            lines.append(line)
    return "\n".join(lines)


def replace_all(text: str, find_text: str, replace_text: str) -> tuple[str, int]:
    if not find_text:
        return text, 0
    return text.replace(find_text, replace_text), text.count(find_text)


def clear_markdown_marks(text: str) -> str:
    cleaned = selection_to_plain_text(text)
    for token in ["**", "~~", "*", "<u>", "</u>"]:
        cleaned = cleaned.replace(token, "")
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^>\s?", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
    return cleaned


def text_statistics(text: str) -> TextStatistics:
    words = re.findall(r"\b[\wА-Яа-яЁё-]+\b", text, flags=re.UNICODE)
    paragraphs = len([paragraph for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()])
    scene_markers = text.count("\n---") + text.count("# Сцена") + text.count("## Сцена")
    reading_minutes = max(1, round(len(words) / 180)) if words else 0
    return TextStatistics(
        words=len(words),
        characters=len(text),
        characters_no_spaces=len(text.replace(" ", "").replace("\n", "").replace("\t", "")),
        paragraphs=paragraphs,
        scene_markers=scene_markers,
        reading_minutes=reading_minutes,
    )
