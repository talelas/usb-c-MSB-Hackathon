# 🚀 Setup Guide - AI Minds Memory System

## Prerequisites

- Python 3.8+
- Ollama installed and running (optional but recommended)
- 4GB+ RAM
- Internet connection (for downloading models on first run)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- **sentence-transformers** - For generating embeddings
- **PyPDF2** - For PDF processing
- **Pillow** - For image processing
- **requests** - For Ollama API communication
- Other utilities

### 2. Start Ollama (Optional but Recommended)

Ollama provides semantic enrichment (summarization, keyword extraction).

```bash
# Start Ollama service (if not already running)
ollama serve

# In another terminal, pull llama 3.2
ollama pull llama3.2
```

**Note:** The system works without Ollama, but enrichment features will be limited.

### 3. Prepare Input Files

Place files to process in:
```
data/raw/
```

Supported formats:
- **Text**: `.txt`, `.md`
- **PDF**: `.pdf`
- **Images**: `.jpg`, `.jpeg`, `.png`
- **Audio**: `.mp3`, `.wav`, `.m4a`, `.flac`

Example:
```
data/raw/
├── document1.txt
├── document2.pdf
├── image1.jpg
└── audio1.mp3
```

### 4. Run Tests

Verify the system works:

```bash
python test_pipeline.py
```

This tests:
- ✓ Embedder initialization
- ✓ Ollama connection
- ✓ File ingestion
- ✓ Complete pipeline
- ✓ Storage system

### 5. Process Files

```bash
python src/main.py
```

This will:
1. **Ingest** all files from `data/raw/`
2. **Extract** text from each file
3. **Chunk** text into processable segments
4. **Embed** each chunk with HuggingFace
5. **Enrich** with summaries and keywords (if Ollama available)
6. **Store** metadata + embeddings to JSON and CSV

### 6. Check Output

Results saved to `output/`:
```
output/
├── metadata_embeddings.json      # Full metadata + embeddings
├── metadata_embeddings.csv        # Metadata summary
└── embeddings_only.json           # Just embeddings for vector DB
```

## File Structure

```
.
├── data/
│   └── raw/               ← Input files here
├── output/                ← Results here
├── src/
│   ├── config.py          ← Configuration
│   ├── main.py            ← Main processor
│   ├── ingestors/         ← File type handlers
│   ├── embedders/         ← Embedding models
│   ├── storage/           ← Metadata storage
│   └── utils/             ← Helpers
├── test_pipeline.py       ← Integration tests
└── requirements.txt       ← Dependencies
```

## Configuration

Edit `src/config.py` to customize:

```python
# Embedding Model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # HuggingFace model
EMBEDDING_DIMENSION = 384

# Ollama Settings
OLLAMA_MODEL = "llama3.2"
OLLAMA_API_URL = "http://localhost:11434"

# Processing
CHUNK_SIZE = 512           # Characters per chunk
CHUNK_OVERLAP = 50         # Overlap between chunks
```

## Troubleshooting

### "sentence-transformers not found"
```bash
pip install sentence-transformers
```

### "Ollama not running"
- Start Ollama: `ollama serve`
- System works without it (reduced features)

### "No files processed"
- Check that files are in `data/raw/`
- Verify file extensions are supported

### "PDF extraction failed"
```bash
pip install PyPDF2
```

### Memory issues
- Reduce `CHUNK_SIZE` in config
- Process fewer files at once
- Use smaller embedding model

## Performance Tips

1. **Batch Processing**: Process multiple files to leverage GPU
2. **Smaller Model**: Use `all-MiniLM-L6-v2` (default) or even smaller models
3. **GPU Acceleration**: Install `pytorch` with CUDA support for faster embeddings
4. **Async Processing**: Modify main.py to process files in parallel

## Next Steps

After embedding and storage:

1. **Build Vector Index** (Qdrant, Weaviate, etc.)
2. **Implement Search** (semantic + metadata filtering)
3. **Add Retrieval-Augmented Generation** (RAG)
4. **Deploy Memory Service** (API endpoint)
5. **Build Frontend** (UI for memory interaction)

---

For more information, see [README.md](README.md)
