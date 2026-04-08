"""Process a single file and update outputs."""
from __future__ import annotations

import sys
from pathlib import Path
import os

# Load .env early so environment overrides are available to imported modules
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"✓ Loaded .env from: {env_path}")
    else:
        # Fallback to system environment or other dotenv locations
        load_dotenv()
except Exception:
    # If python-dotenv isn't installed, continue; env vars may still be set in the shell
    print("⚠ python-dotenv not available; ensure HF_TOKEN is exported in your shell if needed")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import MemoryProcessor


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run_single.py <file_path>")
        return

    file_path = sys.argv[1]
    processor = MemoryProcessor()
    processor.process_single_file(file_path)


if __name__ == "__main__":
    main()
