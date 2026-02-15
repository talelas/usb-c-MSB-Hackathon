"""Test verification with real retrieval results (no full RAG needed)."""
import sys
sys.path.insert(0, '.')

from app.llm.ollama_client import verify_relevance, is_available
from app.graph.builder import load_all
from app.graph.retrieval import retrieve
from app.db.postgres import get_session, get_document

print("=" * 70)
print(" RAG Verification Test with Real Data ".center(70))
print("=" * 70)

# 1. Check Ollama
print("\n[1/3] Checking Ollama...")
if not is_available():
    print("✗ Ollama not running. Start with: ollama serve")
    sys.exit(1)
print("✓ Ollama is running")

# 2. Load graphs
print("\n[2/3] Loading knowledge graphs...")
try:
    kw_graph, sem_graph = load_all()
    print(f"✓ Graphs loaded: {len(kw_graph.nodes())} docs in keyword graph")
    print(f"                 {len(sem_graph.nodes())} docs in semantic graph")
except Exception as e:
    print(f"✗ Error: {e}")
    print("Make sure you've run ingestion first!")
    sys.exit(1)

# 3. Test with real query
print("\n[3/3] Running verification test...")
print("=" * 70)

# Choose a query based on your data
query = "What is a neural network?"
print(f"\nQuery: {query}")

# Retrieve documents
print(f"\nRetrieving top 5 documents...")
try:
    results = retrieve(
        query=query,
        kw_graph=kw_graph,
        sem_graph=sem_graph,
        final_k=5,
    )
    
    if not results:
        print("✗ No documents found. Try a different query or check your ingested data.")
        sys.exit(1)
    
    print(f"✓ Retrieved {len(results)} documents\n")
    
    # Show retrieved docs and verify each
    print("─" * 70)
    print("DOCUMENT VERIFICATION RESULTS:")
    print("─" * 70)
    
    relevant_count = 0
    session = get_session()
    
    for i, result in enumerate(results, 1):
        doc_id = result.get('doc_id')
        score = result.get('final_score', 0)
        
        # Get document details
        try:
            doc = get_document(session, doc_id)
            file_name = doc.file_name if doc else "Unknown"
        except:
            file_name = result.get('file_name', 'Unknown')
        
        # Get text to verify
        doc_text = result.get('chunk_text') or result.get('summary', '')
        if not doc_text:
            print(f"\n{i}. {file_name} (score: {score:.3f})")
            print("   ⚠ No text available to verify")
            continue
        
        # Show document info
        preview = doc_text[:100] + "..." if len(doc_text) > 100 else doc_text
        print(f"\n{i}. {file_name} (score: {score:.3f})")
        print(f"   Preview: {preview}")
        
        # Verify relevance
        print(f"   Verifying...", end="")
        is_relevant = verify_relevance(query, doc_text)
        
        if is_relevant:
            print(" ✓ RELEVANT")
            relevant_count += 1
        else:
            print(" ✗ NOT RELEVANT (would be filtered)")
    
    session.close()
    
    # Summary
    print("\n" + "=" * 70)
    print(" SUMMARY ".center(70))
    print("=" * 70)
    print(f"Retrieved:  {len(results)} documents")
    print(f"Relevant:   {relevant_count} documents")
    print(f"Filtered:   {len(results) - relevant_count} documents")
    
    if relevant_count < len(results):
        print(f"\n✓ Verification would filter out {len(results) - relevant_count} irrelevant document(s)!")
    else:
        print(f"\n→ All retrieved documents are relevant to the query")
    
except Exception as e:
    print(f"✗ Error during retrieval: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("\nTo test with different queries, edit this script or run:")
print("  python test_verification_simple.py  # For basic testing")
print("\nTo use via API, set verify_relevance=true in your request")
