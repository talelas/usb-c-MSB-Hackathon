import json
import os
import datetime
from typing import List, Dict, Any
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

# --- Configuration ---
# Ensure you have Qdrant running locally (e.g., via Docker: docker run -p 6333:6333 qdrant/qdrant)
# Ensure you have Ollama running with Llama-3.2:3b (ollama run llama3.2)
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "multimodal_mind"
LLM_MODEL = "llama3.2:3b"  # Adjust if your local model tag differs
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# --- 1. Initialize Global Settings ---
# We use FastEmbed for local, high-performance dense embeddings
# Using a local cache directory to avoid issues with temp files
Settings.embed_model = FastEmbedEmbedding(model_name=EMBED_MODEL, cache_dir="./fastembed_cache")
# We use Ollama for the LLM
Settings.llm = Ollama(model=LLM_MODEL, request_timeout=300.0, context_window=4096)

def extract_metadata_with_llm(text_chunk: str) -> Dict[str, Any]:
    """
    Cognitive Processing Layer:
    Uses the local LLM to analyze text and extract structured metadata.
    Returns a JSON dictionary.
    """
    prompt = (
        f"Analyze the following text and extract metadata in strict JSON format. "
        f"Fields to extract: 'category', 'people' (list of names), 'topics' (list of key topics). "
        f"Use lowercase for 'category' and 'topics'. "
        f"If no people are mentioned, return an empty list []. "
        f"Do not output anything else other than the JSON object.\n\n"
        f"Text: {text_chunk}\n\n"
        f"JSON:"
    )
    
    response = Settings.llm.complete(prompt)
    response_text = response.text.strip()
    
    # Basic cleaning to ensure we get just the JSON part if the model chats a bit
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    
    try:
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            print("Warning: Could not parse JSON from LLM response.")
            return {}
    except json.JSONDecodeError:
        print("Warning: JSON decode error.")
        return {}

def ingest_data(data_folder: str):
    """
    Main Ingestion Flow:
    1. Reads files from data folder.
    2. Extracts Metadata (Ollama) + File System Metadata.
    3. Indexes into Qdrant.
    """
    client = qdrant_client.QdrantClient(url=QDRANT_URL)
    vector_store = QdrantVectorStore(
        client=client, 
        collection_name=COLLECTION_NAME,
        enable_hybrid=True,
        fastembed_sparse_model="Qdrant/bm25"
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    llama_docs = []
    
    print("--- Starting Ingestion Pipeline ---")
    
    # Iterate over files in the data folder
    for filename in os.listdir(data_folder):
        file_path = os.path.join(data_folder, filename)
        
        if not os.path.isfile(file_path) or not filename.endswith(".txt"):
            continue

        print(f"Processing File: {filename}...")
        
        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Get File Metadata
        stats = os.stat(file_path)
        last_modified = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

        # A. Cognitive Step: Extract Metadata
        extracted_metadata = extract_metadata_with_llm(text)
        
        # Merge File Metadata
        extracted_metadata["file_name"] = filename
        extracted_metadata["last_modified"] = last_modified
        
        print(f"  -> Extracted Metadata: {extracted_metadata}")
        
        # C. Create Document
        doc = Document(
            text=text,
            metadata=extracted_metadata,
            excluded_llm_metadata_keys=["people", "topics", "file_name", "last_modified"], 
            excluded_embed_metadata_keys=["people", "file_name", "last_modified"] 
        )
        llama_docs.append(doc)

    if not llama_docs:
        print("No documents found in data folder!")
        return

    # --- 3. Indexing ---
    print("Indexing documents into Qdrant...")
    index = VectorStoreIndex.from_documents(
        llama_docs,
        storage_context=storage_context,
    )
    
    print(f"Successfully indexed {len(llama_docs)} documents.")
    return index

if __name__ == "__main__":
    # Point to the data directory
    data_dir = "./data"
    
    # Ensure data directory exists
    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found.")
    else:
        ingest_data(data_dir)
