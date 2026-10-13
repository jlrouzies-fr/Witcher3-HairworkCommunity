"""Validate community pack folders.
Usage: validate_pack.py <repo_root> [--author USER --changed FILE_LIST]   (stdlib + jsonschema only)"""
import argparse
import json
import os
import re
import sys

import jsonschema

BAD_EXT = {'.w2mesh', '.w2ent', '.bundle', '.apb', '.dll', '.lib', '.exe', '.so', '.dylib'}
BAD_NAME = re.compile(r'nvidia|gfsdk|gameworks|hairworks[_-]?sdk|nvhair', re.I)
BAD_TEXT = re.compile(r'GFSDK|NvHair|NvFoundation')
MAX_PREVIEW, MAX_PACK = 300 * 1024, 2 * 1024 * 1024


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def pack_dirs(root):
    for dp, dn, fn in os.walk(os.path.join(root, 'characters')):
        if 'pack.json' in fn:
            dn[:] = []
            yield dp


def check_pack(root, d, schemas):
    errs = []
    rel = os.path.relpath(d, root).replace('\\', '/')
    parts = rel.split('/')
    if len(parts) != 4 or '__' not in parts[3]:
        errs.append(f'{rel}: path must be characters/<char>/<slot>/<user>__<pack>')
    meta = {}
    try:
        meta = load(os.path.join(d, 'pack.json'))
        jsonschema.validate(meta, schemas['pack'])
        if len(parts) == 4 and '__' in parts[3]:
            user, pack = parts[3].split('__', 1)
            if meta['author'].lower() != user.lower() or meta['name'] != pack:
                errs.append(f'{rel}: folder name must be <author>__<name> of pack.json')
            if meta['character'] != parts[1]:
                errs.append(f'{rel}: character does not match folder')
    except Exception as e:
        errs.append(f'{rel}/pack.json: {str(e).splitlines()[0]}')
    try:
        doc = load(os.path.join(d, 'edits.hwgroom'))
        jsonschema.validate(doc, schemas['hwgroom'])
        ops = doc.get('ops', [])
        if any(o.get('type') == 'delete_face' and o.get('face', -1) >= 0 for o in ops) and 'mesh_fingerprint' not in meta:
            errs.append(f'{rel}/pack.json: delete_face ops need mesh_fingerprint')
        if any(o.get('type') == 'rebuild' for o in ops) and not meta.get('studio_version'):
            errs.append(f'{rel}/pack.json: rebuild ops need studio_version')
        for o in ops:
            if o.get('type') == 'rebuild' and o.get('kind') == 'baked':
                errs += [f'{rel}/edits.hwgroom: {m}' for m in _check_baked(o['params'])]
        if not _sane(doc):
            errs.append(f'{rel}/edits.hwgroom: values out of range (non-finite, huge or too deeply nested)')
    except Exception as e:
        errs.append(f'{rel}/edits.hwgroom: {str(e).splitlines()[0]}')
    total = 0
    for fn in os.listdir(d):
        p = os.path.join(d, fn)
        size = os.path.getsize(p)
        total += size
        if os.path.splitext(fn)[1].lower() in BAD_EXT or BAD_NAME.search(fn):
            errs.append(f'{rel}/{fn}: forbidden file')
        if fn not in ALLOWED_FILES:
            errs.append(f'{rel}/{fn}: not a pack file (allowed: {", ".join(ALLOWED_FILES)})')
        if fn.startswith('preview'):
            with open(p, 'rb') as f:
                head = f.read(8)
            if not (head.startswith(bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])) or head.startswith(bytes([0xFF, 0xD8]))):
                errs.append(f'{rel}/{fn}: not a PNG / JPEG')
        if fn.startswith('preview') and size > MAX_PREVIEW:
            errs.append(f'{rel}/{fn}: preview over 300KB')
        if fn.endswith(('.json', '.hwgroom', '.md', '.txt')):
            with open(p, encoding='utf-8', errors='ignore') as f:
                if BAD_TEXT.search(f.read()):
                    errs.append(f'{rel}/{fn}: SDK identifiers found')
    if total > MAX_PACK:
        errs.append(f'{rel}: pack over 2MB')
    return errs


def _check_baked(p):
    """baked rebuild: guides / uv / faces / face_uv must agree in length, indices in range, one point count per guide"""
    errs = []
    for k in ('guides', 'uv', 'faces', 'face_uv'):
        if not isinstance(p.get(k), list):
            return [f'baked rebuild needs a "{k}" list']
    g, uv, f, fuv = p['guides'], p['uv'], p['faces'], p['face_uv']
    if not g or not f:
        errs.append('baked rebuild is empty')
    if len(uv) != len(g):
        errs.append('baked rebuild: uv count differs from guide count')
    if len(fuv) != len(f):
        errs.append('baked rebuild: face_uv count differs from face count')
    ks = {len(x) if isinstance(x, list) else -1 for x in g}
    if len(ks) != 1 or not 2 <= next(iter(ks)) <= 64:
        errs.append('baked rebuild: every guide needs the same number of points (2..64)')
    if not all(isinstance(x, list) and len(x) == 3 for q in g if isinstance(q, list) for x in q):
        errs.append('baked rebuild: guide points must be [x, y, z]')
    if not all(isinstance(x, list) and len(x) == 3 and all(isinstance(i, int) and 0 <= i < len(g) for i in x) for x in f):
        errs.append('baked rebuild: faces must be 3 guide indices in range')
    if not all(isinstance(x, list) and len(x) == 6 for x in fuv) or not all(isinstance(x, list) and len(x) == 2 for x in uv):
        errs.append('baked rebuild: uv / face_uv have the wrong shape')
    return errs


ALLOWED_FILES = ('pack.json', 'edits.hwgroom', 'ribbons.json', 'preview.jpg', 'preview.png', 'CHANGELOG.md')


def _sane(v, depth=0):
    import math
    if depth > 8:
        return False
    if isinstance(v, bool):
        return True
    if isinstance(v, float):
        return math.isfinite(v) and abs(v) <= 1e6
    if isinstance(v, int):
        return -1 <= v <= 10_000_000
    if isinstance(v, str):
        return len(v) <= 256
    if isinstance(v, list):
        return len(v) <= 100_000 and all(_sane(x, depth + 1) for x in v)
    if isinstance(v, dict):
        return all(len(k) <= 64 and _sane(x, depth + 1) for k, x in v.items())
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--author')
    ap.add_argument('--changed', help='file with changed paths, one per line')
    a = ap.parse_args()
    sch = {'pack': load(os.path.join(a.root, 'schema', 'pack.schema.json')),
           'hwgroom': load(os.path.join(a.root, 'schema', 'hwgroom.schema.json'))}
    errs = []
    if a.author and a.changed:
        pre = a.author.lower() + '__'
        with open(a.changed, encoding='utf-8') as f:
            for line in f:
                p = line.strip().replace('\\', '/')
                if not p:
                    continue
                seg = p.split('/')
                if not (len(seg) >= 5 and seg[0] == 'characters' and seg[3].lower().startswith(pre)):
                    errs.append(f'{p}: outside {a.author}__* folders')
    for d in pack_dirs(a.root):
        errs += check_pack(a.root, d, sch)
    for e in errs:
        print('ERROR', e)
    print('OK' if not errs else f'{len(errs)} error(s)')
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
