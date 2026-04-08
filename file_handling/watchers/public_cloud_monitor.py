"""
Public Cloud Folder Monitor
Continuously monitors publicly shared Google Drive and OneDrive folders.
Tracks add/modify/delete operations like local filesystem monitoring.
No authentication required - works with public shareable links.
"""
import re
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Dict, List, Callable
from datetime import datetime

from file_handling.core.storage_schemas import FileEvent, EventType, Source, FileType, get_file_type_from_mime
from file_handling.core.event_queue import EventQueue
from file_handling.cloud.shareable_link_parser import ShareableLinkParser
from file_handling.cloud.public_gdrive_access import PublicGoogleDriveAccess
from file_handling.cloud.public_onedrive_access import PublicOneDriveAccess
from file_handling.core.config import ingestion, GOOGLE_API_KEY

logger = logging.getLogger(__name__)


class PublicCloudMonitor:
    """
    Monitors publicly shared cloud folders for changes.
    Supports Google Drive and OneDrive without authentication.
    All folder scans run in parallel - no folder blocks another.
    """
    
    def __init__(
        self,
        event_queue: EventQueue,
        poll_interval: int = 30,
        google_api_key: Optional[str] = None,
        on_event_callback: Optional[Callable[[FileEvent], None]] = None
    ):
        """
        Initialize public cloud monitor.
        
        Args:
            event_queue: Event queue for file change notifications
            poll_interval: How often to check for changes (seconds)
            google_api_key: API key for Google Drive (optional)
            on_event_callback: Callback for each event (for hello/bye talel)
        """
        self.event_queue = event_queue
        self.poll_interval = poll_interval
        self.on_event_callback = on_event_callback
        
        # Initialize cloud access modules
        self.gdrive_access = PublicGoogleDriveAccess(api_key=google_api_key or GOOGLE_API_KEY)
        self.onedrive_access = PublicOneDriveAccess()
        
        # Tracked folders: {folder_url: {'source': Source, 'recursive': bool, 'metadata': dict}}
        self.tracked_folders: Dict[str, Dict] = {}
        self._folders_lock = threading.Lock()  # protects tracked_folders dict
        
        # File state tracking: {file_key: {'id': str, 'modified': str, 'size': int}}
        self.file_states: Dict[str, Dict] = {}
        self._states_lock = threading.Lock()  # protects file_states dict
        
        # Per-folder scan locks - prevents overlapping scans of the SAME folder
        # but different folders scan in parallel
        self._folder_scan_locks: Dict[str, threading.Lock] = {}
        self._folder_locks_lock = threading.Lock()  # protects the locks dict
        
        # Thread pool for parallel scanning
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cloud-scan")
        
        # Control
        self._running = False
        self._monitor_thread = None
        
        # Statistics
        self.stats = {
            'folders_monitored': 0,
            'files_tracked': 0,
            'events_generated': 0,
            'last_scan_time': None,
            'errors': 0
        }
        
        logger.info("Public cloud monitor initialized")
    
    def _get_folder_lock(self, share_url: str) -> threading.Lock:
        """Get or create a per-folder lock."""
        with self._folder_locks_lock:
            if share_url not in self._folder_scan_locks:
                self._folder_scan_locks[share_url] = threading.Lock()
            return self._folder_scan_locks[share_url]
    
    def add_folder(
        self,
        share_url: str,
        recursive: bool = True,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a public folder to monitor. Returns immediately.
        Initial scan runs in a background thread - does NOT block the caller.
        
        Args:
            share_url: Shareable URL from Google Drive or OneDrive
            recursive: Whether to monitor subfolders
            metadata: Additional metadata to attach
        
        Returns:
            True if folder was added successfully
        """
        # Check if already tracked - return success immediately
        with self._folders_lock:
            if share_url in self.tracked_folders:
                logger.info(f"Folder already tracked: {share_url}")
                return True
        
        # Parse the URL
        parser = ShareableLinkParser()
        parsed = parser.parse_any_url(share_url)
        
        if not parsed:
            logger.error(f"Could not parse URL: {share_url}")
            return False
        
        if parsed['type'] != 'folder':
            logger.error(f"URL is not a folder: {share_url}")
            return False
        
        # Determine source
        source = Source.GOOGLE_DRIVE if parsed['source'] == 'google_drive' else Source.ONEDRIVE
        
        # Check if service is available for this source
        if source == Source.GOOGLE_DRIVE and not self.gdrive_access.service:
            logger.error("Google Drive API key not configured. Cannot monitor Google Drive folders.")
            return False

        # Store folder info (thread-safe)
        with self._folders_lock:
            self.tracked_folders[share_url] = {
                'source': source,
                'folder_id': parsed['id'],
                'recursive': recursive,
                'metadata': metadata or {},
                'parsed': parsed
            }
            self.stats['folders_monitored'] = len(self.tracked_folders)
        
        logger.info(f"Added public folder to monitor: {share_url} ({source.value})")
        
        # Do initial scan in background thread - never blocks the HTTP request
        if self._running:
            self._executor.submit(self._scan_folder_safe, share_url)
        
        return True
    
    def remove_folder(self, share_url: str) -> bool:
        """
        Remove a folder from monitoring.
        
        Args:
            share_url: Shareable URL
        
        Returns:
            True if removed
        """
        with self._folders_lock:
            if share_url in self.tracked_folders:
                del self.tracked_folders[share_url]
                self.stats['folders_monitored'] = len(self.tracked_folders)
                logger.info(f"Removed folder from monitoring: {share_url}")
                return True
        return False
    
    def start(self):
        """Start monitoring all tracked folders."""
        if self._running:
            logger.warning("Monitor already running")
            return
        
        logger.info(f"Starting public cloud monitor for {len(self.tracked_folders)} folders...")
        self._running = True
        
        # Do initial scan of all folders in parallel
        with self._folders_lock:
            urls = list(self.tracked_folders.keys())
        for share_url in urls:
            self._executor.submit(self._scan_folder_safe, share_url)
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Public cloud monitor started")
    
    def stop(self):
        """Stop monitoring."""
        if not self._running:
            return
        
        logger.info("Stopping public cloud monitor...")
        self._running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        self._executor.shutdown(wait=False)
        
        logger.info("Public cloud monitor stopped")
    
    def _scan_folder_safe(self, share_url: str):
        """Wrapper for _scan_folder that catches all exceptions (for use in thread pool)."""
        try:
            self._scan_folder(share_url)
        except Exception as e:
            logger.error(f"Error scanning folder {share_url}: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def _monitor_loop(self):
        """Main monitoring loop. Scans all folders in parallel each cycle."""
        while self._running:
            try:
                # Get snapshot of tracked folder URLs
                with self._folders_lock:
                    urls = list(self.tracked_folders.keys())
                
                if urls:
                    # Submit all folder scans in parallel
                    futures = {
                        self._executor.submit(self._scan_folder_safe, url): url
                        for url in urls
                    }
                    
                    # Wait for all scans to complete (with timeout)
                    for future in as_completed(futures, timeout=120):
                        if not self._running:
                            break
                
                self.stats['last_scan_time'] = datetime.utcnow().isoformat()
                
                # Wait for next poll
                time.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                self.stats['errors'] += 1
                time.sleep(10)  # Back off on error
    
    def _scan_folder(self, share_url: str):
        """
        Scan a folder and detect changes.
        Uses per-folder lock so different folders scan in parallel.
        """
        folder_lock = self._get_folder_lock(share_url)
        
        # Non-blocking acquire: if this folder is already being scanned, skip
        if not folder_lock.acquire(blocking=False):
            logger.debug(f"Scan already in progress for: {share_url}, skipping")
            return
        
        try:
            with self._folders_lock:
                folder_info = self.tracked_folders.get(share_url)
            
            if not folder_info:
                return
            
            source = folder_info['source']
            folder_id = folder_info['folder_id']
            recursive = folder_info['recursive']
            
            logger.debug(f"Scanning folder: {share_url}")
            
            # Get current files
            current_files = None
            
            if source == Source.GOOGLE_DRIVE:
                current_files = self._scan_gdrive_folder(folder_id, recursive, share_url)
            elif source == Source.ONEDRIVE:
                current_files = self._scan_onedrive_folder(share_url, recursive)
            
            # If scan failed (rate limited, API error), skip change detection
            if current_files is None:
                logger.warning(f"Scan failed for {share_url}, skipping change detection")
                return
            
            # Compare with previous state to detect changes
            self._detect_changes(current_files, share_url, source)
            
        except Exception as e:
            logger.error(f"Error scanning folder {share_url}: {e}", exc_info=True)
            self.stats['errors'] += 1
        finally:
            folder_lock.release()
    
    def _scan_gdrive_folder(
        self,
        folder_id: str,
        recursive: bool,
        base_url: str,
        parent_path: str = ""
    ) -> Dict[str, Dict]:
        """
        Recursively scan Google Drive folder.
        
        Returns:
            Dict of {file_path: file_metadata}
        """
        files = {}
        
        # List folder contents
        items = self.gdrive_access.list_folder_contents(folder_id)
        
        # If None, the API call failed (rate limit, etc.) - skip this scan
        if items is None:
            logger.warning(f"Skipping scan of {folder_id} - API call failed")
            return None
        
        for item in items:
            item_id = item['id']
            item_name = item['name']
            mime_type = item['mimeType']
            
            # Check if it's a folder
            if mime_type == 'application/vnd.google-apps.folder':
                if recursive:
                    # Recursively scan subfolder
                    subfolder_files = self._scan_gdrive_folder(
                        item_id, recursive, base_url, f"{parent_path}/{item_name}"
                    )
                    if subfolder_files is not None:
                        files.update(subfolder_files)
                    else:
                        logger.warning(f"Subfolder scan failed for {item_name}, skipping")
            else:
                # It's a file - use file ID as stable key (not URL path)
                file_key = f"{base_url}::{item_id}"
                files[file_key] = {
                    'id': item_id,
                    'name': item_name,
                    'modified': item.get('modifiedTime', ''),
                    'created': item.get('createdTime', ''),
                    'size': int(item.get('size', 0)),
                    'mime_type': mime_type,
                    'owners': item.get('owners', []),
                    'source': Source.GOOGLE_DRIVE,
                    'folder_id': folder_id,
                    'share_url': base_url,
                    'parent_path': parent_path,
                }
        
        return files
    
    def _scan_onedrive_folder(
        self,
        share_url: str,
        recursive: bool,
        parent_path: str = "",
        folder_id: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Recursively scan OneDrive folder.
        
        Returns:
            Dict of {file_path: file_metadata}
        """
        files = {}
        
        # List folder contents (root or subfolder)
        items = self.onedrive_access.list_folder_contents(share_url, item_id=folder_id)
        
        for item in items:
            item_id = item['id']
            item_name = item['name']
            
            # Check if it's a folder
            if 'folder' in item:
                if recursive:
                    # Recursively scan subfolder using its ID
                    subfolder_files = self._scan_onedrive_folder(
                        share_url, 
                        recursive, 
                        f"{parent_path}/{item_name}", 
                        folder_id=item_id
                    )
                    files.update(subfolder_files)
            else:
                # It's a file - use file ID as stable key
                file_key = f"{share_url}::{item_id}"
                files[file_key] = {
                    'id': item_id,
                    'name': item_name,
                    'modified': item.get('lastModifiedDateTime', ''),
                    'created': item.get('createdDateTime', ''),
                    'size': item.get('size', 0),
                    'mime_type': item.get('file', {}).get('mimeType', 'application/octet-stream'),
                    'download_url': item.get('@microsoft.graph.downloadUrl'),
                    'web_url': item.get('webUrl', ''),
                    'source': Source.ONEDRIVE,
                    'share_url': share_url,
                    'parent_path': parent_path,
                }
        
        return files
    
    def _detect_changes(
        self,
        current_files: Dict[str, Dict],
        share_url: str,
        source: Source
    ):
        """
        Detect changes between current and previous file states.
        Thread-safe: uses _states_lock for file_states access.
        
        IMPORTANT: Only updates file_states for files that were successfully
        downloaded. Failed downloads are NOT recorded, so they'll be retried
        on the next scan cycle.
        """
        # --- Phase 1: Compute changes under lock ---
        with self._states_lock:
            # Get subset of known files belonging to this share_url
            previous_paths = set(
                path for path in self.file_states.keys()
                if path.startswith(share_url + "::")
            )
            current_paths = set(current_files.keys())
            
            new_paths = current_paths - previous_paths
            deleted_paths = previous_paths - current_paths
            
            common_paths = current_paths & previous_paths
            modified_files = []
            for file_path in common_paths:
                current_meta = current_files[file_path]
                previous_meta = self.file_states.get(file_path)
                if not previous_meta:
                    continue
                if (current_meta.get('modified') != previous_meta.get('modified') or
                    current_meta.get('size') != previous_meta.get('size')):
                    modified_files.append(file_path)
            
            # Remove state for deleted files immediately
            deleted_metas = {}
            for file_path in deleted_paths:
                deleted_metas[file_path] = self.file_states.pop(file_path, {})
        
        # --- Phase 2: Emit events OUTSIDE the lock (downloads can be slow) ---
        # Only update file_states for files where download succeeded.
        # Failed downloads will appear as "new" again next scan cycle → auto retry.
        
        for file_path in new_paths:
            success = self._emit_event(file_path, current_files[file_path], EventType.CREATED, source)
            if success:
                with self._states_lock:
                    self.file_states[file_path] = current_files[file_path]
        
        for file_path in deleted_paths:
            meta = deleted_metas.get(file_path, {})
            self._emit_event(file_path, meta, EventType.DELETED, source)
        
        for file_path in modified_files:
            success = self._emit_event(file_path, current_files[file_path], EventType.MODIFIED, source)
            if success:
                with self._states_lock:
                    self.file_states[file_path] = current_files[file_path]
        
        with self._states_lock:
            self.stats['files_tracked'] = len(self.file_states)
    
    def _emit_event(
        self,
        file_path: str,
        file_meta: Dict,
        event_type: EventType,
        source: Source
    ) -> bool:
        """
        Emit a file event to the queue.
        
        Returns:
            True if event was emitted successfully.
            False if download failed (caller should NOT update state so file is retried).
        """
        try:
            # Determine file type from mime type
            mime_type = file_meta.get('mime_type', '')
            file_type = get_file_type_from_mime(mime_type, file_meta['name'])
            
            # Download file for CREATED/MODIFIED events
            local_path = None
            if event_type in (EventType.CREATED, EventType.MODIFIED):
                local_path = self._download_file(file_meta, source)
                if local_path is None:
                    # Download failed - DON'T emit event, DON'T update state
                    # File will appear as "new" on next scan → automatic retry
                    logger.warning(f"Skipping event for {file_meta['name']} - download failed, will retry next cycle")
                    return False
            
            # Prepare metadata dict
            share_url = file_meta.get('share_url', '')
            metadata = {
                'file_name': file_meta.get('name', 'unknown'),
                'file_type': file_type.value,
                'file_size': file_meta.get('size', 0),
                'file_size_bytes': file_meta.get('size', 0),
                'modified_time': file_meta.get('modified', ''),
                'created_time': file_meta.get('created', ''),
                'mime_type': mime_type,
                'is_public_share': True,
                'source_url': share_url,
                'owners': file_meta.get('owners', []),
                'relative_path': file_path.replace(share_url, '').lstrip('/') if share_url else file_path,
                'parent_path': file_meta.get('parent_path', ''),
            }
            
            if local_path:
                metadata['local_path'] = str(local_path)

            # Create event
            event = FileEvent(
                file_path=file_path,
                event_type=event_type,
                source=source,
                timestamp=datetime.utcnow(),
                metadata=metadata
            )
            
            # Push to queue
            self.event_queue.put(event)
            self.stats['events_generated'] += 1
            
            # Call callback for hello/bye talel
            if self.on_event_callback:
                self.on_event_callback(event)
            
            logger.info(f"Event: {event_type.value} - {file_meta['name']} ({source.value})")
            return True
        
        except Exception as e:
            logger.error(f"Error emitting event: {e}", exc_info=True)
            self.stats['errors'] += 1
            return False
    
    def _download_file(self, file_meta: Dict, source: Source) -> Optional[Path]:
        """Download file to tmp directory, preserving subfolder structure."""
        try:
            if source == Source.GOOGLE_DRIVE:
                return self.gdrive_access.download_file(
                    file_meta['id'], 
                    file_meta['name'],
                    mime_type=file_meta.get('mime_type', ''),
                    sub_path=file_meta.get('parent_path', '')
                )
            elif source == Source.ONEDRIVE:
                download_url = file_meta.get('download_url')
                if download_url:
                    return self.onedrive_access.download_file(
                        download_url,
                        file_meta['name']
                    )
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
        return None
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics."""
        return self.stats.copy()
    
    def get_tracked_folders(self) -> List[Dict]:
        """Get list of tracked folders."""
        return [
            {
                'url': url,
                'source': info['source'].value,
                'recursive': info['recursive'],
                'metadata': info['metadata']
            }
            for url, info in self.tracked_folders.items()
        ]
