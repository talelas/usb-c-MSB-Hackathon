"""Process only image/audio files in data/raw/media_only and show embeddings."""
from pathlib import Path

from src.main import MemoryProcessor
from src.config import DATA_DIR, METADATA_OUTPUT_FILE, METADATA_CSV_FILE
from src.storage.storage import MetadataStorage


def summarize_media_embeddings():
    """Print summary stats for image/audio embeddings."""
    storage = MetadataStorage(str(METADATA_OUTPUT_FILE), str(METADATA_CSV_FILE))
    docs = [
        d for d in storage.data.get("documents", [])
        if d.get("file_metadata", {}).get("modality") in ("image", "audio")
    ]

    if not docs:
        print("No image/audio documents found in metadata.")
        return

    print("\nMedia Embedding Summary")
    print("=" * 60)
    for doc in docs:
        meta = doc.get("file_metadata", {})
        file_name = meta.get("file_name", "")
        modality = meta.get("modality", "")
        chunks = doc.get("chunks", [])
        print(f"- {file_name} ({modality}) -> chunks: {len(chunks)}")
        if chunks:
            emb = chunks[0].get("embedding", [])
            if emb:
                values = emb[:10]
                print(f"  sample embedding (first 10): {values}")


def main():
    media_dir = DATA_DIR / "raw" / "media_only"
    print(f"Processing media-only folder: {media_dir}")
    processor = MemoryProcessor()
    processor.process_directory(media_dir)
    summarize_media_embeddings()


if __name__ == "__main__":
    main()
