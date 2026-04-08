"""PostgreSQL persistence layer (replaces CSV).

Uses SQLAlchemy 2.0 async-compatible style.  Tables:
  * **documents** – one row per ingested file
  * **chunks**    – one row per chunk (with FK to documents)
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    relationship,
    sessionmaker,
)

from app.config import DATABASE_URL


# ── ORM base ─────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Models ───────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    file_name       = Column(String(512), nullable=False)
    file_path       = Column(Text, nullable=False)
    modality        = Column(String(32), nullable=False)         # text|pdf|image|audio
    file_size_bytes = Column(Integer)
    file_extension  = Column(String(16))
    file_timestamp  = Column(DateTime)
    image_caption   = Column(Text, default="")
    audio_transcript= Column(Text, default="")
    summary         = Column(Text, default="")
    keywords        = Column(ARRAY(String), default=[])
    num_chunks      = Column(Integer, default=0)
    embedding_dim   = Column(Integer, default=384)
    extra           = Column(JSONB, default={})                  # any extra metadata
    created_at      = Column(DateTime, server_default=func.now())

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    doc_id      = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text        = Column(Text, default="")
    # embeddings stored only in Qdrant, not in Postgres
    created_at  = Column(DateTime, server_default=func.now())

    document = relationship("Document", back_populates="chunks")


# ── Engine / session factory ─────────────────────────────────

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    """Create all tables (idempotent)."""
    Base.metadata.create_all(get_engine())


# ── CRUD helpers ─────────────────────────────────────────────

def upsert_document(
    session: Session,
    file_path: str,
    file_name: str,
    modality: str,
    summary: str = "",
    keywords: list[str] | None = None,
    num_chunks: int = 0,
    embedding_dim: int = 384,
    image_caption: str = "",
    audio_transcript: str = "",
    file_size_bytes: int = 0,
    file_extension: str = "",
    file_timestamp: datetime | None = None,
    extra: dict | None = None,
) -> Document:
    """Insert or update a document (keyed on file_path)."""
    doc = session.query(Document).filter_by(file_path=file_path).first()
    if doc is None:
        doc = Document(file_path=file_path, file_name=file_name, modality=modality)
        session.add(doc)
    doc.summary = summary
    doc.keywords = keywords or []
    doc.num_chunks = num_chunks
    doc.embedding_dim = embedding_dim
    doc.image_caption = image_caption
    doc.audio_transcript = audio_transcript
    doc.file_size_bytes = file_size_bytes
    doc.file_extension = file_extension
    doc.file_timestamp = file_timestamp
    doc.extra = extra or {}
    session.flush()
    return doc


def upsert_chunks(session: Session, doc_id: int, chunks: list[dict]) -> None:
    """Replace all chunks for *doc_id*."""
    session.query(Chunk).filter_by(doc_id=doc_id).delete()
    for c in chunks:
        session.add(Chunk(
            doc_id=doc_id,
            chunk_index=c["chunk_index"],
            text=c.get("text", ""),
            # embeddings stored only in Qdrant
        ))
    session.flush()


def get_all_documents(session: Session) -> List[Document]:
    return session.query(Document).order_by(Document.id).all()


def get_document_by_id(session: Session, doc_id: int) -> Optional[Document]:
    return session.query(Document).get(doc_id)


def search_documents_by_keyword(session: Session, keyword: str) -> List[Document]:
    """Return documents whose keywords array contains *keyword* (case-insensitive)."""
    return (
        session.query(Document)
        .filter(Document.keywords.any(keyword.lower()))
        .all()
    )
