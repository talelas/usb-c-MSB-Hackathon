"""Test script to debug /api/documents endpoint"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import postgres as pg
from app.api.schemas import DocumentOut

def test_document_serialization():
    """Test if documents can be serialized properly"""
    print("Testing document serialization...")
    
    session = pg.get_session()
    try:
        docs = pg.get_all_documents(session)
        print(f"\n✅ Found {len(docs)} documents in database")
        
        # Test serializing each document
        successful = 0
        failed = []
        
        for i, doc in enumerate(docs):
            try:
                doc_out = DocumentOut(
                    id=doc.id,
                    file_name=doc.file_name,
                    file_path=doc.file_path,
                    modality=doc.modality,
                    summary=doc.summary or "",
                    keywords=doc.keywords or [],
                    num_chunks=doc.num_chunks or 0,
                )
                # Convert to dict to test JSON serialization
                _ = doc_out.model_dump()
                successful += 1
                if i < 5:
                    print(f"  ✅ {doc.file_name} (id={doc.id})")
            except Exception as e:
                failed.append((doc.id, doc.file_name, str(e)))
                print(f"  ❌ {doc.file_name} (id={doc.id}): {e}")
        
        print(f"\n📊 Results:")
        print(f"  Successful: {successful}/{len(docs)}")
        print(f"  Failed: {len(failed)}")
        
        if failed:
            print(f"\n❌ Failed documents:")
            for doc_id, file_name, error in failed:
                print(f"  - {file_name} (id={doc_id}): {error}")
        else:
            print(f"\n✅ All documents serialized successfully!")
            
            # Test JSON encoding the whole list
            print(f"\nTesting JSON encoding of all documents...")
            import json
            all_docs = [
                DocumentOut(
                    id=d.id,
                    file_name=d.file_name,
                    file_path=d.file_path,
                    modality=d.modality,
                    summary=d.summary or "",
                    keywords=d.keywords or [],
                    num_chunks=d.num_chunks or 0,
                ).model_dump()
                for d in docs
            ]
            json_str = json.dumps(all_docs)
            print(f"✅ JSON encoding successful! Size: {len(json_str)} bytes")
            print(f"First document: {json.dumps(all_docs[0], indent=2)}")
            
    finally:
        session.close()

if __name__ == "__main__":
    test_document_serialization()
