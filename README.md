# RedCord 0.8.3

**RedCord Writer Desktop** is an offline-first desktop writing environment built with **Python** and **PyQt6**. It combines a WYSIWYG editor, project and concept management, lightweight versioning, an integrated art workspace, optional AI tools, and self-healing utilities in a single application designed for writers.

RedCord works locally without an internet connection. The desktop application stores its data in **SQLite**. An optional online beta backend can use **PostgreSQL** for account and synchronization features.

## Highlights

- Offline-first desktop workflow for writers.
- WYSIWYG editor with familiar Word-like formatting controls.
- Project, document, tag, category, template, and concept management.
- Built-in commit history, rollback, and branch support.
- **BoC Lite** art workspace for concept art and cover sketches.
- Optional AI assistant with mock and OpenAI-compatible providers.
- Self-healing tools for health checks, recovery, backups, and event logging.
- 12 dark themes plus a customizable dark theme.
- Optional online beta backend for authentication and synchronization.

## What's New in 0.8.3

- Updated the application version to `0.8.3`.
- Reworked the top interface into a contextual Word-like ribbon.
- Added dedicated ribbon sections: `Home`, `Insert`, `Art`, `Review`, `View`, and `Settings`.
- Kept ribbon commands, shortcuts, tooltips, and Help Center entries synchronized through `CommandRegistry`.
- Improved BoC Lite with a cleaner service layer, canvas presets, composition grid, and fill tool.
- Focused art workflows on concept art, book covers, comic covers, and manga covers.
- Added persistent custom dark theme colors in `data/custom_theme.json`.
- Kept 12 Dark Color's themes, with `Dark Crimson` as the default.

## Run RedCord

```powershell
python -m redcord.app.main
```

The primary 0.8.x local database is stored in:

```text
data/redcord_08.db
```

User data that should be preserved during updates includes:

```text
data/
commits/
.env
data/redcord.db
data/redcord_08.db
data/settings.json
data/custom_theme.json
data/ai_settings.json
data/accounts.json
data/branches.json
data/redcord.log
```

## Main Workspace

### Documents

Create and manage projects and documents, organize them with tags and categories, use autosave and Save As, import files or folders, export to PDF, search and replace text, view statistics, and insert writer blocks.

### Concepts

Create, edit, save, delete, and convert concepts into full documents.

### Art / BoC Lite

Create quick visual assets for writing projects, including:

- concept art;
- book covers;
- comic covers;
- manga covers.

BoC Lite includes brush, eraser, fill, line, rectangle, ellipse, color picker, brush size controls, composition grid, canvas presets, undo, clear canvas, image import, save, and PNG export.

It is intentionally lightweight: BoC Lite is designed for sketches, concepts, and cover drafts rather than professional digital painting.

Art metadata is stored in `data/redcord_08.db`, while exported and saved images are kept in:

```text
data/art_assets/
```

### Git / Versions

RedCord includes an internal versioning workflow with commits, history preview, rename, delete, rollback, and branches.

### AI Agent

The AI tab can work with the current document or selection and supports inserting, replacing, or creating content in a new document.

Supported providers:

- `mock` — default local provider that works offline;
- `openai_compatible` — configurable OpenAI-compatible endpoint.

AI settings are stored locally in:

```text
data/ai_settings.json
```

API keys are not stored in source code and are not written to application logs. If an API key is saved through the UI, it is stored locally in the user's RedCord data files.

### Self-Healing

The Self-Healing workspace provides health checks, recovery tools, backups, outbox testing, and system event information.

### Settings

Settings include themes, custom dark colors, profile/account options, templates, ZIP updates, synchronization, and help.

## Ribbon Interface

The top interface is organized as a compact contextual ribbon.

- **Quick bar** — save, undo, redo, new document, find, export PDF, art actions, and focus mode.
- **Home** — file, document, editing, and formatting commands.
- **Insert** — writer blocks and concepts.
- **Art** — BoC Lite canvas tools and cover presets.
- **Review** — commits, rollback, and branches.
- **View** — side panels, focus mode, compact mode, and font size.
- **Settings** — themes, custom theme, updates, synchronization, and help.

Ribbon commands are defined through:

```text
redcord/services/command_registry.py
```

## Formatting Shortcuts

Formatting is WYSIWYG and works as toggleable On/Off tools.

```text
Ctrl+B        Bold On/Off
Ctrl+I        Italic On/Off
Ctrl+U        Underline On/Off
Ctrl+Alt+1    H1 On/Off
Ctrl+Alt+2    H2 On/Off
Ctrl+Alt+3    H3 On/Off
Ctrl+Shift+8  Bullet list On/Off
Ctrl+Shift+7  Numbered list On/Off
```

## Themes

RedCord includes 12 dark themes. `Dark Crimson` is the default.

To create a custom palette, open the application settings, select `Custom Dark`, edit the colors, and save the custom theme.

The custom palette is stored locally in:

```text
data/custom_theme.json
```

## Build EXE

```powershell
scripts\build_exe.bat
```

Expected output:

```text
redcord_build\redcord\RedCord.exe
```

## Build Installer

```powershell
scripts\build_installer.bat
```

Expected output:

```text
installer_output\RedCord_Setup_0_8_3.exe
```

The installer contains only **RedCord Writer Desktop**. It does not install the optional beta backend, PostgreSQL, or Docker, and updates must preserve user data.

## Online Beta Backend

The online backend is optional and distributed separately from the desktop installer.

```powershell
docker compose -f docker-compose.backend.yml up --build
```

Available endpoints:

```text
GET  /health
POST /auth/request-code
POST /auth/verify-code
POST /sync/status
POST /sync/pull
POST /sync/push
```

Authentication uses an email code. In development mode, if SMTP is not configured, the code is written to backend logs.

## Update ZIP Manifest

RedCord 0.8 update archives may include a `redcord_update_manifest.json` file:

```json
{
  "version": "0.8.3",
  "min_version": "0.8.2",
  "migration_required": false,
  "files": [
    {
      "path": "redcord/__init__.py",
      "sha256": "..."
    }
  ]
}
```

Before applying an update, RedCord backs up current application files to `data/update_backups/`, validates the manifest, preserves `data/`, `commits/`, and `.env`, writes `data/update.log`, and in EXE mode stages the update through `apply_update.bat`.

## Migration from 0.7.x

On the first 0.8.x launch, RedCord checks for the legacy `data/redcord.db` database, creates a backup, and imports compatible projects, documents, concepts, commits, templates, accounts, and branches into `data/redcord_08.db`.

The original database is not modified. Migration is a one-way import into the 0.8 schema.

## Tests

```powershell
python -m compileall redcord tests
python -m unittest discover -s tests
```

If `pytest` is installed:

```powershell
pytest
```

## Known Limitations

- BoC Lite is intended for quick sketches and cover concepts, not full professional digital painting.
- Online accounts and synchronization are still beta features.
- Real email delivery requires SMTP configuration; development mode writes the verification code to backend logs.
- The desktop installer does not include PostgreSQL or Docker.
- The editor provides a Word-like WYSIWYG workflow but is not intended to replicate the full Microsoft Word feature set.
