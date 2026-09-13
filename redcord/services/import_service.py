from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from docx import Document as DocxDocument


class ImportErrorForUser(RuntimeError):
    """Import error with message safe to show in UI."""


class ImportService:
    SUPPORTED_EXTENSIONS = {".docx", ".doc", ".txt", ".md", ".markdown"}

    def read_file_text(self, path: str | Path) -> str:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            return self._read_docx(file_path)
        if suffix == ".doc":
            return self._read_doc(file_path)
        if suffix in {".txt", ".md", ".markdown"}:
            return self._read_text(file_path)
        raise ImportErrorForUser("Поддерживаются .docx, .doc, .txt, .md и .markdown файлы.")

    def list_importable_files(self, directory: str | Path) -> list[Path]:
        root = Path(directory)
        if not root.exists() or not root.is_dir():
            raise ImportErrorForUser("Папка не найдена")
        files: list[Path] = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                files.append(path)
        return sorted(files)

    def _read_text(self, path: Path) -> str:
        for encoding in ["utf-8-sig", "utf-8", "cp1251", "latin-1"]:
            try:
                return path.read_text(encoding=encoding).strip()
            except UnicodeDecodeError:
                continue
        raise ImportErrorForUser("Не удалось прочитать текстовый файл. Проверь кодировку.")

    def _read_docx(self, path: Path) -> str:
        # Some files have a .docx extension but are not real OOXML zip files.
        # Instead of exploding with "File is not a zip file", try safe fallbacks.
        if not zipfile.is_zipfile(path):
            text = self._try_libreoffice(path)
            if text:
                return text
            text = self._try_pypandoc(path)
            if text:
                return text
            text = self._try_as_plain_text(path)
            if text:
                return text
            raise ImportErrorForUser(
                "Файл имеет расширение .docx, но не является настоящим docx-файлом. "
                "Попробуйте открыть его в Word/LibreOffice и сохранить заново как .docx."
            )

        try:
            document = DocxDocument(path)
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            return "\n".join(paragraphs).strip()
        except Exception as exc:  # noqa: BLE001
            raise ImportErrorForUser(f"Не удалось прочитать .docx файл: {exc}") from exc

    def _read_doc(self, path: Path) -> str:
        text = self._try_libreoffice(path)
        if text:
            return text

        text = self._try_antiword(path)
        if text:
            return text

        text = self._try_pypandoc(path)
        if text:
            return text

        text = self._try_as_plain_text(path)
        if text:
            return text

        raise ImportErrorForUser(
            "Формат .doc требует установленный LibreOffice или конвертер. "
            "Установите LibreOffice или сохраните файл как .docx."
        )

    def _try_as_plain_text(self, path: Path) -> str | None:
        try:
            raw = path.read_bytes()
            if b"\x00" in raw[:2048]:
                return None
            for encoding in ["utf-8-sig", "utf-8", "cp1251", "latin-1"]:
                try:
                    text = raw.decode(encoding).strip()
                    return text if text else None
                except UnicodeDecodeError:
                    continue
        except Exception:
            return None
        return None

    def _try_libreoffice(self, path: Path) -> str | None:
        executable = shutil.which("soffice") or shutil.which("libreoffice")
        if executable is None:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            try:
                subprocess.run(
                    [
                        executable,
                        "--headless",
                        "--convert-to",
                        "docx",
                        "--outdir",
                        str(tmp_path),
                        str(path),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=45,
                )
                converted = tmp_path / f"{path.stem}.docx"
                if converted.exists() and zipfile.is_zipfile(converted):
                    document = DocxDocument(converted)
                    paragraphs = [paragraph.text for paragraph in document.paragraphs]
                    return "\n".join(paragraphs).strip()
            except Exception:
                return None
        return None

    def _try_antiword(self, path: Path) -> str | None:
        executable = shutil.which("antiword")
        if executable is None:
            return None
        try:
            result = subprocess.run(
                [executable, str(path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            return result.stdout.decode("utf-8", errors="replace").strip()
        except Exception:
            return None

    def _try_pypandoc(self, path: Path) -> str | None:
        if importlib.util.find_spec("pypandoc") is None:
            return None
        try:
            import pypandoc  # type: ignore

            return str(pypandoc.convert_file(str(path), "plain")).strip()
        except Exception:
            return None
