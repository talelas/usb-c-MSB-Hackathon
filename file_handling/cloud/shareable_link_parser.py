"""
Shareable Link Parser
Extract folder/file IDs from Google Drive and OneDrive shareable URLs.
"""
import re
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs


class ShareableLinkParser:
    """Parse Google Drive and OneDrive shareable links to extract IDs and metadata."""
    
    @staticmethod
    def parse_google_drive_url(url: str) -> Optional[Dict]:
        """
        Parse a Google Drive shareable URL.
        
        Supported formats:
        - https://drive.google.com/drive/folders/FOLDER_ID
        - https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing
        - https://drive.google.com/file/d/FILE_ID/view
        - https://drive.google.com/open?id=FOLDER_ID
        
        Args:
            url: Google Drive shareable URL
        
        Returns:
            Dict with 'id', 'type' (folder/file), 'is_public' or None
        """
        try:
            # Pattern 1: /folders/FOLDER_ID
            folder_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
            if folder_match:
                return {
                    'id': folder_match.group(1),
                    'type': 'folder',
                    'is_public': '?usp=sharing' in url or 'anyone' in url.lower(),
                    'source': 'google_drive',
                    'original_url': url
                }
            
            # Pattern 2: /file/d/FILE_ID
            file_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            if file_match:
                return {
                    'id': file_match.group(1),
                    'type': 'file',
                    'is_public': '?usp=sharing' in url or 'anyone' in url.lower(),
                    'source': 'google_drive',
                    'original_url': url
                }
            
            # Pattern 3: ?id=FOLDER_ID
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if 'id' in query_params:
                folder_id = query_params['id'][0]
                return {
                    'id': folder_id,
                    'type': 'folder',
                    'is_public': True,
                    'source': 'google_drive',
                    'original_url': url
                }
            
            return None
        
        except Exception as e:
            print(f"Error parsing Google Drive URL: {e}")
            return None
    
    @staticmethod
    def parse_onedrive_url(url: str) -> Optional[Dict]:
        """
        Parse a OneDrive shareable URL.
        
        Supported formats:
        - https://1drv.ms/f/s!SHARED_ID
        - https://onedrive.live.com/redir?resid=RESOURCE_ID
        - https://contoso-my.sharepoint.com/:f:/g/personal/user/FOLDER_ID
        
        Args:
            url: OneDrive shareable URL
        
        Returns:
            Dict with 'id', 'type', 'is_public' or None
        """
        try:
            # Pattern 1: 1drv.ms short link
            if '1drv.ms' in url:
                share_match = re.search(r'1drv\.ms/[a-z]/([sc])!([^/?]+)|1drv\.ms/f/([sc])/([^/?]+)', url)
                if share_match:
                    type_char = share_match.group(1) or share_match.group(3)
                    id_part = share_match.group(2) or share_match.group(4)
                    
                    return {
                        'id': id_part,
                        'type': 'folder',
                        'is_public': True,
                        'source': 'onedrive',
                        'original_url': url,
                        'short_url': url
                    }
                
                # Fallback for 1drv.ms containing URL
                return {
                    'id': 'unknown',
                    'type': 'folder',
                    'is_public': True,
                    'source': 'onedrive',
                    'original_url': url,
                    'short_url': url
                }
            
            # Pattern 2: Full OneDrive URL
            if 'onedrive.live.com' in url or 'sharepoint.com' in url:
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                
                if 'resid' in query_params:
                    return {
                        'id': query_params['resid'][0],
                        'type': 'folder',
                        'is_public': True,
                        'source': 'onedrive',
                        'original_url': url
                    }
                
                # SharePoint path-based sharing
                path_match = re.search(r'/:([fbu]):/[gp]/[^/]+/([a-zA-Z0-9_-]+)', url)
                if path_match:
                    item_type = {'f': 'folder', 'b': 'folder', 'u': 'file'}[path_match.group(1)]
                    return {
                        'id': path_match.group(2),
                        'type': item_type,
                        'is_public': True,
                        'source': 'onedrive',
                        'original_url': url
                    }
            
            return None
        
        except Exception as e:
            print(f"Error parsing OneDrive URL: {e}")
            return None
    
    @staticmethod
    def parse_any_url(url: str) -> Optional[Dict]:
        """
        Parse any supported shareable URL.
        
        Args:
            url: Shareable URL (Google Drive or OneDrive)
        
        Returns:
            Parsed dict with 'id', 'type', 'source' or None
        """
        # Try Google Drive
        result = ShareableLinkParser.parse_google_drive_url(url)
        if result:
            return result
        
        # Try OneDrive
        result = ShareableLinkParser.parse_onedrive_url(url)
        if result:
            return result
        
        return None
    
    @staticmethod
    def is_google_drive_url(url: str) -> bool:
        """Check if URL is a Google Drive URL."""
        return 'drive.google.com' in url or 'docs.google.com' in url
    
    @staticmethod
    def is_onedrive_url(url: str) -> bool:
        """Check if URL is a OneDrive URL."""
        return '1drv.ms' in url or 'onedrive.live.com' in url or 'sharepoint.com' in url
