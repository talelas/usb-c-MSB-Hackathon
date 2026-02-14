import json
import os
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
Settings.llm = Ollama(model=LLM_MODEL, request_timeout=300.0)

def extract_metadata_with_llm(text_chunk: str) -> Dict[str, Any]:
    """
    Cognitive Processing Layer:
    Uses the local LLM to analyze text and extract structured metadata.
    Returns a JSON dictionary.
    """
    prompt = (
        f"Analyze the following text and extract metadata in strict JSON format. "
        f"Fields to extract: 'category' (e.g., tech, health, finance), "
        f"'people' (list of names), 'topics' (list of key topics). "
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

def ingest_data(documents_content: List[str]):
    """
    Main Ingestion Flow:
    1. Extract metadata for raw text.
    2. Create LlamaIndex Documents.
    3. Index into Qdrant with Hybrid support (Dense + Sparse/BM25).
    """
    
    # --- 2. Initialize Qdrant Client & Vector Store ---
    client = qdrant_client.QdrantClient(url=QDRANT_URL)
    
    # Initialize QdrantVectorStore with Hybrid Search enabled.
    # enable_hybrid=True: Tells LlamaIndex to prepare for hybrid queries.
    # fastembed_sparse_model: Uses the "Qdrant/bm25" model from FastEmbed to generate 
    # sparse vectors on the client side, allowing for keyword-based search in Qdrant.
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        enable_hybrid=True, 
        fastembed_sparse_model="Qdrant/bm25" 
    )
    
    # Store the vector store in a StorageContext
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    llama_docs = []
    
    print("--- Starting Ingestion Pipeline ---")
    
    for text in documents_content:
        print(f"Processing: {text[:30]}...")
        
        # A. Cognitive Step: Extract Metadata
        extracted_metadata = extract_metadata_with_llm(text)
        print(f"  -> Extracted Metadata: {extracted_metadata}")
        
        # B. flatten metadata for easier filtering if needed (e.g. lists to strings? 
        # LlamaIndex MetadataFilters usually work best with exact matches on strings or numbers).
        # For this example, we keep structure but robust systems might flatten 'people' list.
        # We will assume 'category' is a single string for filter simplicity later.
        
        # C. Create Document
        # LlamaIndex will generate the embedding for 'text' automatically during indexing.
        doc = Document(
            text=text,
            metadata=extracted_metadata,
            excluded_llm_metadata_keys=["people", "topics"], # Optional: Exclude from LLM context window to save tokens
            excluded_embed_metadata_keys=["people"] # Optional: Exclude from embedding generation
        )
        llama_docs.append(doc)

    # --- 3. Indexing ---
    # creating the index triggers the embedding generation (Dense) 
    # AND the sparse vector generation (BM25) because of our Qdrant settings.
    print("Indexing documents into Qdrant...")
    index = VectorStoreIndex.from_documents(
        llama_docs,
        storage_context=storage_context,
    )
    
    print(f"Successfully indexed {len(llama_docs)} documents.")
    return index

if __name__ == "__main__":
    # Sample Data (Simulated input from a multimodal parser)
    sample_texts = [
        "Elon Musk announced new updates for the Starship rocket at SpaceX today. The engineering team is optimistic.",
        "The recipe for the perfect apple pie involves cinnamon, nutmeg, and granny smith apples. Cooking time is 45 mins.",
        "Generative AI is transforming the software industry. Jensen Huang discussed NVIDIA's role in this revolution.",
        "New health guidelines suggest walking 10,000 steps a day for better cardiovascular health."
    ]
    
    ingest_data(sample_texts)
