"""Build media text cache (captions/transcripts) for offline embedding."""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path
from typing import Iterable

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import (
    PHOTO_INGESTION_URL,
    PHOTO_INGESTION_PROMPT,
    PHOTO_INGESTION_TIMEOUT,
    AUDIO_TRANSCRIBE_MODEL,
    AUDIO_TRANSCRIBE_DEVICE,
    AUDIO_TRANSCRIBE_COMPUTE_TYPE,
    DATA_DIR,
)
from media_cache import MediaTextCache

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac"}


def get_image_caption(path: Path, prompt: str) -> str:
    if not PHOTO_INGESTION_URL:
        print("  ⚠ PHOTO_INGESTION_URL not set")
        return ""

    try:
        image_bytes = path.read_bytes()
        ext = path.suffix.lower().lstrip(".")
        mime = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "image_b64": f"data:{mime};base64,{image_b64}",
            "prompt": prompt,
        }
        response = requests.post(
            PHOTO_INGESTION_URL,
            json=payload,
            timeout=PHOTO_INGESTION_TIMEOUT,
        )
        if response.status_code == 200:
            caption = (response.json().get("description") or "").strip()
            print(f"  ✓ Caption ({len(caption)} chars)")
            return caption
        print(f"  ✗ Caption server error: {response.status_code}")
    except Exception as exc:
        print(f"  ✗ Caption failed: {exc}")

    return ""


def transcribe_audio(path: Path) -> str:
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        print(f"  ⚠ faster-whisper not available: {exc}")
        return ""

    try:
        print("  → Transcribing audio...")
        model = WhisperModel(
            AUDIO_TRANSCRIBE_MODEL,
            device=AUDIO_TRANSCRIBE_DEVICE,
            compute_type=AUDIO_TRANSCRIBE_COMPUTE_TYPE,
        )
        segments, _info = model.transcribe(str(path))
        parts = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                parts.append(text)
        transcript = " ".join(parts)
        print(f"  ✓ Transcript ({len(transcript)} chars)")
        return transcript
    except Exception as exc:
        print(f"  ✗ Transcription failed: {exc}")
        return ""


def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for ext in sorted(IMAGE_EXTS | AUDIO_EXTS):
        yield from path.glob(f"**/*{ext}")


def process_file(path: Path, cache: MediaTextCache, prompt: str, force: bool) -> None:
    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTS:
        if not force and cache.get_caption(path):
            print(f"  ✓ Cached caption exists: {path.name}")
            return
        print(f"  → Captioning image: {path.name}")
        caption = get_image_caption(path, prompt)
        if caption:
            cache.set_caption(path, caption)
        return

    if suffix in AUDIO_EXTS:
        if not force and cache.get_transcript(path):
            print(f"  ✓ Cached transcript exists: {path.name}")
            return
        print(f"  → Transcribing audio: {path.name}")
        transcript = transcribe_audio(path)
        if transcript:
            cache.set_transcript(path, transcript)
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Build media text cache.")
    parser.add_argument(
        "--path",
        default=str(DATA_DIR / "raw"),
        help="File or directory to process (default: data/raw)",
    )
    parser.add_argument(
        "--prompt",
        default=PHOTO_INGESTION_PROMPT,
        help="Prompt for image captioning",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate cache entries even if they exist",
    )
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"✗ Path not found: {target}")
        return

    cache = MediaTextCache()
    files = list(iter_files(target))
    if not files:
        print(f"✗ No media files found in {target}")
        return

    print(f"Found {len(files)} media files")
    for path in files:
        process_file(path, cache, args.prompt, args.force)

    print(f"✓ Cache saved: {cache.cache_path}")


if __name__ == "__main__":
    main()
