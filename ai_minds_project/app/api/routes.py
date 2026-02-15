"""FastAPI route definitions.

All routes are mounted on the ``/api`` prefix by the main app.
"""
from __future__ import annotations

import logging
from pathlib import Path

import networkx as nx
from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    DocumentOut,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    LogsResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.db import postgres as pg
from app.db import redis_client as rdb
from app.graph.builder import build_all, load_all
from app.graph import retrieval as graph_retrieval
from app.llm import ollama_client as llm_client
from app.llm.rag import answer as rag_answer, clear_history, get_history
from app.pipeline.workflow import ingest_directory, ingest_file as pipeline_ingest_file

log = logging.getLogger(__name__)

router = APIRouter()

# ── Shared graph state (loaded once at startup) ──────────────
_kw_graph: nx.Graph = nx.Graph()
_sem_graph: nx.Graph = nx.Graph()


def load_graphs() -> None:
    """Load or build graphs into module-level state."""
    global _kw_graph, _sem_graph
    try:
        _kw_graph, _sem_graph = load_all()
        log.info("Graphs loaded from disk")
    except FileNotFoundError:
        log.warning("Graph files not found — building from scratch")
        try:
            _kw_graph, _sem_graph = build_all()
        except Exception:
            log.exception("Failed to build graphs at startup")


# ── Health ───────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Service health and dependency status."""
    qdrant_ok = False
    try:
        from app.db.qdrant_client import get_client
        get_client().get_collections()
        qdrant_ok = True
    except Exception:
        pass

    pg_ok = False
    try:
        session = pg.get_session()
        session.execute(pg.func.now())
        session.close()
        pg_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        rdb._get_client().ping()
        redis_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        ollama=llm_client.is_available(),
        qdrant=qdrant_ok,
        postgres=pg_ok,
        redis=redis_ok,
    )


# ── Chat (RAG) ──────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Answer a question using the RAG pipeline."""
    result = rag_answer(
        req.query,
        _kw_graph,
        _sem_graph,
        session_id=req.session_id,
        top_k=req.top_k,
        temperature=req.temperature,
        verify_relevance=req.verify_relevance,
        min_confidence=req.min_confidence,
    )
    return ChatResponse(**result)


# ── Ingestion ────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    """Run the ingestion pipeline on a directory."""
    global _kw_graph, _sem_graph
    summary = ingest_directory(
        directory=req.directory,
        rebuild_graphs=req.rebuild_graphs,
    )
    if "error" in summary:
        raise HTTPException(status_code=400, detail=summary["error"])

    # Reload graphs if they were rebuilt
    if summary.get("graph_built"):
        try:
            _kw_graph, _sem_graph = load_all()
        except Exception:
            pass

    return IngestResponse(**summary)


# ── Documents ────────────────────────────────────────────────

@router.get("/documents", response_model=list[DocumentOut])
def list_documents():
    """List all ingested documents."""
    session = pg.get_session()
    try:
        docs = pg.get_all_documents(session)
        return [
            DocumentOut(
                id=d.id,
                file_name=d.file_name,
                file_path=d.file_path,
                modality=d.modality,
                summary=d.summary or "",
                keywords=d.keywords or [],
                num_chunks=d.num_chunks or 0,
            )
            for d in docs
        ]
    finally:
        session.close()


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int):
    """Get a single document by ID."""
    session = pg.get_session()
    try:
        doc = pg.get_document_by_id(session, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentOut(
            id=doc.id,
            file_name=doc.file_name,
            file_path=doc.file_path,
            modality=doc.modality,
            summary=doc.summary or "",
            keywords=doc.keywords or [],
            num_chunks=doc.num_chunks or 0,
        )
    finally:
        session.close()


# ── Search ───────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """Graph-augmented semantic search (without LLM generation)."""
    results = graph_retrieval.retrieve(
        req.query, _kw_graph, _sem_graph, final_k=req.top_k,
    )
    return SearchResponse(
        query=req.query,
        results=[SearchResult(**r) for r in results],
    )


# ── Conversation history ─────────────────────────────────────

@router.get("/conversations/{session_id}", response_model=ConversationResponse)
def conversation_history(session_id: str, last_n: int = 20):
    """Retrieve conversation history for a session."""
    messages = get_history(session_id, last_n=last_n)
    return ConversationResponse(session_id=session_id, messages=messages)


@router.delete("/conversations/{session_id}")
def conversation_delete(session_id: str):
    """Clear conversation history for a session."""
    clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}


# ── Logs ─────────────────────────────────────────────────────

@router.get("/logs", response_model=LogsResponse)
def pipeline_logs(last_n: int = 50):
    """Get recent pipeline log entries from Redis."""
    return LogsResponse(logs=rdb.get_logs(last_n))


# ── Graphs ───────────────────────────────────────────────────

@router.post("/graphs/rebuild")
def rebuild_graphs():
    """Force rebuild of keyword + semantic graphs."""
    global _kw_graph, _sem_graph
    try:
        _kw_graph, _sem_graph = build_all()
        return {
            "status": "rebuilt",
            "keyword_nodes": _kw_graph.number_of_nodes(),
            "keyword_edges": _kw_graph.number_of_edges(),
            "semantic_nodes": _sem_graph.number_of_nodes(),
            "semantic_edges": _sem_graph.number_of_edges(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── File Management ──────────────────────────────────────────

@router.post("/files/ingest")
def ingest_single_file(file_path: str):
    """Ingest a single file by path."""
    from pathlib import Path
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    result = pipeline_ingest_file(path)
    
    # Reload graphs if file was successfully ingested
    if result.get("status") == "success":
        global _kw_graph, _sem_graph
        try:
            _kw_graph, _sem_graph = load_all()
        except Exception:
            pass
    
    return result


@router.delete("/files")
def delete_file_from_system(file_path: str):
    """Delete a file from the database and vector store (not from disk)."""
    from pathlib import Path
    
    path = Path(file_path).resolve()
    
    try:
        session = pg.get_session()
        try:
            # Find document by file path
            doc = session.query(pg.Document).filter_by(file_path=str(path)).first()
            
            if not doc:
                raise HTTPException(status_code=404, detail="File not found in database")
            
            doc_id = doc.id
            
            # Delete from Postgres (cascades to chunks)
            session.delete(doc)
            session.commit()
            
            # Delete from Qdrant
            from app.db import qdrant_client as qdb
            try:
                client = qdb.get_client()
                points = qdb.scroll_all()
                ids_to_delete = [
                    p.id for p in points 
                    if p.payload and p.payload.get("doc_id") == doc_id
                ]
                if ids_to_delete:
                    client.delete(
                        collection_name=qdb.QDRANT_COLLECTION,
                        points_selector=ids_to_delete
                    )
            except Exception as e:
                log.error(f"Failed to delete from Qdrant: {e}")
            
            # Reload graphs
            global _kw_graph, _sem_graph
            try:
                _kw_graph, _sem_graph = build_all()
            except Exception:
                pass
            
            return {
                "status": "deleted",
                "doc_id": doc_id,
                "file_path": str(path),
                "vectors_deleted": len(ids_to_delete) if ids_to_delete else 0
            }
                
        finally:
            session.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
