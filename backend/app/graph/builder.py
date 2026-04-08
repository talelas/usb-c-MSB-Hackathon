"""Build keyword and semantic memory graphs.

Keyword graph  – edges via Jaccard similarity on document keywords.
Semantic graph – edges via cosine similarity on Qdrant embeddings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import networkx as nx
import numpy as np

from app.config import OUTPUT_DIR
from app.db import qdrant_client as qdb
from app.db.postgres import Document, get_session


# ── Math helpers ─────────────────────────────────────────────

def cosine_similarity(a: List[float], b: List[float]) -> float:
    v1, v2 = np.array(a), np.array(b)
    d = np.dot(v1, v2)
    n = np.linalg.norm(v1) * np.linalg.norm(v2)
    return float(d / n) if n else 0.0


def jaccard(s1: set, s2: set) -> float:
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


# ── Data loading ─────────────────────────────────────────────

def _docs_from_postgres() -> List[dict]:
    """Pull document metadata from PostgreSQL."""
    session = get_session()
    try:
        docs = session.query(Document).order_by(Document.id).all()
        return [
            {
                "id": d.id,
                "file_name": d.file_name,
                "file_path": d.file_path,
                "modality": d.modality,
                "keywords": d.keywords or [],
                "summary": d.summary or "",
            }
            for d in docs
        ]
    finally:
        session.close()


# ── Graph construction ───────────────────────────────────────

def build_keyword_graph(documents: List[dict], threshold: float = 0.1) -> nx.Graph:
    G = nx.Graph()
    for doc in documents:
        G.add_node(doc["id"], **doc)

    with_kw = [d for d in documents if d.get("keywords")]
    for i, d1 in enumerate(with_kw):
        kw1 = {k.lower() for k in d1["keywords"]}
        for d2 in with_kw[i + 1:]:
            kw2 = {k.lower() for k in d2["keywords"]}
            sim = jaccard(kw1, kw2)
            if sim >= threshold:
                G.add_edge(d1["id"], d2["id"], weight=sim, edge_type="keyword")
    return G


def build_semantic_graph(
    documents: List[dict],
    doc_embeddings: Dict[int, List[float]],
    threshold: float = 0.5,
    max_edges: int = 10,
) -> nx.Graph:
    G = nx.Graph()
    for doc in documents:
        G.add_node(doc["id"], **doc)

    ids = list(doc_embeddings.keys())
    for i, id1 in enumerate(ids):
        sims = []
        for id2 in ids[i + 1:]:
            s = cosine_similarity(doc_embeddings[id1], doc_embeddings[id2])
            if s >= threshold:
                sims.append((id2, s))
        sims.sort(key=lambda x: x[1], reverse=True)
        for id2, s in sims[:max_edges]:
            G.add_edge(id1, id2, weight=s, edge_type="semantic")
    return G


# ── Persistence ──────────────────────────────────────────────

def _export(G: nx.Graph, path: Path) -> None:
    data = {
        "nodes": [
            {k: v for k, v in {**G.nodes[n], "id": n}.items()}
            for n in G.nodes()
        ],
        "edges": [
            {"source": u, "target": v, "weight": d.get("weight"), "edge_type": d.get("edge_type")}
            for u, v, d in G.edges(data=True)
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _load_graph(path: Path) -> nx.Graph:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    G = nx.Graph()
    for n in data["nodes"]:
        G.add_node(n["id"], **n)
    for e in data["edges"]:
        G.add_edge(e["source"], e["target"], weight=e.get("weight", 0), edge_type=e.get("edge_type"))
    return G


# ── Public API ───────────────────────────────────────────────

KEYWORD_PATH  = OUTPUT_DIR / "keyword_graph.json"
SEMANTIC_PATH = OUTPUT_DIR / "semantic_graph.json"


def build_all() -> tuple[nx.Graph, nx.Graph]:
    """Build both graphs from Postgres + Qdrant and persist to disk."""
    docs = _docs_from_postgres()
    kw_g = build_keyword_graph(docs)
    _export(kw_g, KEYWORD_PATH)

    embs = qdb.get_doc_embeddings()
    sem_g = build_semantic_graph(docs, embs)
    _export(sem_g, SEMANTIC_PATH)

    return kw_g, sem_g


def load_all() -> tuple[nx.Graph, nx.Graph]:
    """Load persisted graphs (call :func:`build_all` first)."""
    return _load_graph(KEYWORD_PATH), _load_graph(SEMANTIC_PATH)
