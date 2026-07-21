"""Fixed-size text chunking with overlap."""

from __future__ import annotations


def chunk_text(
    text: str,
    *,
    chunk_size: int = 600,
    overlap: int = 80,
) -> list[str]:
    """Split *text* into overlapping character windows."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(cleaned):
            break
        start += step
    return chunks
