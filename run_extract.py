import requests
import json
import time

file_name = '《颈椎胸椎功能强化训练》已整理完毕.docx'
print(f'Starting extraction: {file_name}')
r = requests.post('http://localhost:8000/extract',
    data={'file_name': file_name, 'source_type': 'local file', 'model': 'deepseek_chat', 'language': 'zh'},
    timeout=900)
print(f'Status: {r.status_code}')
d = r.json()
print(f"Result: {d['status']}")
if 'data' in d:
    print(f"Nodes: {d['data'].get('nodeCount', '?')}")
    print(f"Rels: {d['data'].get('relationshipCount', '?')}")
    print(f"Time: {d['data'].get('total_processing_time', '?')}s")
