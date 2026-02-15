"""Process a single file and update outputs."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import MemoryProcessor


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run_single.py <file_path>")
        return

    file_path = sys.argv[1]
    processor = MemoryProcessor()
    processor.process_single_file(file_path)


if __name__ == "__main__":
    main()
