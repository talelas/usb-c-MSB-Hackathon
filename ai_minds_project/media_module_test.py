"""Test image/audio ingestion module end-to-end for embeddings."""
import sys
from pathlib import Path

# Fix Windows encoding
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from src.config import DATA_DIR
from src.ingestors.ingestor import ImageIngestor, AudioIngestor
from src.embedders.embedder import EmbeddingPipeline


def pick_first(path: Path, exts):
    for ext in exts:
        files = list(path.glob(f"**/*{ext}"))
        if files:
            return files[0]
    return None


def test_image(image_path: Path, pipeline: EmbeddingPipeline):
    ingestor = ImageIngestor()
    text, meta = ingestor.ingest(str(image_path))
    result = pipeline.process_text(text, meta)

    print("\nIMAGE TEST")
    print("=" * 60)
    print("file:", meta.get("file_name"))
    print("caption:", (meta.get("caption") or "")[:200])
    print("num_chunks:", result.get("num_chunks"))
    print("embedding_dimension:", result.get("embedding_dimension"))
    if result.get("chunks"):
        print("sample_embedding_first10:", result["chunks"][0]["embedding"][:10])


def test_audio(audio_path: Path, pipeline: EmbeddingPipeline):
    ingestor = AudioIngestor()
    text, meta = ingestor.ingest(str(audio_path))
    result = pipeline.process_text(text, meta)

    print("\nAUDIO TEST")
    print("=" * 60)
    print("file:", meta.get("file_name"))
    print("transcript:", (meta.get("transcript") or "")[:200])
    print("num_chunks:", result.get("num_chunks"))
    print("embedding_dimension:", result.get("embedding_dimension"))
    if result.get("chunks"):
        print("sample_embedding_first10:", result["chunks"][0]["embedding"][:10])


def main():
    media_dir = DATA_DIR / "raw" / "media_only"
    pipeline = EmbeddingPipeline()

    image_path = pick_first(media_dir, [".jpg", ".jpeg", ".png", ".bmp"])
    audio_path = pick_first(media_dir, [".mp3", ".wav", ".m4a", ".flac"])

    if image_path:
        test_image(image_path, pipeline)
    else:
        print("No image found in media_only.")

    if audio_path:
        test_audio(audio_path, pipeline)
    else:
        print("No audio found in media_only.")


if __name__ == "__main__":
    main()
