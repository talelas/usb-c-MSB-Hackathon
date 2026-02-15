# AI-MINDS — Cognitive Memory & RAG System

Modular retrieval-augmented generation system with graph-augmented search, conversation memory, and multi-modal ingestion.

## Architecture

```
ai_minds_project/
├── app/
│   ├── main.py              # FastAPI entry-point
│   ├── config.py            # Centralized env-based config
│   ├── api/
│   │   ├── routes.py        # REST endpoints
│   │   └── schemas.py       # Pydantic models
│   ├── core/
│   │   ├── chunker.py       # Text chunking
│   │   ├── embedder.py      # sentence-transformers wrapper
│   │   ├── enricher.py      # Ollama summarization + keywords
│   │   ├── ingestor.py      # File → (text, metadata)
│   │   └── media.py         # VLM captioning + Whisper transcription
│   ├── db/
│   │   ├── postgres.py      # SQLAlchemy ORM (Document + Chunk)
│   │   ├── redis_client.py  # Cache, logs, conversation memory
│   │   └── qdrant_client.py # Vector search
│   ├── graph/
│   │   ├── builder.py       # Keyword + semantic graph construction
│   │   └── retrieval.py     # Graph-augmented retrieval + temporal scoring
│   ├── llm/
│   │   ├── ollama_client.py # Ollama chat/generate wrapper
│   │   ├── prompts.py       # System prompt + context formatting
│   │   └── rag.py           # Full RAG pipeline
│   └── pipeline/
│       └── workflow.py       # End-to-end ingestion orchestration
├── data/raw/                 # Input files
├── output/                   # Graph JSON exports
├── docker-compose.yml        # Qdrant + PostgreSQL + Redis
├── requirements.txt
└── .env
```

## Quick Start

### 1. Start infrastructure

```bash
docker compose up -d
```

This starts **Qdrant** (`:6333`), **PostgreSQL** (`:5432`), and **Redis** (`:6379`).

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Pull the LLM

```bash
ollama pull llama3.2
```

### 4. Run the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs at **http://localhost:8000/docs**.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/health` | Service + dependency health check |
| `POST` | `/api/chat` | RAG chat (query -> retrieve -> generate) |
| `POST` | `/api/ingest` | Run ingestion pipeline on a directory |
| `POST` | `/api/search` | Graph-augmented semantic search |
| `GET`  | `/api/documents` | List all ingested documents |
| `GET`  | `/api/documents/{id}` | Get single document |
| `GET`  | `/api/conversations/{session_id}` | Get conversation history |
| `DELETE` | `/api/conversations/{session_id}` | Clear conversation |
| `GET`  | `/api/logs` | Pipeline log entries |
| `POST` | `/api/graphs/rebuild` | Force graph rebuild |

## Chat Example

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are cognitive systems?", "session_id": "demo"}'
```

## Environment Variables

See `.env` for all configurable settings (Postgres, Redis, Qdrant, Ollama, VLM mode, etc.).

## Key Design Decisions

- **DRY**: Each concern lives in exactly one module.
- **KISS**: Simple HTTP wrappers, no over-abstraction.
- **Conversation memory**: Redis lists with 24h TTL, per-session.
- **Graph-augmented retrieval**: `score = a*semantic + b*centrality + g*recency + d*importance`.
- **VLM dual-mode**: `VLM_MODE=server` (photoingestion HTTP) or `inline` (load Qwen2-VL in-process).
- **Idempotent pipeline**: Re-running ingestion skips already-stored files.

