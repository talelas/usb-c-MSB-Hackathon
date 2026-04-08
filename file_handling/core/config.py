"""
File Handling Configuration
Self-contained settings for the file_handling module.
"""
import os
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Base paths - file_handling module root
MODULE_ROOT = Path(__file__).parent
PROJECT_ROOT = MODULE_ROOT.parent
TMP_DIR = MODULE_ROOT / "tmp"

# Load environment variables from file_handling/.env
env_path = MODULE_ROOT / ".env"
load_dotenv(dotenv_path=env_path)
print(f"Loaded .env from: {env_path}")

# Create directories if they don't exist
TMP_DIR.mkdir(parents=True, exist_ok=True)
(TMP_DIR / "local").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "google_drive").mkdir(parents=True, exist_ok=True)
(TMP_DIR / "onedrive").mkdir(parents=True, exist_ok=True)


@dataclass
class PathConfig:
    """File system paths configuration"""
    project_root: Path = PROJECT_ROOT
    tmp_dir: Path = TMP_DIR
    local_tmp: Path = TMP_DIR / "local"
    gdrive_tmp: Path = TMP_DIR / "google_drive"
    onedrive_tmp: Path = TMP_DIR / "onedrive"


@dataclass
class IngestionConfig:
    """Ingestion layer configuration"""
    # Filesystem watcher
    watch_enabled: bool = True
    watch_recursive: bool = True
    watch_debounce_seconds: float = 1.0
    
    # File filters
    ignore_hidden: bool = True
    ignore_temp: bool = True
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "*.tmp", "~$*", ".DS_Store", "*.swp", "__pycache__", "node_modules",
        ".git", ".venv", "*.pyc", "Thumbs.db"
    ])
    
    # Supported file extensions
    supported_extensions: Dict[str, List[str]] = field(default_factory=lambda: {
        "text": [".txt", ".md", ".rst", ".log"],
        "code": [".py", ".js", ".java", ".cpp", ".c", ".h", ".css", ".html", ".json", ".yaml", ".yml", ".xml"],
        "pdf": [".pdf"],
        "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
        "document": [".docx", ".doc", ".odt", ".rtf"],
        "spreadsheet": [".xlsx", ".xls", ".csv", ".tsv"],
        "presentation": [".pptx", ".ppt", ".odp"],
        "audio": [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"],
        "video": [".mp4", ".avi", ".mkv", ".mov", ".wmv"]
    })
    
    # Queue settings
    max_queue_size: int = 1000
    processing_workers: int = 4
    
    # Cloud poll interval
    cloud_poll_interval: int = 30  # seconds


# Global instances
paths = PathConfig()
ingestion = IngestionConfig()

# API Keys from environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
