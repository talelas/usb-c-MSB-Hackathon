"""Test hybrid graph-augmented search capabilities."""
import requests
import json

BASE_URL = 'http://localhost:8000/api'

print('='*70)
print('🔬 TESTING HYBRID GRAPH-AUGMENTED RAG')
print('='*70)

test_queries = [
    "What is epigenetics?",
    "Tell me about autonomous cars",
    "Explain machine learning",
]

for query in test_queries:
    print(f'\n{"─"*70}')
    print(f'Query: "{query}"')
    print('─'*70)
    
    # Test search endpoint
    r = requests.post(f'{BASE_URL}/search', json={'query': query, 'top_k': 5})
    if r.status_code == 200:
        results = r.json()['results']
        print(f'\n📊 Search Results: {len(results)} documents')
        for i, res in enumerate(results[:3], 1):
            print(f'\n  {i}. {res["file_name"]} (score: {res["final_score"]:.3f})')
            print(f'     └─ Semantic: {res["semantic_score"]:.3f}, '
                  f'Centrality: {res["centrality_score"]:.3f}, '
                  f'Temporal: {res["temporal_score"]:.3f}')
            if res.get('chunk_text') and res['chunk_text'].strip():
                print(f'     └─ "{res["chunk_text"][:80]}..."')
    
    # Test chat endpoint
    r = requests.post(f'{BASE_URL}/chat', json={
        'query': query, 
        'session_id': 'hybrid_test',
        'top_k': 8,
        'temperature': 0.5
    })
    if r.status_code == 200:
        result = r.json()
        print(f'\n💬 RAG Answer:')
        print(f'   {result["answer"]}')
        print(f'\n   📚 Sources: {len(result["sources"])} documents used')
    
    print()

print('='*70)
print('✅ Hybrid search test complete!')
print('='*70)
