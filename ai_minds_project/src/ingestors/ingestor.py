"""File Ingestors - Convert various file types to text"""
import os
import base64
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
import json
import requests

from config import (
    PHOTO_INGESTION_URL,
    PHOTO_INGESTION_PROMPT,
    PHOTO_INGESTION_TIMEOUT,
    USE_MEDIA_TEXT_CACHE,
    GENERATE_MEDIA_TEXT,
    AUDIO_TRANSCRIBE_ENABLED,
    AUDIO_TRANSCRIBE_MODEL,
    AUDIO_TRANSCRIBE_DEVICE,
    AUDIO_TRANSCRIBE_COMPUTE_TYPE,
)
from media_cache import MediaTextCache

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
            'file_path': str(path),
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
            'file_path': str(path),
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
        caption = self._get_image_caption(path)
        if caption:
            content = f"{content}\nCaption: {caption}"

        # Try to extract EXIF data
        exif_data = self._extract_exif(path)
        
        metadata = {
            'modality': 'image',
            'file_name': path.name,
            'file_path': str(path),
            'file_size_bytes': path.stat().st_size,
            'timestamp': str(datetime.fromtimestamp(path.stat().st_mtime)),
            'file_extension': path.suffix,
            'exif_data': exif_data,
            'caption': caption
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

    def _get_image_caption(self, path: Path) -> str:
        """Generate image caption using Qwen2-VL server (optional)"""
        if USE_MEDIA_TEXT_CACHE:
            cache = MediaTextCache()
            cached = cache.get_caption(path)
            if cached:
                print("  ✓ Using cached caption")
                return cached

        if not GENERATE_MEDIA_TEXT:
            print("  ⚠ Media text generation disabled, skipping caption")
            return ""

        if not PHOTO_INGESTION_URL:
            print(f"  ⚠ No PHOTO_INGESTION_URL configured, skipping caption")
            return ""

        try:
            print(f"  → Requesting caption from {PHOTO_INGESTION_URL}...")
            image_bytes = path.read_bytes()
            ext = path.suffix.lower().lstrip('.')
            mime = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            payload = {
                "image_b64": f"data:{mime};base64,{image_b64}",
                "prompt": PHOTO_INGESTION_PROMPT
            }

            response = requests.post(
                PHOTO_INGESTION_URL,
                json=payload,
                timeout=PHOTO_INGESTION_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                caption = (data.get("description") or "").strip()
                print(f"  ✓ Got caption ({len(caption)} chars)")
                if USE_MEDIA_TEXT_CACHE and caption:
                    MediaTextCache().set_caption(path, caption)
                return caption
            else:
                print(f"  ✗ Caption server error: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Caption failed: {e}")
            return ""

        return ""


class AudioIngestor(FileIngestor):
    """Ingest audio files - extract metadata"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.mp3', '.wav', '.m4a', '.flac']
    
    def ingest(self, file_path: str) -> Tuple[str, dict]:
        """Extract metadata from audio file"""
        path = Path(file_path)
        
        content = f"[Audio: {path.name}] - Audio file"
        transcript = self._transcribe_audio(path) if AUDIO_TRANSCRIBE_ENABLED else ""
        if transcript:
            content = f"{content}\nTranscript: {transcript}"

        # Try to extract audio metadata
        audio_metadata = self._extract_audio_metadata(path)
        
        metadata = {
            'modality': 'audio',
            'file_name': path.name,
            'file_path': str(path),
            'file_size_bytes': path.stat().st_size,
            'timestamp': str(datetime.fromtimestamp(path.stat().st_mtime)),
            'file_extension': path.suffix,
            'audio_metadata': audio_metadata,
            'transcript': transcript
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

    def _transcribe_audio(self, path: Path) -> str:
        """Transcribe audio using faster-whisper (optional)"""
        if USE_MEDIA_TEXT_CACHE:
            cache = MediaTextCache()
            cached = cache.get_transcript(path)
            if cached:
                print("  ✓ Using cached transcript")
                return cached

        if not GENERATE_MEDIA_TEXT:
            print("  ⚠ Media text generation disabled, skipping transcription")
            return ""

        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            print(f"  ⚠ faster-whisper not available: {e}")
            return ""

        try:
            print(f"  → Transcribing audio with faster-whisper...")
            model = WhisperModel(
                AUDIO_TRANSCRIBE_MODEL,
                device=AUDIO_TRANSCRIBE_DEVICE,
                compute_type=AUDIO_TRANSCRIBE_COMPUTE_TYPE
            )
            segments, _info = model.transcribe(str(path))

            parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    parts.append(text)

            transcript = " ".join(parts)
            print(f"  ✓ Got transcript ({len(transcript)} chars)")
            if USE_MEDIA_TEXT_CACHE and transcript:
                MediaTextCache().set_transcript(path, transcript)
            return transcript
        except Exception as e:
            print(f"  ✗ Transcription failed: {e}")
            return ""


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
