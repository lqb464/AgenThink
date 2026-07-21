"""Parse uploaded documents to plain text (PDF / DOCX / MD / TXT)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SUPPORTED = {".pdf", ".docx", ".md", ".txt", ".markdown", ".text"}


def supported_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in _SUPPORTED


def parse_bytes(filename: str, data: bytes) -> str:
    """Extract plain text from file bytes. Raises ValueError on failure."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(data)
    if suffix == ".docx":
        return _parse_docx(data)
    if suffix in {".md", ".txt", ".markdown", ".text"}:
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix or '(none)'}")


def _parse_pdf(data: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    text = "\n\n".join(parts).strip()
    if not text:
        raise ValueError("PDF produced no extractable text")
    return text


def _parse_docx(data: bytes) -> str:
    from io import BytesIO

    from docx import Document

    doc = Document(BytesIO(data))
    parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    text = "\n\n".join(parts).strip()
    if not text:
        raise ValueError("DOCX produced no extractable text")
    return text
