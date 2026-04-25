# RedCord

**RedCord** — desktop-only редактор для писателей с упором на отказоустойчивость и self-healing.

## Тема проекта
«Проектирование отказоустойчивой распределённой информационной системы с использованием паттернов self-healing».

> Важно: RedCord не является VPN и не является web-сайтом. Это локальное desktop-приложение на PyQt6 + PostgreSQL.

## Архитектура
- **Desktop UI**: PyQt6 (вкладки Editor, Concepts, Versions, AI, Health, Settings)
- **Core**: конфигурация, пути, логирование, обработка ошибок
- **Data layer**: SQLAlchemy 2.x + psycopg 3 + Alembic
- **Service layer**: documents, versions, autosave, backup, recovery, integrity, AI mock
- **Self-healing monitor**: health dashboard + failure simulation
- **Launcher**: C# .NET 8 WPF (проверка среды, запуск/перезапуск, recovery)

## Основные возможности
- Проекты, документы, концепты, шаблоны
- Встроенная version control система (snapshot + diff + rollback)
- Autosave каждые 10 секунд (по умолчанию)
- Backup/Recovery center
- Integrity check по SHA-256
- AI Assistant mock (без внешнего API)
- Health dashboard + безопасные simulation-кнопки

## Установка PostgreSQL (Windows)
1. Установите PostgreSQL 15+.
2. Создайте пользователя `redcord_user` и пароль `redcord_password` (или свои значения).
3. Создайте БД `redcord`.
4. Разрешите локальные подключения на `localhost:5432`.

## Настройка окружения
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
```

Отредактируйте `.env` при необходимости.

## Инициализация БД
```bat
scripts\init_db.bat
```
Скрипт применяет миграции Alembic и выполняет проверку подключения.

## Запуск приложения
```bat
scripts\run_redcord.bat
```
Или напрямую:
```bash
python -m redcord.main
```

## CLI режим
- `python -m redcord.main --health-check`
- `python -m redcord.main --backup-now`
- `python -m redcord.main --recovery-check`
- `python -m redcord.main --init-templates`

## Сборка EXE (PyInstaller)
```bat
scripts\build_exe.bat
```

## C# Launcher
Сборка и запуск:
```bat
scripts\build_launcher.bat
scripts\run_launcher.bat
```

Функции лаунчера:
- проверка PostgreSQL
- проверка наличия RedCord.exe / Python entrypoint
- запуск desktop-приложения
- фиксация падения и предложение перезапуска
- запуск recovery-check
- launcher logs (`logs/launcher.log`)

## Как работает self-healing
1. **Autosave**: периодически сохраняет draft в `autosaves`.
2. **Integrity**: на чтении документа сверяет hash.
3. **Backup**: снапшоты проекта в `data/backups`.
4. **Recovery**:
   - из autosave
   - из backup
   - из последней stable version
5. **Health Dashboard**: агрегирует статус БД, autosave, backup, integrity, AI и watchdog.

## Demo-сценарий для защиты
1. Создать проект.
2. Создать документ Character по шаблону.
3. Отредактировать текст.
4. Дождаться autosave.
5. Создать commit.
6. Посмотреть историю версий.
7. Сравнить версии.
8. Откатиться к stable версии.
9. Создать концепт в Concept Vault.
10. Запросить у AI mock улучшение текста.
11. Открыть Health dashboard.
12. Нажать `Corrupt current document`.
13. Выполнить `Restore from stable version`.
14. Собрать `RedCord.exe`.
