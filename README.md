# RedCord 0.8.3

RedCord Writer Desktop - offline-first desktop editor for writers on Python + PyQt6.
Version 0.8.3 keeps the 0.8 architecture, polishes the top Word-like ribbon,
continues BoC Lite as an internal RedCord art tab, and improves the visual layer
without adding any external legacy product.

The desktop client works locally without internet. SQLite is used by the app;
PostgreSQL is used only by the optional online beta backend.

## What's New In 0.8.3

- Version updated to `0.8.3`; installer output is `RedCord_Setup_0_8_3.exe`.
- Reworked the top bar into a contextual Word-like ribbon: quick actions stay
  visible, while command groups are split into `Home`, `Insert`, `Art`,
  `Review`, `View`, and `Settings`.
- Ribbon buttons, shortcuts, tooltips and Help Center are still generated from
  `CommandRegistry`, so documentation follows the real UI commands.
- BoC Lite gained a cleaner service layer, canvas presets, composition grid and
  fill tool.
- Art sections remain focused on writer assets: concept art, book covers, comic
  covers and manga covers.
- Custom dark theme colors are saved locally in `data/custom_theme.json`.
- 12 Dark Color's themes remain available, with `Dark Crimson` as the default.

## Run

```powershell
python -m redcord.app.main
```

Local 0.8.x data is stored in:

```text
data/redcord_08.db
```

User files that must be preserved:

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

The installer installs only RedCord Writer Desktop. It does not install the beta
backend or local PostgreSQL and must not remove user data during updates.

## Main Tabs

- `Документы`: projects, documents, tags/categories, autosave, save/save as,
  import file/folder, export PDF, find/replace, stats and writer blocks.
- `Концепты`: create, edit, save, delete and convert concepts into documents.
- `Арты / BoC Lite`: concept art, book covers, comic covers and manga covers.
- `Git / версии`: commits, preview, rename, delete, rollback and branches.
- `ИИ-агент`: mock provider by default, OpenAI-compatible settings, current
  document/selection input, insert/replace/new-document actions.
- `Self-Healing`: health checks, recovery, backup, outbox test and events.
- `Настройки`: theme, custom dark color, profile/account, templates, update ZIP,
  online beta sync.

## Ribbon

The top UI is compact and contextual:

- `Quick bar`: save, undo, redo, new document, find, export PDF, new/save art,
  focus mode.
- `Home`: file/document, edit and format tools.
- `Insert`: writer blocks and concepts.
- `Art`: BoC Lite canvas tools and cover presets.
- `Review`: commits, rollback and branches.
- `View`: side panels, focus mode, compact mode and font size.
- `Settings`: theme, custom theme, updates, sync and help.

The ribbon is built from:

```text
redcord/services/command_registry.py
```

## Formatting

Formatting is WYSIWYG and works like On/Off tools:

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

## BoC Lite

`BoC Lite` is a lightweight art studio inside RedCord, focused on writer assets:

- concept art;
- book covers;
- comic covers;
- manga covers.

Tools include brush, eraser, fill, line, rectangle, ellipse, color picker, brush
size, composition grid, canvas presets, undo, clear canvas, image import, save
and PNG export. It is not a full Krita replacement; it is a quick sketch/concept
layer for story projects.

Art metadata is stored in `data/redcord_08.db`; PNG files are saved under:

```text
data/art_assets/
```

## Custom Theme

Open `Настройки`, choose `Custom Dark`, edit colors and press
`Сохранить custom`. The palette is stored locally:

```text
data/custom_theme.json
```

## AI Agent

AI settings are stored locally:

```text
data/ai_settings.json
```

Supported providers:

- `mock` - default local provider, works offline.
- `openai_compatible` - universal OpenAI-compatible endpoint.

API keys are never stored in source code and are not logged. If you save an API
key in the UI, it is stored locally in JSON; protect access to your Windows
profile and RedCord data folder.

## Online Beta Backend

The backend is optional and shipped separately from the desktop installer:

```powershell
docker compose -f docker-compose.backend.yml up --build
```

Backend endpoints:

```text
GET  /health
POST /auth/request-code
POST /auth/verify-code
POST /sync/status
POST /sync/pull
POST /sync/push
```

Auth uses an email code. In development, if SMTP is not configured, the code is
written to backend logs.

## Update ZIP Manifest

0.8 update archives may include `redcord_update_manifest.json`:

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

Before applying an update, RedCord backs up current app files to
`data/update_backups/`, validates the manifest, preserves `data/`, `commits/`,
`.env`, writes `data/update.log`, and in EXE mode stages the update through
`apply_update.bat`.

## Migration From 0.7.x

On first 0.8.x launch, RedCord looks for legacy `data/redcord.db`, creates a
backup, and imports compatible projects, documents, concepts, commits, templates,
accounts and branches into `data/redcord_08.db`.

The old database is not edited. This is a one-way import into the new schema.

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

- `BoC Lite` is for quick concept sketches and covers, not full professional
  digital painting.
- Online accounts and sync remain beta.
- Real email delivery requires SMTP settings; development mode logs the code.
- The desktop installer does not include PostgreSQL or Docker.
- The editor is Word-like and WYSIWYG, but it is not a full Microsoft Word clone.
