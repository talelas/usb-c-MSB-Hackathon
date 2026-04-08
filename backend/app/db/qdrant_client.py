"""Qdrant vector-store operations.

Wraps :pypi:`qdrant-client` with helpers used by the pipeline
and the retrieval layer.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import (
    EMBEDDING_DIMENSION,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    QDRANT_PORT,
)


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, prefer_grpc=False)


def ensure_collection(name: str = QDRANT_COLLECTION) -> None:
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
        )


# ── Write ────────────────────────────────────────────────────

def upsert_points(points: List[PointStruct], collection: str = QDRANT_COLLECTION) -> int:
    """Upsert *points* and return count."""
    ensure_collection(collection)
    client = get_client()
    client.upsert(collection_name=collection, points=points)
    return len(points)


def build_point(
    point_id: int,
    vector: List[float],
    doc_id: int,
    file_name: str = "",
    file_path: str = "",
    modality: str = "",
    chunk_index: int = 0,
    chunk_text: str = "",
    keywords: List[str] | None = None,
    summary: str = "",
) -> PointStruct:
    """Create a :class:`PointStruct` with a standard payload schema."""
    return PointStruct(
        id=point_id,
        vector=vector,
        payload={
            "doc_id": doc_id,
            "file_name": file_name,
            "file_path": file_path,
            "modality": modality,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "keywords": keywords or [],
            "summary": summary,
        },
    )


# ── Read / search ────────────────────────────────────────────

def search(
    vector: List[float],
    limit: int = 5,
    collection: str = QDRANT_COLLECTION,
    keyword: Optional[str] = None,
) -> list:
    """Semantic search returning scored results."""
    client = get_client()
    query_filter = None
    if keyword:
        query_filter = Filter(
            must=[FieldCondition(key="keywords", match=MatchValue(value=keyword))]
        )
    
    results = client.search(
        collection_name=collection,
        query_vector=vector,
        limit=limit,
        query_filter=query_filter,
    )
    return results


def scroll_all(collection: str = QDRANT_COLLECTION, with_vectors: bool = False):
    """Return all points (up to 10 000)."""
    ensure_collection(collection)  # Make sure collection exists
    client = get_client()
    try:
        points, _ = client.scroll(
            collection_name=collection,
            limit=10_000,
            with_payload=True,
            with_vectors=with_vectors,
        )
        return points
    except Exception:
        # Return empty list if scroll fails
        return []


def get_doc_embeddings(collection: str = QDRANT_COLLECTION) -> Dict[int, List[float]]:
    """Return {doc_id: embedding} using only chunk_index==0."""
    points = scroll_all(collection, with_vectors=True)
    out: dict[int, list[float]] = {}
    for p in points:
        payload = p.payload or {}
        if payload.get("chunk_index", 0) == 0:
            doc_id = payload.get("doc_id")
            if doc_id is not None:
                out[doc_id] = p.vector
    return out
