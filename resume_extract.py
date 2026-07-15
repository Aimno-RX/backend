import requests
import json

file_name = '《颈椎胸椎功能强化训练》已整理完毕.docx'
print(f'Resuming extraction: {file_name}')
r = requests.post('http://localhost:8000/extract',
    data={
        'file_name': file_name,
        'source_type': 'local file',
        'model': 'deepseek_chat',
        'language': 'zh',
        'retry_condition': 'start_from_last_processed_position'
    },
    timeout=900)
print(f'Status: {r.status_code}')
d = r.json()
print(f"Result: {d['status']}")
if 'data' in d:
    data = d['data']
    print(f"Nodes: {data.get('nodeCount', '?')}")
    print(f"Rels: {data.get('relationshipCount', '?')}")
    print(f"Time: {data.get('total_processing_time', '?')}s")
    print(f"Chunks: {data.get('total_chunks', '?')}")
