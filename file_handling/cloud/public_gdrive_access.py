"""
Public Google Drive Access
Access publicly shared Google Drive folders and files using shareable links.
No OAuth required - uses API key for public content only.
"""
import os
import io
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict

from file_handling.core.config import paths, GOOGLE_API_KEY
from file_handling.core.storage_schemas import FileEvent, EventType, Source, FileType, get_file_type_from_extension

logger = logging.getLogger(__name__)

# Google Workspace MIME types that need export instead of download
GOOGLE_APPS_EXPORT_MAP = {
    'application/vnd.google-apps.document': ('application/pdf', '.pdf'),
    'application/vnd.google-apps.spreadsheet': ('text/csv', '.csv'),
    'application/vnd.google-apps.presentation': ('application/pdf', '.pdf'),
    'application/vnd.google-apps.drawing': ('image/png', '.png'),
    'application/vnd.google-apps.jam': ('application/pdf', '.pdf'),
}


class PublicGoogleDriveAccess:
    """
    Access publicly shared Google Drive content using API key (no OAuth required).
    Only works with publicly shared folders/files.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        temp_dir: Optional[Path] = None
    ):
        """
        Initialize public Google Drive access.
        
        Args:
            api_key: Google API key (get from Cloud Console)
            temp_dir: Directory for downloaded files
        """
        self.api_key = api_key or GOOGLE_API_KEY
        self.temp_dir = temp_dir or paths.gdrive_tmp
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.service = None
        
        if self.api_key:
            try:
                from googleapiclient.discovery import build
                self.service = build('drive', 'v3', developerKey=self.api_key)
                logger.info("Public Google Drive access initialized with API key")
            except ImportError:
                logger.error("Failed to initialize Google Drive: No module named 'googleapiclient'. "
                           "Install with: pip install google-api-python-client")
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive service: {e}")
        else:
            logger.warning("No Google API key provided. Set GOOGLE_API_KEY environment variable.")
    
    def list_folder_contents(self, folder_id: str) -> List[Dict]:
        """
        List contents of a publicly shared folder.
        
        Args:
            folder_id: Google Drive folder ID
        
        Returns:
            List of file/folder metadata dicts
        """
        if not self.service:
            logger.error("Google Drive Service not initialized. Please set GOOGLE_API_KEY.")
            return []
        
        try:
            from googleapiclient.errors import HttpError
            
            results = []
            page_token = None
            
            while True:
                response = self.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, createdTime, owners, version, md5Checksum)",
                    pageToken=page_token,
                    supportsAllDrives=True
                ).execute()
                
                results.extend(response.get('files', []))
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            logger.debug(f"Found {len(results)} items in folder {folder_id}")
            return results
        
        except Exception as e:
            if hasattr(e, 'resp'):
                if e.resp.status == 404:
                    logger.error(f"Folder not found or not public: {folder_id}")
                elif e.resp.status == 403:
                    logger.warning(f"Rate limited or access denied for folder: {folder_id}")
                else:
                    logger.error(f"Error listing folder: {e}")
            else:
                logger.error(f"Error listing folder: {e}")
            return None  # Return None so caller knows it failed (vs empty folder)
    
    def download_file(self, file_id: str, file_name: str, mime_type: str = "", sub_path: str = "") -> Optional[Path]:
        """
        Download a publicly shared file. Handles Google Docs/Sheets/Slides
        by exporting them to a standard format.
        
        Downloads to a .tmp file first, then renames on success.
        This prevents empty files when the download fails (e.g. rate limiting).
        
        Args:
            file_id: Google Drive file ID
            file_name: Name for saved file
            mime_type: MIME type of the file (to detect Google Workspace files)
            sub_path: Subfolder path to preserve folder structure (e.g. "/Reports/Q1")
        
        Returns:
            Path to downloaded file or None
        """
        if not self.service:
            logger.error("Service not initialized")
            return None
        
        tmp_file = None  # Track the temp file for cleanup on failure
        
        try:
            from googleapiclient.http import MediaIoBaseDownload
            
            # Determine destination directory (create subfolder if needed)
            dest_dir = self.temp_dir
            if sub_path:
                dest_dir = self.temp_dir / sub_path.strip('/')
                dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if this is a Google Workspace file that needs export
            if mime_type in GOOGLE_APPS_EXPORT_MAP:
                export_mime, ext = GOOGLE_APPS_EXPORT_MAP[mime_type]
                # Add extension if not already present
                export_name = file_name if file_name.endswith(ext) else f"{file_name}{ext}"
                file_path = dest_dir / export_name
                
                request = self.service.files().export_media(
                    fileId=file_id, mimeType=export_mime
                )
            else:
                file_path = dest_dir / file_name
                request = self.service.files().get_media(fileId=file_id)
            
            # Download to a temp file first - prevents empty files on failure
            tmp_file = file_path.with_suffix(file_path.suffix + '.tmp')
            
            with io.FileIO(tmp_file, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.debug(f"Download {int(status.progress() * 100)}%")
            
            # Download succeeded - rename temp file to final name
            if tmp_file.exists() and tmp_file.stat().st_size > 0:
                if file_path.exists():
                    file_path.unlink()
                tmp_file.rename(file_path)
                logger.info(f"Downloaded: {file_path.name} ({file_path.stat().st_size} bytes)")
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                return file_path
            else:
                logger.warning(f"Download produced empty file for {file_name}")
                if tmp_file.exists():
                    tmp_file.unlink()
                return None
        
        except Exception as e:
            # Clean up temp file on any failure
            if tmp_file and tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass
            
            error_str = str(e)
            if "fileNotDownloadable" in error_str:
                # Try export as PDF fallback for unknown Google types
                return self._export_as_pdf(file_id, file_name, sub_path=sub_path)
            elif "403" in error_str or "rate" in error_str.lower() or "Sorry" in error_str:
                logger.warning(f"Rate limited downloading {file_name}, will retry next cycle")
                return None
            else:
                logger.error(f"Download failed for {file_name}: {e}")
                return None
    
    def _export_as_pdf(self, file_id: str, file_name: str, sub_path: str = "") -> Optional[Path]:
        """Fallback: export a Google Workspace file as PDF."""
        tmp_file = None
        try:
            from googleapiclient.http import MediaIoBaseDownload
            
            dest_dir = self.temp_dir
            if sub_path:
                dest_dir = self.temp_dir / sub_path.strip('/')
                dest_dir.mkdir(parents=True, exist_ok=True)
            
            export_name = f"{file_name}.pdf" if not file_name.endswith('.pdf') else file_name
            file_path = dest_dir / export_name
            tmp_file = file_path.with_suffix(file_path.suffix + '.tmp')
            
            request = self.service.files().export_media(
                fileId=file_id, mimeType='application/pdf'
            )
            
            with io.FileIO(tmp_file, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            if tmp_file.exists() and tmp_file.stat().st_size > 0:
                if file_path.exists():
                    file_path.unlink()
                tmp_file.rename(file_path)
                logger.info(f"Exported as PDF: {export_name}")
                time.sleep(0.5)
                return file_path
            else:
                if tmp_file.exists():
                    tmp_file.unlink()
                return None
        except Exception as e:
            if tmp_file and tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass
            logger.warning(f"Export failed for {file_name}: {e}")
            return None
    
    def scan_folder_recursive(
        self,
        folder_id: str,
        recursive: bool = True
    ) -> List[Dict]:
        """
        Recursively scan folder.
        
        Args:
            folder_id: Folder ID to scan
            recursive: Scan subfolders
        
        Returns:
            List of all files found
        """
        all_files = []
        
        def scan_folder(fid: str, path_prefix: str = ""):
            items = self.list_folder_contents(fid)
            
            for item in items:
                item_id = item['id']
                item_name = item['name']
                mime_type = item['mimeType']
                
                # Check if it's a folder
                if mime_type == 'application/vnd.google-apps.folder':
                    if recursive:
                        logger.debug(f"Scanning subfolder: {item_name}")
                        scan_folder(item_id, f"{path_prefix}/{item_name}")
                else:
                    # It's a file
                    file_info = {
                        'id': item_id,
                        'name': item_name,
                        'mime_type': mime_type,
                        'size': int(item.get('size', 0)),
                        'modified_time': item.get('modifiedTime'),
                        'created_time': item.get('createdTime'),
                        'owners': item.get('owners', []),
                        'path': f"{path_prefix}/{item_name}",
                        'folder_id': fid
                    }
                    all_files.append(file_info)
        
        scan_folder(folder_id)
        logger.info(f"Found {len(all_files)} files total")
        return all_files
    
    def get_file_type(self, file_path: Path) -> FileType:
        """Determine file type from extension."""
        return get_file_type_from_extension(file_path.suffix)
