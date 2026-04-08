"""
FastAPI Server for File Monitoring
Provides REST API endpoints for file tracking using the integrated modules.
"""
import os
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import httpx

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from file_handling.core.storage_schemas import FileEvent, EventType, Source
from file_handling.core.event_queue import EventQueue
from file_handling.watchers.filesystem_watcher import FilesystemMonitor
from file_handling.watchers.public_cloud_monitor import PublicCloudMonitor
from file_handling.core.config import paths, ingestion, GOOGLE_API_KEY

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Backend API configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_TIMEOUT = 30.0


# ============================================================================
# Request/Response Models
# ============================================================================

class LocalFolderRequest(BaseModel):
    """Request to add a local folder to monitor."""
    path: str = Field(..., description="Absolute path to the folder")
    recursive: bool = Field(default=True, description="Watch subdirectories")


class CloudFolderRequest(BaseModel):
    """Request to add a cloud folder to monitor."""
    url: str = Field(..., description="Shareable URL (Google Drive or OneDrive)")
    recursive: bool = Field(default=True, description="Watch subfolders")


class MonitorStats(BaseModel):
    """Monitor statistics response."""
    local_folders: int
    cloud_folders: int
    files_tracked: int
    events_generated: int
    queue_size: int
    workers_running: int


class FileEventResponse(BaseModel):
    """File event response."""
    event_type: str
    source: str
    file_path: str
    timestamp: str
    metadata: Dict[str, Any]


# ============================================================================
# Global State
# ============================================================================

event_queue: Optional[EventQueue] = None
filesystem_monitor: Optional[FilesystemMonitor] = None
cloud_monitor: Optional[PublicCloudMonitor] = None
event_history: List[FileEvent] = []
MAX_HISTORY = 1000


def call_backend_api(method: str, endpoint: str, **kwargs) -> Optional[Dict]:
    """Make a synchronous call to the backend API."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        with httpx.Client(timeout=BACKEND_TIMEOUT) as client:
            if method == "POST":
                response = client.post(url, **kwargs)
            elif method == "DELETE":
                response = client.delete(url, **kwargs)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend API HTTP error ({method} {url}): {e.response.status_code} - {e.response.text}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"Backend API connection error ({method} {url}): {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling backend: {e}")
        return None


def event_processor(event: FileEvent) -> bool:
    """Process file events - communicate with backend API."""
    event_type = event.event_type
    if isinstance(event_type, EventType):
        event_type = event_type.value
    
    file_path = event.file_path
    file_name = event.metadata.get('file_name', Path(file_path).name)
    
    # Handle file events by calling backend API
    if event_type in ["created", "modified"]:
        logger.info(f"📥 File {event_type}: {file_name} -> Sending to backend for ingestion")
        
        result = call_backend_api(
            "POST",
            "/api/files/ingest",
            params={"file_path": file_path}
        )
        
        if result:
            logger.info(f"✅ Backend ingested {file_name}: doc_id={result.get('doc_id')}")
        else:
            logger.error(f"❌ Failed to ingest {file_name}")
            
    elif event_type == "deleted":
        logger.info(f"🗑️ File deleted: {file_name} -> Sending to backend for cleanup")
        
        result = call_backend_api(
            "DELETE",
            "/api/files",
            params={"file_path": file_path}
        )
        
        if result:
            logger.info(f"✅ Backend cleaned up {file_name}: {result.get('vectors_deleted', 0)} vectors removed")
        else:
            logger.error(f"❌ Failed to cleanup {file_name}")
    
    # Store in history
    event_history.append(event)
    if len(event_history) > MAX_HISTORY:
        event_history.pop(0)
    
    return True


def event_callback(event: FileEvent):
    """Callback for direct event notification."""
    event_type = event.event_type
    if isinstance(event_type, EventType):
        event_type = event_type.value
    
    file_name = event.metadata.get('file_name', Path(event.file_path).name)
    
    # Immediate console output for user visibility
    if event_type in ["created", "modified"]:
        print(f"📁 FILE EVENT: {event_type.upper()} -> {file_name}")
    elif event_type == "deleted":
        print(f"🗑️ FILE EVENT: DELETED -> {file_name}")
    
    # Store in history
    event_history.append(event)
    if len(event_history) > MAX_HISTORY:
        event_history.pop(0)


# ============================================================================
# FastAPI Application
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop monitors."""
    global event_queue, filesystem_monitor, cloud_monitor
    
    logger.info("Starting file handling server...")
    
    # Create event queue
    event_queue = EventQueue(maxsize=ingestion.max_queue_size)
    event_queue.start_workers(event_processor, num_workers=ingestion.processing_workers)
    
    # Create filesystem monitor (starts empty, folders added via API)
    filesystem_monitor = FilesystemMonitor(
        event_queue=event_queue,
        on_event_callback=event_callback
    )
    
    # Create cloud monitor
    cloud_monitor = PublicCloudMonitor(
        event_queue=event_queue,
        poll_interval=ingestion.cloud_poll_interval,
        google_api_key=GOOGLE_API_KEY,
        on_event_callback=event_callback
    )
    cloud_monitor.start()
    
    logger.info("File handling server started")
    
    yield  # Server runs here
    
    # Cleanup
    logger.info("Stopping file handling server...")
    
    if filesystem_monitor:
        filesystem_monitor.stop()
    
    if cloud_monitor:
        cloud_monitor.stop()
    
    if event_queue:
        event_queue.stop_workers()
    
    logger.info("File handling server stopped")


# Create FastAPI app
app = FastAPI(
    title="File Handling Server",
    description="REST API for monitoring local and cloud files",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "file-handling",
        "version": "1.0.0"
    }


