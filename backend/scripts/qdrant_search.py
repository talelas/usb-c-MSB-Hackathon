"""Search Qdrant for similar embeddings and return file paths."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Dict
import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import requests


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import OUTPUT_DIR, EMBEDDING_DIMENSION, EMBEDDING_MODEL
from src.embedders.embedder import HuggingFaceEmbedder

# Load .env if present so QDRANT_* settings can be supplied there
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass


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


def query(client: QdrantClient, name: str, text: str, limit: int, host: str = "127.0.0.1", port: int = 6333, keyword: str | None = None) -> None:
    embedder = HuggingFaceEmbedder(EMBEDDING_MODEL)
    vector = embedder.embed(text).tolist()
    # Qdrant client has different method names across versions: try common variants
    results = None
    try:
        # Build a filter object if a keyword is provided (client-side search)
        filter_obj = None
        if keyword:
            try:
                filter_obj = Filter(must=[FieldCondition(key="keywords", match=MatchValue(value=keyword))])
            except Exception:
                filter_obj = None

        if hasattr(client, "search"):
            if filter_obj is not None:
                results = client.search(collection_name=name, query_vector=vector, limit=limit, query_filter=filter_obj)
            else:
                results = client.search(collection_name=name, query_vector=vector, limit=limit)
        elif hasattr(client, "search_points"):
            # older client variants
            if filter_obj is not None:
                results = client.search_points(collection_name=name, query_vector=vector, limit=limit, query_filter=filter_obj)
            else:
                results = client.search_points(collection_name=name, query_vector=vector, limit=limit)
        elif hasattr(client, "search_collection"):
            results = client.search_collection(collection_name=name, query_vector=vector, limit=limit)
        elif hasattr(client, "search_points_with_payload"):
            # some older variants
            results = client.search_points_with_payload(collection_name=name, query_vector=vector, limit=limit)
        else:
            # No suitable client method found — fall back to HTTP REST API
            results = None
    except Exception as e:
        print(f"⚠ Qdrant client search attempt failed: {e}")
        results = None

    def _extract(res):
        # payload
        if hasattr(res, "payload"):
            payload = res.payload or {}
        elif isinstance(res, dict):
            payload = res.get("payload") or (res.get("point") or {}).get("payload") or {}
        else:
            payload = {}

        # score
        if hasattr(res, "score"):
            score = getattr(res, "score")
        elif isinstance(res, dict):
            score = res.get("score") or res.get("distance")
        else:
            score = None

        return payload, score

    # If client-based search didn't produce results, use HTTP API
    if not results:
        try:
            url = f"http://{host}:{port}/collections/{name}/points/search"
            body = {"vector": vector, "limit": limit, "with_payload": True}
            resp = requests.post(url, json=body, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # common shapes: data.get('result') -> list OR data.get('result', {}).get('result')
            results_list = data.get('result') or (data.get('result') or {}).get('result') or data.get('result', {}).get('points') or []
            # Normalize to list of dict-like items
            results = results_list
        except Exception as e:
            print(f"⚠ Qdrant HTTP search failed: {e}")
            return

    print("\nTop matches:")
    for rank, res in enumerate(results, start=1):
        payload, score = _extract(res)
        score_display = f"{score:.4f}" if isinstance(score, (int, float)) else str(score)
        print(f"{rank}. score={score_display} file={payload.get('file_name')} chunk={payload.get('chunk_index')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Qdrant similarity search.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6333)
    parser.add_argument("--collection", default="memoir_embeddings")
    parser.add_argument("--upsert", action="store_true", help="Upsert embeddings before searching")
    parser.add_argument("--query", required=True, help="Query text")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--keyword", help="Optional keyword filter")
    args = parser.parse_args()

    # Determine host/port with precedence: CLI args > env vars > defaults
    use_docker = os.getenv("QDRANT_USE_DOCKER", "True").lower() in ("1", "true", "yes")
    env_host = os.getenv("QDRANT_HOST")
    env_port = os.getenv("QDRANT_PORT")

    host = args.host or env_host or ("127.0.0.1")
    port = args.port or (int(env_port) if env_port else 6333)

    mode = "docker" if use_docker else "local"
    print(f"Connecting to Qdrant ({mode}) at {host}:{port} (use QDRANT_USE_DOCKER=0 to change)")

    # Note: qdrant-client is only a client library; it does not install the Qdrant server.
    client = QdrantClient(host=host, port=port)

    # Quick connectivity check and helpful guidance
    try:
        _ = client.get_collections()
    except Exception as e:
        print(f"⚠ Failed to contact Qdrant at {host}:{port}: {e}")
        if use_docker:
            print("Tip: start a Qdrant docker container with:\n  docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.2.2")
        else:
            print("Tip: ensure a local Qdrant server is running (see https://qdrant.tech/documentation/).")
        return
    ensure_collection(client, args.collection)

    if args.upsert:
        upsert_points(client, args.collection)

    query(client, args.collection, args.query, args.limit, host=host, port=port, keyword=args.keyword)


if __name__ == "__main__":
    main()
