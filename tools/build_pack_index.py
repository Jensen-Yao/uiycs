# -*- coding: utf-8 -*-
# Rebuild search index from semantic-name layout (packs/<slug>.json + media/<slug>/<role>.ext)
import json, os, sys, re
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)


sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PACKS = os.path.join(ROOT, 'packs')
MEDIA = os.path.join(ROOT, 'media')
INDEX = os.path.join(ROOT, 'index')

def main():
    previews = {it['id']: it for it in json.load(open(os.path.join(INDEX, 'previews.json'), encoding='utf-8'))['items']}
    rmap = json.load(open(os.path.join(INDEX, 'rename_map.json'), encoding='utf-8'))
    entries = []
    for pid, r in rmap.items():
        slug = r['slug']
        it = previews.get(pid, {})
        p = os.path.join(PACKS, slug + '.json')
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        fm = r.get('files') or {}
        def local(url):
            if not url: return ''
            base = url.rsplit('/', 1)[-1].split('?')[0]
            rec = fm.get(base)
            if rec:
                return os.path.join(MEDIA, slug, rec['new'])
            return url

        ins = d.get('inspector') or {}
        ic = d.get('iosCapture') or {}
        cap = d.get('capture') or {}
        screens = []
        for s in ic.get('screens') or []:
            screens.append({
                'id': s.get('id'), 'title': s.get('title'),
                'patterns': s.get('patterns') or [],
                'action': s.get('action'),
                'text': (s.get('text') or '')[:1500],
                'image': local(s.get('imageUrl')),
            })
        views = []
        for v in ins.get('views') or []:
            views.append({'label': v.get('label'), 'image': local(v.get('url')),
                          'width': v.get('width'), 'height': v.get('height')})
        colors = ins.get('palette') or [{'hex': c.get('value'), 'role': c.get('name')} for c in d.get('colors') or []][:8]
        entries.append({
            'id': pid, 'slug': slug,
            'name': it.get('name', slug),
            'platform': 'ios' if ic else 'web',
            'tagline': it.get('tagline') or d.get('summary') or '',
            'theme': d.get('theme') or '',
            'site': d.get('originalSiteUrl') or '',
            'capturedAt': (cap.get('capturedAt') or ic.get('capturedAt') or ''),
            'colors': colors,
            'typography': ins.get('typography') or [],
            'fontFamilies': d.get('fontFamilies') or [],
            'geometry': ins.get('geometry') or {},
            'components': d.get('componentNames') or [],
            'screens': screens,
            'views': views,
            'fullPage': local(cap.get('fullPageUrl')),
            'poster': local(d.get('detailPosterUrl')),
            'motion': local(d.get('detailVideoUrl')),
            'cover': local(it.get('coverUrl')),
        })
    json.dump({'version': 2, 'count': len(entries), 'items': entries},
              open(os.path.join(INDEX, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'indexed {len(entries)} packs (semantic layout)')

if __name__ == '__main__':
    main()
