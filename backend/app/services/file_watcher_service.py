"""Standalone file watcher service for automatic ingestion.

Start with:
    python -m app.services.file_watcher_service --watch data/raw
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.integration.file_watcher import FileEventHandler, create_watchdog_callback

# Try to import file_handling
try:
    from file_handling.filesystem_watcher import FilesystemWatcher
    from file_handling.event_queue import EventQueue
    from file_handling.storage_schemas import FileEvent, EventType
    HAS_FILE_HANDLING = True
except ImportError:
    HAS_FILE_HANDLING = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)


def main():
    """Run the file watcher service."""
    parser = argparse.ArgumentParser(description="File watcher service for automatic ingestion")
    parser.add_argument(
        "--watch",
        type=str,
        nargs="+",
        default=["data/raw"],
        help="Directories to watch (default: data/raw)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Watch subdirectories recursively",
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        help="Debounce delay in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--no-auto-rebuild",
        action="store_true",
        help="Disable automatic graph rebuilding after each file",
    )
    
    args = parser.parse_args()
    
    if not HAS_FILE_HANDLING:
        log.error("file_handling module not found. Please install watchdog: pip install watchdog")
        sys.exit(1)
    
    # Create handler
    handler = FileEventHandler(auto_rebuild_graphs=not args.no_auto_rebuild)
    
    # Create event queue and watcher
    event_queue = EventQueue()
    
    def on_file_event(file_event: FileEvent):
        """Callback for file events from watchdog."""
        event_data = {
            "type": file_event.event_type.value if hasattr(file_event.event_type, 'value') else str(file_event.event_type),
            "path": file_event.file_path,
            "timestamp": file_event.timestamp,
            "source": file_event.source.value if hasattr(file_event.source, 'value') else str(file_event.source),
        }
        log.info(f"📁 File event: {event_data['type']} - {Path(event_data['path']).name}")
        
        # Process file event
        event_type = event_data["type"].lower()
        file_path = event_data["path"]
        
        if event_type in ("created", "added"):
            handler.on_created(file_path)
        elif event_type == "modified":
            handler.on_modified(file_path)
        elif event_type == "deleted":
            handler.on_deleted(file_path)
    
    watcher = FilesystemWatcher(
        event_queue=event_queue,
        watch_paths=args.watch,
        recursive=args.recursive,
        debounce_seconds=args.debounce,
        on_event_callback=on_file_event,
    )
    
    log.info(f"Starting file watcher for: {args.watch}")
    log.info(f"Recursive: {args.recursive}, Debounce: {args.debounce}s")
    log.info(f"Auto-rebuild graphs: {not args.no_auto_rebuild}")
    log.info("Press Ctrl+C to stop")
    
    try:
        watcher.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
            # Print stats every 30 seconds
            if int(time.time()) % 30 == 0:
                stats = handler.get_stats()
                log.info(f"Stats: {stats['ingested']} ingested, {stats['deleted']} deleted")
                
    except KeyboardInterrupt:
        log.info("\nStopping file watcher...")
        watcher.stop()
        stats = handler.get_stats()
        log.info(f"Final stats: {stats}")
    
    except Exception as e:
        log.exception("Error in file watcher service")
        watcher.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
