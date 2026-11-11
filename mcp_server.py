# -*- coding: utf-8 -*-
# uiycs MCP server (stdio, JSON-RPC 2.0 / MCP 2025-06-18)
# 对齐官方三工具签名，但素材层是真检索：pack / font / icon / animated_icon。
import json, os, sys, base64, re
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)


sys.stdout.reconfigure(encoding='utf-8', errors='replace')
IDX_PATH = os.path.join(ROOT, 'index', 'index.json')
if not os.path.exists(IDX_PATH):
    sys.stderr.write(
        f'[uiycs] no pack index at {IDX_PATH}\n'
        f'        build one:   python tools/build_pack_index.py\n'
        f'        or start from the demos:\n'
        f'                     cp -r examples/demo-packs/packs/* packs/\n'
        f'                     cp -r examples/demo-packs/media/* media/\n')
    sys.exit(1)
IDX = json.load(open(IDX_PATH, encoding='utf-8'))
ITEMS = IDX['items']

_FONTS = _ICONS = _LOTTIE = None


def _load_json(rel, hint):
    """Load a derived index, or fail with the command that builds it."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f'{rel} is missing — run: python tools/{hint}')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def fonts_index():
    global _FONTS
    if _FONTS is None:
        _FONTS = _load_json(os.path.join('fonts', 'INDEX.json'), 'build_fonts_index.py')
    return _FONTS


def icons_index():
    global _ICONS
    if _ICONS is None:
        _ICONS = _load_json(os.path.join('icons', 'INDEX.json'), 'build_icons_index.py')
    return _ICONS


def lottie_index():
    global _LOTTIE
    if _LOTTIE is None:
        _LOTTIE = _load_json(os.path.join('animated-icons', 'MANIFEST.json'),
                             'harvest_lottiefiles.py  +  collect_lottie.py')
    return _LOTTIE


def abspath(rel):
    return os.path.join(ROOT, rel.replace('/', os.sep))


TOOLS = [
    {"name": "find_ui_references",
     "description": "Search the local design reference mirror (685 captured web/iOS apps) for UI references matching a query. Returns packs with screenshots (local paths), design tokens, components and screen OCR text.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "What to find: app name, product type, UI pattern, or text expected on screen"},
         "platform": {"type": "string", "enum": ["ios", "web"]},
         "limit": {"type": "integer", "minimum": 1, "maximum": 3, "default": 2},
         "element": {"type": "string", "description": "Require packs whose captured components include this, e.g. Table, Dialog, Tab Bar"},
         "screenshot": {"type": "boolean", "default": False, "description": "Inline the poster screenshot as base64 image content"}
     }, "required": ["query"]}},
    {"name": "find_ui_materials",
     "description": "Retrieve design material from the local mirror. kind=pack returns a captured app's full design system (palette/typography/geometry/components/views). kind=font searches 217 font families (114 Google Fonts OFL, 100 Fontshare commercial-free, 3 CJK variable) and returns local woff2/ttf paths. kind=icon searches 6307 icon names across lucide, heroicons and Material Symbols (27278 SVG files) and returns local SVG paths. kind=animated_icon searches 750 Lottie animations.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "App name (kind=pack), font family name (kind=font), icon name such as arrow-right (kind=icon), or animation name/category"},
         "kind": {"type": "string", "enum": ["font", "icon", "animated_icon", "pack"], "default": "pack"},
         "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5}
     }, "required": ["query", "kind"]}},
    {"name": "get_pack_detail",
     "description": "Return the complete local record for one pack id or exact name: all tokens, every screen with OCR text, and local file paths for screenshots, full-page captures and motion videos.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "Pack id, slug or exact app name (e.g. \"airbnb\", \"nominal\")"}
     }, "required": ["id"]}},
]

# ---------- pack search (unchanged) ----------

def score(e, ql):
    s = 0
    name = e['name'].lower()
    if ql == name: s += 100
    elif ql in name: s += 60
    for f in (e.get('tagline'), e.get('theme'), e.get('site')):
        if f and ql in f.lower(): s += 30
    for c in e.get('components') or []:
        if ql in c.lower(): s += 20
    for sc in e.get('screens') or []:
        if ql in (sc.get('title') or '').lower(): s += 20
        if any(ql in p.lower() for p in sc.get('patterns') or []): s += 15
        if ql in (sc.get('text') or '').lower(): s += 6
    return s


def brief(e):
    return {
        'id': e['id'], 'name': e['name'], 'platform': e['platform'],
        'tagline': e['tagline'], 'theme': e['theme'], 'site': e['site'],
        'capturedAt': e['capturedAt'],
        'palette': [{'hex': c.get('hex'), 'role': c.get('role')} for c in e.get('colors') or []][:6],
        'typography': e.get('typography') or [],
        'fontFamilies': e.get('fontFamilies') or [],
        'components': e.get('components') or [],
        'screens': [{'id': s['id'], 'title': s['title'], 'image': s['image'],
                     'patterns': s['patterns']} for s in e.get('screens') or []],
        'views': [{'label': v['label'], 'image': v['image']} for v in e.get('views') or []],
        'fullPage': e.get('fullPage'), 'poster': e.get('poster'), 'motion': e.get('motion'),
        'cover': e.get('cover'),
    }


def find(query, platform=None, limit=2, element=None):
    ql = (query or '').lower().strip()
    pool = [e for e in ITEMS if (not platform or e['platform'] == platform)]
    if element:
        el = element.lower()
        pool = [e for e in pool if any(el in c.lower() for c in e.get('components') or [])]
    if not ql:
        pool.sort(key=lambda e: e.get('capturedAt') or '', reverse=True)
        return pool[:limit]
    terms = [t for t in re.split(r'\s+', ql) if t]
    scored = []
    for e in pool:
        per = [score(e, t) for t in terms]
        hits = sum(1 for s in per if s > 0)
        if hits == 0:
            continue
        total = sum(per) + (40 if hits == len(terms) else 0)
        scored.append((total, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:limit]]


# ---------- material search ----------

def find_fonts(q, limit):
    raw = (q or '').lower().strip()
    variants = {raw, raw.replace(' ', '-'), raw.replace(' ', '')}
    fams = fonts_index()['families']
    out = []
    for f in fams:
        name = (f.get('name') or '').lower()
        slug = (f.get('slug') or '').lower()
        s = 0
        if variants & {name, slug}: s = 100
        elif any(v and (v in name or v in slug) for v in variants): s = 70
        elif raw and raw in (f.get('category') or '').lower(): s = 40
        elif raw and raw in (f.get('publisher') or '').lower(): s = 25
        if s:
            out.append((s, f))
    out.sort(key=lambda x: -x[0])
    if not out and ql in ('', 'any', 'all'):
        out = [(1, f) for f in fams]
    res = []
    for _, f in out[:limit]:
        res.append({
            'name': f.get('name'), 'slug': f.get('slug'), 'source': f.get('source'),
            'license': f.get('license'), 'license_file': f.get('license_file'),
            'category': f.get('category'), 'publisher': f.get('publisher'),
            'cjk': f.get('cjk'), 'variable': f.get('variable'),
            'weights': f.get('weights'), 'italics': f.get('italics'),
            'dir': abspath(f['dir']),
            'files': [abspath(p) for p in f.get('files', [])],
        })
    return res


def find_icons(q, limit):
    ql = (q or '').lower().strip().replace('_', '-')
    idx = icons_index()
    hits = []
    if ql in idx:
        hits.append((1000, ql))
    for name in idx:
        if len(hits) > limit * 6:
            break
        if name == ql:
            continue
        if ql and (name.startswith(ql) or ql in name):
            s = 700 if name.startswith(ql) else 400
            hits.append((s - len(name) // 10, name))
    hits.sort(key=lambda x: -x[0])
    res = []
    for _, name in hits[:limit]:
        res.append({
            'name': name,
            'files': [abspath('icons/' + p) for p in idx[name]],
        })
    return res


def find_lottie(q, limit):
    ql = (q or '').lower().strip()
    items = lottie_index().get('items', [])
    out = []
    for it in items:
        path = it.get('file') or ''
        cat = (it.get('category') or '').lower()
        nm = os.path.basename(path).lower()
        s = 0
        if ql and ql in nm: s = 60
        elif ql and ql in cat: s = 40
        elif not ql: s = 1
        if s:
            out.append((s, it))
    out.sort(key=lambda x: -x[0])
    return [{'file': abspath(it['file']), 'category': it.get('category'),
             'source': it.get('source'), 'license': it.get('license')}
            for _, it in out[:limit]]


def inline_images(results, want):
    out = []
    for e in results[:1] if want else []:
        p = e.get('poster') or e.get('cover')
        if p and os.path.exists(p):
            mime = 'image/webp' if p.endswith('.webp') else 'image/png'
            out.append({'type': 'image', 'data': base64.b64encode(open(p, 'rb').read()).decode(),
                        'mimeType': mime})
    return out


def handle_call(name, args):
    if name == 'find_ui_references':
        res = find(args.get('query', ''), args.get('platform'), args.get('limit', 2), args.get('element'))
        text = json.dumps({'count': len(res), 'results': [brief(e) for e in res]}, ensure_ascii=False)
        content = [{'type': 'text', 'text': text}] + inline_images(res, args.get('screenshot'))
        return content

    if name == 'find_ui_materials':
        kind = (args.get('kind') or 'pack').lower()
        q = args.get('query', '')
        limit = int(args.get('limit', 5))
        if kind == 'font':
            res = find_fonts(q, limit)
            return [{'type': 'text', 'text': json.dumps(
                {'kind': 'font', 'count': len(res), 'families': res}, ensure_ascii=False)}]
        if kind == 'icon':
            res = find_icons(q, limit)
            return [{'type': 'text', 'text': json.dumps(
                {'kind': 'icon', 'count': len(res), 'icons': res}, ensure_ascii=False)}]
        if kind == 'animated_icon':
            res = find_lottie(q, limit)
            return [{'type': 'text', 'text': json.dumps(
                {'kind': 'animated_icon', 'count': len(res), 'animations': res}, ensure_ascii=False)}]
        res = find(q, None, min(limit, 3))
        packs = []
        for e in res:
            packs.append(brief(e) | {'geometry': e.get('geometry') or {},
                                     'screenTexts': [{'title': s['title'], 'text': s['text']}
                                                     for s in e.get('screens') or []]})
        return [{'type': 'text', 'text': json.dumps({'count': len(packs), 'packs': packs}, ensure_ascii=False)}]

    if name == 'get_pack_detail':
        key = (args.get('id') or '').strip()
        match = [e for e in ITEMS if e['id'] == key or e['slug'].lower() == key.lower()
                 or e['name'].lower() == key.lower()]
        if not match:
            return [{'type': 'text', 'text': json.dumps({'error': 'not found', 'id': key})}]
        return [{'type': 'text', 'text': json.dumps(brief(match[0]) | {'geometry': match[0].get('geometry') or {}}, ensure_ascii=False)}]

    return [{'type': 'text', 'text': json.dumps({'error': f'unknown tool {name}'})}]


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        rid, method, params = req.get('id'), req.get('method', ''), req.get('params') or {}
        resp = {'jsonrpc': '2.0', 'id': rid}
        if method == 'initialize':
            resp['result'] = {
                'protocolVersion': params.get('protocolVersion', '2025-06-18'),
                'capabilities': {'tools': {}},
                'serverInfo': {'name': 'uiycs', 'version': '2.0.0'},
            }
        elif method == 'tools/list':
            resp['result'] = {'tools': TOOLS}
        elif method == 'tools/call':
            try:
                content = handle_call(params.get('name'), params.get('args') or params.get('arguments') or {})
                resp['result'] = {'content': content, 'isError': False}
            except Exception as e:
                resp['result'] = {'content': [{'type': 'text', 'text': f'error: {e}'}], 'isError': True}
        elif method == 'ping':
            resp['result'] = {}
        elif method.startswith('notifications/'):
            continue
        else:
            resp['error'] = {'code': -32601, 'message': f'method not found: {method}'}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
