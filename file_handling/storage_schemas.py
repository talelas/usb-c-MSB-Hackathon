"""
Data Schemas and Models for File Handling
Defines the structure of data flowing through the system using Pydantic.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Enumeration of supported file types"""
    TEXT = "text"
    CODE = "code"
    PDF = "pdf"
    IMAGE = "image"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    """File system event types"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


class Source(str, Enum):
    """Data source types"""
    LOCAL = "local_filesystem"
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"


class FileEvent(BaseModel):
    """File system event"""
    event_type: EventType
    source: Source
    file_path: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


def get_file_type_from_extension(extension: str) -> FileType:
    """Get FileType from file extension."""
    ext = extension.lower()
    
    extension_map = {
        # Text
        '.txt': FileType.TEXT, '.md': FileType.TEXT, '.rst': FileType.TEXT, '.log': FileType.TEXT,
        # Code
        '.py': FileType.CODE, '.js': FileType.CODE, '.java': FileType.CODE, '.cpp': FileType.CODE,
        '.c': FileType.CODE, '.h': FileType.CODE, '.css': FileType.CODE, '.html': FileType.CODE,
        '.json': FileType.CODE, '.yaml': FileType.CODE, '.yml': FileType.CODE, '.xml': FileType.CODE,
        '.ts': FileType.CODE, '.jsx': FileType.CODE, '.tsx': FileType.CODE, '.go': FileType.CODE,
        '.rs': FileType.CODE, '.php': FileType.CODE, '.rb': FileType.CODE, '.swift': FileType.CODE,
        # PDF
        '.pdf': FileType.PDF,
        # Image
        '.jpg': FileType.IMAGE, '.jpeg': FileType.IMAGE, '.png': FileType.IMAGE, '.gif': FileType.IMAGE,
        '.bmp': FileType.IMAGE, '.webp': FileType.IMAGE, '.svg': FileType.IMAGE,
        # Document
        '.docx': FileType.DOCUMENT, '.doc': FileType.DOCUMENT, '.odt': FileType.DOCUMENT, '.rtf': FileType.DOCUMENT,
        # Spreadsheet
        '.xlsx': FileType.SPREADSHEET, '.xls': FileType.SPREADSHEET, '.csv': FileType.SPREADSHEET, '.tsv': FileType.SPREADSHEET,
        # Presentation
        '.pptx': FileType.PRESENTATION, '.ppt': FileType.PRESENTATION, '.odp': FileType.PRESENTATION,
        # Audio
        '.mp3': FileType.AUDIO, '.wav': FileType.AUDIO, '.m4a': FileType.AUDIO, '.flac': FileType.AUDIO,
        '.ogg': FileType.AUDIO, '.aac': FileType.AUDIO,
        # Video
        '.mp4': FileType.VIDEO, '.avi': FileType.VIDEO, '.mkv': FileType.VIDEO, '.mov': FileType.VIDEO,
        '.wmv': FileType.VIDEO, '.webm': FileType.VIDEO,
        # Archive
        '.zip': FileType.ARCHIVE, '.tar': FileType.ARCHIVE, '.gz': FileType.ARCHIVE, 
        '.rar': FileType.ARCHIVE, '.7z': FileType.ARCHIVE,
    }
    
    return extension_map.get(ext, FileType.UNKNOWN)


def get_file_type_from_mime(mime_type: str, file_name: str) -> FileType:
    """Determine FileType from MIME type and filename."""
    from pathlib import Path
    
    mime_lower = mime_type.lower()
    ext = Path(file_name).suffix.lower()
    
    # Try from extension first
    ext_type = get_file_type_from_extension(ext)
    if ext_type != FileType.UNKNOWN:
        return ext_type
    
    # Fallback to MIME type detection
    if 'text' in mime_lower:
        return FileType.TEXT
    if any(x in mime_lower for x in ['word', 'document']):
        return FileType.DOCUMENT
    if any(x in mime_lower for x in ['spreadsheet', 'excel']):
        return FileType.SPREADSHEET
    if any(x in mime_lower for x in ['presentation', 'powerpoint']):
        return FileType.PRESENTATION
    if 'pdf' in mime_lower:
        return FileType.PDF
    if 'image' in mime_lower:
        return FileType.IMAGE
    if 'audio' in mime_lower:
        return FileType.AUDIO
    if 'video' in mime_lower:
        return FileType.VIDEO
    if any(x in mime_lower for x in ['zip', 'tar', 'compress']):
        return FileType.ARCHIVE
    
    return FileType.UNKNOWN
