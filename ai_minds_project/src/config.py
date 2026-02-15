"""Configuration for the Memory System"""
import os
from pathlib import Path
try:
    # Load .env automatically when config is imported so env overrides work
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except Exception:
    pass

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Create directories if they don't exist
for directory in [DATA_DIR, OUTPUT_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Embedding Configuration
# Allow overriding via environment variables (e.g. in a .env file)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")  # HuggingFace model
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

# Photo ingestion (Qwen2-VL server)
PHOTO_INGESTION_URL = os.getenv("PHOTO_INGESTION_URL", "http://127.0.0.1:5000/analyze")
PHOTO_INGESTION_PROMPT = "Describe this image in detail."
PHOTO_INGESTION_TIMEOUT = 300  # Increased for CPU inference (can exceed 180 seconds)

# Media text caching (use captions/transcripts from JSON to avoid slow inference)
USE_MEDIA_TEXT_CACHE = os.getenv("USE_MEDIA_TEXT_CACHE", "True").lower() in ("1", "true", "yes")
GENERATE_MEDIA_TEXT = os.getenv("GENERATE_MEDIA_TEXT", "False").lower() in ("1", "true", "yes")
MEDIA_TEXT_CACHE_FILE = OUTPUT_DIR / "media_text_cache.json"

# Audio transcription (faster-whisper)
AUDIO_TRANSCRIBE_ENABLED = os.getenv("AUDIO_TRANSCRIBE_ENABLED", "True").lower() in ("1", "true", "yes")
AUDIO_TRANSCRIBE_MODEL = os.getenv("AUDIO_TRANSCRIBE_MODEL", "base")
AUDIO_TRANSCRIBE_DEVICE = os.getenv("AUDIO_TRANSCRIBE_DEVICE", "cpu")
AUDIO_TRANSCRIBE_COMPUTE_TYPE = os.getenv("AUDIO_TRANSCRIBE_COMPUTE_TYPE", "int8")

# Storage control (production memory optimization)
STORE_MEDIA_TEXT_IN_METADATA = True
STORE_CHUNK_TEXT = True

# Storage
METADATA_OUTPUT_FILE = OUTPUT_DIR / "metadata_embeddings.json"
METADATA_CSV_FILE = OUTPUT_DIR / "metadata_embeddings.csv"

# Processing
CHUNK_SIZE = 512  # Characters per chunk
CHUNK_OVERLAP = 50
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Supported file types
SUPPORTED_FORMATS = {
    'text': ['.txt', '.md'],
    'pdf': ['.pdf'],
    'image': ['.jpg', '.jpeg', '.png', '.bmp'],
    'audio': ['.mp3', '.wav', '.m4a', '.flac']
}
