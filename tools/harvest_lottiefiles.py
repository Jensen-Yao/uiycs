# -*- coding: utf-8 -*-
# LottieFiles free-library harvester. Runs AFTER the human clears the Turnstile
# challenge in the shared browser; pulls cf_clearance + UA from cookie flush.
import json, os, re, sys, time, io
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)

from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUT = os.path.join(ROOT, 'animated-icons', 'lottiefiles-official')
COOKIE_FILE = os.path.join(ROOT, 'index', 'cf_cookies.json')
UA_FILE = os.path.join(ROOT, 'index', 'cf_ua.txt')

def load_session():
    cks = json.load(open(COOKIE_FILE, encoding='utf-8'))
    ua = open(UA_FILE, encoding='utf-8').read().strip()
    jar = '; '.join(f"{c['name']}={c['value']}" for c in cks if 'lottiefiles' in c.get('domain', ''))
    return ua, jar

def fetch(url, referer=None, binary=False):
    ua, jar = load_session()
    h = {'User-Agent': ua, 'Cookie': jar, 'Accept': '*/*',
         'Accept-Language': 'en-US,en;q=0.9'}
    if referer:
        h['Referer'] = referer
    req = Request(url, headers=h)
    with urlopen(req, timeout=40) as r:
        b = r.read()
    return b if binary else b.decode('utf-8', 'replace')

def fetch_bin(url, referer=None):
    return fetch(url, referer=referer, binary=True)

def is_lottie(b):
    try:
        d = json.loads(b)
        return isinstance(d, dict) and 'layers' in d and 'v' in d
    except Exception:
        return False

def harvest_category(slug, label, max_pages=6):
    got = []
    d = os.path.join(OUT, label)
    os.makedirs(d, exist_ok=True)
    for page in range(1, max_pages + 1):
        u = f'https://lottiefiles.com/free-animations/{slug}' + (f'?page={page}' if page > 1 else '')
        try:
            html = fetch(u)
        except HTTPError as e:
            print(f'[{label}] page {page}: HTTP {e.code}, stop')
            break
        if 'Just a moment' in html:
            print(f'[{label}] page {page}: challenge, stop')
            break
        # animation JSON/asset links embedded in RSC payload
        urls = set(re.findall(r'https://assets\d*\.lottiefiles\.com/(?:packages/)?[A-Za-z0-9_/.-]+\.(?:json|lottie)', html))
        urls |= set(re.findall(r'https://lottie\.host/[A-Za-z0-9_/-]+\.(?:json|lottie)', html))
        new = 0
        for au in sorted(urls):
            base = re.sub(r'[^A-Za-z0-9._-]', '_', au.rsplit('/', 1)[-1])
            ext = '.lottie' if base.endswith('.lottie') else '.json'
            name = base if base.endswith(ext) else base + ext
            dest = os.path.join(d, name)
            if os.path.exists(dest):
                continue
            try:
                b = fetch_bin(au, referer=u)
                if ext == '.json' and not is_lottie(b):
                    continue
                open(dest, 'wb').write(b)
                got.append({'file': os.path.relpath(dest, ROOT), 'source': au, 'category': label,
                            'license': 'LottieFiles free license (per-item, kept with item)'})
                new += 1
                time.sleep(0.3)
            except Exception:
                continue
        print(f'[{label}] page {page}: {len(urls)} links, {new} saved')
        if new == 0 and page > 1:
            break
    return got

def main():
    cats = [('loading', 'loading'), ('success-check', 'success'), ('empty', 'empty'),
            ('toggle', 'toggle'), ('icons', 'icons'), ('button', 'button'),
            ('check', 'check')]
    all_items = []
    for slug, label in cats:
        all_items += harvest_category(slug, label)
        time.sleep(1)
    mp = os.path.join(ROOT, 'animated-icons', 'MANIFEST.json')
    m = json.load(open(mp, encoding='utf-8'))
    known = {it['file'] for it in m['items']}
    add = [it for it in all_items if it['file'] not in known]
    m['items'] += add
    m['collected'] = len(m['items'])
    json.dump(m, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('added', len(add), 'total', m['collected'])

if __name__ == '__main__':
    main()
