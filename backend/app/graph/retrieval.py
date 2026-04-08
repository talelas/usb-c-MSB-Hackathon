"""Graph-augmented retrieval with temporal scoring.

Scoring formula:
  score = α·semantic + β·centrality + γ·recency + δ·importance
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

import networkx as nx
import numpy as np

from app.config import OUTPUT_DIR, QDRANT_COLLECTION
from app.core.embedder import get_embedder
from app.db import postgres as pg
from app.db import qdrant_client as qdb
from app.db import redis_client as rdb


# ── Temporal helpers ─────────────────────────────────────────

def recency_score(doc_id: int, decay: float = 0.0001) -> float:
    """Exponential decay based on last-access timestamp in Redis."""
    raw = rdb.cache_get(f"temporal:access:{doc_id}")
    if not raw:
        return 0.5
    try:
        ts = float(raw)
        hours = (time.time() - ts) / 3600
        return float(np.exp(-decay * hours))
    except Exception:
        return 0.5


def importance_score(doc_id: int) -> float:
    """Importance = normalised query-match count from Redis."""
    raw = rdb.cache_get(f"temporal:matches:{doc_id}")
    return min(float(raw or 0) / 10.0, 1.0)  # cap at 1


def record_access(doc_id: int) -> None:
    rdb.cache_set(f"temporal:access:{doc_id}", str(time.time()), ttl=86400 * 30)


def record_query_match(doc_id: int) -> None:
    r = rdb._get_client()
    r.incr(f"cache:temporal:matches:{doc_id}")
    r.expire(f"cache:temporal:matches:{doc_id}", 86400 * 30)


# ── Graph helpers ────────────────────────────────────────────

def centrality(
    doc_id: int,
    kw_graph: nx.Graph,
    sem_graph: nx.Graph,
    kw_w: float = 0.4,
    sem_w: float = 0.6,
) -> float:
    """Hybrid centrality: combines keyword and semantic graph degree centrality."""
    kw_c = sem_c = 0.0
    if doc_id in kw_graph:
        mx = max(dict(kw_graph.degree()).values()) or 1
        kw_c = kw_graph.degree(doc_id) / mx
    if doc_id in sem_graph:
        mx = max(dict(sem_graph.degree()).values()) or 1
        sem_c = sem_graph.degree(doc_id) / mx
    # Hybrid score: keyword graph helps surface topically related docs
    return kw_w * kw_c + sem_w * sem_c


def expand_neighbourhood(
    seeds: Set[int],
    kw_graph: nx.Graph,
    sem_graph: nx.Graph,
    hops: int = 2,
) -> Set[int]:
    expanded = set(seeds)
    for node in seeds:
        for G in (kw_graph, sem_graph):
            if node in G:
                neighbours = nx.single_source_shortest_path_length(G, node, cutoff=hops)
                expanded.update(neighbours.keys())
    return expanded


# ── Main retrieval function ──────────────────────────────────

def retrieve(
    query: str,
    kw_graph: nx.Graph,
    sem_graph: nx.Graph,
    *,
    alpha: float = 0.5,
    beta: float = 0.2,
    gamma: float = 0.2,
    delta: float = 0.1,
    initial_k: int = 20,
    final_k: int = 10,
    hops: int = 2,
) -> List[Dict]:
    """Graph-augmented semantic search.

    Returns a ranked list of dicts with keys:
    ``doc_id, file_name, modality, final_score, semantic_score, ...``
    """
    embedder = get_embedder()
    vec = embedder.embed(query).tolist()

    # Step 1 – Qdrant semantic search
    hits = qdb.search(vec, limit=initial_k)
    initial: dict[int, dict] = {}
    for h in hits:
        p = h.payload or {}
        doc_id = p.get("doc_id")
        if doc_id is not None:
            initial[doc_id] = {
                "semantic_score": h.score,
                "file_name": p.get("file_name"),
                "file_path": p.get("file_path"),
                "modality": p.get("modality"),
                "chunk_text": p.get("chunk_text", ""),
            }
            record_query_match(doc_id)

    # Step 2 – graph expansion
    expanded = expand_neighbourhood(set(initial.keys()), kw_graph, sem_graph, hops)
    
    # Log expansion for debugging
    import logging
    log = logging.getLogger(__name__)
    log.info(f"Retrieval: {len(initial)} initial hits → {len(expanded)} after graph expansion (hops={hops})")

    # Step 2.5 - Fetch summaries for expanded documents that don't have chunk_text
    expanded_without_text = expanded - set(initial.keys())
    if expanded_without_text:
        session = pg.get_session()
        try:
            for doc_id in expanded_without_text:
                doc = pg.get_document_by_id(session, doc_id)
                if doc:
                    # Use summary, or image_caption, or audio_transcript as fallback
                    text = doc.summary or doc.image_caption or doc.audio_transcript or "(no content available)"
                    initial[doc_id] = {
                        "semantic_score": 0.0,
                        "file_name": doc.file_name,
                        "file_path": doc.file_path,
                        "modality": doc.modality,
                        "chunk_text": text,
                    }
        finally:
            session.close()

    # Step 3 – score
    scored: list[dict] = []
    for doc_id in expanded:
        meta = initial.get(doc_id, {
            "semantic_score": 0.0,
            "file_name": kw_graph.nodes[doc_id].get("file_name") if doc_id in kw_graph else None,
            "file_path": kw_graph.nodes[doc_id].get("file_path") if doc_id in kw_graph else None,
            "modality": kw_graph.nodes[doc_id].get("modality") if doc_id in kw_graph else None,
            "chunk_text": "",
        })
        ss = meta.get("semantic_score", 0.0)
        cs = centrality(doc_id, kw_graph, sem_graph)
        rs = recency_score(doc_id)
        imp = importance_score(doc_id)
        fs = alpha * ss + beta * cs + gamma * rs + delta * imp

        scored.append({
            "doc_id": doc_id,
            "file_name": meta.get("file_name"),
            "file_path": meta.get("file_path"),
            "modality": meta.get("modality"),
            "chunk_text": meta.get("chunk_text", ""),
            "final_score": fs,
            "semantic_score": ss,
            "centrality_score": cs,
            "temporal_score": rs,
            "importance_score": imp,
        })
        record_access(doc_id)

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored[:final_k]
