"""Test script - verify embeddings and metadata generation"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import DATA_DIR, OUTPUT_DIR, EMBEDDING_MODEL
from embedders.embedder import HuggingFaceEmbedder, OllamaEnricher, EmbeddingPipeline
from ingestors.ingestor import TextIngestor, IngestorFactory
from storage.storage import MetadataStorage, MemoryIndex


def test_embedder():
    """Test HuggingFace embedder"""
    print("\n" + "="*60)
    print("🧪 TEST 1: HuggingFace Embedder")
    print("="*60)
    
    try:
        embedder = HuggingFaceEmbedder(EMBEDDING_MODEL)
        
        test_texts = [
            "Artificial intelligence is reshaping industries.",
            "Machine learning powers modern applications.",
            "Deep learning networks process complex data."
        ]
        
        embeddings = embedder.embed_batch(test_texts)
        
        print(f"✓ Generated {len(embeddings)} embeddings")
        print(f"✓ Embedding dimension: {embedder.get_dimension()}")
        print(f"✓ Sample embedding shape: {embeddings[0].shape}")
        
        # Check similarity
        import numpy as np
        sim = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        print(f"✓ Similarity between first two texts: {sim:.4f}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_ollama():
    """Test Ollama enricher"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Ollama Enricher (llama 3.2)")
    print("="*60)
    
    enricher = OllamaEnricher()
    
    if not enricher.available:
        print("⚠ Ollama not available (this is okay, system will work without it)")
        return True
    
    try:
        test_text = "Artificial intelligence and machine learning are revolutionizing how computers process information and make decisions."
        
        summary = enricher.summarize(test_text)
        print(f"✓ Summary: {summary}")
        
        keywords = enricher.extract_keywords(test_text)
        print(f"✓ Keywords: {keywords}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_ingestor():
    """Test file ingestor"""
    print("\n" + "="*60)
    print("🧪 TEST 3: File Ingestor")
    print("="*60)
    
    try:
        factory = IngestorFactory()
        
        # Create sample test file
        test_file = DATA_DIR / "raw" / "test_sample.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        sample_content = """
        AI Minds Cognitive Memory System
        
        This is a test document for the memory ingestion system.
        It demonstrates how text files are processed for embedding.
        
        The system supports multiple file types:
        - Text files (.txt)
        - Markdown (.md)
        - PDF documents
        - Images with metadata
        - Audio files
        
        Each file is converted to embeddings using HuggingFace models.
        """
        
        with open(test_file, 'w') as f:
            f.write(sample_content)
        
        # Test ingestor
        text, metadata = factory.ingest(str(test_file))
        
        print(f"✓ Ingested file: {metadata['file_name']}")
        print(f"✓ Modality: {metadata['modality']}")
        print(f"✓ Content length: {len(text)} characters")
        print(f"✓ File size: {metadata['file_size_bytes']} bytes")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_pipeline():
    """Test complete embedding pipeline"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Complete Embedding Pipeline")
    print("="*60)
    
    try:
        pipeline = EmbeddingPipeline()
        
        sample_text = """
        Machine Learning is a subset of artificial intelligence.
        It focuses on enabling computers to learn from data.
        Deep learning models use neural networks.
        Natural language processing handles text.
        Computer vision processes images.
        """
        
        sample_metadata = {
            'file_name': 'test.txt',
            'modality': 'text',
            'file_size_bytes': len(sample_text),
            'timestamp': '2026-02-14'
        }
        
        result = pipeline.process_text(sample_text, sample_metadata)
        
        print(f"✓ Processed text ({len(sample_text)} chars)")
        print(f"✓ Created {result['num_chunks']} chunks")
        print(f"✓ Summary: {result['text_summary'][:60]}...")
        print(f"✓ Keywords: {result['keywords']}")
        print(f"✓ Embedding dimension: {result['embedding_dimension']}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage():
    """Test storage system"""
    print("\n" + "="*60)
    print("🧪 TEST 5: Storage System")
    print("="*60)
    
    try:
        storage = MetadataStorage(
            str(OUTPUT_DIR / "test_metadata.json"),
            str(OUTPUT_DIR / "test_metadata.csv")
        )
        
        # Create sample processed data
        sample_data = {
            'file_metadata': {
                'file_name': 'test.txt',
                'modality': 'text',
                'file_size_bytes': 1000,
                'timestamp': '2026-02-14',
                'file_extension': '.txt'
            },
            'text_summary': 'This is a test summary of the document.',
            'keywords': ['test', 'sample', 'embedding'],
            'num_chunks': 2,
            'embedding_model': 'all-MiniLM-L6-v2',
            'embedding_dimension': 384,
            'chunks': [
                {
                    'text': 'First chunk text',
                    'embedding': [0.1] * 384,
                    'chunk_index': 0
                },
                {
                    'text': 'Second chunk text',
                    'embedding': [0.2] * 384,
                    'chunk_index': 1
                }
            ]
        }
        
        storage.add_document(sample_data)
        storage.save_json()
        storage.save_csv()
        
        summary = storage.get_summary()
        print(f"✓ Stored document")
        print(f"✓ Total documents: {summary['total_documents']}")
        print(f"✓ Total chunks: {summary['total_chunks']}")
        
        # Test index
        index = MemoryIndex(storage)
        results = index.find_by_keyword('test')
        print(f"✓ Index search found {len(results)} documents")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 AI MINDS - Integration Tests")
    print("="*60)
    
    tests = [
        ("Embedder", test_embedder),
        ("Ollama", test_ollama),
        ("Ingestor", test_ingestor),
        ("Pipeline", test_pipeline),
        ("Storage", test_storage),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"✗ Test '{name}' failed with exception: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    if passed == total:
        print("✅ All tests passed! System is ready to process files.")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
