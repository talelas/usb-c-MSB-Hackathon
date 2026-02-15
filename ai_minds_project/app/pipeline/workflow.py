"""End-to-end ingestion workflow.

Scan directory → ingest each file → chunk → embed → enrich → persist
(Postgres + Qdrant) → build graphs.

The workflow is designed to be **idempotent**: re-running it on the
same directory skips files already stored in Postgres (by file_path).

Supports:
- Local directory paths
- Google Drive shareable links
- OneDrive shareable links
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import networkx as nx

from app.config import RAW_DATA_DIR, EMBEDDING_DIMENSION
from app.core.chunker import chunk_text
from app.core.embedder import get_embedder
from app.core.enricher import extract_keywords, summarize
from app.core.ingestor import ingest
from app.db import postgres as pg
from app.db import qdrant_client as qdb
from app.db import redis_client as rdb
from app.graph.builder import build_all as build_graphs

log = logging.getLogger(__name__)


# ── Drive Link Detection & Download ──────────────────────────

def _is_drive_link(input_str: str) -> bool:
    """Check if input is a Google Drive or OneDrive shareable link."""
    if not isinstance(input_str, str):
        return False
    return (
        'drive.google.com' in input_str or
        '1drv.ms' in input_str or
        'onedrive.live.com' in input_str or
        'sharepoint.com' in input_str
    )


def _download_from_drive_link(link: str) -> Path | None:
    """Download files from Google Drive or OneDrive link to temp directory.
    
    Returns the directory where files were downloaded.
    """
    try:
        # Add file_handling to path if not already there
        project_root = Path(__file__).parent.parent.parent.parent
        file_handling_path = project_root / "file_handling"
        if str(file_handling_path) not in sys.path:
            sys.path.insert(0, str(file_handling_path))
        
        from shareable_link_parser import ShareableLinkParser
        
        log.info("Parsing drive link: %s", link)
        
        # Try Google Drive
        if 'drive.google.com' in link:
            parsed = ShareableLinkParser.parse_google_drive_url(link)
            if not parsed:
                log.error("Failed to parse Google Drive URL")
                return None
            
            log.info("Detected Google Drive %s: %s", parsed['type'], parsed['id'])
            
            from public_gdrive_access import PublicGoogleDriveAccess
            gdrive = PublicGoogleDriveAccess()
            
            if not gdrive.service:
                raise ValueError("Google Drive service not initialized. Set GOOGLE_API_KEY environment variable.")
            
            if parsed['type'] == 'folder':
                # List and download all files in folder
                log.info("Downloading files from Google Drive folder...")
                files = gdrive.list_folder_contents(parsed['id'])
                
                if files is None:
                    raise ValueError("Failed to access Google Drive folder. Check if it's publicly shared.")
                
                if not files:
                    log.warning("No files found in Google Drive folder")
                    return None
                
                download_dir = gdrive.temp_dir
                downloaded_count = 0
                
                for file_meta in files:
                    # Skip Google Drive folders (we only download files)
                    if file_meta.get('mimeType', '').endswith('.folder'):
                        continue
                    
                    file_id = file_meta['id']
                    file_name = file_meta['name']
                    mime_type = file_meta.get('mimeType', '')
                    
                    result = gdrive.download_file(file_id, file_name, mime_type)
                    if result:
                        downloaded_count += 1
                        log.info("Downloaded: %s", file_name)
                
                log.info("Downloaded %d files from Google Drive to %s", downloaded_count, download_dir)
                return download_dir
            else:
                # Single file
                log.info("Downloading single file from Google Drive...")
                file_meta = gdrive.service.files().get(
                    fileId=parsed['id'],
                    fields='id,name,mimeType'
                ).execute()
                
                result = gdrive.download_file(
                    parsed['id'],
                    file_meta['name'],
                    file_meta['mimeType']
                )
                if result:
                    return result.parent
                return None
        
        # Try OneDrive
        elif any(x in link for x in ['1drv.ms', 'onedrive.live.com', 'sharepoint.com']):
            parsed = ShareableLinkParser.parse_onedrive_url(link)
            if not parsed:
                log.error("Failed to parse OneDrive URL")
                return None
            
            log.info("Detected OneDrive %s", parsed['type'])
            
            from public_onedrive_access import PublicOneDriveAccess
            onedrive = PublicOneDriveAccess()
            
            if parsed['type'] == 'folder':
                # List and download all files in folder
                log.info("Downloading files from OneDrive folder...")
                files = onedrive.list_folder_contents(link)
                
                if not files:
                    log.warning("No files found in OneDrive folder")
                    return None
                
                download_dir = onedrive.temp_dir
                downloaded_count = 0
                
                for file_meta in files:
                    # Skip folders
                    if 'folder' in file_meta:
                        continue
                    
                    download_url = file_meta.get('@microsoft.graph.downloadUrl')
                    if not download_url:
                        continue
                    
                    file_name = file_meta['name']
                    result = onedrive.download_file(download_url, file_name)
                    if result:
                        downloaded_count += 1
                        log.info("Downloaded: %s", file_name)
                
                log.info("Downloaded %d files from OneDrive to %s", downloaded_count, download_dir)
                return download_dir
            else:
                # Single file
                log.info("Downloading single file from OneDrive...")
                item = onedrive.get_shared_item(link)
                if item and '@microsoft.graph.downloadUrl' in item:
                    result = onedrive.download_file(
                        item['@microsoft.graph.downloadUrl'],
                        item['name']
                    )
                    if result:
                        return result.parent
                return None
        
        return None
    
    except ImportError as e:
        log.error("Drive link functionality requires file_handling module: %s", e)
        log.error("Make sure the file_handling module is available and dependencies are installed.")
        return None
    except Exception as e:
        log.exception("Failed to download from drive link: %s", e)
        return None


# ── Single-file pipeline ─────────────────────────────────────

def ingest_file(path: Path, session=None) -> dict:
    """Process one file through the full pipeline.

    Returns dict with keys: status, doc_id, chunks, error
    """
    path = Path(path)
    own_session = session is None
    if own_session:
        session = pg.get_session()

    try:
        # Skip if already persisted
        existing = session.query(pg.Document).filter_by(file_path=str(path.resolve())).first()
        if existing:
            log.info("⏭️  SKIPPED (already stored): %s [doc_id=%d]", path.name, existing.id)
            return {"status": "skipped", "doc_id": existing.id, "reason": "already_exists"}

        # 1 – Ingest raw content
        log.info("🔄 PROCESSING: %s", path.name)
        text, meta = ingest(path)
        if not text.strip():
            log.warning("⚠️  SKIPPED (empty content): %s", path.name)
            return {"status": "skipped", "reason": "empty_content", "file_name": path.name}
        rdb.log_event("ingest", {"file": path.name, "modality": meta["modality"]})

        # 2 – Chunk
        chunks = chunk_text(text)
        rdb.log_event("chunk", {"file": path.name, "n_chunks": len(chunks)})

        # 3 – Embed
        embedder = get_embedder()
        vectors = embedder.embed_batch(chunks)
        rdb.log_event("embed", {"file": path.name, "dim": EMBEDDING_DIMENSION})

        # 4 – Enrich (summary + keywords)
        summary = summarize(text)
        keywords = extract_keywords(text)
        rdb.log_event("enrich", {"file": path.name, "keywords": keywords})

        # 5 – Persist to Postgres (metadata + chunk text only, no embeddings)
        doc = pg.upsert_document(
            session,
            file_path=str(path.resolve()),
            file_name=path.name,
            modality=meta["modality"],
            summary=summary,
            keywords=keywords,
            num_chunks=len(chunks),
            embedding_dim=EMBEDDING_DIMENSION,
            image_caption=meta.get("caption", ""),
            audio_transcript=meta.get("transcript", ""),
            file_size_bytes=meta.get("file_size_bytes", 0),
            file_extension=meta.get("file_extension", ""),
            file_timestamp=_parse_ts(meta.get("timestamp")),
            extra=meta,
        )
        pg.upsert_chunks(session, doc.id, [
            {"chunk_index": i, "text": c}
            for i, c in enumerate(chunks)
        ])
        session.commit()
        rdb.log_event("postgres_upsert", {"file": path.name, "doc_id": doc.id})

        # 6 – Persist to Qdrant (embeddings + metadata)
        points = []
        existing_count = _qdrant_max_id()
        for i, c in enumerate(chunks):
            pid = existing_count + (doc.id * 1000) + i  # unique point id
            points.append(qdb.build_point(
                point_id=pid,
                vector=vectors[i].tolist(),
                doc_id=doc.id,
                file_name=path.name,
                file_path=str(path.resolve()),
                modality=meta["modality"],
                chunk_index=i,
                chunk_text=c,
                keywords=keywords,
                summary=summary,
            ))
        qdb.upsert_points(points)
        rdb.log_event("qdrant_upsert", {"file": path.name, "n_points": len(points)})

        log.info("✅ SUCCESS: %s → doc_id=%d, %d chunks, %s", path.name, doc.id, len(chunks), meta["modality"])
        return {
            "status": "success",
            "doc_id": doc.id,
            "chunks": len(chunks),
            "file_name": path.name,
            "modality": meta["modality"]
        }

    except Exception as e:
        log.exception("❌ FAILED to ingest %s", path.name)
        session.rollback()
        return {"status": "error", "error": str(e), "file_name": path.name}
    finally:
        if own_session:
            session.close()


# ── Directory pipeline ────────────────────────────────────────

def ingest_directory(
    directory: Path | str | None = None,
    rebuild_graphs: bool = True,
) -> dict:
    """Ingest all supported files from *directory* or drive link (default: data/raw).

    Supports:
    - Local directory paths: /path/to/documents
    - Google Drive links: https://drive.google.com/drive/folders/...
    - OneDrive links: https://1drv.ms/f/s!...

    Returns a summary dict: ``{ingested, skipped, failed, graph_built}``.
    """
    # Check if input is a drive link
    if directory and isinstance(directory, str) and _is_drive_link(directory):
        log.info("Detected drive link: %s", directory)
        rdb.log_event("drive_link_detected", {"link": directory})
        
        try:
            download_dir = _download_from_drive_link(directory)
            if not download_dir:
                error_msg = "Failed to download files from drive link"
                log.error(error_msg)
                return {"error": error_msg, "drive_link": directory}
            
            log.info("Files downloaded to: %s", download_dir)
            directory = download_dir
        except Exception as e:
            error_msg = f"Drive link processing failed: {str(e)}"
            log.exception(error_msg)
            return {"error": error_msg, "drive_link": str(directory)}
    
    # Convert to Path object
    directory = Path(directory) if directory else RAW_DATA_DIR
    if not directory.exists():
        log.error("Directory does not exist: %s", directory)
        return {"error": f"Directory not found: {directory}"}

    from app.config import SUPPORTED_EXTENSIONS
    all_exts = {ext for exts in SUPPORTED_EXTENSIONS.values() for ext in exts}

    files = sorted(
        f for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in all_exts
    )
    log.info("Found %d files in %s", len(files), directory)
    rdb.log_event("pipeline_start", {"directory": str(directory), "n_files": len(files)})

    session = pg.get_session()
    ingested, skipped, failed = 0, 0, 0
    results = []

    for path in files:
        result = ingest_file(path, session=session)
        status = result.get("status")
        results.append(result)
        if status == "success":
            ingested += 1
        elif status == "skipped":
            skipped += 1
        else:
            failed += 1

    session.close()
    
    # Log summary of what was processed
    log.info("═" * 60)
    log.info("INGESTION SUMMARY: %d success, %d skipped, %d failed", ingested, skipped, failed)
    if ingested > 0:
        log.info("✅ Successfully ingested files:")
        for r in results:
            if r.get("status") == "success":
                log.info("   - %s (doc_id=%d, %d chunks)", r["file_name"], r["doc_id"], r["chunks"])
    if failed > 0:
        log.info("❌ Failed files:")
        for r in results:
            if r.get("status") == "error":
                log.info("   - %s: %s", r.get("file_name", "unknown"), r.get("error", "unknown error"))
    log.info("═" * 60)

    # Build / rebuild graphs
    graph_built = False
    if rebuild_graphs and ingested > 0:
        try:
            build_graphs()
            graph_built = True
            rdb.log_event("graphs_built", {"ingested": ingested})
        except Exception:
            log.exception("Graph build failed")

    summary = {
        "directory": str(directory),
        "total_files": len(files),
        "ingested": ingested,
        "skipped": skipped,
        "failed": failed,
        "graph_built": graph_built,
    }
    rdb.log_event("pipeline_complete", summary)
    log.info("Pipeline complete: %s", summary)
    return summary


# ── Helpers ──────────────────────────────────────────────────

def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _qdrant_max_id() -> int:
    """Get the current max point id in Qdrant (for uniqueness)."""
    try:
        info = qdb.get_client().get_collection(qdb.QDRANT_COLLECTION)
        return info.points_count or 0
    except Exception:
        return 0
