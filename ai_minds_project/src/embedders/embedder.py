"""Embedding system using HuggingFace + Ollama"""
import numpy as np
from typing import List, Dict, Tuple
import json
import requests
from pathlib import Path

from config import STORE_MEDIA_TEXT_IN_METADATA, STORE_CHUNK_TEXT

class HuggingFaceEmbedder:
    """Embed text using HuggingFace sentence-transformers"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize embedder with HuggingFace model"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            print(f"✓ Loaded embedder: {model_name}")
        except ImportError:
            raise ImportError("Install: pip install sentence-transformers")
    
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for single text"""
        if not text or not text.strip():
            return np.zeros(384)  # Return zero vector for empty text
        
        embedding = self.model.encode(text)
        return embedding
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for batch of texts"""
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(texts)
        return embeddings
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


class OllamaEnricher:
    """Use Ollama (llama 3.2) for semantic enrichment and summarization"""
    
    def __init__(self, api_url: str = "http://localhost:11434", model: str = "llama3.2"):
        """Initialize Ollama connection"""
        self.api_url = api_url
        self.model = model
        self.available = self._check_connection()
    
    def _check_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            print(f"✓ Ollama connected at {self.api_url}")
            return True
        except:
            print(f"⚠ Ollama not available at {self.api_url}")
            return False
    
    def summarize(self, text: str, max_length: int = 150) -> str:
        """Summarize text using llama"""
        if not self.available or not text:
            return text[:max_length]
        
        try:
            prompt = f"Summarize this in {max_length} characters or less:\n{text[:1000]}"
            
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', text[:max_length])
        except Exception as e:
            print(f"⚠ Summarization failed: {e}")
        
        return text[:max_length]
    
    def extract_keywords(self, text: str, num_keywords: int = 5) -> List[str]:
        """Extract keywords using llama"""
        if not self.available or not text:
            return []

        try:
            prompt = (
                f"List {num_keywords} important keywords from the following text. "
                f"Only output a comma-separated list of keywords, nothing else:\n{text[:500]}"
            )

            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                keywords_str = result.get('response', '').strip()
                # Remove markdown-style formatting if present
                keywords_str = keywords_str.replace('\n', ',').replace('*', '').replace('-', ',')
                keywords = [k.strip().strip('.') for k in keywords_str.split(',')]
                keywords = [k for k in keywords if k and len(k) < 50]
                if keywords:
                    return keywords[:num_keywords]
                print(f"⚠ Ollama returned empty keywords: {keywords_str[:100]}")
            else:
                print(f"⚠ Ollama keyword endpoint returned status {response.status_code}")
        except Exception as e:
            print(f"⚠ Keyword extraction failed: {e}")

        return []


class EmbeddingPipeline:
    """Complete embedding pipeline: ingest -> chunk -> embed -> enrich"""
    
    def __init__(self, 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 ollama_url: str = "http://localhost:11434",
                 ollama_model: str = "llama3.2"):
        """Initialize embedding pipeline"""
        self.embedder = HuggingFaceEmbedder(embedding_model)
        self.enricher = OllamaEnricher(ollama_url, ollama_model)
        self.chunk_size = 512
        self.chunk_overlap = 50
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split text into overlapping chunks"""
        if chunk_size is None:
            chunk_size = self.chunk_size
        if overlap is None:
            overlap = self.chunk_overlap
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start += chunk_size - overlap
        
        return chunks if chunks else [text]
    
    def process_text(self, text: str, file_metadata: dict) -> Dict:
        """Process text: chunk -> embed -> enrich"""
        
        # Chunk text
        chunks = self.chunk_text(text)
        
        # Embed chunks
        embeddings = self.embedder.embed_batch(chunks)
        
        # Generate summary
        summary = self.enricher.summarize(text)
        
        # Extract keywords
        keywords = self.enricher.extract_keywords(text)
        
        # Optionally drop media text fields from metadata after embedding
        if not STORE_MEDIA_TEXT_IN_METADATA:
            if isinstance(file_metadata, dict):
                file_metadata = dict(file_metadata)
                file_metadata.pop('caption', None)
                file_metadata.pop('transcript', None)

        # Create result
        result = {
            'file_metadata': file_metadata,
            'text_summary': summary,
            'keywords': keywords,
            'num_chunks': len(chunks),
            'chunks': [
                {
                    'text': chunk if STORE_CHUNK_TEXT else "",
                    'embedding': embedding.tolist(),
                    'chunk_index': i
                }
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
            ],
            'embedding_model': self.embedder.model_name,
            'embedding_dimension': self.embedder.get_dimension()
        }
        
        return result


# Test embeddings
if __name__ == "__main__":
    # Test HuggingFace embedder
    embedder = HuggingFaceEmbedder()
    
    test_texts = [
        "This is a test sentence.",
        "Another test text for embedding.",
        "The quick brown fox jumps over the lazy dog."
    ]
    
    embeddings = embedder.embed_batch(test_texts)
    print(f"Generated {len(embeddings)} embeddings")
    print(f"Embedding dimension: {embedder.get_dimension()}")
    
    # Test Ollama enricher
    enricher = OllamaEnricher()
    test_text = "Artificial intelligence is transforming how we work and live."
    
    if enricher.available:
        summary = enricher.summarize(test_text)
        keywords = enricher.extract_keywords(test_text)
        print(f"Summary: {summary}")
        print(f"Keywords: {keywords}")
