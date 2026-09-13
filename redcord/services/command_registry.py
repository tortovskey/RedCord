from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    id: str
    group: str
    label: str
    shortcut: str
    tooltip: str
    help_text: str


class CommandRegistry:
    def __init__(self) -> None:
        self.commands = _default_commands()

    def by_id(self, command_id: str) -> Command:
        return self.commands[command_id]

    def groups(self) -> dict[str, list[Command]]:
        grouped: dict[str, list[Command]] = {}
        for command in self.commands.values():
            grouped.setdefault(command.group, []).append(command)
        return grouped

    def help_markdown(self) -> str:
        sections = ["# RedCord Help Center", ""]
        for group, commands in self.groups().items():
            sections.append(f"## {group}")
            for command in commands:
                shortcut = f" (`{command.shortcut}`)" if command.shortcut else ""
                sections.append(f"- **{command.label}**{shortcut}: {command.help_text}")
            sections.append("")
        return "\n".join(sections)


def _default_commands() -> dict[str, Command]:
    rows = [
        ("new_project", "File / Document", "Новый проект", "Ctrl+Shift+N", "Создать проект", "Создаёт новый писательский проект."),
        ("new_document", "File / Document", "Новый документ", "Ctrl+N", "Создать документ", "Создаёт HTML-документ в текущем проекте."),
        ("save", "File / Document", "Сохранить", "Ctrl+S", "Сохранить", "Сохраняет HTML и plain text текущего документа."),
        ("save_as", "File / Document", "Сохранить как", "Ctrl+Shift+S", "Сохранить как HTML", "Экспортирует текущий документ в HTML."),
        ("import_file", "File / Document", "Импорт файла", "Ctrl+O", "Импорт файла", "Импортирует txt, md, html или docx в текущий проект."),
        ("import_folder", "File / Document", "Импорт папки", "", "Импорт папки", "Импортирует текстовые файлы из папки в текущий проект."),
        ("export_pdf", "File / Document", "Экспорт PDF", "Ctrl+P", "Экспорт PDF", "Печатает текущий QTextDocument в PDF."),
        ("commit", "File / Document", "Коммит", "Ctrl+Alt+C", "Создать snapshot", "Создаёт локальный Git-like снимок документа."),
        ("undo", "Edit", "Undo", "Ctrl+Z", "Отменить", "Отменяет последнее действие редактора."),
        ("redo", "Edit", "Redo", "Ctrl+Y", "Повторить", "Повторяет отменённое действие."),
        ("cut", "Edit", "Cut", "Ctrl+X", "Вырезать", "Вырезает выделенный текст."),
        ("copy", "Edit", "Copy", "Ctrl+C", "Копировать", "Копирует выделенный текст."),
        ("paste", "Edit", "Paste", "Ctrl+V", "Вставить", "Вставляет текст из буфера."),
        ("select_all", "Edit", "Select All", "Ctrl+A", "Выделить всё", "Выделяет весь текст документа."),
        ("find", "Edit", "Найти", "Ctrl+F", "Найти", "Ищет текст в текущем документе."),
        ("replace", "Edit", "Replace", "Ctrl+H", "Заменить", "Заменяет текущее найденное совпадение."),
        ("replace_all", "Edit", "Replace All", "", "Заменить всё", "Заменяет все совпадения в документе."),
        ("bold", "Format", "Bold", "Ctrl+B", "Жирный On/Off", "Переключает жирное начертание в WYSIWYG редакторе."),
        ("italic", "Format", "Italic", "Ctrl+I", "Курсив On/Off", "Переключает курсив."),
        ("underline", "Format", "Underline", "Ctrl+U", "Подчёркивание On/Off", "Переключает подчёркивание."),
        ("strike", "Format", "Strike", "", "Зачёркивание On/Off", "Переключает зачёркивание."),
        ("h1", "Format", "H1", "Ctrl+Alt+1", "Заголовок 1 On/Off", "Переключает стиль H1 или возвращает обычный текст."),
        ("h2", "Format", "H2", "Ctrl+Alt+2", "Заголовок 2 On/Off", "Переключает стиль H2 или возвращает обычный текст."),
        ("h3", "Format", "H3", "Ctrl+Alt+3", "Заголовок 3 On/Off", "Переключает стиль H3 или возвращает обычный текст."),
        ("bullet_list", "Format", "List", "Ctrl+Shift+8", "Маркированный список On/Off", "Переключает маркированный список."),
        ("numbered_list", "Format", "Numbered", "Ctrl+Shift+7", "Нумерованный список On/Off", "Переключает нумерованный список."),
        ("quote", "Format", "Quote", "", "Цитата On/Off", "Переключает оформление цитаты для текущего блока."),
        ("separator", "Format", "Separator", "", "Разделитель", "Вставляет горизонтальный разделитель."),
        ("table", "Format", "Table", "", "Таблица", "Вставляет простую таблицу 2x2."),
        ("scene", "Writer", "Сцена", "", "Вставить сцену", "Вставляет структурированный блок сцены."),
        ("dialogue", "Writer", "Диалог", "", "Вставить диалог", "Вставляет заготовку диалога."),
        ("author_note", "Writer", "Заметка автора", "", "Заметка автора", "Вставляет заметку автора."),
        ("character_card", "Writer", "Карточка", "", "Карточка персонажа", "Вставляет карточку персонажа."),
        ("chapter_plan", "Writer", "План главы", "", "План главы", "Вставляет план главы."),
        ("beat_sheet", "Writer", "Beat-sheet", "", "Beat-sheet", "Вставляет beat-sheet."),
        ("stats", "Writer", "Статистика", "", "Статистика", "Показывает слова, символы и примерное время чтения."),
        ("new_concept", "Concepts", "Новый концепт", "", "Новый концепт", "Создаёт концепт в текущем проекте."),
        ("save_concept", "Concepts", "Сохранить концепт", "", "Сохранить концепт", "Сохраняет HTML и plain text концепта."),
        ("delete_concept", "Concepts", "Удалить концепт", "", "Удалить концепт", "Мягко удаляет выбранный концепт."),
        ("convert_concept", "Concepts", "В документ", "", "В документ", "Создаёт документ из выбранного концепта."),
        ("new_art", "Art / BoC Lite", "Новый арт", "Ctrl+Alt+A", "Новый арт", "Очищает холст BoC Lite для concept art или обложки."),
        ("save_art", "Art / BoC Lite", "Сохранить арт", "Ctrl+Alt+S", "Сохранить арт", "Сохраняет PNG и карточку арта в проекте."),
        ("export_art", "Art / BoC Lite", "Экспорт PNG", "", "Экспорт PNG", "Экспортирует текущий холст в PNG."),
        ("clear_canvas", "Art / BoC Lite", "Очистить", "", "Очистить холст", "Очищает холст BoC Lite."),
        ("brush_tool", "Art / BoC Lite", "Кисть", "", "Кисть", "Включает кисть."),
        ("eraser_tool", "Art / BoC Lite", "Ластик", "", "Ластик", "Включает ластик."),
        ("fill_tool", "Art / BoC Lite", "Заливка", "", "Заливка", "Включает заливку фона выбранным цветом."),
        ("toggle_art_grid", "Art / BoC Lite", "Сетка", "", "Сетка композиции", "Показывает или скрывает композиционную сетку."),
        ("apply_art_preset", "Art / BoC Lite", "Размер", "", "Размер холста", "Применяет выбранный preset размера для арта или обложки."),
        ("commit_history", "Git / Versions", "История", "", "История коммитов", "Показывает историю локальных снимков."),
        ("preview_commit", "Git / Versions", "Preview", "", "Preview", "Показывает содержимое выбранного коммита."),
        ("rename_commit", "Git / Versions", "Rename", "", "Rename", "Переименовывает выбранный коммит."),
        ("delete_commit", "Git / Versions", "Delete", "", "Delete", "Мягко удаляет выбранный коммит."),
        ("rollback_commit", "Git / Versions", "Rollback", "", "Rollback", "Откатывает документ к выбранному коммиту."),
        ("new_branch", "Git / Versions", "Новая ветка", "", "Новая ветка", "Создаёт альтернативный снимок текущего документа."),
        ("save_branch", "Git / Versions", "Save branch", "", "Save branch", "Сохраняет текущий документ в выбранную ветку."),
        ("checkout_branch", "Git / Versions", "Checkout", "", "Checkout", "Загружает выбранную ветку в документ."),
        ("delete_branch", "Git / Versions", "Delete branch", "", "Delete branch", "Мягко удаляет выбранную ветку."),
        ("template_manager", "Settings", "Шаблоны", "", "Шаблоны", "Открывает управление шаблонами."),
        ("custom_theme", "Settings", "Custom color", "", "Кастомный цвет", "Открывает настройки кастомной тёмной темы."),
        ("update_dialog", "Settings", "Обновление", "", "Обновление", "Открывает обновление из ZIP."),
        ("sync_status", "Settings", "Sync status", "", "Sync status", "Проверяет состояние online beta sync."),
        ("toggle_left", "View", "Left panel", "", "Левая панель", "Скрывает или показывает левую панель документов."),
        ("toggle_right", "View", "Right panel", "", "Правая панель", "Скрывает или показывает правую панель документов."),
        ("compact", "View", "Compact", "", "Compact Mode", "Переключает плотный режим интерфейса."),
        ("focus", "View", "Focus", "F11", "Focus Mode", "Скрывает боковые панели и оставляет редактор."),
        ("font_increase", "View", "A+", "Ctrl+=", "Увеличить шрифт", "Увеличивает шрифт редактора."),
        ("font_decrease", "View", "A-", "Ctrl+-", "Уменьшить шрифт", "Уменьшает шрифт редактора."),
        ("help", "View", "Help", "F1", "Справка", "Открывает auto documentation."),
    ]
    return {row[0]: Command(*row) for row in rows}
