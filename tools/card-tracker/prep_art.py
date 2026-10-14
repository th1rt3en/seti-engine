import os, re, json, shutil, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SP = sys.argv[1]
PK = os.path.join(SP, 'asset-repo', 'seti', 'packages')
IMG = os.path.join(PK, 'cards', 'assets', 'images')
OUT = os.path.join(SP, 'art')
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
meta = {'sheets': {}, 'files': []}

def put(src, name):
    shutil.copy(src, os.path.join(OUT, name)); meta['files'].append(name)

for n in ('1', '2'):
    f = f'sheet-cards-{n}.webp'; put(os.path.join(IMG, 'cards', f'cards-{n}.webp'), f)
for sp in ('amoeba', 'anomalies', 'centaurians', 'exertians', 'glyphids', 'mascamites', 'oumuamua'):
    put(os.path.join(IMG, 'aliens', sp + '.webp'), f'sheet-alien-{sp}.webp')
for f in os.listdir(os.path.join(IMG, 'cards', 'space-agency')):
    n = os.path.splitext(f)[0]
    put(os.path.join(IMG, 'cards', 'space-agency', f), f'sa-{n}.webp')
corp = os.path.join(PK, 'web', 'public', 'images', 'corporations')
for f in os.listdir(corp):
    slug = re.sub(r'[^a-z0-9]+', '-', os.path.splitext(f)[0].lower()).strip('-')
    put(os.path.join(corp, f), f'org-{slug}.jpg')
# rival action card sheet from the owner's assets: reduce to webp
src = os.path.join(SP, '..', '..', '..', '..', '..', '..', 'workspace', 'seti-engine', 'assets', 'solo-rival-action-cards-sheet.png')
src = r'C:\Users\Admin\workspace\seti-engine\assets\solo-rival-action-cards-sheet.png'
im = Image.open(src).convert('RGB'); im = im.resize((im.size[0] // 2, im.size[1] // 2), Image.LANCZOS)
im.save(os.path.join(OUT, 'ref-rival-actions.webp'), quality=80); meta['files'].append('ref-rival-actions.webp')
for f in meta['files']:
    if f.startswith('sheet-'):
        w, h = Image.open(os.path.join(OUT, f)).size
        meta['sheets'][f] = {'w': w, 'h': h, 'cols': round(w / 373.5), 'rows': round(h / 520)}
json.dump(meta, open(os.path.join(SP, 'art-meta.json'), 'w'), indent=1)
tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in meta['files'])
print(len(meta['files']), 'files', round(tot / 1e6, 1), 'MB')
print(meta['sheets'])
