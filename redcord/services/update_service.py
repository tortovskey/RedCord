from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from redcord import __version__
from redcord.app.config import get_settings


@dataclass
class UpdateResult:
    copied_files: int
    skipped_files: int
    backup_dir: Path
    message: str
    mode: str
    staged_dir: Path | None = None
    apply_script: Path | None = None
    detected_version: str = "unknown"
    current_version: str = __version__
    migration_required: bool = False


@dataclass
class UpdateArchiveManifest:
    version: str
    min_version: str
    files: list[str]
    sha256: dict[str, str]
    migration_required: bool
    raw: dict[str, object]


class UpdateErrorForUser(RuntimeError):
    """Safe update error to show in the UI."""


class UpdateService:
    """Manifest-aware ZIP updater that preserves user data.

    Source/dev mode copies files directly. EXE mode stages the update into
    data/pending_update and writes apply_update.bat so locked binaries can be
    replaced after RedCord exits.
    """

    SKIP_DIR_NAMES = {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".idea",
        ".pytest_cache",
        "data",
        "commits",
        "redcord_build",
        "build",
        "dist",
        "update_backups",
        "pending_update",
        "update_extract",
    }
    SKIP_FILE_NAMES = {
        ".env",
        "redcord.db",
        "redcord_08.db",
        "settings.json",
        "accounts.json",
        "branches.json",
        "redcord.log",
    }
    CODE_MARKERS = {
        "redcord",
        "scripts",
        "requirements.txt",
        "pyproject.toml",
        "README.md",
        "redcord.spec",
        "alembic.ini",
    }

    def __init__(self) -> None:
        self.settings = get_settings()

    def apply_update_from_archive(self, archive_path: str | Path) -> UpdateResult:
        archive = Path(archive_path)
        if not archive.exists() or archive.suffix.lower() != ".zip":
            raise UpdateErrorForUser("Выберите ZIP-архив новой версии RedCord.")

        target_dir = self.settings.app_dir
        if not target_dir.exists():
            raise UpdateErrorForUser("Папка приложения не найдена.")

        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.commit_dir.mkdir(parents=True, exist_ok=True)

        with self._temporary_extract_dir() as tmp_path:
            try:
                with zipfile.ZipFile(archive, "r") as zip_file:
                    zip_file.extractall(tmp_path)
            except Exception as exc:  # noqa: BLE001
                raise UpdateErrorForUser(f"Не удалось распаковать архив: {exc}") from exc

            source_root = self._find_source_root(tmp_path)
            archive_manifest = self._load_archive_manifest(source_root)
            if archive_manifest:
                self._validate_archive_manifest(source_root, archive_manifest)
                detected_version = archive_manifest.version
            else:
                detected_version = self._detect_version(source_root)

            if detected_version == "unknown":
                self._write_update_log(
                    "rejected",
                    f"Archive version was not detected. Archive={archive}; source_root={source_root}",
                )
                raise UpdateErrorForUser(
                    "В архиве не удалось определить версию RedCord. "
                    "Проверьте, что внутри есть redcord/__init__.py с __version__ "
                    "или redcord_update_manifest.json."
                )

            target_has_exe = (target_dir / "RedCord.exe").exists()
            source_has_exe = (source_root / "RedCord.exe").exists()
            if target_has_exe and not source_has_exe:
                raise UpdateErrorForUser(
                    "RedCord запущен как EXE, но в выбранном архиве нет RedCord.exe. "
                    "Для обновления установленной версии нужен ZIP уже собранной папки "
                    "redcord_build/redcord. Архив с исходным кодом подходит только для "
                    "запуска через python -m redcord.app.main."
                )

            backup_dir = self._backup_current(target_dir)
            self._write_update_log(
                "start",
                f"Current={__version__}; new={detected_version}; archive={archive}; backup={backup_dir}",
            )

            if self._needs_external_apply(target_dir):
                return self._stage_result(
                    source_root=source_root,
                    target_dir=target_dir,
                    backup_dir=backup_dir,
                    detected_version=detected_version,
                    archive_manifest=archive_manifest,
                )

            copied, skipped = self._copy_update(source_root, target_dir)
            self._write_manifest(
                staged_dir=self.settings.data_dir,
                source_root=source_root,
                backup_dir=backup_dir,
                detected_version=detected_version,
                mode="direct",
                copied_files=copied,
                skipped_files=skipped,
                archive_manifest=archive_manifest,
            )
            self._write_update_log(
                "direct",
                f"Current={__version__}; new={detected_version}; copied={copied}; skipped={skipped}; backup={backup_dir}",
            )

        return UpdateResult(
            copied_files=copied,
            skipped_files=skipped,
            backup_dir=backup_dir,
            detected_version=detected_version,
            current_version=__version__,
            migration_required=archive_manifest.migration_required if archive_manifest else False,
            mode="direct",
            message=(
                "Обновление установлено.\n"
                f"Текущая версия: {__version__}\n"
                f"Новая версия: {detected_version}\n"
                f"Скопировано файлов: {copied}.\n"
                f"Пропущено пользовательских/защищённых файлов: {skipped}.\n\n"
                "Перезапустите RedCord."
            ),
        )

    def launch_apply_script(self, script_path: str | Path) -> None:
        script = Path(script_path)
        if not script.exists():
            raise UpdateErrorForUser("Скрипт применения обновления не найден.")
        subprocess.Popen(["cmd", "/c", "start", "", str(script)], cwd=str(script.parent), shell=False)

    def _stage_result(
        self,
        source_root: Path,
        target_dir: Path,
        backup_dir: Path,
        detected_version: str,
        archive_manifest: UpdateArchiveManifest | None,
    ) -> UpdateResult:
        staged_dir = self._stage_update(source_root, detected_version)
        apply_script = self._write_apply_script(staged_dir, target_dir, backup_dir)
        self._write_manifest(
            staged_dir=staged_dir,
            source_root=source_root,
            backup_dir=backup_dir,
            detected_version=detected_version,
            mode="staged",
            archive_manifest=archive_manifest,
        )
        self._write_update_log(
            "staged",
            f"Current={__version__}; new={detected_version}; staged={staged_dir}; script={apply_script}; backup={backup_dir}",
        )
        return UpdateResult(
            copied_files=0,
            skipped_files=0,
            backup_dir=backup_dir,
            staged_dir=staged_dir,
            apply_script=apply_script,
            detected_version=detected_version,
            current_version=__version__,
            migration_required=archive_manifest.migration_required if archive_manifest else False,
            mode="staged",
            message=(
                "Обновление подготовлено.\n"
                f"Текущая версия: {__version__}\n"
                f"Новая версия: {detected_version}\n\n"
                "RedCord запущен как EXE, поэтому файлы приложения будут заменены "
                "после закрытия программы.\n"
                f"Папка обновления: {staged_dir}\n"
                f"Скрипт применения: {apply_script}\n\n"
                "Нажмите кнопку запуска применителя или закройте RedCord и запустите "
                "apply_update.bat вручную."
            ),
        )

    def _needs_external_apply(self, target_dir: Path) -> bool:
        return bool(getattr(sys, "frozen", False)) or (target_dir / "RedCord.exe").exists()

    def _find_source_root(self, extracted_root: Path) -> Path:
        candidates: list[Path] = []

        directories = [extracted_root, *[p for p in extracted_root.rglob("*") if p.is_dir()]]
        for directory in directories:
            names = {p.name for p in directory.iterdir()} if directory.exists() else set()
            if "redcord" in names and (directory / "redcord").is_dir():
                candidates.append(directory)
            if "RedCord.exe" in names:
                candidates.append(directory)

        if not candidates:
            raise UpdateErrorForUser(
                "В архиве не найдена структура RedCord. Ожидалась папка redcord/ "
                "или собранный RedCord.exe."
            )

        def score(path: Path) -> int:
            names = {p.name for p in path.iterdir()}
            return len(names & self.CODE_MARKERS) + (3 if "RedCord.exe" in names else 0)

        return sorted(candidates, key=score, reverse=True)[0]

    def _detect_version(self, source_root: Path) -> str:
        manifest = self._load_archive_manifest(source_root)
        if manifest:
            return manifest.version
        init_file = source_root / "redcord" / "__init__.py"
        if init_file.exists():
            text = init_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                if "__version__" in line and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return "unknown"

    def _load_archive_manifest(self, source_root: Path) -> UpdateArchiveManifest | None:
        for name in ("redcord_update_manifest.json", "update_manifest.json", "manifest.json"):
            path = source_root / name
            if not path.exists():
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise UpdateErrorForUser(f"Manifest обновления повреждён: {exc}") from exc
            if not isinstance(raw, dict):
                raise UpdateErrorForUser("Manifest обновления должен быть JSON object.")

            version = str(raw.get("version", "")).strip()
            min_version = str(raw.get("min_version", "")).strip()
            migration_required = bool(raw.get("migration_required", False))
            files = self._manifest_files(raw)
            sha256 = self._manifest_hashes(raw)
            if not version:
                raise UpdateErrorForUser("Manifest обновления не содержит поле version.")
            return UpdateArchiveManifest(
                version=version,
                min_version=min_version,
                files=files,
                sha256=sha256,
                migration_required=migration_required,
                raw=raw,
            )
        return None

    def _manifest_files(self, raw: dict[str, object]) -> list[str]:
        files_value = raw.get("files", [])
        result: list[str] = []
        if isinstance(files_value, list):
            for item in files_value:
                if isinstance(item, str):
                    result.append(item.replace("\\", "/").strip("/"))
                elif isinstance(item, dict) and isinstance(item.get("path"), str):
                    result.append(str(item["path"]).replace("\\", "/").strip("/"))
        return [path for path in result if path]

    def _manifest_hashes(self, raw: dict[str, object]) -> dict[str, str]:
        hashes: dict[str, str] = {}
        sha_value = raw.get("sha256", {})
        if isinstance(sha_value, dict):
            for path, digest in sha_value.items():
                hashes[str(path).replace("\\", "/").strip("/")] = str(digest).lower()

        files_value = raw.get("files", [])
        if isinstance(files_value, list):
            for item in files_value:
                if not isinstance(item, dict):
                    continue
                path = item.get("path")
                digest = item.get("sha256")
                if isinstance(path, str) and isinstance(digest, str):
                    hashes[path.replace("\\", "/").strip("/")] = digest.lower()
        return hashes

    def _validate_archive_manifest(self, source_root: Path, manifest: UpdateArchiveManifest) -> None:
        if manifest.min_version and self._version_tuple(__version__) < self._version_tuple(manifest.min_version):
            raise UpdateErrorForUser(
                f"Эта сборка требует RedCord не ниже {manifest.min_version}. "
                f"Текущая версия: {__version__}."
            )

        manifest_files = set(manifest.files) | set(manifest.sha256)
        for rel in manifest_files:
            path = self._safe_manifest_path(source_root, rel)
            if not path.exists() or not path.is_file():
                raise UpdateErrorForUser(f"Manifest ссылается на отсутствующий файл: {rel}")
            expected = manifest.sha256.get(rel)
            if expected:
                actual = self._sha256(path)
                if actual.lower() != expected.lower():
                    raise UpdateErrorForUser(
                        f"Checksum не совпал для {rel}. Архив может быть повреждён."
                    )

    def _safe_manifest_path(self, source_root: Path, rel_path: str) -> Path:
        path = (source_root / rel_path).resolve()
        root = source_root.resolve()
        if root != path and root not in path.parents:
            raise UpdateErrorForUser(f"Manifest содержит небезопасный путь: {rel_path}")
        return path

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _version_tuple(self, version: str) -> tuple[int, ...]:
        parts: list[int] = []
        for raw_part in version.replace("-", ".").split("."):
            digits = "".join(ch for ch in raw_part if ch.isdigit())
            if digits:
                parts.append(int(digits))
        return tuple(parts or [0])

    def _backup_current(self, target_dir: Path) -> Path:
        backup_root = self.settings.data_dir / "update_backups"
        backup_dir = backup_root / f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{uuid4().hex[:8]}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        names_to_backup = [
            "redcord",
            "scripts",
            "requirements.txt",
            "pyproject.toml",
            "README.md",
            "redcord.spec",
            "alembic.ini",
            "RedCord.exe",
        ]
        for name in names_to_backup:
            src = target_dir / name
            if not src.exists():
                continue
            dst = backup_dir / name
            try:
                if src.is_dir():
                    shutil.copytree(
                        src,
                        dst,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
                    )
                else:
                    shutil.copy2(src, dst)
            except (PermissionError, OSError):
                continue

        return backup_dir

    def _stage_update(self, source_root: Path, detected_version: str) -> Path:
        staging_root = self.settings.data_dir / "pending_update"
        staging_root.mkdir(parents=True, exist_ok=True)
        staged_dir = staging_root / f"redcord_{detected_version}_{datetime.now():%Y-%m-%d_%H-%M-%S}_{uuid4().hex[:8]}"
        staged_dir.mkdir(parents=True, exist_ok=False)

        copied, skipped = self._copy_update(source_root, staged_dir)
        (staged_dir / "_stage_info.json").write_text(
            json.dumps(
                {
                    "current_version": __version__,
                    "version": detected_version,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "copied_files": copied,
                    "skipped_files": skipped,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return staged_dir

    def _write_apply_script(self, staged_dir: Path, target_dir: Path, backup_dir: Path) -> Path:
        script = self.settings.data_dir / "pending_update" / "apply_update.bat"
        script.parent.mkdir(parents=True, exist_ok=True)

        redcord_exe = target_dir / "RedCord.exe"
        script.write_text(
            f"""@echo off
setlocal
title RedCord Update Applicator

echo [RedCord] Applying staged update...
echo Target: {target_dir}
echo Staged: {staged_dir}
echo Backup: {backup_dir}
echo.

echo Waiting for RedCord.exe to close...
:wait_loop
tasklist /FI "IMAGENAME eq RedCord.exe" | find /I "RedCord.exe" >nul
if not errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_loop
)

echo Copying files...
robocopy "{staged_dir}" "{target_dir}" /E /XD data commits update_backups pending_update update_extract __pycache__ .git .venv venv build dist redcord_build /XF .env redcord.db redcord_08.db settings.json accounts.json branches.json redcord.log *.pyc *.pyo _stage_info.json
set RC=%ERRORLEVEL%
if %RC% GEQ 8 (
    echo.
    echo [RedCord] Update failed. Robocopy code: %RC%
    echo Backup is here: {backup_dir}
    pause
    exit /b %RC%
)

echo.
echo [RedCord] Update applied.
echo User data was preserved.
echo.

if exist "{redcord_exe}" (
    echo Starting RedCord...
    start "" "{redcord_exe}"
) else (
    echo RedCord.exe was not found. Start the app manually.
)

endlocal
""",
            encoding="utf-8",
        )
        return script

    @contextmanager
    def _temporary_extract_dir(self) -> Iterator[Path]:
        root = self.settings.data_dir / "update_extract"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"extract_{datetime.now():%Y-%m-%d_%H-%M-%S}_{uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _write_manifest(
        self,
        staged_dir: Path,
        source_root: Path,
        backup_dir: Path,
        detected_version: str,
        mode: str,
        copied_files: int = 0,
        skipped_files: int = 0,
        archive_manifest: UpdateArchiveManifest | None = None,
    ) -> None:
        manifest_path = self.settings.data_dir / "last_update.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "version": detected_version,
                    "mode": mode,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "source_root": str(source_root),
                    "staged_dir": str(staged_dir),
                    "backup_dir": str(backup_dir),
                    "copied_files": copied_files,
                    "skipped_files": skipped_files,
                    "migration_required": archive_manifest.migration_required if archive_manifest else False,
                    "archive_manifest": archive_manifest.raw if archive_manifest else None,
                    "preserved": [
                        "data/",
                        "commits/",
                        ".env",
                        "redcord.db",
                        "redcord_08.db",
                        "settings.json",
                        "accounts.json",
                        "branches.json",
                        "redcord.log",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _write_update_log(self, event: str, message: str) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.settings.data_dir / "update.log"
        line = f"{datetime.now().isoformat(timespec='seconds')} | {event} | {message}\n"
        with log_path.open("a", encoding="utf-8") as file:
            file.write(line)

    def _should_skip(self, rel_path: Path) -> bool:
        if any(part in self.SKIP_DIR_NAMES for part in rel_path.parts):
            return True
        if rel_path.name in self.SKIP_FILE_NAMES:
            return True
        if rel_path.suffix in {".pyc", ".pyo"}:
            return True
        return False

    def _copy_update(self, source_root: Path, target_dir: Path) -> tuple[int, int]:
        copied = 0
        skipped = 0
        for src in source_root.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(source_root)
            if self._should_skip(rel):
                skipped += 1
                continue
            dst = target_dir / rel
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
            except (PermissionError, OSError):
                skipped += 1
        return copied, skipped
