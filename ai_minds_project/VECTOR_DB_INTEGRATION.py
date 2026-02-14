"""Guide: Using Output Embeddings with Vector Databases"""

# ============================================================
# 🎯 Vector Database Integration Guide
# ============================================================

"""
The system outputs embeddings in a format ready for any vector database.
Choose based on your needs:
"""

# ============================================================
# OPTION 1: Qdrant (Recommended for Production)
# ============================================================

"""
Installation:
  pip install qdrant-client

Usage:
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import json

def load_embeddings_to_qdrant():
    # Initialize Qdrant client
    client = QdrantClient(":memory:")  # Use :memory: for demo, or "localhost:6333" for server
    
    # Load embeddings from our export
    with open("output/embeddings_only.json") as f:
        embeddings_data = json.load(f)
    
    collection_name = "ai_minds_memory"
    
    # Create collection
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        # For Ollama embeddings (3072 dims):
        # vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
    )
    
    # Prepare points
    points = []
    for item in embeddings_data:
        point = PointStruct(
            id=f"{item['doc_id']}_{item['chunk_index']}",
            vector=item['embedding'],
            payload={
                'doc_id': item['doc_id'],
                'file_name': item['file_name'],
                'chunk_index': item['chunk_index'],
                'text': item['chunk_text'],
                'keywords': item['keywords'],
                'modality': item['modality']
            }
        )
        points.append(point)
    
    # Upload to Qdrant
    client.upsert(
        collection_name=collection_name,
        points=points,
    )
    
    print(f"✓ Loaded {len(points)} vectors to Qdrant")
    return client


def semantic_search_qdrant(client, query_embedding, query_text):
    # Search similar documents
    results = client.search(
        collection_name="ai_minds_memory",
        query_vector=query_embedding,
        query_filter=None,  # Or add filter: models.Filter(must=[...])
        limit=5,
        score_threshold=0.7
    )
    
    print(f"\n🔍 Query: {query_text}")
    print(f"Found {len(results)} similar results:\n")
    
    for result in results:
        payload = result.payload
        print(f"Score: {result.score:.2f}")
        print(f"File: {payload['file_name']}")
        print(f"Text: {payload['text'][:100]}...")
        print(f"Keywords: {payload['keywords']}\n")


# ============================================================
# OPTION 2: Weaviate (Great for Complex Queries)
# ============================================================

"""
Installation:
  pip install weaviate-client

Usage:
"""

# from weaviate import Client
# from weaviate.util import generate_uuid5
# import json

# def load_embeddings_to_weaviate():
#     # Connect to Weaviate
#     client = Client("http://localhost:8080")
#     
#     # Create class
#     class_obj = {
#         "class": "AIMindMemory",
#         "properties": [
#             {"name": "fileName", "dataType": ["string"]},
#             {"name": "text", "dataType": ["text"]},
#             {"name": "keywords", "dataType": ["string[]"]},
#             {"name": "modality", "dataType": ["string"]},
#             {"name": "docId", "dataType": ["int"]},
#        ]
#     }
#     
#     client.schema.create_class(class_obj)
#     
#     # Load embeddings
#     with open("output/embeddings_only.json") as f:
#         embeddings_data = json.load(f)
#     
#     # Upload to Weaviate
#     for item in embeddings_data:
#         object_uuid = generate_uuid5(f"{item['doc_id']}_{item['chunk_index']}")
#         
#         client.data_object.create(
#             class_name="AIMindMemory",
#             data_object={
#                 "fileName": item['file_name'],
#                 "text": item['chunk_text'],
#                 "keywords": item['keywords'],
#                 "modality": item['modality'],
#                 "docId": item['doc_id'],
#             },
#             vector=item['embedding'],
#             uuid=object_uuid
#         )
#     
#     print(f"✓ Loaded {len(embeddings_data)} vectors to Weaviate")


# ============================================================
# OPTION 3: LanceDB (Fast, Simple, Local)
# ============================================================

"""
Installation:
  pip install lancedb

