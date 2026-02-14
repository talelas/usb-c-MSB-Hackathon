import json
from typing import Dict, Any, Optional
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, ExactMatchFilter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

# --- Configuration ---
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "multimodal_mind"
LLM_MODEL = "llama3.2:3b"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# --- 1. Initialize Global Settings ---
# Using a local cache directory to avoid issues with temp files
Settings.embed_model = FastEmbedEmbedding(model_name=EMBED_MODEL, cache_dir="./fastembed_cache")
Settings.llm = Ollama(model=LLM_MODEL, request_timeout=300.0, context_window=4096)

def extract_query_intent(query: str) -> Dict[str, Any]:
    """
    Query Router:
    Analyzing the user's natural language query to extract potential metadata filters.
    Returns a dictionary of filters (e.g., {"category": "tech"}).
    """
    prompt = (
        f"Analyze the user query for specific metadata constraints. "
        f"Available metadata fields are: 'category', 'people' (names), 'topics'. "
        f"For 'topics', extract key subjects in lowercase (e.g., 'cooking', 'ai'). "
        f"Return ONLY a JSON object with the extracted filters. "
        f"User Query: '{query}'\n\n"
        f"JSON:\n"
    )
    
    response = Settings.llm.complete(prompt)
    response_text = response.text.strip()
    
    # Robust JSON parsing
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    
    try:
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            return {}
    except json.JSONDecodeError:
        return {}

def construct_metadata_filters(extracted_filters: Dict[str, Any]) -> Optional[MetadataFilters]:
    """
    Dynamic Metadata Construction:
    Converts a raw dictionary of filters into LlamaIndex MetadataFilters.
    We prioritize ExactMatchFilter for strict filtering.
    """
    filters_list = []
    
    for key, value in extracted_filters.items():
        if value:
            # Handle list values (e.g., "people": ["Elon Musk"]) - take the first primarily for simplicity
            # OR loop through them. Here we'll take the first non-empty value for strict filtering.
            val_to_filter = value[0] if isinstance(value, list) and len(value) > 0 else value
            
            if val_to_filter:
                filters_list.append(
                    ExactMatchFilter(key=key, value=val_to_filter)
                )

    if not filters_list:
        return None
        
    return MetadataFilters(filters=filters_list)

def hybrid_search_pipeline(query: str):
    """
    Flow 2: Retrieval (Hybrid + Dynamic Filtering + Fallback)
    """
    print(f"\nProcessing User Query: '{query}'")

    # --- Step 1: Query Routing (Intent Extraction) ---
    intent_filters = extract_query_intent(query)
    print(f"  -> Extracted Intent Filters: {intent_filters}")
    
    llama_filters = construct_metadata_filters(intent_filters)
    
    # --- Step 2: Initialize Vector Store (Connection) ---
    client = qdrant_client.QdrantClient(url=QDRANT_URL)
    vector_store = QdrantVectorStore(
        client=client, 
        collection_name=COLLECTION_NAME,
        enable_hybrid=True, # Critical for RRF
        fastembed_sparse_model="Qdrant/bm25"
    )
    
    # Load index from existing vector store
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

    # --- Step 3: Configure Retrieval Engine ---
    # vector_store_query_mode="hybrid": Enables the combination of Dense + Sparse search
    # alpha: Weight for dense vs sparse (0.5 is balanced, but Qdrant handles RRF automatically if supported)
    # response_mode="compact": Concatenates retrieved chunks for LLM context
    
    query_engine = index.as_query_engine(
        vector_store_query_mode="hybrid", 
        sparse_top_k=10, 
        similarity_top_k=5,
        filters=llama_filters,  # Apply dynamic filters first
    )
    
    # --- Step 4: Execution with Fallback Logic ---
    print("  -> Running Hybrid Search with Filters...")
    response = query_engine.query(query)
    
    # Check if we got any source nodes (retrieved documents)
    if not response.source_nodes and llama_filters is not None:
        print("  -> [FALLBACK TRIGGERED] No results found with strict filters. Dropping filters and retrying...")
        
        # Re-create engine without filters
        fallback_query_engine = index.as_query_engine(
            vector_store_query_mode="hybrid",
            sparse_top_k=10,
            similarity_top_k=5,
            filters=None  # Clear filters
        )
        response = fallback_query_engine.query(query)

    return response

if __name__ == "__main__":
    # Example Queries to Test Logic
    test_queries = [
        "What did Elon Musk say about rockets?",   # Should trigger 'people': 'Elon Musk' filter
        "Tell me about cooking apples.",         # Should trigger 'category': 'cooking' or topic
        "General artificial intelligence news."   # Broad query, might have 'category': 'tech'
    ]

    for q in test_queries:
        result = hybrid_search_pipeline(q)
        print(f"  -> LLM Final Answer: {str(result)}")
        
        # Display Sources
        if hasattr(result, 'source_nodes') and result.source_nodes:
            print("\n  -> Sources Used:")
            for node in result.source_nodes:
                md = node.metadata
                print(f"     - File: {md.get('file_name', 'Unknown')}")
                print(f"       Modified: {md.get('last_modified', 'Unknown')}")
                # print(f"       Relevance: {node.score:.4f}") # Optional
        print(f"\n{'-'*50}")
