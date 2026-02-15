# usb-c-MSB-Hackathon

This repo contains the AI Minds multimodal ingestion pipeline (text, image, audio) plus a local caption server for Qwen2-VL.

## Prerequisites

- Windows PowerShell
- Python 3.10+ with venv
- Disk space for models (Qwen2-VL and sentence-transformers)
- Optional: Ollama running at http://localhost:11434 (for summaries/keywords)

## One-time setup

From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r photoingestion\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r ai_minds_project\requirements.txt
```

If you already have the venv, just install missing deps:

```powershell
.\.venv\Scripts\python.exe -m pip install qwen-vl-utils faster-whisper sentence-transformers
```

## 1) Start the image caption server (Qwen2-VL)

From the repo root:

```powershell
cd photoingestion
..\.venv\Scripts\python.exe server.py
```

Expected logs:
- "Model Loaded Successfully"
- "Server running at http://127.0.0.1:5000"

Note: This server responds to POST /analyze. Visiting the root URL in a browser shows "Not Found".

## 2) Run media-only test (optional)

Put test files here:
- ai_minds_project/data/raw/media_only/test.jpg
- ai_minds_project/data/raw/media_only/test.mp3

Then run:

```powershell
cd ..\ai_minds_project
..\.venv\Scripts\python.exe media_module_test.py
```

Expected:
- Image caption shows non-empty text (may take 2-5 minutes on CPU)
- Audio transcript shows non-empty text

## 3) Run full pipeline

```powershell
cd ..\ai_minds_project
..\.venv\Scripts\python.exe src\main.py
```

Outputs are written to:
- ai_minds_project/output/metadata_embeddings.json
- ai_minds_project/output/metadata_embeddings.csv

## 3b) Run a single file

Process one file and update outputs:

```powershell
cd ai_minds_project
..\.venv\Scripts\python.exe run_single.py "data/raw/media_only/test.jpg"
```

## 4) (Optional) Qdrant demo

If Qdrant is running locally, you can store and query media embeddings:

```powershell
cd ai_minds_project
..\.venv\Scripts\python.exe qdrant_media_demo.py
```

## 4b) Qdrant similarity search

Upsert embeddings and search by query text:

```powershell
cd ai_minds_project
..\.venv\Scripts\python.exe qdrant_search.py --upsert --query "ginger cat on floor"
```

## Troubleshooting

- Caption timeouts on CPU: Increase PHOTO_INGESTION_TIMEOUT in ai_minds_project/src/config.py (and config.py).
- "Not Found" in browser: Use POST http://127.0.0.1:5000/analyze, not the root URL.
- Ollama timeouts: Start Ollama or disable summarization in the pipeline.

## Useful paths

- Caption server: photoingestion/server.py
- Main pipeline: ai_minds_project/src/main.py
- Media test: ai_minds_project/media_module_test.py
- Config: ai_minds_project/src/config.py

---

# PROJECT CONTEXT — AI MINDS Cognitive Memory System

## Objective

Build a persistent multimodal cognitive assistant that:

- Automatically ingests raw personal data
- Converts it into structured semantic memory
- Maintains relationships over time
- Retrieves information using reasoning (not keyword matching)
- Verifies its own answers before responding
- Runs fully locally (LLM < 4B parameters)

This is NOT a chatbot.

This is a Graph-Augmented Persistent Memory Engine.

---

# High-Level Architecture

## 1) Multimodal Ingestion Layer

The system continuously ingests:

- Text
- PDF documents
- Images
- Audio

Each input passes through a modality adapter:

```
Raw Data
   ↓
Modality Adapter
   ↓
Unified Text Representation
   ↓
Embedding Model
```

Adapters:

- PDF → text chunks
- Image → caption model → text
- Audio → speech-to-text → text
- Text → cleaned & summarized

All modalities become unified semantic text.

---

# 2) Dual Storage Strategy

For each memory item, we store:

## Raw Layer

- Original file
- File path
- Timestamp

## Semantic Layer

- Cleaned text summary
- Embedding vector (256 dimensions)
- Metadata vector:
  - modality
  - timestamp
  - workspace
  - importance score
  - confidence score
  - user interaction count

Storage backend suggestion:

- Qdrant (vector DB with metadata filtering)

---

# 3) Vector + Metadata Coupled Representation

Each memory item =

```
{
  id,
  raw_reference,
  text_summary,
  embedding[256],
  metadata {
	  modality,
	  timestamp,
	  importance,
	  confidence,
	  workspace,
	  interaction_score
  }
}
```

Metadata is NOT cosmetic. It influences retrieval scoring.

---

# 4) Graph Memory Construction

A semantic graph is built dynamically.

Nodes:

- Memory items

Edges:
Weighted relationships based on:

```
Edge Weight =
  f(
	semantic_similarity,
	temporal_proximity,
	shared_metadata,
	co-occurrence,
  )
```

This graph is NOT static. It evolves as new memories are added.

Graph can be implemented using:

- Lightweight graph layer (e.g. NetworkX)
- Or adjacency stored in DB payload

---

# 5) Retrieval & Reasoning Pipeline

When a user asks a question:

## Step 1 — Semantic Retrieval

Query embedding → top-k vectors from Qdrant.

## Step 2 — Graph Expansion

Expand neighborhood around top-k nodes.

## Step 3 — Relevance Scoring

Final relevance score:

```
Score =
  α * semantic_similarity
+ β * graph_centrality
+ γ * recency_score
+ δ * importance_score
```

This prevents pure embedding search behavior.

---

# 6) Self-Verification Layer

Before answering:

1. Generate draft answer using retrieved nodes.
2. Check:
   - Does answer reference retrieved memory IDs?
   - Is there semantic agreement among top nodes?
3. If confidence < threshold:
   - Respond with uncertainty message.

This avoids confident hallucination.

---

# 7) Memory Adaptation Mechanism

The system updates memory importance based on:

- Query frequency
- User feedback
- Explicit reinforcement
- Time decay

Importance is dynamic.

Memory behaves cognitively.

---

# 8) Temporal Reasoning

Recency affects retrieval but does not dominate.

Temporal score example:

```
recency_score = e^(-λ * time_difference)
```

Allows:

- Recent information prioritization
- Old but important memories retained

---

# 9) LLM Constraints

Must comply with:

- Local open-source model
- < 4B parameters
- No proprietary APIs

Possible models:

- TinyLlama
- Phi-2
- Small Mistral quantized (if allowed)

Embedding model:

- Lightweight local sentence-transformer

---

# Innovation Points

This system differs from standard RAG because:

- It uses graph-augmented retrieval
- It applies temporal reasoning
- It maintains persistent memory
- It performs self-verification
- It adapts importance over time

It behaves like a cognitive memory engine.

---

# Folder Structure Suggestion

```
/core
	ingestion.py
	adapters/
	embedding.py
	storage.py
	graph_builder.py
	retrieval.py
	reasoning.py
	verification.py

/models
	local_llm/
	embedding_model/

/database
	qdrant_config/

/api
	main.py

/ui
	interface.py
```

---

# System Flow Summary

```
New Data →
	Adapt →
		Embed →
			Store →
				Update Graph

User Query →
	Embed →
		Retrieve →
			Expand Graph →
				Score →
					Generate →
						Verify →
							Answer
```

---

# Final Concept Name

Hybrid Graph-Augmented Persistent Semantic Memory System
