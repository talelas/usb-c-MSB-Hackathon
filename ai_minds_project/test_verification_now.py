"""Quick test script for relevance verification with your ingested data."""
import sys
sys.path.insert(0, '.')

from app.llm.rag import answer
from app.graph.builder import load_all
from app.llm.ollama_client import is_available

print("=" * 70)
print(" Testing RAG Document Relevance Verification ".center(70))
print("=" * 70)

# 1. Check Ollama
print("\n[1/4] Checking Ollama server...")
if is_available():
    print("✓ Ollama is running")
else:
    print("✗ Ollama is NOT running. Start it with: ollama serve")
    sys.exit(1)

# 2. Load graphs
print("\n[2/4] Loading knowledge graphs...")
try:
    kw_graph, sem_graph = load_all()
    print(f"✓ Loaded graphs: {len(kw_graph.nodes())} keyword nodes, {len(sem_graph.nodes())} semantic nodes")
except Exception as e:
    print(f"✗ Error loading graphs: {e}")
    print("Run ingestion first if you haven't: python ingest_directory.py")
    sys.exit(1)

# 3. Test query WITHOUT verification
print("\n[3/4] Testing WITHOUT verification (default)...")
print("-" * 70)
query = "What is a neural network?"
print(f"Query: {query}\n")

result1 = answer(
    query=query,
    kw_graph=kw_graph,
    sem_graph=sem_graph,
    session_id="test_no_verify",
    top_k=5,
    verify_relevance=False,  # Disabled
    min_confidence=0.0,
)

print(f"Answer: {result1['answer'][:300]}...\n")
print(f"Sources used: {len(result1['sources'])}")
for i, src in enumerate(result1['sources'], 1):
    print(f"  {i}. {src['file_name']} (score: {src['score']:.3f})")

# 4. Test query WITH verification
print("\n" + "=" * 70)
print("[4/4] Testing WITH VERIFICATION enabled...")
print("-" * 70)
print(f"Query: {query}\n")

result2 = answer(
    query=query,
    kw_graph=kw_graph,
    sem_graph=sem_graph,
    session_id="test_with_verify",
    top_k=5,
    verify_relevance=True,   # ← ENABLED!
    min_confidence=0.4,      # Documents below 0.4 will be verified
)

print(f"Answer: {result2['answer'][:300]}...\n")
print(f"Verified sources: {len(result2['sources'])}")
for i, src in enumerate(result2['sources'], 1):
    verified_badge = "✓" if src.get('verified') else ""
    print(f"  {i}. {src['file_name']} (score: {src['score']:.3f}) {verified_badge}")

# Show comparison
print("\n" + "=" * 70)
print(" COMPARISON ".center(70))
print("=" * 70)
print(f"Without verification: {len(result1['sources'])} documents used")
print(f"With verification:    {len(result2['sources'])} documents used")

filtered = len(result1['sources']) - len(result2['sources'])
if filtered > 0:
    print(f"\n✓ Filtered out {filtered} irrelevant document(s)!")
elif filtered < 0:
    print(f"\n⚠ Note: More docs after verification (edge case)")
else:
    print(f"\n→ Same number of documents (all were relevant)")

print("\n" + "=" * 70)
print("\nTry different queries to see how verification filters documents:")
print("  - Specific queries: 'How does backpropagation work?'")
print("  - Broad queries: 'Tell me about AI'")
print("  - Off-topic queries: 'What is climate change?'")
print("\nEdit this script to test your own queries!")
