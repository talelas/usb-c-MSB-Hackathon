"""
Public OneDrive Access
Access publicly shared OneDrive folders and files using shareable links.
No authentication required for public links.
"""
import logging
import base64
import requests
from pathlib import Path
from typing import Optional, List, Dict

from file_handling.core.config import paths
from file_handling.core.storage_schemas import FileType, get_file_type_from_extension

logger = logging.getLogger(__name__)


class PublicOneDriveAccess:
    """
    Access publicly shared OneDrive content without authentication.
    Only works with publicly shared folders/files.
    """
    
    GRAPH_API = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, temp_dir: Optional[Path] = None):
        """
        Initialize public OneDrive access.
        
        Args:
            temp_dir: Directory for downloaded files
        """
        self.temp_dir = temp_dir or paths.onedrive_tmp
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Public OneDrive access initialized")
    
    def _encode_sharing_url(self, share_url: str) -> str:
        """
        Encode a sharing URL for Microsoft Graph API.
        
        Args:
            share_url: OneDrive shareable URL
        
        Returns:
            Encoded share token for API use
        """
        # Encode URL to base64
        encoded = base64.urlsafe_b64encode(share_url.encode('utf-8')).decode('utf-8')
        # Remove padding and prepend 'u!'
        encoded = encoded.rstrip('=')
        return f"u!{encoded}"
    
    def get_shared_item(self, share_url: str) -> Optional[Dict]:
        """
        Get metadata for a publicly shared OneDrive item.
        
        Args:
            share_url: OneDrive shareable URL
        
        Returns:
            Item metadata dict or None
        """
        try:
            encoded_url = self._encode_sharing_url(share_url)
            
            response = requests.get(
                f"{self.GRAPH_API}/shares/{encoded_url}/driveItem",
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.error("Shared item not found or not publicly accessible")
            elif response.status_code == 403:
                logger.error("Access denied. Item may not be publicly shared.")
            else:
                logger.error(f"Error accessing shared item: {response.status_code}")
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting shared item: {e}")
            return None
    
    def list_folder_contents(self, share_url: str, item_id: Optional[str] = None) -> List[Dict]:
        """
        List contents of a publicly shared folder (root or subfolder).
        
        Args:
            share_url: OneDrive shareable folder URL
            item_id: Optional item ID for subfolder (if None, lists root of share)
        
        Returns:
            List of file/folder metadata dicts
        """
        try:
            encoded_url = self._encode_sharing_url(share_url)
            
            # Construct URL based on whether we are listing root or subfolder
            if item_id:
                url = f"{self.GRAPH_API}/shares/{encoded_url}/items/{item_id}/children"
            else:
                url = f"{self.GRAPH_API}/shares/{encoded_url}/driveItem/children"
            
            response = requests.get(
                url,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('value', [])
                logger.debug(f"Found {len(items)} items in folder {'root' if not item_id else item_id}")
                return items
            else:
                logger.error(f"Error listing folder: {response.status_code} {response.text}")
                return []
        
        except Exception as e:
            logger.error(f"Error listing folder contents: {e}")
            return []
    
    def download_file(self, download_url: str, file_name: str) -> Optional[Path]:
        """
        Download a file from OneDrive.
        
        Args:
            download_url: Direct download URL from item metadata
            file_name: Name for saved file
        
        Returns:
            Path to downloaded file or None
        """
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            file_path = self.temp_dir / file_name
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded: {file_name}")
            return file_path
        
        except Exception as e:
            logger.error(f"Download failed for {file_name}: {e}")
            return None
    
    def scan_folder_recursive(
        self,
        share_url: str,
        recursive: bool = True
    ) -> List[Dict]:
        """
        Recursively scan shared folder.
        
        Args:
            share_url: OneDrive shareable folder URL
            recursive: Scan subfolders
        
        Returns:
            List of all files found
        """
        all_files = []
        
        def scan_folder(url: str, path_prefix: str = "", folder_id: Optional[str] = None):
            items = self.list_folder_contents(url, item_id=folder_id)
            
            for item in items:
                item_id = item.get('id')
                item_name = item.get('name', 'unknown')
                
                # Check if it's a folder
                if 'folder' in item:
                    if recursive:
                        logger.debug(f"Scanning subfolder: {item_name}")
                        # Recursively scan subfolder using its ID
                        scan_folder(url, f"{path_prefix}/{item_name}", folder_id=item_id)
                else:
                    # It's a file
                    file_info = {
                        'id': item_id,
                        'name': item_name,
                        'mime_type': item.get('file', {}).get('mimeType', ''),
                        'size': item.get('size', 0),
                        'modified_time': item.get('lastModifiedDateTime'),
                        'created_time': item.get('createdDateTime'),
                        'download_url': item.get('@microsoft.graph.downloadUrl'),
                        'web_url': item.get('webUrl', ''),
                        'path': f"{path_prefix}/{item_name}"
                    }
                    all_files.append(file_info)
        
        scan_folder(share_url)
        logger.info(f"Found {len(all_files)} files total")
        return all_files
    
    def get_file_type(self, file_path: Path) -> FileType:
        """Determine file type from extension."""
        return get_file_type_from_extension(file_path.suffix)
