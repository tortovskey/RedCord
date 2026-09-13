from __future__ import annotations

from redcord.db.database import new_session
from redcord.db.repositories import TemplateRepository

DEFAULT_TEMPLATES: dict[str, tuple[str, str]] = {
    "character": ("Персонаж", """# Имя персонажа

## Роль
...

## Внешность
...

## Характер
...

## Биография
...

## Цели
...

## Конфликты
...

## Связи с другими персонажами
...

## Силы / способности
...

## Заметки автора
...
"""),
    "lore": ("Лор", """# Лор

## Суть
...

## История
...

## Правила мира
...

## Влияние на сюжет
...

## Заметки автора
...
"""),
    "organization": ("Организация", """# Организация

## Название
...

## Цели
...

## Структура
...

## Лидерство
...

## Союзники и враги
...
"""),
    "arc": ("Арка", """# Арка

## Завязка
...

## Главный конфликт
...

## Ключевые сцены
...

## Финал
...
"""),
    "chapter": ("Глава", """# Глава

## Краткое содержание
...

## Сцены
...

## Цель главы
...

## Итог
...
"""),
    "scene": ("Сцена", """# Сцена

## Место
...

## Участники
...

## Цель сцены
...

## Конфликт
...

## Текст сцены
...
"""),
    "timeline": ("Таймлайн", """# Таймлайн

## События
- ...

## Причины
...

## Последствия
...
"""),
    "item": ("Предмет", """# Предмет

## Описание
...

## Происхождение
...

## Свойства
...

## Роль в сюжете
...
"""),
    "ability": ("Способность", """# Способность

## Название
...

## Принцип работы
...

## Ограничения
...

## Цена использования
...
"""),
    "world": ("Мир", """# Мир

## География
...

## Культура
...

## Законы
...

## Конфликты
...
"""),
    "faction": ("Фракция", """# Фракция

## Идеология
...

## Ресурсы
...

## Представители
...

## Конфликты
...
"""),
    "note": ("Заметка", """# Заметка

...
"""),
    "concept": ("Концепт", """# Концепт

## Идея
...

## Почему это интересно
...

## Как использовать
...
"""),
}


class TemplateService:
    def ensure_default_templates(self) -> None:
        with new_session() as session:
            repo = TemplateRepository(session)
            for template_type, (name, content) in DEFAULT_TEMPLATES.items():
                repo.upsert(name=name, template_type=template_type, content=content)

    def list_templates(self) -> list[tuple[str, str]]:
        with new_session() as session:
            repo = TemplateRepository(session)
            return [(template.type, template.name) for template in repo.list()]

    def get_template_content(self, template_type: str) -> str:
        with new_session() as session:
            repo = TemplateRepository(session)
            template = repo.get_by_type(template_type)
            if template is None:
                return DEFAULT_TEMPLATES.get(template_type, ("Заметка", "# Заметка\n\n"))[1]
            return template.content

    def display_name(self, template_type: str) -> str:
        return DEFAULT_TEMPLATES.get(template_type, (template_type, ""))[0]

    def create_or_update_template(self, template_type: str, name: str, content: str) -> None:
        clean_type = template_type.strip().lower().replace(" ", "_") or "custom"
        with new_session() as session:
            TemplateRepository(session).upsert(name=name.strip() or clean_type, template_type=clean_type, content=content)

    def delete_template(self, template_type: str) -> None:
        with new_session() as session:
            repo = TemplateRepository(session)
            template = repo.get_by_type(template_type)
            if template is None:
                raise ValueError("Тип документа не найден")
            session.delete(template)
            session.commit()
