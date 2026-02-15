"""Media text cache (captions/transcripts) for offline embedding."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict

from config import MEDIA_TEXT_CACHE_FILE


class MediaTextCache:
    """Load/save captions/transcripts keyed by file path and metadata."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = Path(cache_path) if cache_path else Path(MEDIA_TEXT_CACHE_FILE)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict:
        if self.cache_path.exists():
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"items": {}}

    def _key(self, path: Path) -> str:
        return str(path.resolve())

    def _file_meta(self, path: Path) -> Dict:
        resolved = path.resolve()
        stat = resolved.stat()
        return {
            "file_name": resolved.name,
            "file_path": str(resolved),
            "file_size_bytes": stat.st_size,
            "file_mtime": stat.st_mtime,
        }

    def _is_stale(self, entry: Dict, path: Path) -> bool:
        try:
            stat = path.resolve().stat()
            return (
                entry.get("file_size_bytes") != stat.st_size
                or entry.get("file_mtime") != stat.st_mtime
            )
        except Exception:
            return True

    def get_caption(self, path: Path) -> str:
        key = self._key(path)
        entry = self.data.get("items", {}).get(key)
        if not entry:
            return ""
        if self._is_stale(entry, path):
            return ""
        return entry.get("caption", "") or ""

    def get_transcript(self, path: Path) -> str:
        key = self._key(path)
        entry = self.data.get("items", {}).get(key)
        if not entry:
            return ""
        if self._is_stale(entry, path):
            return ""
        return entry.get("transcript", "") or ""

    def set_caption(self, path: Path, caption: str) -> None:
        key = self._key(path)
        entry = dict(self._file_meta(path))
        entry["caption"] = caption
        entry["transcript"] = self.data.get("items", {}).get(key, {}).get("transcript", "")
        self.data.setdefault("items", {})[key] = entry
        self.save()

    def set_transcript(self, path: Path, transcript: str) -> None:
        key = self._key(path)
        entry = dict(self._file_meta(path))
        entry["transcript"] = transcript
        entry["caption"] = self.data.get("items", {}).get(key, {}).get("caption", "")
        self.data.setdefault("items", {})[key] = entry
        self.save()

    def save(self) -> None:
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
