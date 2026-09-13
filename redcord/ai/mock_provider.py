from __future__ import annotations

import re

from redcord.ai.base import AIResponse, AISettings
from redcord.ai.prompts import get_prompt


class MockAIProvider:
    name = "mock"

    def generate(self, action: str, text: str, settings: AISettings) -> AIResponse:
        source = self._normalize(text)
        handlers = {
            "improve_text": self._improve_text,
            "fix_style": self._fix_style,
            "vivid": self._vivid,
            "shorten": self._shorten,
            "expand": self._expand,
            "summarize": self._summarize,
            "contradictions": self._contradictions,
            "scene_development": self._scene_development,
            "chapter_title": self._chapter_title,
            "character_questions": self._character_questions,
            "rewrite_tone": self._rewrite_tone,
            "check_dialogues": self._check_dialogues,
            "chapter_plan": self._chapter_plan,
            "beat_sheet": self._beat_sheet,
            "character_card": self._character_card,
        }
        prompt = get_prompt(action)
        result = handlers.get(action, self._improve_text)(source)
        return AIResponse(action=action, title=prompt.title, text=result, provider=self.name)

    def test_connection(self, settings: AISettings) -> str:
        return "MockAIProvider работает локально, интернет и API key не нужны."

    def _improve_text(self, text: str) -> str:
        cleaned = re.sub(r"\b(очень|просто|как бы|в общем|на самом деле)\s+", "", text, flags=re.IGNORECASE)
        return (
            cleaned.strip()
            + "\n\n[Редакторская заметка] Проверь ритм фраз, повторы имен, силу глаголов и точку зрения."
        )

    def _fix_style(self, text: str) -> str:
        cleaned = self._improve_text(text).split("\n\n[Редакторская заметка]", 1)[0]
        return (
            cleaned
            + "\n\n## Что проверить вручную\n"
            "- Повторы одинаковых вводных слов.\n"
            "- Слабые глаголы вроде «был», «стал», «казалось».\n"
            "- Длинные предложения без драматической необходимости.\n"
            "- Места, где действие можно показать через поступок."
        )

    def _vivid(self, text: str) -> str:
        return (
            text
            + "\n\n## Усиление живости\n"
            "- Добавь одну конкретную деталь места, которую персонаж замечает из-за своего состояния.\n"
            "- Замени нейтральную эмоцию действием тела или выбором.\n"
            "- Дай сцене маленький звук, запах или предмет, который работает на атмосферу.\n"
            "- Заверши абзац движением, решением или новым вопросом."
        )

    def _shorten(self, text: str) -> str:
        sentences = self._sentences(text)
        if len(sentences) <= 2:
            return text
        keep = max(1, round(len(sentences) * 0.55))
        return " ".join(sentences[:keep])

    def _expand(self, text: str) -> str:
        return (
            (text or "Сцена пока пустая.")
            + "\n\n## Расширение\n"
            "- Чего герой хочет прямо сейчас?\n"
            "- Что мешает ему получить это немедленно?\n"
            "- Какая цена у выбранного действия?\n"
            "- Что меняется к концу сцены?\n\n"
            "Добавь один абзац действия, один абзац внутреннего напряжения и один короткий обмен репликами."
        )

    def _summarize(self, text: str) -> str:
        sentences = self._sentences(text)
        if not sentences:
            return "Текст пустой."
        summary = sentences[:3]
        return "\n".join(f"- {sentence}" for sentence in summary)

    def _contradictions(self, text: str) -> str:
        lower = text.lower()
        markers = {
            "время": ["вчера", "сегодня", "завтра", "утром", "ночью", "вечером"],
            "мотивация": ["хочет", "боится", "цель", "ненавидит", "любит"],
            "локация": ["комната", "город", "лес", "дом", "улица"],
            "правила мира": ["может", "нельзя", "правило", "способность", "магия", "сила"],
        }
        lines = ["## Возможные зоны проверки"]
        for title, words in markers.items():
            found = [word for word in words if word in lower]
            lines.append(f"- {title}: найдено маркеров {len(found)} ({', '.join(found) if found else 'нет'}).")
        lines.extend(
            [
                "",
                "## Вопросы",
                "- Не меняется ли цель персонажа без причины?",
                "- Совпадают ли время, место и состояние персонажей?",
                "- Есть ли последствия у важных решений?",
                "- Не нарушены ли ранее заявленные правила мира?",
            ]
        )
        return "\n".join(lines)

    def _scene_development(self, text: str) -> str:
        return (
            "## Развитие сцены\n"
            "1. Начни с конкретной цели героя.\n"
            "2. Дай препятствие, которое нельзя обойти разговором.\n"
            "3. Усиль конфликт через выбор между двумя потерями.\n"
            "4. Покажи маленькую победу или ошибку.\n"
            "5. Заверши сцену изменением информации, отношений или риска.\n\n"
            f"## Опора из текущего текста\n{self._normalize(text)[:1200]}"
        )

    def _chapter_title(self, text: str) -> str:
        words = [w.strip(".,!?;:()[]«»\"'").capitalize() for w in text.split() if len(w) > 4]
        base: list[str] = []
        for word in words:
            if word and word not in base:
                base.append(word)
            if len(base) >= 4:
                break
        if len(base) < 2:
            base = ["Тихий", "След", "Граница", "Выбор"]
        ideas = [
            f"{base[0]} и {base[1]}",
            f"После {base[0].lower()}",
            f"Граница {base[-1].lower()}",
            "Точка невозврата",
            "Цена выбора",
            "Когда дверь закрылась",
            "Последний спокойный день",
            "Невидимый долг",
            "Пока никто не смотрит",
            "Там, где начинается страх",
        ]
        return "\n".join(f"- {idea}" for idea in ideas)

    def _character_questions(self, text: str) -> str:
        return (
            "## Вопросы персонажу\n"
            "- Чего ты хочешь прямо сейчас?\n"
            "- Что ты боишься признать даже себе?\n"
            "- Что ты никогда не простишь?\n"
            "- Кого ты защищаешь, хотя делаешь вид, что тебе все равно?\n"
            "- Какая привычка выдает твое прошлое?\n"
            "- Какой выбор сломает твою старую версию?\n\n"
            f"## Контекст\n{self._normalize(text)[:1200]}"
        )

    def _rewrite_tone(self, text: str) -> str:
        return (
            "## Мрачнее\n"
            f"{text}\n\n"
            "## Теплее\n"
            f"{text}\n\n"
            "## Напряженнее\n"
            f"{text}\n\n"
            "[Mock] Это каркас вариантов тона. Подключи openai_compatible provider для полноценной переписи."
        )

    def _check_dialogues(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append("")
            elif stripped.startswith(("-", "—")):
                lines.append("- " + stripped.lstrip("-— ").strip())
            else:
                lines.append(stripped)
        return (
            "\n".join(lines)
            + "\n\n## Проверка диалогов\n"
            "- У каждой реплики должна быть цель.\n"
            "- Голоса персонажей должны отличаться словарем и длиной фраз.\n"
            "- Подтекст сильнее прямого объяснения.\n"
            "- После важной реплики должно что-то измениться."
        )

    def _chapter_plan(self, text: str) -> str:
        return (
            "## План главы\n"
            "1. Крючок: событие или образ, который сразу задает вопрос.\n"
            "2. Цель героя: что нужно получить до конца главы.\n"
            "3. Давление: препятствие, дедлайн или личная цена.\n"
            "4. Поворот: новая информация меняет смысл происходящего.\n"
            "5. Выбор: герой действует и платит цену.\n"
            "6. Выход: новое состояние мира или отношений.\n"
            "7. Крючок следующей главы.\n\n"
            f"## Материал\n{self._normalize(text)[:1000]}"
        )

    def _beat_sheet(self, text: str) -> str:
        return (
            "## Beat-sheet\n"
            "- Opening image: текущая жизнь героя.\n"
            "- Theme stated: главный вопрос главы.\n"
            "- Catalyst: событие, которое нельзя игнорировать.\n"
            "- Debate: сомнение или попытка избежать действия.\n"
            "- Break into action: герой делает выбор.\n"
            "- Midpoint: победа с подвохом или поражение с новой возможностью.\n"
            "- Bad guys close in: давление растет.\n"
            "- Crisis: самое дорогое оказывается под угрозой.\n"
            "- Finale: действие, меняющее расстановку сил.\n"
            "- Final image: контраст с началом."
        )

    def _character_card(self, text: str) -> str:
        return (
            "## Карточка персонажа\n"
            "**Имя:** ...\n\n"
            "**Роль в истории:** ...\n\n"
            "**Внешняя цель:** ...\n\n"
            "**Внутренняя потребность:** ...\n\n"
            "**Страх:** ...\n\n"
            "**Секрет:** ...\n\n"
            "**Слабость:** ...\n\n"
            "**Сильная сторона:** ...\n\n"
            "**Арка:** ...\n\n"
            f"**Подсказки из текста:** {self._normalize(text)[:700]}"
        )

    def _normalize(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _sentences(self, text: str) -> list[str]:
        cleaned = self._normalize(text)
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?…])\s+", cleaned) if sentence.strip()]
