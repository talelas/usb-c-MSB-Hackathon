"""Store image/audio embeddings in Qdrant and run a text query."""
import json
import sys
from pathlib import Path

from src.config import METADATA_OUTPUT_FILE
from src.embedders.embedder import HuggingFaceEmbedder


def load_media_points():
    data = json.loads(Path(METADATA_OUTPUT_FILE).read_text(encoding="utf-8"))
    points = []
    point_id = 1

    for doc in data.get("documents", []):
        meta = doc.get("file_metadata", {})
        modality = meta.get("modality")
        if modality not in ("image", "audio"):
            continue

        for chunk in doc.get("chunks", []):
            points.append({
                "id": point_id,
                "vector": chunk.get("embedding", []),
                "payload": {
                    "file_name": meta.get("file_name", ""),
                    "file_path": meta.get("file_path", ""),
                    "modality": modality,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "chunk_text": chunk.get("text", "")[:500],
                    "keywords": doc.get("keywords", []),
                    "caption": meta.get("caption", ""),
                    "transcript": meta.get("transcript", "")
                }
            })
            point_id += 1

    return points


def get_qdrant_client():
    try:
        from qdrant_client import QdrantClient
    except Exception as exc:
        raise RuntimeError("qdrant-client is not installed") from exc

    url = "http://localhost:6333"
    client = QdrantClient(url=url)
    return client


def ensure_collection(client, name, vector_size):
    from qdrant_client.http.models import Distance, VectorParams

    collections = [c.name for c in client.get_collections().collections]
    if name in collections:
        return

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )


def main():
    points = load_media_points()
    if not points:
        print("No media embeddings found. Run media_only_test.py first.")
        return 1

    client = get_qdrant_client()
    collection_name = "media_only"
    vector_size = len(points[0]["vector"])

    ensure_collection(client, collection_name, vector_size)
    client.upsert(collection_name=collection_name, points=points)
    print(f"Stored {len(points)} media embeddings in Qdrant collection '{collection_name}'.")

    query = input("\nEnter a text query to retrieve source (or press Enter to quit): ").strip()
    if not query:
        return 0

    embedder = HuggingFaceEmbedder()
    query_vector = embedder.embed(query).tolist()

    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=5
    )

    print("\nTop results:")
    for rank, hit in enumerate(results, start=1):
        payload = hit.payload or {}
        print(f"{rank}. score={hit.score:.4f} file={payload.get('file_name')}")
        print(f"   path={payload.get('file_path')}")
        preview = payload.get("chunk_text", "")
        if preview:
            print(f"   preview={preview[:120]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
