import requests, json
r = requests.post('http://localhost:8000/sources_list', timeout=10)
d = r.json()
for s in d['data']:
    name = s['fileName'][:50]
    sc = s['processed_chunk']
    tc = s['total_chunks']
    print(f"{name} | {s['status']} | chunks={sc}/{tc} | nodes={s['nodeCount']} | rels={s['relationshipCount']} | {s['processingTime']}s")
