# Memoir — Backend (FastAPI RAG Engine)

Modular retrieval-augmented generation system with graph-augmented search, conversation memory, and multi-modal ingestion.

→ **See the [root README](../README.md) for the full project overview and quick-start.**

---

## Architecture

```
backend/
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
│   ├── integration/
│   │   └── file_watcher.py  # In-process file-watcher integration
│   ├── llm/
│   │   ├── ollama_client.py # Ollama chat/generate wrapper
│   │   ├── prompts.py       # System prompt + context formatting
│   │   └── rag.py           # Full RAG pipeline
│   ├── pipeline/
│   │   └── workflow.py      # End-to-end ingestion orchestration
│   └── services/
│       └── file_watcher_service.py  # Standalone watcher service
├── scripts/
│   ├── build_graphs.py      # CLI: rebuild knowledge graphs
│   └── qdrant_search.py     # CLI: debug Qdrant search
├── docs/
│   └── RELEVANCE_VERIFICATION.md  # LLM relevance filtering docs
├── data/                    # git-ignored — put raw input files here
│   ├── raw/
│   └── processed/
├── output/                  # git-ignored — auto-generated graph JSON
├── docker-compose.yml       # Qdrant + PostgreSQL + Redis
├── requirements.txt
├── .env.example
└── .env                     # git-ignored
```

---

## Quick Start

### 1. Start infrastructure

```bash
docker compose up -d
```

Starts **Qdrant** (`:6333`), **PostgreSQL** (`:5432`), and **Redis** (`:6379`).

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your Postgres, Redis, Qdrant, and Ollama settings
```

### 4. Pull the LLM

```bash
ollama pull llama3.2
```

### 5. Run the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs → **http://localhost:8000/docs**

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/health` | Service + dependency health check |
| `POST` | `/api/chat` | RAG chat (query → retrieve → generate) |
| `POST` | `/api/ingest` | Run ingestion pipeline on a directory or drive link |
| `POST` | `/api/search` | Graph-augmented semantic search |
| `GET`  | `/api/documents` | List all ingested documents |
| `GET`  | `/api/documents/{id}` | Get single document |
| `GET`  | `/api/conversations/{session_id}` | Get conversation history |
| `DELETE` | `/api/conversations/{session_id}` | Clear conversation |
| `GET`  | `/api/logs` | Pipeline log entries |
| `POST` | `/api/graphs/rebuild` | Force graph rebuild |

---

## Chat Example

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are cognitive systems?", "session_id": "demo"}'
```

---

## Scripts

```bash
# Rebuild knowledge graphs from existing DB data
python scripts/build_graphs.py

# Debug Qdrant vector search
python scripts/qdrant_search.py --query "your query here"
```

---

## Key Design Decisions

- **DRY**: Each concern lives in exactly one module.
- **KISS**: Simple HTTP wrappers, no over-abstraction.
- **Conversation memory**: Redis lists with 24h TTL, per-session.
- **Graph-augmented retrieval**: `score = α·semantic + β·centrality + γ·recency + δ·importance`.
- **VLM dual-mode**: `VLM_MODE=server` (photoingestion HTTP) or `inline` (load Qwen2-VL in-process).
- **Idempotent pipeline**: Re-running ingestion skips already-stored files.

---

## Further Reading

- [Relevance Verification](docs/RELEVANCE_VERIFICATION.md) — LLM-based document filtering
- [File Watching Guide](../file_handling/docs/FILE_WATCHING.md) — Auto-ingestion via local + cloud watchers
- [Drive Integration](../file_handling/docs/DRIVE_LINK_INTEGRATION.md) — Google Drive / OneDrive ingestion
