# -*- coding: utf-8 -*-
"""Rebuild index/index.json from the pack directory.

Reads `packs/<slug>.json` and resolves media under `media/<slug>/`. Works with
packs produced by `tools/capture_site.py` and with packs that carry absolute
media URLs (those are matched against the local media directory by basename).

Usage:
  python tools/build_pack_index.py
"""
import hashlib
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PACKS = os.path.join(ROOT, 'packs')
MEDIA = os.path.join(ROOT, 'media')
INDEX = os.path.join(ROOT, 'index')

MOTION_EXT = ('.webm', '.mp4', '.mov')


def stable_id(slug):
    h = hashlib.md5(slug.encode('utf-8')).hexdigest()
    return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'


def media_dir(slug):
    return os.path.join(MEDIA, slug)


def resolve(slug, value, fallback_names=()):
    """Turn a pack media reference into an absolute path that exists."""
    d = media_dir(slug)
    if value:
        v = str(value).replace('\\', '/')
        if v.startswith('media/') or v.startswith('media\\'):
            p = os.path.join(ROOT, v)
            if os.path.exists(p):
                return p
        if os.path.isabs(v) and os.path.exists(v):
            return v
        if v.startswith('http'):
            base = v.rsplit('/', 1)[-1].split('?')[0]
            p = os.path.join(d, base)
            if os.path.exists(p):
                return p
    for name in fallback_names:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return ''


def find_motion(slug):
    d = media_dir(slug)
    if not os.path.isdir(d):
        return ''
    for f in sorted(os.listdir(d)):
        if f.startswith('motion') and f.lower().endswith(MOTION_EXT):
            return os.path.join(d, f)
    return ''


def first_existing(slug, names):
    d = media_dir(slug)
    for n in names:
        p = os.path.join(d, n)
        if os.path.exists(p):
            return p
    return ''


def load_legacy():
    """Optional uizze-style metadata, if present. Absent is fine."""
    previews, rename = {}, {}
    p = os.path.join(INDEX, 'previews.json')
    if os.path.exists(p):
        try:
            previews = {it['id']: it for it in json.load(open(p, encoding='utf-8'))['items']}
        except Exception:
            previews = {}
    p = os.path.join(INDEX, 'rename_map.json')
    if os.path.exists(p):
        try:
            rename = json.load(open(p, encoding='utf-8'))
        except Exception:
            rename = {}
    return previews, rename


def build_entry(slug, d, previews, rename):
    ins = d.get('inspector') or {}
    ic = d.get('iosCapture') or {}
    cap = d.get('capture') or {}

    # palette: inspector.palette, else colors[] with either key naming
    colors = ins.get('palette')
    if not colors:
        colors = []
        for c in d.get('colors') or []:
            colors.append({'hex': c.get('hex') or c.get('value'),
                           'role': c.get('role') or c.get('name')})
    colors = [c for c in colors if c.get('hex')][:8]

    screens = []
    for s in ic.get('screens') or []:
        screens.append({
            'id': s.get('id'),
            'title': s.get('title'),
            'patterns': s.get('patterns') or [],
            'action': s.get('action'),
            'text': (s.get('text') or '')[:1500],
            'image': resolve(slug, s.get('imageUrl')),
        })

    views = []
    for v in ins.get('views') or []:
        views.append({
            'label': v.get('label'),
            'image': resolve(slug, v.get('url')),
            'width': v.get('width'),
            'height': v.get('height'),
        })

    poster = resolve(slug, d.get('detailPosterUrl'),
                     ('poster.webp', 'poster.png', 'poster.jpg'))
    if not poster:
        for v in views:
            if v['image'] and (v.get('label') or '').lower() in ('desktop', 'home'):
                poster = v['image']
                break
    if not poster and views:
        poster = views[0]['image']

    full = resolve(slug, cap.get('fullPageUrl'), ('fullpage.webp', 'full-page.webp'))
    motion = resolve(slug, d.get('detailVideoUrl')) or find_motion(slug)
    cover = resolve(slug, (previews.get(d.get('id')) or {}).get('coverUrl'),
                    ('thumb.webp', 'card.webp', 'icon.webp'))
    if not cover:
        cover = first_existing(slug, ('thumb.webp', 'card.webp', 'icon.webp'))

    pid = d.get('id') or stable_id(slug)
    tagline = d.get('tagline') or d.get('summary') or ''
    name = d.get('name') or slug
    return {
        'id': pid,
        'slug': slug,
        'name': name,
        'platform': d.get('platform') or ('ios' if ic else 'web'),
        'tagline': tagline,
        'theme': d.get('theme') or '',
        'site': d.get('site') or d.get('originalSiteUrl') or '',
        'capturedAt': d.get('capturedAt') or cap.get('capturedAt') or ic.get('capturedAt') or '',
        'colors': colors,
        'typography': ins.get('typography') or d.get('typography') or [],
        'fontFamilies': d.get('fontFamilies') or [],
        'geometry': ins.get('geometry') or {},
        'components': d.get('componentNames') or d.get('components') or [],
        'screens': screens,
        'views': views,
        'fullPage': full,
        'poster': poster,
        'motion': motion,
        'cover': cover,
    }


def main():
    os.makedirs(INDEX, exist_ok=True)
    if not os.path.isdir(PACKS):
        sys.exit(f'no packs directory at {PACKS}')

    previews, rename = load_legacy()
    entries, skipped = [], 0
    for f in sorted(os.listdir(PACKS)):
        if not f.endswith('.json') or f.endswith('.capture.json'):
            continue
        slug = f[:-5]
        try:
            d = json.load(open(os.path.join(PACKS, f), encoding='utf-8'))
        except Exception as e:
            print(f'  skip {f}: {e}')
            skipped += 1
            continue
        entries.append(build_entry(slug, d, previews, rename))

    # newest first, undated last
    entries.sort(key=lambda e: e.get('capturedAt') or '', reverse=True)

    out = os.path.join(INDEX, 'index.json')
    json.dump({'version': 2, 'count': len(entries), 'items': entries},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False)

    no_poster = sum(1 for e in entries if not e['poster'])
    no_full = sum(1 for e in entries if not e['fullPage'])
    print(f'indexed {len(entries)} packs -> {out}')
    if skipped:
        print(f'skipped {skipped}')
    print(f'  poster missing: {no_poster}   fullpage missing: {no_full}')
    if previews:
        print(f'  legacy metadata merged: {len(previews)} previews, {len(rename)} rename records')


if __name__ == '__main__':
    main()
