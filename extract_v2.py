import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

file_path = r'E:\xwechat_files\wxid_kngvfm4spkj422_1a7f\msg\file\2026-06\《颈椎胸椎功能强化训练》已整理完毕.docx'
out_dir = r'C:\Users\ASUS\Desktop\backend-fix-backend-chase\extracted_images_v2'
os.makedirs(out_dir, exist_ok=True)

doc = Document(file_path)

nsmap = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
}

# Build image part map
image_part_map = {}
for rel in doc.part.rels.values():
    if "image" in rel.reltype:
        image_part_map[rel.rId] = {
            "blob": rel.target_part.blob,
            "ext": rel.target_part.content_type.split("/")[-1],
        }

# Extract images grouped by paragraph
img_count = 0
small_imgs = []
medium_imgs = []
large_imgs = []

for para_idx, paragraph in enumerate(doc.paragraphs):
    blips = paragraph._element.findall('.//' + etree.QName(nsmap['a'], 'blip').text, nsmap)
    if not blips:
        continue
    
    for blip_idx, blip in enumerate(blips):
        rId = blip.get(etree.QName(nsmap['r'], 'embed').text)
        if rId and rId in image_part_map:
            img_data = image_part_map[rId]
            ext = img_data['ext']
            if ext == 'jpeg': ext = 'jpg'
            if ext == 'x-emf': ext = 'emf'
            size_kb = len(img_data['blob']) / 1024
            
            fname = f'img_{img_count:03d}_p{para_idx}.{ext}'
            fpath = os.path.join(out_dir, fname)
            with open(fpath, 'wb') as f:
                f.write(img_data['blob'])
            
            if size_kb < 50:
                small_imgs.append((fname, size_kb, para_idx))
            elif size_kb < 300:
                medium_imgs.append((fname, size_kb, para_idx))
            else:
                large_imgs.append((fname, size_kb, para_idx))
            
            img_count += 1

print(f'Total images extracted: {img_count}')
print(f'\nSmall images (<50KB): {len(small_imgs)} - exercise demonstration photos')
print(f'Medium images (50-300KB): {len(medium_imgs)} - section illustrations')  
print(f'Large images (>300KB): {len(large_imgs)} - title/header images')

print(f'\n=== LARGE IMAGES (titles/headers) ===')
for fname, size, para_idx in large_imgs:
    print(f'  {fname}: {size:.1f}KB at paragraph {para_idx}')

print(f'\n=== SAMPLE SMALL IMAGES (exercise demos, every 20th) ===')
for i in range(0, len(small_imgs), max(1, len(small_imgs)//15)):
    fname, size, para_idx = small_imgs[i]
    print(f'  {fname}: {size:.1f}KB at p{para_idx}')

print(f'\nSaved to: {out_dir}')