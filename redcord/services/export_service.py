from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from docx import Document as DocxDocument


class ExportErrorForUser(RuntimeError):
    """Export error with message safe to show in UI."""


class ExportService:
    def export_text(self, path: str | Path, title: str, content: str) -> Path:
        export_path = Path(path)
        suffix = export_path.suffix.lower()

        if suffix in {"", ".md", ".markdown"}:
            if export_path.suffix == "":
                export_path = export_path.with_suffix(".md")
            body = f"# {title.strip() or 'Без названия'}\n\n{content}"
            export_path.write_text(body, encoding="utf-8")
            return export_path

        if suffix == ".txt":
            export_path.write_text(content, encoding="utf-8")
            return export_path

        if suffix == ".docx":
            self._write_docx(export_path, title, content)
            return export_path

        if suffix == ".doc":
            self._write_doc(export_path, title, content)
            return export_path

        raise ExportErrorForUser("Поддерживаются форматы .md, .txt, .docx, .doc и .pdf.")

    def _write_docx(self, path: Path, title: str, content: str) -> None:
        document = DocxDocument()
        document.add_heading(title.strip() or "Без названия", level=1)
        for line in content.splitlines():
            document.add_paragraph(line)
        document.save(path)

    def _write_doc(self, path: Path, title: str, content: str) -> None:
        executable = shutil.which("soffice") or shutil.which("libreoffice")
        if executable is None:
            raise ExportErrorForUser(
                "Экспорт в .doc требует LibreOffice. "
                "Установите LibreOffice или сохраните файл как .docx."
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tmp_docx = tmp_path / f"{path.stem}.docx"
            self._write_docx(tmp_docx, title, content)

            try:
                subprocess.run(
                    [
                        executable,
                        "--headless",
                        "--convert-to",
                        "doc",
                        "--outdir",
                        str(tmp_path),
                        str(tmp_docx),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=45,
                )
            except Exception as exc:  # noqa: BLE001
                raise ExportErrorForUser(f"Не удалось сконвертировать в .doc: {exc}") from exc

            converted = tmp_path / f"{path.stem}.doc"
            if not converted.exists():
                raise ExportErrorForUser("LibreOffice не создал .doc файл.")
            path.write_bytes(converted.read_bytes())
