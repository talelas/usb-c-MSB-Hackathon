"""Test RAG pipeline - search and chat."""
import requests
import json

BASE_URL = 'http://localhost:8000/api'

print('='*60)
print('📊 CHECKING INGESTION RESULTS')
print('='*60)

# 1. Get all documents
r = requests.get(f'{BASE_URL}/documents')
docs = r.json() if isinstance(r.json(), list) else r.json().get('documents', [])
print(f'\n✅ Total documents ingested: {len(docs)}')

# Show sample with images
print('\n📸 Sample with image captions:')
for doc in [d for d in docs if d['modality'] == 'image'][:3]:
    print(f"\n  ID {doc['id']}: {doc['file_name']}")
    print(f"  Chunks: {doc['num_chunks']}")
    if doc.get('image_caption'):
        print(f"  Caption: {doc['image_caption'][:150]}...")

print('\n'+'='*60)
print('🔍 TESTING SEMANTIC SEARCH')
print('='*60)

# 2. Test search
search_query = "What are autonomous cars?"
print(f'\nQuery: "{search_query}"')
r = requests.post(f'{BASE_URL}/search', json={'query': search_query, 'top_k': 3})
if r.status_code == 200:
    results = r.json()
    print(f'\n✅ Found {len(results["results"])} results:')
    for i, res in enumerate(results['results'][:3], 1):
        print(f'\n  {i}. Score: {res["final_score"]:.3f}')
        print(f'     File: {res["file_name"]}')
        if res.get('chunk_text'):
            print(f'     Text: {res["chunk_text"][:100]}...')
else:
    print(f'❌ Search failed: {r.status_code}')

print('\n'+'='*60)
print('💬 TESTING RAG CHAT')
print('='*60)

# 3. Test chat (RAG)
chat_query = "Explain what epigenetics is in 2 sentences."
print(f'\nQuery: "{chat_query}"')
r = requests.post(f'{BASE_URL}/chat', json={'query': chat_query, 'session_id': 'test_session'})
if r.status_code == 200:
    result = r.json()
    print(f'\n✅ RAG Response:')
    print(f'   {result["answer"]}')
    print(f'\n   Sources: {len(result["sources"])} documents')
else:
    print(f'❌ Chat failed: {r.status_code}')

print('\n'+'='*60)
