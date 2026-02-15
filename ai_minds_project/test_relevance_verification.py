"""Test script for document relevance verification.

This demonstrates how the relevance verification system works.
Run this after starting your Ollama server and FastAPI application.
"""
import requests

# Configuration
API_BASE = "http://localhost:8000/api"

def test_without_verification():
    """Test RAG without relevance verification (default behavior)."""
    print(" Testing WITHOUT relevance verification ".center(60, "="))
    
    response = requests.post(
        f"{API_BASE}/chat",
        json={
            "query": "What is machine learning?",
            "session_id": "test_no_verify",
            "top_k": 5,
            "temperature": 0.5,
            "verify_relevance": False,  # Disabled (default)
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nQuery: What is machine learning?")
        print(f"Answer: {data['answer'][:200]}...")
        print(f"\nSources used: {len(data['sources'])}")
        for i, source in enumerate(data['sources'], 1):
            print(f"  {i}. {source['file_name']} (score: {source['score']:.3f})")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def test_with_verification():
    """Test RAG with LLM-based relevance verification."""
    print("\n" + " Testing WITH relevance verification ".center(60, "="))
    
    response = requests.post(
        f"{API_BASE}/chat",
        json={
            "query": "What is machine learning?",
            "session_id": "test_with_verify",
            "top_k": 5,
            "temperature": 0.5,
            "verify_relevance": True,  # Enabled - LLM will verify each document
            "min_confidence": 0.3,  # Documents below this score will be verified
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nQuery: What is machine learning?")
        print(f"Answer: {data['answer'][:200]}...")
        print(f"\nSources used after verification: {len(data['sources'])}")
        for i, source in enumerate(data['sources'], 1):
            print(f"  {i}. {source['file_name']} (score: {source['score']:.3f})")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def test_direct_verification():
    """Test the verification function directly (for debugging)."""
    print("\n" + " Direct Verification Test ".center(60, "="))
    
    from app.llm.ollama_client import verify_relevance
    
    # Example: relevant document
    query = "What is neural network?"
    relevant_doc = """
    A neural network is a computational model inspired by biological neurons.
    It consists of interconnected layers of nodes that process information
    through weighted connections. Neural networks are fundamental to deep learning.
    """
    
    irrelevant_doc = """
    Climate change refers to long-term shifts in global weather patterns.
    It is primarily caused by human activities that increase greenhouse gas emissions.
    The effects include rising temperatures and extreme weather events.
    """
    
    print(f"\nQuery: {query}\n")
    
    print("Testing RELEVANT document:")
    print(f"Document: {relevant_doc[:80]}...")
    result1 = verify_relevance(query, relevant_doc)
    print(f"Result: {'✓ RELEVANT' if result1 else '✗ NOT RELEVANT'}\n")
    
    print("Testing IRRELEVANT document:")
    print(f"Document: {irrelevant_doc[:80]}...")
    result2 = verify_relevance(query, irrelevant_doc)
    print(f"Result: {'✓ RELEVANT' if result2 else '✗ NOT RELEVANT'}")


if __name__ == "__main__":
    print("\n" + " RAG Relevance Verification Test Suite ".center(60, "="))
    print("\nMake sure your services are running:")
    print("  1. Ollama server (ollama serve)")
    print("  2. FastAPI app (uvicorn app.main:app)")
    print("  3. Qdrant, PostgreSQL, Redis\n")
    
    try:
        # Check if API is available
        health = requests.get(f"{API_BASE}/health", timeout=5)
        if health.status_code == 200:
            print("✓ API is online\n")
            
            # Run API tests
            test_without_verification()
            test_with_verification()
            
            # Run direct verification test (requires imports)
            print("\n\nTo test verification directly without API:")
            print("  python -c 'from test_relevance_verification import test_direct_verification; test_direct_verification()'")
            
        else:
            print("✗ API health check failed")
            
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API. Make sure it's running.")
    except Exception as e:
        print(f"✗ Error: {e}")
