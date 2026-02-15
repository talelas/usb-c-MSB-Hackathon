"""
Quick Example: RAG with Document Relevance Verification
========================================================

This shows the simplest way to use the new verification feature.
"""

# Example 1: Using the API (curl)
# ================================

# Without verification (default)
"""
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "verify_relevance": false
  }'
"""

# With verification enabled
"""
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "verify_relevance": true,
    "min_confidence": 0.5
  }'
"""


# Example 2: Using Python requests
# ==================================

import requests

def rag_with_verification():
    """Query RAG with document verification enabled."""
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "query": "How do neural networks learn?",
            "verify_relevance": True,      # ← Enable verification
            "min_confidence": 0.5,          # ← Documents below 0.5 score get verified
            "top_k": 10,
        }
    )
    
    result = response.json()
    print(f"Answer: {result['answer']}")
    print(f"\nVerified sources: {len(result['sources'])}")
    for source in result['sources']:
        print(f"  - {source['file_name']} (score: {source['score']})")


# Example 3: Direct function call (in your code)
# ===============================================

from app.llm.ollama_client import verify_relevance

# Check if a document is relevant
query = "What is deep learning?"
document = "Deep learning uses neural networks with multiple layers..."

is_relevant = verify_relevance(query, document)
print(f"Is relevant: {is_relevant}")  # True or False


# Example 4: Custom RAG call with verification
# =============================================

from app.llm.rag import answer
from app.graph.builder import load_all

# Load graphs
kw_graph, sem_graph = load_all()

# Run RAG with verification
result = answer(
    query="Explain backpropagation",
    kw_graph=kw_graph,
    sem_graph=sem_graph,
    verify_relevance=True,     # Enable verification
    min_confidence=0.6,        # Auto-keep docs with score ≥ 0.6
    top_k=10,
)

print(result["answer"])


# Example 5: Batch verification (for multiple documents)
# =======================================================

from app.llm.ollama_client import verify_relevance

query = "What is linear regression?"
documents = [
    "Linear regression is a statistical method...",
    "The weather today is sunny and warm...",
    "Machine learning models need training data...",
]

# Verify each document
for i, doc in enumerate(documents):
    is_relevant = verify_relevance(query, doc)
    status = "✓ RELEVANT" if is_relevant else "✗ FILTERED"
    print(f"Doc {i+1}: {status}")


if __name__ == "__main__":
    # Quick test
    print("Testing RAG with verification...")
    print("Make sure your services are running!\n")
    
    try:
        rag_with_verification()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("  1. Ollama is running: ollama serve")
        print("  2. API is running: uvicorn app.main:app")
