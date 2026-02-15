"""Test search and chat API endpoints."""
import requests
import json

BASE_URL = "http://localhost:8001/api"

print('Testing Search Endpoint...')
r = requests.post(f'{BASE_URL}/search', json={'query': 'What is epigenetics?', 'top_k': 3})
print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'Found {len(data["results"])} results')
    for i, res in enumerate(data['results'][:2], 1):
        print(f'\n  Result {i}: (score: {res["final_score"]:.3f})')
        if res.get('chunk_text'):
            print(f'    {res["chunk_text"][:150]}...')
else:
    print(f'Error: {r.text[:500]}')

print('\n' + '='*60)
print('Testing Chat Endpoint...')
r = requests.post(f'{BASE_URL}/chat', json={'query': 'What is epigenetics?', 'session_id': 'test123'})
print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'Answer: {data["answer"][:300]}...')
    print(f'\nSources: {len(data.get("sources", []))} chunks used')
else:
    print(f'Error: {r.text[:500]}')
