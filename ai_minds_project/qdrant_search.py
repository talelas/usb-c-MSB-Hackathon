"""Search Qdrant for similar embeddings and return file paths."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

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


def load_doc_metadata() -> Dict[int, Dict]:
    """Map doc_id -> file metadata for payload enrichment and display."""
    meta_path = OUTPUT_DIR / "metadata_embeddings.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing metadata file: {meta_path}")

    import json

    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    for doc in data.get("documents", []):
        doc_id = doc.get("id")
        file_meta = doc.get("file_metadata", {})
        modality = file_meta.get("modality")
        caption = (file_meta.get("caption") or "").strip()
        transcript = (file_meta.get("transcript") or "").strip()
        summary = (doc.get("text_summary") or "").strip()

        if modality == "image" and caption:
            description = caption
        elif modality == "audio" and transcript:
            description = transcript
        else:
            description = summary

        mapping[doc_id] = {
            "file_name": file_meta.get("file_name"),
            "file_path": file_meta.get("file_path"),
            "modality": modality,
            "file_extension": file_meta.get("file_extension"),
            "description": description,
        }

    return mapping


def load_points() -> List[PointStruct]:
    data_path = OUTPUT_DIR / "embeddings_only.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Missing embeddings file: {data_path}")

    import json

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc_meta = load_doc_metadata()
    points = []
    for idx, item in enumerate(data, start=1):
        doc_id = item.get("doc_id")
        meta = doc_meta.get(doc_id, {})
        payload = {
            "doc_id": doc_id,
            "file_name": meta.get("file_name"),
            "file_path": meta.get("file_path"),
            "file_extension": meta.get("file_extension"),
            "chunk_index": item.get("chunk_index"),
            "keywords": item.get("keywords"),
            "modality": meta.get("modality") or item.get("modality"),
        }
        # Do not store transcript/chunk_text in Qdrant payload
        points.append(PointStruct(id=idx, vector=item.get("embedding", []), payload=payload))

    return points


def upsert_points(client: QdrantClient, name: str) -> None:
    points = load_points()
    client.upsert(collection_name=name, points=points)
    print(f"✓ Upserted {len(points)} points into {name}")


def get_description_and_link(doc_meta: Dict[int, Dict], doc_id: int | None) -> Dict[str, str]:
    if not doc_id:
        return {"description": "", "file_path": ""}
    meta = doc_meta.get(doc_id, {})
    return {
        "description": meta.get("description", ""),
        "file_path": meta.get("file_path", ""),
    }


def query(client: QdrantClient, name: str, text: str, limit: int, keyword: str | None) -> None:
    embedder = HuggingFaceEmbedder(EMBEDDING_MODEL)
    vector = embedder.embed(text).tolist()
    doc_meta = load_doc_metadata()
    query_filter = None
    if keyword:
        query_filter = Filter(
            must=[FieldCondition(key="keywords", match=MatchValue(value=keyword))]
        )
    response = client.query_points(
        collection_name=name,
        query=vector,
        limit=limit,
        query_filter=query_filter,
    )
    results = response.points

    print("\nTop matches:")
    for rank, res in enumerate(results, start=1):
        payload = res.payload or {}
        doc_id = payload.get("doc_id")
        meta = get_description_and_link(doc_meta, doc_id)
        print(
            f"{rank}. score={res.score:.4f} file={payload.get('file_name')} "
            f"path={payload.get('file_path')} chunk={payload.get('chunk_index')}"
        )
        if meta.get("description"):
            print(f"   description: {meta.get('description')[:200]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Qdrant similarity search.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6333)
    parser.add_argument("--collection", default="ai_minds_embeddings")
    parser.add_argument("--upsert", action="store_true", help="Upsert embeddings before searching")
    parser.add_argument("--query", required=True, help="Query text")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--keyword", help="Optional keyword filter")
    args = parser.parse_args()

    client = QdrantClient(host=args.host, port=args.port)
    ensure_collection(client, args.collection)

    if args.upsert:
        upsert_points(client, args.collection)

    query(client, args.collection, args.query, args.limit, args.keyword)


if __name__ == "__main__":
    main()
