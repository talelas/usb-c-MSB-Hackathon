"""File Ingestors - Convert various file types to text"""
import os
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
import json

class FileIngestor:
    """Base class for file ingestors"""
    
    def __init__(self):
        self.supported_extensions = []
    
    def ingest(self, file_path: str) -> Tuple[str, dict]:
        """
        Ingest a file and return (text_content, metadata)
        """
        raise NotImplementedError


class TextIngestor(FileIngestor):
    """Ingest plain text and markdown files"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.txt', '.md']
    
    def ingest(self, file_path: str) -> Tuple[str, dict]:
        """Read text file"""
        path = Path(file_path)
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        metadata = {
            'modality': 'text',
            'file_name': path.name,
            'file_size_bytes': path.stat().st_size,
            'timestamp': str(datetime.fromtimestamp(path.stat().st_mtime)),
            'file_extension': path.suffix
        }
        
        return content, metadata


class PDFIngestor(FileIngestor):
    """Ingest PDF files"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.pdf']
    
    def ingest(self, file_path: str) -> Tuple[str, dict]:
        """Extract text from PDF"""
        path = Path(file_path)
        
        try:
            import PyPDF2
            text = []
            with open(path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            
            content = '\n'.join(text)
        except ImportError:
            return "", {'error': 'PyPDF2 not installed', 'modality': 'pdf'}
        except Exception as e:
            return "", {'error': str(e), 'modality': 'pdf'}
        
        metadata = {
            'modality': 'pdf',
            'file_name': path.name,
            'file_size_bytes': path.stat().st_size,
            'timestamp': str(datetime.fromtimestamp(path.stat().st_mtime)),
            'file_extension': path.suffix
        }
        
        return content, metadata


class ImageIngestor(FileIngestor):
    """Ingest images - extract EXIF data and use caption model"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    
    def ingest(self, file_path: str) -> Tuple[str, dict]:
        """Extract metadata and caption from image"""
        path = Path(file_path)
        
        content = f"[Image: {path.name}] - Image file"
        
        # Try to extract EXIF data
        exif_data = self._extract_exif(path)
        
        metadata = {
            'modality': 'image',
            'file_name': path.name,
            'file_size_bytes': path.stat().st_size,
            'timestamp': str(datetime.fromtimestamp(path.stat().st_mtime)),
            'file_extension': path.suffix,
            'exif_data': exif_data
        }
        
        return content, metadata
    
    def _extract_exif(self, path: Path) -> dict:
        """Extract EXIF metadata from image"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            image = Image.open(path)
            exif_data = image._getexif()
            
            if not exif_data:
                return {}
            
            exif_dict = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_dict[tag] = str(value)[:100]  # Limit to 100 chars
            
            return exif_dict
        except:
            return {}


class AudioIngestor(FileIngestor):
    """Ingest audio files - extract metadata"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.mp3', '.wav', '.m4a', '.flac']
    
    def ingest(self, file_path: str) -> Tuple[str, dict]:
        """Extract metadata from audio file"""
        path = Path(file_path)
        
        content = f"[Audio: {path.name}] - Audio file"
        
        # Try to extract audio metadata
        audio_metadata = self._extract_audio_metadata(path)
        
        metadata = {
            'modality': 'audio',
            'file_name': path.name,
            'file_size_bytes': path.stat().st_size,
            'timestamp': str(datetime.fromtimestamp(path.stat().st_mtime)),
            'file_extension': path.suffix,
            'audio_metadata': audio_metadata
        }
        
        return content, metadata
    
    def _extract_audio_metadata(self, path: Path) -> dict:
        """Extract audio metadata"""
        try:
            from mutagen import File
            audio = File(path)
            
            if audio is None:
                return {}
            
            metadata = {}
            for key, value in audio.items():
                metadata[key] = str(value)[:100]  # Limit to 100 chars
            
            return metadata
        except:
            return {}


class IngestorFactory:
    """Factory to get appropriate ingestor for file type"""
    
    def __init__(self):
        self.ingestors = {
            '.txt': TextIngestor(),
            '.md': TextIngestor(),
            '.pdf': PDFIngestor(),
            '.jpg': ImageIngestor(),
            '.jpeg': ImageIngestor(),
            '.png': ImageIngestor(),
            '.bmp': ImageIngestor(),
            '.mp3': AudioIngestor(),
            '.wav': AudioIngestor(),
            '.m4a': AudioIngestor(),
            '.flac': AudioIngestor(),
        }
    
    def get_ingestor(self, file_path: str) -> Optional[FileIngestor]:
        """Get appropriate ingestor for file"""
        ext = Path(file_path).suffix.lower()
        return self.ingestors.get(ext)
    
    def ingest(self, file_path: str) -> Tuple[str, dict]:
        """Ingest file with appropriate ingestor"""
        ingestor = self.get_ingestor(file_path)
        
        if not ingestor:
            raise ValueError(f"Unsupported file type: {Path(file_path).suffix}")
        
        return ingestor.ingest(file_path)
