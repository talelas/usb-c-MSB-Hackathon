"""Storage system for metadata and embeddings"""
import json
import csv
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class MetadataStorage:
    """Store and retrieve metadata + embeddings"""
    
    def __init__(self, json_path: str, csv_path: str):
        """Initialize storage"""
        self.json_path = Path(json_path)
        self.csv_path = Path(csv_path)
        
        # Create parent directories
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing data if available
        self.data = self._load_json()
    
    def _load_json(self) -> Dict:
        """Load existing JSON data"""
        if self.json_path.exists():
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'documents': []}
    
    def add_document(self, processed_data: Dict) -> None:
        """Add processed document to storage"""
        doc_entry = {
            'id': len(self.data['documents']) + 1,
            'timestamp': str(datetime.now().isoformat()),
            'file_metadata': processed_data['file_metadata'],
            'text_summary': processed_data['text_summary'],
            'keywords': processed_data['keywords'],
            'num_chunks': processed_data['num_chunks'],
            'embedding_model': processed_data['embedding_model'],
            'embedding_dimension': processed_data['embedding_dimension'],
            'chunks': processed_data['chunks']
        }
        
        self.data['documents'].append(doc_entry)
        print(f"✓ Added document: {processed_data['file_metadata'].get('file_name', 'unknown')}")
    
    def save_json(self) -> None:
        """Save all data to JSON"""
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)
        print(f"✓ Saved to JSON: {self.json_path}")
    
    def save_csv(self) -> None:
        """Save metadata to CSV (without embeddings for readability)"""
        if not self.data['documents']:
            print("⚠ No documents to save to CSV")
            return
        
        rows = []
        for doc in self.data['documents']:
            file_meta = doc['file_metadata']
            caption = file_meta.get('caption', '')
            transcript = file_meta.get('transcript', '')
            
            row = {
                'doc_id': doc['id'],
                'file_name': file_meta.get('file_name', ''),
                'file_path': file_meta.get('file_path', ''),
                'modality': file_meta.get('modality', ''),
                'file_size_bytes': file_meta.get('file_size_bytes', ''),
                'file_timestamp': file_meta.get('timestamp', ''),
                'file_extension': file_meta.get('file_extension', ''),
                'image_caption': caption[:200],
                'audio_transcript': transcript[:200],
                'summary': doc['text_summary'][:200],  # Truncate for readability
                'keywords': ', '.join(doc['keywords']),
                'num_chunks': doc['num_chunks'],
                'embedding_dimension': doc['embedding_dimension'],
                'processed_timestamp': doc['timestamp']
            }
            rows.append(row)
        
        if rows:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            
            print(f"✓ Saved to CSV: {self.csv_path}")
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        total_docs = len(self.data['documents'])
        total_chunks = sum(doc['num_chunks'] for doc in self.data['documents'])
        modalities = {}
        
        for doc in self.data['documents']:
            modality = doc['file_metadata'].get('modality', 'unknown')
            modalities[modality] = modalities.get(modality, 0) + 1
        
        return {
            'total_documents': total_docs,
            'total_chunks': total_chunks,
            'modalities': modalities,
            'storage_path_json': str(self.json_path),
            'storage_path_csv': str(self.csv_path)
        }
    
    def print_summary(self) -> None:
        """Print summary to console"""
        summary = self.get_summary()
        print("\n" + "="*50)
        print("📊 STORAGE SUMMARY")
        print("="*50)
        print(f"Total Documents: {summary['total_documents']}")
        print(f"Total Chunks: {summary['total_chunks']}")
        print(f"Modalities: {summary['modalities']}")
        print(f"JSON Storage: {summary['storage_path_json']}")
        print(f"CSV Storage: {summary['storage_path_csv']}")
        print("="*50 + "\n")
    
    def export_embeddings_only(self, output_path: str) -> None:
        """Export just embeddings for vector DB ingestion"""
        embeddings_data = []
        
        for doc in self.data['documents']:
            file_name = doc['file_metadata'].get('file_name', 'unknown')
            
            for chunk in doc['chunks']:
                embeddings_data.append({
                    'doc_id': doc['id'],
                    'file_name': file_name,
                    'chunk_index': chunk['chunk_index'],
                    'chunk_text': chunk['text'][:200],  # Preview text
                    'embedding': chunk['embedding'],
                    'keywords': doc['keywords'],
                    'modality': doc['file_metadata'].get('modality', '')
                })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, indent=2)
        
        print(f"✓ Exported embeddings: {output_path}")


class MemoryIndex:
    """Index for fast retrieval"""
    
    def __init__(self, storage: MetadataStorage):
        """Initialize index"""
        self.storage = storage
        self.build_index()
    
    def build_index(self) -> None:
        """Build index from storage"""
        self.file_index = {}
        self.modality_index = {}
        
        for doc in self.storage.data['documents']:
            file_name = doc['file_metadata'].get('file_name', '')
            modality = doc['file_metadata'].get('modality', '')
            
            self.file_index[file_name] = doc['id']
            
            if modality not in self.modality_index:
                self.modality_index[modality] = []
            self.modality_index[modality].append(doc['id'])
    
    def find_by_file(self, file_name: str) -> List[Dict]:
        """Find documents by file name"""
        results = []
        for doc in self.storage.data['documents']:
            if doc['file_metadata'].get('file_name') == file_name:
                results.append(doc)
        return results
    
    def find_by_modality(self, modality: str) -> List[Dict]:
        """Find documents by modality"""
        results = []
        for doc in self.storage.data['documents']:
            if doc['file_metadata'].get('modality') == modality:
                results.append(doc)
        return results
    
    def find_by_keyword(self, keyword: str) -> List[Dict]:
        """Find documents containing keyword"""
        results = []
        keyword_lower = keyword.lower()
        
        for doc in self.storage.data['documents']:
            keywords = [k.lower() for k in doc['keywords']]
            if any(keyword_lower in k for k in keywords):
                results.append(doc)
        
        return results
