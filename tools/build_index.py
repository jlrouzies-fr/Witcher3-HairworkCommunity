"""Regenerate index.json from all packs. Usage: build_index.py <repo_root>"""
import hashlib
import json
import subprocess
import os
import sys

root = sys.argv[1] if len(sys.argv) > 1 else '.'
PACK_FILES = ('pack.json', 'edits.hwgroom', 'ribbons.json', 'preview.jpg', 'preview.png')
# the commit the files are served from: the Studio downloads from this exact commit and checks each SHA-256
commit = os.environ.get('GITHUB_SHA') or subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
packs = []
for dp, dn, fn in os.walk(os.path.join(root, 'characters')):
    if 'pack.json' in fn:
        dn[:] = []
        with open(os.path.join(dp, 'pack.json'), encoding='utf-8') as f:
            m = json.load(f)
        m['path'] = os.path.relpath(dp, root).replace('\\', '/')
        m['has_preview'] = any(os.path.exists(os.path.join(dp, x)) for x in ('preview.png', 'preview.jpg'))
        m['commit'] = commit
        m['sha256'] = {x: hashlib.sha256(open(os.path.join(dp, x), 'rb').read()).hexdigest() for x in PACK_FILES if x in fn}
        m['size'] = sum(os.path.getsize(os.path.join(dp, x)) for x in fn)
        packs.append(m)
packs.sort(key=lambda m: m['path'])
with open(os.path.join(root, 'index.json'), 'w', encoding='utf-8') as f:
    json.dump({'version': 1, 'packs': packs}, f, indent=1)
print(len(packs), 'pack(s)')
