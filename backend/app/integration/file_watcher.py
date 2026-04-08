"""File watching integration with ingestion pipeline.

Connects file_handling watchdog service to the RAG ingestion pipeline:
- Added/Modified files → automatic ingestion
- Deleted files → cleanup from DB and vector store
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from app.db import postgres as pg
from app.db import qdrant_client as qdb
from app.graph.builder import build_all
from app.pipeline.workflow import ingest_file

log = logging.getLogger(__name__)


class FileEventHandler:
    """Processes file system events and triggers pipeline actions."""
    
    def __init__(self, auto_rebuild_graphs: bool = True):
        """
        Initialize file event handler.
        
        Args:
            auto_rebuild_graphs: Whether to rebuild graphs after ingestion
        """
        self.auto_rebuild_graphs = auto_rebuild_graphs
        self._ingested_count = 0
        self._deleted_count = 0
        
        log.info("FileEventHandler initialized")
    
    def on_created(self, file_path: str | Path) -> bool:
        """
        Handle file creation event.
        
        Args:
            file_path: Path to the created file
            
        Returns:
            True if successfully ingested, False otherwise
        """
        return self._handle_file_change(file_path, "created")
    
    def on_modified(self, file_path: str | Path) -> bool:
        """
        Handle file modification event.
        
        Args:
            file_path: Path to the modified file
            
        Returns:
            True if successfully re-ingested, False otherwise
        """
        return self._handle_file_change(file_path, "modified")
    
    def on_deleted(self, file_path: str | Path) -> bool:
        """
        Handle file deletion event.
        
        Args:
            file_path: Path to the deleted file
            
        Returns:
            True if successfully deleted from DB, False otherwise
        """
        path = Path(file_path).resolve()
        
        try:
            session = pg.get_session()
            try:
                # Find document by file path
                doc = session.query(pg.Document).filter_by(file_path=str(path)).first()
                
                if not doc:
                    log.debug(f"File not in database: {path.name}")
                    return False
                
                doc_id = doc.id
                
                # Delete from Postgres (cascades to chunks)
                session.delete(doc)
                session.commit()
                
                # Delete from Qdrant
                try:
                    client = qdb.get_client()
                    # Delete all points with this doc_id
                    points = qdb.scroll_all()
                    ids_to_delete = [
                        p.id for p in points 
                        if p.payload and p.payload.get("doc_id") == doc_id
                    ]
                    if ids_to_delete:
                        client.delete(
                            collection_name=qdb.QDRANT_COLLECTION,
                            points_selector=ids_to_delete
                        )
                        log.info(f"Deleted {len(ids_to_delete)} embeddings for doc_id={doc_id}")
                except Exception as e:
                    log.error(f"Failed to delete from Qdrant: {e}")
                
                # Rebuild graphs if enabled
                if self.auto_rebuild_graphs:
                    try:
                        build_all()
                        log.info("Graphs rebuilt after file deletion")
                    except Exception as e:
                        log.error(f"Failed to rebuild graphs: {e}")
                
                self._deleted_count += 1
                log.info(f"✓ Deleted from DB: {path.name}")
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            log.error(f"Error deleting file {path}: {e}")
            return False
    
    def _handle_file_change(self, file_path: str | Path, event_type: str) -> bool:
        """
        Handle file creation or modification.
        
        Args:
            file_path: Path to the file
            event_type: "created" or "modified"
            
        Returns:
            True if successfully processed
        """
        path = Path(file_path).resolve()
        
        if not path.exists():
            log.warning(f"File no longer exists: {path}")
            return False
        
        if not path.is_file():
            log.debug(f"Not a file: {path}")
            return False
        
        try:
            # If modified, delete the old document first
            if event_type == "modified":
                session = pg.get_session()
                try:
                    doc = session.query(pg.Document).filter_by(file_path=str(path)).first()
                    if doc:
                        doc_id = doc.id
                        
                        # Delete from Postgres (cascades to chunks)
                        session.delete(doc)
                        session.commit()
                        
                        # Delete from Qdrant
                        try:
                            client = qdb.get_client()
                            points = qdb.scroll_all()
                            ids_to_delete = [
                                p.id for p in points 
                                if p.payload and p.payload.get("doc_id") == doc_id
                            ]
                            if ids_to_delete:
                                client.delete(
                                    collection_name=qdb.QDRANT_COLLECTION,
                                    points_selector=ids_to_delete
                                )
                        except Exception as e:
                            log.error(f"Failed to delete from Qdrant during modification: {e}")
                        
                        log.debug(f"Removed old version of: {path.name}")
                finally:
                    session.close()
            
            # Ingest the file
            log.info(f"🔄 Ingesting {event_type} file: {path.name}")
            result = ingest_file(path)
            
            if result.get("status") == "success":
                # Rebuild graphs if enabled
                if self.auto_rebuild_graphs:
                    try:
                        build_all()
                        log.info("Graphs rebuilt after ingestion")
                    except Exception as e:
                        log.error(f"Failed to rebuild graphs: {e}")
                
                self._ingested_count += 1
                log.info(f"✓ Ingested: {path.name} ({result.get('chunks', 0)} chunks)")
                return True
            else:
                log.error(f"✗ Failed to ingest: {path.name} - {result.get('error')}")
                return False
                
        except Exception as e:
            log.error(f"Error processing {event_type} file {path}: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get handler statistics."""
        return {
            "ingested": self._ingested_count,
            "deleted": self._deleted_count,
        }


def create_watchdog_callback(handler: FileEventHandler) -> Callable:
    """
    Create a callback function compatible with file_handling's watchdog.
    
    Args:
        handler: FileEventHandler instance
        
    Returns:
        Callback function that can be passed to FilesystemWatcher
    """
    def callback(event_data: dict) -> None:
        """
        Process file event from watchdog.
        
        Args:
            event_data: Event dictionary with keys: type, path, timestamp, source
        """
        event_type = event_data.get("type", "").lower()
        file_path = event_data.get("path")
        
        if not file_path:
            return
        
        # Map event types to handler methods
        if event_type in ("created", "added"):
            handler.on_created(file_path)
        elif event_type == "modified":
            handler.on_modified(file_path)
        elif event_type == "deleted":
            handler.on_deleted(file_path)
    
    return callback
