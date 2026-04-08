"""
Filesystem Watcher
Monitors local directories for file changes using watchdog.
"""
import time
import logging
import shutil
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler, 
    FileSystemEvent,
    FileMovedEvent
)

from file_handling.core.storage_schemas import FileEvent, EventType, Source, FileType, get_file_type_from_extension
from file_handling.core.event_queue import EventQueue, EventDebouncer
from file_handling.core.config import ingestion, paths

logger = logging.getLogger(__name__)


class FilesystemWatcher(FileSystemEventHandler):
    """
    Watches local filesystem for changes and pushes events to queue.
    """
    
    def __init__(
        self, 
        event_queue: EventQueue,
        watch_paths: List[str],
        recursive: bool = True,
        debounce_seconds: float = 1.0,
        on_event_callback: Optional[Callable[[FileEvent], None]] = None
    ):
        """
        Initialize filesystem watcher.
        
        Args:
            event_queue: Queue to push events to
            watch_paths: List of directory paths to watch
            recursive: Watch subdirectories
            debounce_seconds: Debounce delay for rapid changes
            on_event_callback: Optional callback for each event (for hello/bye talel)
        """
        super().__init__()
        self.event_queue = event_queue
        self.watch_paths = [Path(p).resolve() for p in watch_paths]
        self.recursive = recursive
        self.debouncer = EventDebouncer(delay=debounce_seconds)
        self.on_event_callback = on_event_callback
        
        # Observer for watching filesystem
        self.observer = Observer()
        
        # Tracking
        self._active = False
        self._handlers = []
        
        # Load ignore patterns from config
        self.ignore_patterns = set(ingestion.ignore_patterns)
        self.ignore_hidden = ingestion.ignore_hidden
        self.ignore_temp = ingestion.ignore_temp
        
        # Temp dir for copying files
        self.temp_dir = paths.local_tmp
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"FilesystemWatcher initialized for {len(watch_paths)} paths "
            f"(recursive={recursive}, debounce={debounce_seconds}s)"
        )
    
    def start(self):
        """Start watching filesystem"""
        if self._active:
            logger.warning("Watcher already active")
            return
        
        # Schedule watches for each path
        for path in self.watch_paths:
            if not path.exists():
                logger.warning(f"Watch path does not exist: {path}")
                continue
            
            if not path.is_dir():
                logger.warning(f"Watch path is not a directory: {path}")
                continue
            
            try:
                handler = self.observer.schedule(
                    self, 
                    str(path), 
                    recursive=self.recursive
                )
                self._handlers.append(handler)
                logger.info(f"Started watching: {path}")
            
            except Exception as e:
                logger.error(f"Failed to watch {path}: {e}")
        
        # Start observer
        self.observer.start()
        self._active = True
        logger.info("Filesystem watcher started")
    
    def stop(self, wait: bool = True, timeout: float = 30.0):
        """
        Stop watching filesystem.
        
        Args:
            wait: Wait for observer to stop
            timeout: Maximum wait time
        """
        if not self._active:
            return
        
        logger.info("Stopping filesystem watcher...")
        self._active = False
        
        # Cancel pending debounced events
        self.debouncer.cancel_all()
        
        # Stop observer
        self.observer.stop()
        if wait:
            self.observer.join(timeout=timeout)
        
        self._handlers.clear()
        logger.info("Filesystem watcher stopped")
    
    def is_active(self) -> bool:
        """Check if watcher is active"""
        return self._active
    
    def should_ignore(self, file_path: str) -> bool:
        """
        Check if file should be ignored.
        
        Args:
            file_path: Path to file
        
        Returns:
            True if should be ignored
        """
        path = Path(file_path)
        
        # Check hidden files
        if self.ignore_hidden and any(part.startswith('.') for part in path.parts):
            return True
        
        # Check temp files
        if self.ignore_temp and (path.name.startswith('~$') or path.suffix == '.tmp'):
            return True
        
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if path.match(pattern):
                return True
        
        return False
    
    def get_file_type(self, file_path: str) -> FileType:
        """
        Determine file type from extension.
        
        Args:
            file_path: Path to file
        
        Returns:
            FileType enum
        """
        return get_file_type_from_extension(Path(file_path).suffix)
    
    def copy_to_tmp(self, file_path: str, source_root: Optional[Path] = None) -> Optional[Path]:
        """
        Copy file to tmp directory, preserving folder structure.
        
        Args:
            file_path: Source file path
            source_root: Root of the watched folder (to preserve relative structure)
            
        Returns:
            Path to copied file in tmp or None
        """
        try:
            src = Path(file_path)
            if not src.exists() or not src.is_file():
                return None
            
            # Preserve folder structure relative to watch root
            if source_root:
                try:
                    rel_path = src.relative_to(source_root)
                    dest = self.temp_dir / rel_path
                except ValueError:
                    # File not under source_root, use flat name
                    dest = self.temp_dir / src.name
            else:
                # No root specified, use flat name
                dest = self.temp_dir / src.name
            
            # Create parent directories if needed
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file (overwrite if exists to avoid duplicates)
            shutil.copy2(src, dest)
            logger.debug(f"Copied {src.name} to tmp")
            return dest
        except Exception as e:
            logger.error(f"Failed to copy to tmp: {e}")
            return None
    
    def create_file_event(
        self, 
        event_type: EventType, 
        file_path: str
    ) -> FileEvent:
        """
        Create FileEvent from filesystem event.
        
        Args:
            event_type: Type of event
            file_path: Path to file
        
        Returns:
            FileEvent
        """
        path = Path(file_path)
        
        # Get file metadata
        metadata = {
            'file_name': path.name,
            'file_extension': path.suffix.lower(),
            'file_type': self.get_file_type(file_path).value,
        }
        
        # Add size and timestamps if file exists
        if path.exists() and path.is_file():
            stat = path.stat()
            metadata.update({
                'file_size_bytes': stat.st_size,
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            })
            
            # Copy to tmp only for CREATED events to avoid duplicates
            if event_type == EventType.CREATED:
                # Find which watch path this file belongs to
                source_root = None
                for watch_path in self.watch_paths:
                    if path.is_relative_to(Path(watch_path)):
                        source_root = Path(watch_path)
                        break
                
                tmp_path = self.copy_to_tmp(file_path, source_root)
                if tmp_path:
                    metadata['local_path'] = str(tmp_path)
        
        return FileEvent(
            event_type=event_type,
            source=Source.LOCAL,
            file_path=str(path),
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
    
    def handle_event(self, event_type: EventType, file_path: str):
        """
        Handle filesystem event with debouncing.
        
        Args:
            event_type: Type of event
            file_path: Path to file
        """
        def process_event(e: FileEvent):
            # Queue the event
            self.event_queue.put(e)
            
            # Call callback for hello/bye talel
            if self.on_event_callback:
                self.on_event_callback(e)
        
        # Create event
        file_event = self.create_file_event(event_type, file_path)
        
        # Debounce and queue
        self.debouncer.debounce(file_event, callback=process_event)
    
    # Watchdog event handlers
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self.should_ignore(file_path):
            logger.debug(f"Ignoring created file: {file_path}")
            return
        
        logger.debug(f"File created: {file_path}")
        self.handle_event(EventType.CREATED, file_path)
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self.should_ignore(file_path):
            logger.debug(f"Ignoring modified file: {file_path}")
            return
        
        logger.debug(f"File modified: {file_path}")
        self.handle_event(EventType.MODIFIED, file_path)
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self.should_ignore(file_path):
            logger.debug(f"Ignoring deleted file: {file_path}")
            return
        
        logger.debug(f"File deleted: {file_path}")
        self.handle_event(EventType.DELETED, file_path)
    
    def on_moved(self, event: FileMovedEvent):
        """Handle file move/rename"""
        if event.is_directory:
            return
        
        src_path = event.src_path
        dest_path = event.dest_path
        
        if self.should_ignore(dest_path):
            logger.debug(f"Ignoring moved file: {dest_path}")
            return
        
        logger.debug(f"File moved: {src_path} -> {dest_path}")
        
        # Treat as delete + create
        if not self.should_ignore(src_path):
            self.handle_event(EventType.DELETED, src_path)
        self.handle_event(EventType.CREATED, dest_path)


class FilesystemMonitor:
    """
    High-level filesystem monitoring service.
    Manages watcher lifecycle and configuration.
    """
    
    def __init__(
        self, 
        event_queue: EventQueue,
        watch_paths: Optional[List[str]] = None,
        on_event_callback: Optional[Callable[[FileEvent], None]] = None
    ):
        """
        Initialize filesystem monitor.
        
        Args:
            event_queue: Queue for events
            watch_paths: Paths to watch (can be added later)
            on_event_callback: Callback for each event
        """
        self.event_queue = event_queue
        self.on_event_callback = on_event_callback
        self.watch_paths = []
        self.watcher = None
        self.temp_dir = paths.local_tmp  # Store tmp dir reference
        
        if watch_paths:
            for path in watch_paths:
                self.add_watch_path(path)
        
        logger.info(f"FilesystemMonitor initialized")
    
    def import_all_files(self, folder_path: Path):
        """
        Import all existing files from folder into tmp (recursively).
        Called when a folder is first added to monitoring.
        
        Args:
            folder_path: Root folder to import from
        """
        logger.info(f"Importing all files from: {folder_path}")
        imported_count = 0
        
        try:
            # Walk through all files recursively
            for item in folder_path.rglob('*'):
                if not item.is_file():
                    continue
                
                # Check if should ignore
                if self.watcher:
                    if self.watcher.should_ignore(str(item)):
                        continue
                
                try:
                    # Preserve folder structure
                    rel_path = item.relative_to(folder_path)
                    dest = self.temp_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(item, dest)
                    imported_count += 1
                    logger.debug(f"Imported: {rel_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to import {item}: {e}")
            
            logger.info(f"Imported {imported_count} files from {folder_path}")
            
        except Exception as e:
            logger.error(f"Error importing files from {folder_path}: {e}")
    
    def add_watch_path(self, path: str) -> bool:
        """
        Add a path to watch. Can be called while running - no restart needed.
        Imports all existing files immediately.
        
        Args:
            path: Directory path to watch
            
        Returns:
            True if path was added
        """
        p = Path(path).resolve()
        if p.exists() and p.is_dir():
            if str(p) not in self.watch_paths:
                self.watch_paths.append(str(p))
                logger.info(f"Added watch path: {p}")
                
                # Import all existing files into tmp
                self.import_all_files(p)
                
                # If already running, schedule the new path on the existing observer
                if self.watcher and self.watcher.is_active():
                    try:
                        handler = self.watcher.observer.schedule(
                            self.watcher,
                            str(p),
                            recursive=ingestion.watch_recursive
                        )
                        self.watcher._handlers.append(handler)
                        logger.info(f"Hot-added watch for: {p}")
                    except Exception as e:
                        logger.error(f"Failed to hot-add watch for {p}: {e}")
                return True
        else:
            logger.warning(f"Invalid watch path: {path}")
        return False
    
    def start(self):
        """Start monitoring"""
        if not self.watch_paths:
            logger.warning("No watch paths configured")
            return
        
        if self.watcher and self.watcher.is_active():
            logger.warning("Monitor already running")
            return
        
        logger.info("Starting filesystem monitoring...")
        self.watcher = FilesystemWatcher(
            event_queue=self.event_queue,
            watch_paths=self.watch_paths,
            recursive=ingestion.watch_recursive,
            debounce_seconds=ingestion.watch_debounce_seconds,
            on_event_callback=self.on_event_callback
        )
        self.watcher.start()
    
    def stop(self, wait: bool = True):
        """Stop monitoring"""
        if self.watcher:
            logger.info("Stopping filesystem monitoring...")
            self.watcher.stop(wait=wait)
            self.watcher = None
    
    def is_active(self) -> bool:
        """Check if monitoring is active"""
        return self.watcher is not None and self.watcher.is_active()
    
    def get_watch_paths(self) -> List[str]:
        """Get list of watched paths"""
        return self.watch_paths
