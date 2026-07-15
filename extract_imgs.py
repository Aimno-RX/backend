import os, sys
sys.path.insert(0, '.')
from src.image_processor import extract_images_from_docx

file_path = r'C:\Users\JSJ\xwechat_files\wxid_kngvfm4spkj422_1a7f\msg\file\2026-04\《颈椎胸椎功能强化训练》已整理完毕.docx'
out_dir = r'C:\Users\JSJ\Desktop\backend-fix-backend-chase\extracted_images'
os.makedirs(out_dir, exist_ok=True)

images = extract_images_from_docx(file_path, max_total=200)
print(f'Extracted {len(images)} images')

for img in images:
    ext = img['extension']
    if ext == 'jpeg':
        ext = 'jpg'
    fname = f'img_{img["index"]:03d}_p{img["paragraph_index"]}.{ext}'
    fpath = os.path.join(out_dir, fname)
    with open(fpath, 'wb') as f:
        f.write(img['image_bytes'])
    size_kb = len(img['image_bytes']) / 1024
    print(f'  [{img["index"]}] {fname} ({size_kb:.1f} KB)')

print(f'\nSaved to: {out_dir}')