Usage:
"""

# import lancedb
# import json
# import pyarrow as pa

# def load_embeddings_to_lancedb():
#     # Connect to LanceDB
#     db = lancedb.connect("./lancedb")
#     
#     # Load embeddings
#     with open("output/embeddings_only.json") as f:
#         data = json.load(f)
#     
#     # Prepare table
#     table_data = {
#         "id": [f"{item['doc_id']}_{item['chunk_index']}" for item in data],
#         "embedding": [item['embedding'] for item in data],
#         "text": [item['chunk_text'] for item in data],
#         "file_name": [item['file_name'] for item in data],
#         "keywords": [",".join(item['keywords']) for item in data],
#         "modality": [item['modality'] for item in data],
#     }
#     
#     # Create table
#     table = db.create_table("ai_minds", data=table_data, mode="overwrite")
#     
#     print(f"✓ Loaded {len(data)} vectors to LanceDB")
#     
#     # Search example
#     results = table.search(query_embedding).limit(5).to_list()
#     print(f"Found {len(results)} results")


# ============================================================
# OPTION 4: Pinecone (Managed Cloud Service)
# ============================================================

"""
Installation:
  pip install pinecone-client

Setup:
  1. Create account at pinecone.io
  2. Create index with dimension 384
  3. Get API key

Usage:
"""

# from pinecone import Pinecone
# import json

# def load_embeddings_to_pinecone(api_key, index_name):
#     # Initialize Pinecone
#     pc = Pinecone(api_key=api_key)
#     index = pc.Index(index_name)
#     
#     # Load embeddings
#     with open("output/embeddings_only.json") as f:
#         embeddings_data = json.load(f)
#     
#     # Prepare vectors
#     vectors = []
#     for item in embeddings_data:
#         vectors.append((
#             f"{item['doc_id']}_{item['chunk_index']}",
#             item['embedding'],
#             {
#                 'file_name': item['file_name'],
#                 'text': item['chunk_text'],
#                 'keywords': item['keywords'],
#                 'modality': item['modality']
#            }
#         ))
#     
#     # Upsert to Pinecone
#     index.upsert(vectors)
#     
#     print(f"✓ Loaded {len(vectors)} vectors to Pinecone")


# ============================================================
# Common Patterns
# ============================================================

"""
1. SEMANTIC SEARCH:
   - Query text → embed → search in vector DB → retrieve similar results

2. RETRIEVAL-AUGMENTED GENERATION (RAG):
   - User question → search memory → retrieve relevant chunks
   - → Pass to LLM with context → generate informed response

3. METADATA FILTERING:
   - Search by file name, keywords, modality
   - Combine vector similarity + metadata filters

4. INCREMENTAL INDEXING:
   - New files processed → new vectors generated
   - Upsert to vector DB (updates existing, adds new)

5. HYBRID SEARCH:
   - Combine semantic similarity (vector) + keyword search
   - Re-rank by relevance
"""

# ============================================================
# Production Setup Example
# ============================================================

"""
Production architecture:

┌─────────────────────────────────────┐
│  AI Minds Processing Pipeline       │
│  (generates embeddings)             │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│  Vector Database (Qdrant/Weaviate)  │
│  - Stores embeddings                │
│  - Enables semantic search          │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│  RAG Service                        │
│  - Retrieves relevant chunks        │
│  - Combines with LLM                │
│  - Generates responses              │
└─────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│  User Application                   │
│  - Web UI / API / Chat Interface    │
└─────────────────────────────────────┘

Data flow:
  1. Files → AI Minds → embeddings_only.json
  2. embeddings_only.json → Qdrant/other DB
  3. User query → Embed → Search → Retrieve
  4. Retrieved docs + queries → LLM → Response
"""

if __name__ == "__main__":
    print(__doc__)
    print("\nRun specific database examples above by uncommenting")
