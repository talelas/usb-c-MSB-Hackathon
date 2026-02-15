"""Pydantic request / response schemas for the API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Chat ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's question")
    session_id: str = Field(default="default", description="Conversation session ID")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of context chunks")
    temperature: float = Field(default=0.5, ge=0.0, le=2.0, description="LLM temperature (lower = more focused)")
    verify_relevance: bool = Field(default=False, description="Use LLM to verify document relevance before using them")
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum score to auto-keep documents (0-1)")


class SourceInfo(BaseModel):
    doc_id: int
    file_name: Optional[str] = None
    modality: Optional[str] = None
    score: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceInfo] = []
    session_id: str = "default"


# ── Ingestion ────────────────────────────────────────────────

class IngestRequest(BaseModel):
    directory: Optional[str] = Field(
        default=None,
        description="Path to local directory OR Google Drive/OneDrive shareable link. Defaults to data/raw.",
    )
    rebuild_graphs: bool = Field(default=True, description="Rebuild graphs after ingestion")


class IngestResponse(BaseModel):
    directory: str
    total_files: int = 0
    ingested: int = 0
    failed: int = 0
    graph_built: bool = False
    error: Optional[str] = None


# ── Documents ────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: int
    file_name: str
    file_path: str
    modality: str
    summary: str = ""
    keywords: List[str] = []
    num_chunks: int = 0


# ── Search ───────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    doc_id: int
    file_name: Optional[str] = None
    modality: Optional[str] = None
    chunk_text: Optional[str] = None
    final_score: float = 0.0
    semantic_score: float = 0.0
    centrality_score: float = 0.0
    temporal_score: float = 0.0
    importance_score: float = 0.0


class SearchResponse(BaseModel):
    results: List[SearchResult] = []
    query: str = ""


# ── Conversation History ─────────────────────────────────────

class ConversationMessage(BaseModel):
    role: str
    content: str


class ConversationResponse(BaseModel):
    session_id: str
    messages: List[ConversationMessage] = []


# ── Pipeline Logs ────────────────────────────────────────────

class LogEntry(BaseModel):
    event: str
    ts: float = 0.0
    data: Dict[str, Any] = {}


class LogsResponse(BaseModel):
    logs: List[Dict[str, Any]] = []


# ── Health ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    ollama: bool = False
    qdrant: bool = False
    postgres: bool = False
    redis: bool = False
