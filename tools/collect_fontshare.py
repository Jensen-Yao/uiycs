# -*- coding: utf-8 -*-
# Fontshare: real asset URLs come from the CSS API (styles[].file is an internal id).
import json, os, re, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)

from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUT = os.path.join(ROOT, 'fonts-fontshare')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0'

def get(u, binary=False, t=30):
    req = Request(u, headers={'User-Agent': UA, 'Referer': 'https://www.fontshare.com/'})
    with urlopen(req, timeout=t) as r:
        b = r.read()
    return b if binary else b.decode('utf-8', 'replace')

api = json.loads(get('https://api.fontshare.com/v2/fonts'))
fonts = api['fonts']

def css_urls(query):
    css = get(f'https://api.fontshare.com/v2/css?f[]={query}&display=swap')
    # parse @font-face blocks in order
    out = []
    for block in re.findall(r'@font-face\s*\{(.*?)\}', css, re.S):
        fam = re.search(r"font-family:\s*'([^']+)'", block)
        wt = re.search(r'font-weight:\s*([0-9]+)', block)
        st = re.search(r'font-style:\s*(\w+)', block)
        src = re.search(r"url\('(//[^']+)'\)", block)
        if src:
            u = 'https:' + src.group(1)
            out.append((fam.group(1) if fam else '?', wt.group(1) if wt else '400',
                        st.group(1) if st else 'normal', u))
    return out

ok = fail = 0
man = []
for f in fonts:
    slug = f['slug']
    d = os.path.join(OUT, slug)
    os.makedirs(d, exist_ok=True)
    # clean stale zero-byte files
    for fn in os.listdir(d):
        p = os.path.join(d, fn)
        if os.path.isfile(p) and os.path.getsize(p) == 0:
            os.remove(p)
    entries = []
    queries = [f'{slug}@300,400,500,600,700,800', f'{slug}@300i,400i,500i,600i,700i']
    for q in queries:
        try:
            for fam, wt, st, u in css_urls(q):
                base = u.rsplit('/', 1)[-1].split('?')[0]
                fn = f'{wt}{"i" if st == "italic" else ""}-{base[:10]}.woff2'
                dest = os.path.join(d, fn)
                if not (os.path.exists(dest) and os.path.getsize(dest) > 0):
                    try:
                        b = get(u, binary=True)
                        if len(b) < 200:
                            fail += 1; continue
                        open(dest, 'wb').write(b); ok += 1
                    except Exception:
                        fail += 1; continue
                entries.append(os.path.relpath(dest, ROOT))
        except Exception:
            fail += 1
        time.sleep(0.08)
    man.append({'name': f['name'], 'slug': slug, 'category': f.get('category'),
                'license_type': f.get('license_type'),
                'publisher': (f.get('publisher') or {}).get('name'),
                'files': sorted(set(entries))})

json.dump({'source': 'https://api.fontshare.com/v2/css', 'count': len(man), 'fonts': man},
          open(os.path.join(OUT, 'MANIFEST.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
tot = sum(len(fs) for _, _, fs in os.walk(OUT))
zero = sum(1 for r, _, fs in os.walk(OUT) for f in fs if os.path.getsize(os.path.join(r, f)) == 0)
print(f'families:{len(man)} files:{tot} ok:{ok} fail:{fail} zero-byte:{zero}')
