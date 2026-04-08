"""File ingestors — convert any supported file into (text, metadata)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Tuple

from app.config import SUPPORTED_EXTENSIONS
from app.core.media import get_caption, transcribe_audio


# ── helpers ──────────────────────────────────────────────────

def _base_metadata(path: Path, modality: str) -> dict:
    stat = path.stat()
    return {
        "modality": modality,
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "file_size_bytes": stat.st_size,
        "timestamp": str(datetime.fromtimestamp(stat.st_mtime)),
        "file_extension": path.suffix.lower(),
    }


def _modality_for(path: Path) -> str | None:
    ext = path.suffix.lower()
    for modality, exts in SUPPORTED_EXTENSIONS.items():
        if ext in exts:
            return modality
    return None


# ── per-modality ingestors ───────────────────────────────────

def _ingest_text(path: Path) -> Tuple[str, dict]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    return content, _base_metadata(path, "text")


def _ingest_pdf(path: Path) -> Tuple[str, dict]:
    try:
        import PyPDF2
        pages = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                pages.append(page.extract_text() or "")
        return "\n".join(pages), _base_metadata(path, "pdf")
    except ImportError:
        raise ImportError("Install PyPDF2: pip install PyPDF2")


def _ingest_image(path: Path) -> Tuple[str, dict]:
    meta = _base_metadata(path, "image")
    text = f"[Image: {path.name}]"

    caption = get_caption(path)
    if caption:
        text += f"\nCaption: {caption}"
        meta["caption"] = caption

    return text, meta


def _ingest_audio(path: Path) -> Tuple[str, dict]:
    meta = _base_metadata(path, "audio")
    text = f"[Audio: {path.name}]"

    transcript = transcribe_audio(path)
    if transcript:
        text += f"\nTranscript: {transcript}"
        meta["transcript"] = transcript

    return text, meta


# ── dispatcher ───────────────────────────────────────────────

_INGESTORS = {
    "text":  _ingest_text,
    "pdf":   _ingest_pdf,
    "image": _ingest_image,
    "audio": _ingest_audio,
}


def ingest(path: Path) -> Tuple[str, dict]:
    """Ingest *path* and return ``(text, metadata)``."""
    path = Path(path)
    modality = _modality_for(path)
    if modality is None:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    return _INGESTORS[modality](path)
