"""End-to-end ingestion workflow.

Scan directory → ingest each file → chunk → embed → enrich → persist
(Postgres + Qdrant) → build graphs.

The workflow is designed to be **idempotent**: re-running it on the
same directory skips files already stored in Postgres (by file_path).
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List

import networkx as nx

from app.config import RAW_DATA_DIR, EMBEDDING_DIMENSION
from app.core.chunker import chunk_text
from app.core.embedder import get_embedder
from app.core.enricher import extract_keywords, summarize
from app.core.ingestor import ingest
from app.db import postgres as pg
from app.db import qdrant_client as qdb
from app.db import redis_client as rdb
from app.graph.builder import build_all as build_graphs

log = logging.getLogger(__name__)


# ── Single-file pipeline ─────────────────────────────────────

def ingest_file(path: Path, session=None) -> int | None:
    """Process one file through the full pipeline.

    Returns the Postgres document id, or *None* if the file was skipped.
    """
    path = Path(path)
    own_session = session is None
    if own_session:
        session = pg.get_session()

    try:
        # Skip if already persisted
        existing = session.query(pg.Document).filter_by(file_path=str(path.resolve())).first()
        if existing:
            log.info("Skipping (already stored): %s", path.name)
            return existing.id

        # 1 – Ingest raw content
        text, meta = ingest(path)
        if not text.strip():
            log.warning("Empty content from %s — skipping", path.name)
            return None
        rdb.log_event("ingest", {"file": path.name, "modality": meta["modality"]})

        # 2 – Chunk
        chunks = chunk_text(text)
        rdb.log_event("chunk", {"file": path.name, "n_chunks": len(chunks)})

        # 3 – Embed
        embedder = get_embedder()
        vectors = embedder.embed_batch(chunks)
        rdb.log_event("embed", {"file": path.name, "dim": EMBEDDING_DIMENSION})

        # 4 – Enrich (summary + keywords)
        summary = summarize(text)
        keywords = extract_keywords(text)
        rdb.log_event("enrich", {"file": path.name, "keywords": keywords})

        # 5 – Persist to Postgres (metadata + chunk text only, no embeddings)
        doc = pg.upsert_document(
            session,
            file_path=str(path.resolve()),
            file_name=path.name,
            modality=meta["modality"],
            summary=summary,
            keywords=keywords,
            num_chunks=len(chunks),
            embedding_dim=EMBEDDING_DIMENSION,
            image_caption=meta.get("caption", ""),
            audio_transcript=meta.get("transcript", ""),
            file_size_bytes=meta.get("file_size_bytes", 0),
            file_extension=meta.get("file_extension", ""),
            file_timestamp=_parse_ts(meta.get("timestamp")),
            extra=meta,
        )
        pg.upsert_chunks(session, doc.id, [
            {"chunk_index": i, "text": c}
            for i, c in enumerate(chunks)
        ])
        session.commit()
        rdb.log_event("postgres_upsert", {"file": path.name, "doc_id": doc.id})

        # 6 – Persist to Qdrant (embeddings + metadata)
        points = []
        existing_count = _qdrant_max_id()
        for i, c in enumerate(chunks):
            pid = existing_count + (doc.id * 1000) + i  # unique point id
            points.append(qdb.build_point(
                point_id=pid,
                vector=vectors[i].tolist(),
                doc_id=doc.id,
                file_name=path.name,
                file_path=str(path.resolve()),
                modality=meta["modality"],
                chunk_index=i,
                chunk_text=c,
                keywords=keywords,
                summary=summary,
            ))
        qdb.upsert_points(points)
        rdb.log_event("qdrant_upsert", {"file": path.name, "n_points": len(points)})

        log.info("Ingested %s → doc_id=%d, %d chunks", path.name, doc.id, len(chunks))
        return doc.id

    except Exception:
        log.exception("Failed to ingest %s", path.name)
        session.rollback()
        return None
    finally:
        if own_session:
            session.close()


# ── Directory pipeline ────────────────────────────────────────

def ingest_directory(
    directory: Path | str | None = None,
    rebuild_graphs: bool = True,
) -> dict:
    """Ingest all supported files from *directory* (default: data/raw).

    Returns a summary dict: ``{ingested, skipped, failed, graph_built}``.
    """
    directory = Path(directory) if directory else RAW_DATA_DIR
    if not directory.exists():
        log.error("Directory does not exist: %s", directory)
        return {"error": f"Directory not found: {directory}"}

    from app.config import SUPPORTED_EXTENSIONS
    all_exts = {ext for exts in SUPPORTED_EXTENSIONS.values() for ext in exts}

    files = sorted(
        f for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in all_exts
    )
    log.info("Found %d files in %s", len(files), directory)
    rdb.log_event("pipeline_start", {"directory": str(directory), "n_files": len(files)})

    session = pg.get_session()
    ingested, skipped, failed = 0, 0, 0

    for path in files:
        result = ingest_file(path, session=session)
        if result is None:
            failed += 1
        else:
            # Check if it was a skip or new ingest by checking if doc already existed
            ingested += 1

    session.close()

    # Build / rebuild graphs
    graph_built = False
    if rebuild_graphs and ingested > 0:
        try:
            build_graphs()
            graph_built = True
            rdb.log_event("graphs_built", {"ingested": ingested})
        except Exception:
            log.exception("Graph build failed")

    summary = {
        "directory": str(directory),
        "total_files": len(files),
        "ingested": ingested,
        "failed": failed,
        "graph_built": graph_built,
    }
    rdb.log_event("pipeline_complete", summary)
    log.info("Pipeline complete: %s", summary)
    return summary


# ── Helpers ──────────────────────────────────────────────────

def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _qdrant_max_id() -> int:
    """Get the current max point id in Qdrant (for uniqueness)."""
    try:
        info = qdb.get_client().get_collection(qdb.QDRANT_COLLECTION)
        return info.points_count or 0
    except Exception:
        return 0
