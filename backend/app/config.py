"""Centralized configuration — single source of truth.

All settings are read from environment variables (with defaults).
`python-dotenv` loads `.env` automatically on import.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# ── Paths ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
OUTPUT_DIR   = PROJECT_ROOT / "output"

for _d in (DATA_DIR, RAW_DATA_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Embedding ────────────────────────────────────────────────
EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))

# ── Chunking ─────────────────────────────────────────────────
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ── Ollama (LLM) ────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2")

# ── Media: VLM image captioning ─────────────────────────────
#   Qwen2-VL model loaded inline (requires GPU)
VLM_PROMPT            = os.getenv("VLM_PROMPT", "Describe this image in detail.")

# ── Media: Audio transcription (faster-whisper) ─────────────
WHISPER_MODEL        = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE       = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# ── Feature flags ────────────────────────────────────────────
GENERATE_MEDIA_TEXT = os.getenv("GENERATE_MEDIA_TEXT", "True").lower() in ("1", "true", "yes")

# ── Qdrant ───────────────────────────────────────────────────
QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "memoir_embeddings")

# ── PostgreSQL ───────────────────────────────────────────────
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "memoir_user")
POSTGRES_PASS = os.getenv("POSTGRES_PASSWORD", "memoir_password")
POSTGRES_DB   = os.getenv("POSTGRES_DB", "memoir")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# ── Redis ────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB   = int(os.getenv("REDIS_DB", "0"))
REDIS_URL  = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# ── Supported file types ─────────────────────────────────────
SUPPORTED_EXTENSIONS: dict[str, list[str]] = {
    "text":  [".txt", ".md"],
    "pdf":   [".pdf"],
    "image": [".jpg", ".jpeg", ".png", ".bmp"],
    "audio": [".mp3", ".wav", ".m4a", ".flac"],
}

ALL_EXTENSIONS = [ext for exts in SUPPORTED_EXTENSIONS.values() for ext in exts]
