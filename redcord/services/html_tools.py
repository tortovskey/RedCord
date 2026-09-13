from __future__ import annotations

from html import escape


def plain_to_html(text: str) -> str:
    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n")]
    html_parts = []
    for paragraph in paragraphs:
        if not paragraph:
            continue
        html_parts.append(f"<p>{escape(paragraph).replace(chr(10), '<br>')}</p>")
    return "\n".join(html_parts) or "<p></p>"