@app.get("/stats", response_model=MonitorStats)
async def get_stats():
    """Get monitor statistics."""
    local_folders = len(filesystem_monitor.get_watch_paths()) if filesystem_monitor else 0
    cloud_folders = cloud_monitor.stats['folders_monitored'] if cloud_monitor else 0
    files_tracked = cloud_monitor.stats['files_tracked'] if cloud_monitor else 0
    events = cloud_monitor.stats['events_generated'] if cloud_monitor else 0
    
    queue_stats = event_queue.get_stats() if event_queue else {}
    
    return MonitorStats(
        local_folders=local_folders,
        cloud_folders=cloud_folders,
        files_tracked=files_tracked,
        events_generated=events + len(event_history),
        queue_size=queue_stats.get('queue_size', 0),
        workers_running=queue_stats.get('workers_running', 0)
    )


@app.get("/events", response_model=List[FileEventResponse])
async def get_events(limit: int = 50):
    """Get recent file events."""
    events = event_history[-limit:] if limit > 0 else event_history
    
    return [
        FileEventResponse(
            event_type=str(e.event_type.value if isinstance(e.event_type, EventType) else e.event_type),
            source=str(e.source.value if isinstance(e.source, Source) else e.source),
            file_path=e.file_path,
            timestamp=str(e.timestamp),
            metadata=e.metadata
        )
        for e in reversed(events)
    ]


@app.get("/files")
async def get_files():
    """Get list of tracked files."""
    files = []
    
    # Get cloud files
    if cloud_monitor:
        for path, meta in cloud_monitor.file_states.items():
            files.append({
                "path": path,
                "name": meta.get('name', 'unknown'),
                "size": meta.get('size', 0),
                "modified": meta.get('modified', ''),
                "source": meta.get('source', 'unknown').value if hasattr(meta.get('source'), 'value') else str(meta.get('source', 'unknown'))
            })
    
    return {"count": len(files), "files": files}


@app.post("/folders/local")
async def add_local_folder(request: LocalFolderRequest):
    """Add a local folder to monitor."""
    if not filesystem_monitor:
        raise HTTPException(status_code=503, detail="Filesystem monitor not initialized")
    
    # Normalize path (handle both forward and back slashes)
    path = request.path.replace("\\", "/")
    
    # Check if path exists
    folder_path = Path(path)
    if not folder_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")
    
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
    
    # Add to monitor
    success = filesystem_monitor.add_watch_path(str(folder_path.resolve()))
    
    if success:
        # Start monitoring if not already started
        if not filesystem_monitor.is_active():
            filesystem_monitor.start()
        
        return {
            "status": "success",
            "message": f"Now monitoring: {folder_path.resolve()}",
            "path": str(folder_path.resolve()),
            "recursive": request.recursive
        }
    else:
        raise HTTPException(status_code=400, detail=f"Failed to add folder: {path}")


@app.post("/folders/cloud")
async def add_cloud_folder(request: CloudFolderRequest):
    """Add a cloud folder to monitor (Google Drive or OneDrive)."""
    if not cloud_monitor:
        raise HTTPException(status_code=503, detail="Cloud monitor not initialized")
    
    success = cloud_monitor.add_folder(
        share_url=request.url,
        recursive=request.recursive
    )
    
    if success:
        return {
            "status": "success",
            "message": f"Now monitoring cloud folder",
            "url": request.url,
            "recursive": request.recursive
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail="Failed to add cloud folder. Check the URL and ensure Google API key is set for Drive folders."
        )


@app.get("/folders")
async def get_folders():
    """Get list of monitored folders."""
    local_folders = filesystem_monitor.get_watch_paths() if filesystem_monitor else []
    cloud_folders = cloud_monitor.get_tracked_folders() if cloud_monitor else []
    
    return {
        "local": local_folders,
        "cloud": cloud_folders
    }


@app.get("/tmp")
async def list_tmp_files():
    """List files in tmp directory."""
    tmp_dir = paths.tmp_dir
    files = []
    
    if tmp_dir.exists():
        for item in tmp_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(tmp_dir)
                files.append({
                    "name": item.name,
                    "path": str(rel_path),
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime
                })
    
    return {
        "tmp_dir": str(tmp_dir),
        "count": len(files),
        "files": files
    }


@app.delete("/tmp")
async def clear_tmp():
    """Clear tmp directory."""
    tmp_dir = paths.tmp_dir
    
    if tmp_dir.exists():
        for item in tmp_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        
        # Recreate subdirectories
        (tmp_dir / "local").mkdir(exist_ok=True)
        (tmp_dir / "google_drive").mkdir(exist_ok=True)
        (tmp_dir / "onedrive").mkdir(exist_ok=True)
    
    return {"status": "success", "message": "Tmp directory cleared"}


# ============================================================================
# Main Entry Point
# ============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the server."""
    import uvicorn
    
    print("=" * 60)
    print("  File Handling Server")
    print("=" * 60)
    print()
    print(f"Starting server on http://{host}:{port}")
    print()
    print("API Endpoints:")
    print("  GET  /              - Health check")
    print("  GET  /stats         - Monitor statistics")
    print("  GET  /files         - List tracked files")
    print("  GET  /events        - Recent file events")
    print("  POST /folders/local - Add local folder")
    print("  POST /folders/cloud - Add cloud folder")
    print("  GET  /folders       - List monitored folders")
    print("  GET  /tmp           - List tmp files")
    print("  DELETE /tmp         - Clear tmp directory")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 60)
    print()
    
    uvicorn.run(
        "file_handling.server:app",
        host=host,
        port=port,
        reload=reload
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="File Handling Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")
    
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, reload=args.reload)
