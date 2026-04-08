# 📦 Deployment & Distribution Guide

## Quick Copy-Paste Deploy

The entire `ai_minds_project` folder is self-contained and portable. 

### To Use on Another Machine:

**Option 1: Direct Copy**
```powershell
# Copy entire folder
cp -r "c:\Users\HP\OneDrive\Documents\lang chain\usb-c-MSB-Hackathon\ai_minds_project" "C:\YourLocation\"

# Navigate to it
cd "C:\YourLocation\ai_minds_project"

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_ollama.py
python test_pipeline.py

# Process files
python src/main.py
```

**Option 2: Via Git**
```bash
# Initialize git repo (if not already)
cd "c:\Users\HP\OneDrive\Documents\lang chain\usb-c-MSB-Hackathon\ai_minds_project"
git init
git add .
git commit -m "Initial commit"

# Then clone on another machine
git clone <your-repo-url>
```

---

## System Requirements

- **Python**: 3.8+
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 1GB free (for models)
- **Ollama**: Running (`ollama serve`)
- **Internet**: For downloading models (first run)

---

## Installation Checklist

- [ ] Python 3.8+ installed
- [ ] Ollama running (`ollama serve`)
- [ ] llama3.2 model installed (`ollama pull llama3.2`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Test passed (`python test_ollama.py`)
- [ ] Pipeline works (`python test_pipeline.py`)

---

## File Descriptions

### Core System Files
```
src/
├── config.py                 # Central configuration
├── main.py                   # Main orchestrator
├── ingestors/
│   └── ingestor.py          # File handlers (4 types supported)
├── embedders/
│   └── embedder.py          # Embedding engines (HuggingFace + Ollama)
└── storage/
    └── storage.py           # Storage, indexing, retrieval
```

### Data & Output
```
data/raw/                    # Put files here to process
output/                      # Generated embeddings & metadata
```

### Testing & Documentation
```
test_ollama.py              # Test Ollama connection (run first!)
test_pipeline.py            # Integration tests
COMPLETE_REPORT.md          # Detailed technical report
VECTOR_DB_INTEGRATION.py    # Guide for vector databases
README.md                   # This file
```

### Configuration
```
config.py                   # Edit to customize
requirements.txt            # Dependencies list
```

---

## Common Commands

### Test Everything
```bash
# 1. Test Ollama
python test_ollama.py

# 2. Run integration tests
python test_pipeline.py

# 3. Process your files
python src/main.py

# Result: output/ contains embeddings
```

### Add More Files
```bash
# 1. Place files in data/raw/
# 2. Run processor
python src/main.py

# 3. New embeddings added to output/
```

### Check Output
```bash
# View CSV summary
import pandas as pd
df = pd.read_csv("output/metadata_embeddings.csv")
print(df)

# Load full JSON data
import json
with open("output/metadata_embeddings.json") as f:
    data = json.load(f)
```

---

## Integration Examples

### With Qdrant
```python
# See VECTOR_DB_INTEGRATION.py for full code
from qdrant_client import QdrantClient
import json

# Load embeddings
with open("output/embeddings_only.json") as f:
    data = json.load(f)

# Send to Qdrant
# (Complete code in VECTOR_DB_INTEGRATION.py)
```

### With Your LLM
```python
# Retrieve relevant docs
from src.storage.storage import MemoryIndex, MetadataStorage

index = MemoryIndex(
    MetadataStorage(
        "output/metadata_embeddings.json",
        "output/metadata_embeddings.csv"
    )
)

# Find similar documents
results = index.find_by_keyword("your_query")

# Pass to LLM with context
context = "\n".join([r['text_summary'] for r in results])
# ... feed to your LLM
```

### With FastAPI (REST API)
```python
from fastapi import FastAPI
from src.storage.storage import MetadataStorage, MemoryIndex

app = FastAPI()
storage = MetadataStorage(...)
index = MemoryIndex(storage)

@app.get("/search")
def search(query: str):
    results = index.find_by_keyword(query)
    return results
```

---

## Customization Guide

### Change Embedding Model
Edit `src/config.py`:
```python
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Change this
```

Available models (from HuggingFace):
- `all-MiniLM-L6-v2` (384 dims, fast) - **Default**
- `all-mpnet-base-v2` (768 dims, better quality)
- `paraphrase-MiniLM-L6-v2` (384 dims, semantic)

### Change Ollama Model
Edit `src/config.py`:
```python
OLLAMA_MODEL = "llama3.2"  # Change this
```

Other models available:
- `llama3.2` - 1.88 GB - **Default**
- `llama2` - 3.8 GB
- `mistral` - 4.1 GB
- `neural-chat` - 4.1 GB

### Adjust Chunk Size
Edit `src/config.py`:
```python
CHUNK_SIZE = 512        # Characters per chunk
CHUNK_OVERLAP = 50      # Overlap between chunks
```

### Change Output Location
Edit `src/config.py`:
```python
OUTPUT_DIR = PROJECT_ROOT / "output"  # Change path here
```

---

## Troubleshooting

### "Ollama not running"
```bash
# Solution:
ollama serve
```

### "Model not installed"
```bash
# Solution:
ollama pull llama3.2
```

### "Module not found"
```bash
# Solution:
pip install -r requirements.txt
```

### "Permission denied"
```bash
# Run as administrator or fix permissions
python -m pip install --upgrade pip
```

### "Out of memory"
```python
# Edit config.py
CHUNK_SIZE = 256        # Reduce from 512
MAX_FILE_SIZE = 50 * 1024 * 1024  # Reduce from 100MB
```

---

## Performance Optimization

### For Speed
- Use smaller embedding model: `all-MiniLM-L6-v2` ✓ (already default)
- Process files in batches
- Use GPU if available (see torch install instructions)

### For Quality  
- Use larger embedding model: `all-mpnet-base-v2`
- Increase chunk size: 512 → 1024
- Decrease chunk overlap: 50 → 25

### For Memory
- Reduce chunk size: 512 → 256
- Process fewer files at a time
- Use CPU instead of GPU

---

## Scaling Guide

### Single Machine (Current Setup)
```
Files: 1-1000
Time: Minutes to hours
Storage: MB to GB
Setup: This folder
```

### Multi-Machine
```
Add NAS/shared storage for embeddings
Scale by adding more processing nodes
```

### Cloud Deployment
```
Upload to cloud storage (S3, GCS, Azure Blob)
Deploy processor on serverless (Lambda, Cloud Functions)
Store embeddings in managed vector DB (Pinecone, Weaviate Cloud)
```

---

## Production Checklist

- [ ] All tests passing
- [ ] Ollama running and tested
- [ ] Dependencies installed
- [ ] Sample files processed successfully
- [ ] Output files verified
- [ ] Error handling tested
- [ ] Logging configured
- [ ] Backup strategy in place
- [ ] Performance benchmarks run
- [ ] Security reviewed

---

## Support & Documentation

1. **Technical Details**: See `COMPLETE_REPORT.md`
2. **Vector DB Integration**: See `VECTOR_DB_INTEGRATION.py`
3. **Code Comments**: Check inline comments in src/ files
4. **Test Examples**: Run `test_pipeline.py` and `test_ollama.py`

---

## File Manifest

```
ai_minds_project/
├── src/                           # Core system
│   ├── __init__.py
│   ├── config.py                 # ← EDIT THIS for customization
│   ├── main.py                   # ← RUN THIS
│   ├── ingestors/__init__.py
│   ├── ingestors/ingestor.py     # File handling
│   ├── embedders/__init__.py
│   ├── embedders/embedder.py     # Embeddings & Ollama
│   ├── storage/__init__.py
│   ├── storage/storage.py        # Storage & indexing
│   └── utils/__init__.py
├── data/
│   └── raw/                      # ← PUT FILES HERE
│       ├── ai_foundations.md
│       ├── cognitive_systems.txt
│       └── test_sample.txt
├── output/                       # ← CHECK RESULTS HERE
│   ├── metadata_embeddings.json
│   ├── metadata_embeddings.csv
│   └── embeddings_only.json
├── config.py                     # Configuration reference
├── requirements.txt              # Install these
├── test_ollama.py               # ← RUN FIRST
├── test_pipeline.py             # ← RUN SECOND
├── README.md                     # Overview
├── COMPLETE_REPORT.md            # Technical details
├── VECTOR_DB_INTEGRATION.py      # Vector DB guide
├── quickstart.sh                 # Quick start
└── DEPLOYMENT.md                 # This file
```

---

## Quick Start (TL;DR)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test Ollama
python test_ollama.py

# 3. Test pipeline
python test_pipeline.py

# 4. Add your files to data/raw/

# 5. Process
python src/main.py

# 6. Check output/ for results

# 7. Integrate with vector DB using VECTOR_DB_INTEGRATION.py
```

That's it! 🚀

---

**The system is ready to deploy and use immediately!**

