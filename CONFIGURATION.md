# Configuration Guide for New Users

This guide explains where to configure the addresses/endpoints for Ollama (LLM), Qwen (image captions), and faster-whisper (audio transcription).

## Main Configuration File

**File:** `ai_minds_project/src/config.py`

This is the **single source of truth** for all model endpoints and settings.

---

## 1. Ollama (LLM for Summaries & Keywords)

```python
OLLAMA_MODEL = "llama3.2"
OLLAMA_API_URL = "http://localhost:11434"
```

**What to change:**
- If Ollama is running on a different machine, change `OLLAMA_API_URL` to that IP/port
- Example: `OLLAMA_API_URL = "http://192.168.1.100:11434"`
- If using a different model, change `OLLAMA_MODEL` to your model name

---

## 2. Qwen2-VL (Image Caption Server)

```python
PHOTO_INGESTION_URL = "http://127.0.0.1:5000/analyze"
PHOTO_INGESTION_PROMPT = "Describe this image in detail."
PHOTO_INGESTION_TIMEOUT = 300  # seconds
```

**What to change:**
- If the Qwen server is on a different machine, change `PHOTO_INGESTION_URL`
- Example: `PHOTO_INGESTION_URL = "http://192.168.1.101:5000/analyze"`
- Adjust timeout if your hardware is faster/slower
- Set `PHOTO_INGESTION_URL = None` to disable image captions completely

---

## 3. Faster-Whisper (Audio Transcription)

```python
AUDIO_TRANSCRIBE_ENABLED = True
AUDIO_TRANSCRIBE_MODEL = "base"
AUDIO_TRANSCRIBE_DEVICE = "cpu"
AUDIO_TRANSCRIBE_COMPUTE_TYPE = "int8"
```

**What to change:**
- `AUDIO_TRANSCRIBE_MODEL`: Use `"tiny"`, `"base"`, `"small"`, `"medium"`, or `"large"` (bigger = better quality, slower)
- `AUDIO_TRANSCRIBE_DEVICE`: Change to `"cuda"` if you have NVIDIA GPU
- `AUDIO_TRANSCRIBE_COMPUTE_TYPE`: Use `"float16"` for GPU, `"int8"` for CPU
- Set `AUDIO_TRANSCRIBE_ENABLED = False` to disable audio transcription

---

## 4. Media Cache Settings

```python
USE_MEDIA_TEXT_CACHE = True
GENERATE_MEDIA_TEXT = False
MEDIA_TEXT_CACHE_FILE = OUTPUT_DIR / "media_text_cache.json"
```

**What to change:**
- `GENERATE_MEDIA_TEXT = True` → Enable live caption/transcription generation (requires servers running)
- `GENERATE_MEDIA_TEXT = False` → Use cached captions/transcripts only (fast, offline mode)

---

## 5. Qdrant Vector Database

**Note:** Qdrant host/port are configured via CLI arguments in `qdrant_search.py`:

```bash
python qdrant_search.py --host 127.0.0.1 --port 6333 --query "your query"
```

**What to change:**
- If Qdrant is on another machine, use `--host IP_ADDRESS`
- Example: `--host 192.168.1.102 --port 6333`

---

## Quick Setup Checklist

1. **Edit `ai_minds_project/src/config.py`**:
   - Set Ollama URL/model
   - Set Qwen server URL (or disable)
   - Set audio transcription device/model (or disable)

2. **Start required servers**:
   ```bash
   # Ollama (if not running)
   ollama serve
   
   # Qwen caption server (if using images)
   cd photoingestion
   python server.py
   
   # Qdrant (if using vector search)
   cd qdrant
   .\qdrant.exe
   ```

3. **Run pipeline**:
   ```bash
   cd ai_minds_project
   python src\main.py
   ```

---

## Example: Remote GPU Server Setup

If you have Ollama and Qwen on a remote GPU machine (IP: 192.168.1.50):

```python
# ai_minds_project/src/config.py

OLLAMA_API_URL = "http://192.168.1.50:11434"
PHOTO_INGESTION_URL = "http://192.168.1.50:5000/analyze"
AUDIO_TRANSCRIBE_DEVICE = "cpu"  # Local CPU transcription
```

---

## Troubleshooting

- **"Connection refused"**: Check if the server is running and the IP/port is correct
- **Timeouts**: Increase `PHOTO_INGESTION_TIMEOUT` or use faster hardware
- **"Model not found"**: Install the model (`ollama pull llama3.2`) or change the model name
- **Import errors**: Install dependencies (`pip install -r requirements.txt`)

---

For more details, see the main [README.md](../README.md).
