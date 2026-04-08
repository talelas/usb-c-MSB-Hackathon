"""Text chunking with configurable size and overlap."""
from __future__ import annotations

from typing import List

from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """Split *text* into overlapping windows of *chunk_size* characters.

    Returns at least one chunk (the original text) even when the text
    is shorter than *chunk_size*.
    """
    if not text or not text.strip():
        return [text] if text else [""]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks if chunks else [text]
