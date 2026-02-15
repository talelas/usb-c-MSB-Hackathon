"""Search Qdrant for similar embeddings and return file paths."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import OUTPUT_DIR, EMBEDDING_DIMENSION, EMBEDDING_MODEL
from embedders.embedder import HuggingFaceEmbedder


def ensure_collection(client: QdrantClient, name: str) -> None:
    collections = client.get_collections().collections
    if any(c.name == name for c in collections):
        return
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
    )


def load_points() -> List[PointStruct]:
    data_path = OUTPUT_DIR / "embeddings_only.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Missing embeddings file: {data_path}")

    import json

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    for idx, item in enumerate(data, start=1):
        payload = {
            "doc_id": item.get("doc_id"),
            "file_name": item.get("file_name"),
            "chunk_index": item.get("chunk_index"),
            "chunk_text": item.get("chunk_text"),
            "keywords": item.get("keywords"),
            "modality": item.get("modality"),
        }
        points.append(PointStruct(id=idx, vector=item.get("embedding", []), payload=payload))

    return points


def upsert_points(client: QdrantClient, name: str) -> None:
    points = load_points()
    client.upsert(collection_name=name, points=points)
    print(f"✓ Upserted {len(points)} points into {name}")


def query(client: QdrantClient, name: str, text: str, limit: int) -> None:
    embedder = HuggingFaceEmbedder(EMBEDDING_MODEL)
    vector = embedder.embed(text).tolist()
    results = client.search(collection_name=name, query_vector=vector, limit=limit)

    print("\nTop matches:")
    for rank, res in enumerate(results, start=1):
        payload = res.payload or {}
        print(f"{rank}. score={res.score:.4f} file={payload.get('file_name')} chunk={payload.get('chunk_index')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Qdrant similarity search.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6333)
    parser.add_argument("--collection", default="ai_minds_embeddings")
    parser.add_argument("--upsert", action="store_true", help="Upsert embeddings before searching")
    parser.add_argument("--query", required=True, help="Query text")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    client = QdrantClient(host=args.host, port=args.port)
    ensure_collection(client, args.collection)

    if args.upsert:
        upsert_points(client, args.collection)

    query(client, args.collection, args.query, args.limit)


if __name__ == "__main__":
    main()
