# -*- coding: utf-8 -*-
"""Main processing pipeline - ingest files and generate embeddings"""
import sys
import os
from pathlib import Path
import traceback

# Fix Windows encoding for emojis
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, OUTPUT_DIR, METADATA_OUTPUT_FILE, METADATA_CSV_FILE
from config import EMBEDDING_MODEL, OLLAMA_API_URL, OLLAMA_MODEL
from config import PHOTO_INGESTION_URL, AUDIO_TRANSCRIBE_ENABLED
from ingestors.ingestor import IngestorFactory
from embedders.embedder import EmbeddingPipeline
from storage.storage import MetadataStorage, MemoryIndex


class MemoryProcessor:
    """Main processor for ingesting files and generating embeddings"""
    
    def __init__(self):
        """Initialize processor"""
        self.ingestor_factory = IngestorFactory()
        self.embedding_pipeline = EmbeddingPipeline(
            embedding_model=EMBEDDING_MODEL,
            ollama_url=OLLAMA_API_URL,
            ollama_model=OLLAMA_MODEL
        )
        self.storage = MetadataStorage(
            str(METADATA_OUTPUT_FILE),
            str(METADATA_CSV_FILE)
        )
        if PHOTO_INGESTION_URL:
            print(f"✓ Image captions via: {PHOTO_INGESTION_URL}")
        else:
            print("⚠ Image captions disabled (PHOTO_INGESTION_URL not set)")
        print(f"✓ Audio transcription enabled: {AUDIO_TRANSCRIBE_ENABLED}")
        print("✓ MemoryProcessor initialized\n")
    
    def process_file(self, file_path: str) -> bool:
        """Process single file"""
        try:
            file_path = Path(file_path)
            print(f"\n{'='*60}")
            print(f"📄 Processing: {file_path.name}")
            print('='*60)
            
            # Ingest file
            print("  → Ingesting file...")
            text, file_metadata = self.ingestor_factory.ingest(str(file_path))
            
            if not text:
                print(f"  ⚠ No text extracted from file")
                return False
            
            print(f"    ✓ Extracted {len(text)} characters")
            
            # Process through embedding pipeline
            print("  → Generating embeddings...")
            processed_data = self.embedding_pipeline.process_text(text, file_metadata)
            
            print(f"    ✓ Generated {processed_data['num_chunks']} chunks")
            print(f"    ✓ Embeddings created (dimension: {processed_data['embedding_dimension']})")
            
            # Extract metadata
            print("  → Enriching with metadata...")
            print(f"    ✓ Summary: {processed_data['text_summary'][:100]}...")
            print(f"    ✓ Keywords: {', '.join(processed_data['keywords'][:3])}")
            
            # Store
            self.storage.add_document(processed_data)
            
            print(f"  ✓ COMPLETED: {file_path.name}")
            return True
            
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            traceback.print_exc()
            return False
    
    def process_directory(self, directory: str = None) -> None:
        """Process all supported files in directory"""
        if directory is None:
            directory = DATA_DIR / "raw"
        
        directory = Path(directory)
        
        if not directory.exists():
            print(f"✗ Directory not found: {directory}")
            return
        
        print(f"\n{'='*60}")
        print(f"📁 Processing Directory: {directory}")
        print('='*60)
        
        # Find all supported files
        supported_files = []
        
        for ext, files in [
            ('.txt', directory.glob('**/*.txt')),
            ('.md', directory.glob('**/*.md')),
            ('.pdf', directory.glob('**/*.pdf')),
            ('.jpg', directory.glob('**/*.jpg')),
            ('.jpeg', directory.glob('**/*.jpeg')),
            ('.png', directory.glob('**/*.png')),
            ('.bmp', directory.glob('**/*.bmp')),
            ('.mp3', directory.glob('**/*.mp3')),
            ('.wav', directory.glob('**/*.wav')),
            ('.m4a', directory.glob('**/*.m4a')),
            ('.flac', directory.glob('**/*.flac')),
        ]:
            supported_files.extend(files)
        
        if not supported_files:
            print(f"✗ No supported files found in {directory}")
            return
        
        print(f"Found {len(supported_files)} files to process\n")
        
        # Process each file
        successful = 0
        failed = 0
        
        for file_path in supported_files:
            if self.process_file(str(file_path)):
                successful += 1
            else:
                failed += 1
        
        # Save results
        print(f"\n{'='*60}")
        print("💾 Saving Results")
        print('='*60)
        
        self.storage.save_json()
        self.storage.save_csv()
        self.storage.export_embeddings_only(str(OUTPUT_DIR / "embeddings_only.json"))
        
        # Print summary
        self.storage.print_summary()
        
        # Create index
        print("\n📑 Building Memory Index...")
        index = MemoryIndex(self.storage)
        print("✓ Index built successfully\n")
        
        # Final stats
        print(f"\n{'='*60}")
        print("✅ PROCESSING COMPLETE")
        print('='*60)
        print(f"Total Processed: {len(supported_files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Output Directory: {OUTPUT_DIR}")
        print('='*60 + "\n")


def main():
    """Main entry point"""
    
    print("\n" + "="*60)
    print("🧠 AI MINDS - Cognitive Memory System")
    print("File Ingestion & Embedding Pipeline")
    print("="*60 + "\n")
    
    processor = MemoryProcessor()
    
    # Process all files in data/raw directory
    processor.process_directory(DATA_DIR / "raw")


if __name__ == "__main__":
    main()
