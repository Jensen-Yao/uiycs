# -*- coding: utf-8 -*-
# Collect open-licensed UI lottie animations: verified public CDN URLs + OSS repo assets
import json, os, re, shutil, sys, zipfile, time
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)

from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUT = os.path.join(ROOT, 'animated-icons')
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0'

CDN_CANDIDATES = [
    # (url, category, name)  -- public lottiefiles CDN links widely referenced in OSS docs/tutorials
    ('https://assets3.lottiefiles.com/packages/lf20_XZ3pkn.json', 'misc', 'lottie-react-doc-demo'),
    ('https://assets10.lottiefiles.com/packages/lf20_ytifsoly.json', 'loading', 'lf20_ytifsoly'),
    ('https://assets5.lottiefiles.com/packages/lf20_vnikwe79.json', 'loading', 'lf20_vnikwe79'),
    ('https://assets4.lottiefiles.com/packages/lf20_xRj6rN.json', 'loading', 'lf20_xRj6rN'),
    ('https://assets2.lottiefiles.com/packages/lf20_w51pcehl.json', 'success', 'lf20_w51pcehl'),
    ('https://assets9.lottiefiles.com/packages/lf20_usmfxrbp.json', 'success', 'lf20_usmfxrbp'),
    ('https://assets1.lottiefiles.com/packages/lf20_myejiggj.json', 'loading', 'lf20_myejiggj'),
    ('https://assets6.lottiefiles.com/packages/lf20_w28dvcxd.json', 'misc', 'lf20_w28dvcxd'),
    ('https://assets8.lottiefiles.com/packages/lf20_zrqthn6o.json', 'loading', 'lf20_zrqthn6o'),
    ('https://assets3.lottiefiles.com/packages/lf20_szpquzbt.json', 'misc', 'lf20_szpquzbt'),
    ('https://assets10.lottiefiles.com/packages/lf20_x62chJ.json', 'loading', 'lf20_x62chJ'),
    ('https://assets2.lottiefiles.com/packages/lf20_bkcnoswo.json', 'empty', 'lf20_bkcnoswo'),
    ('https://assets4.lottiefiles.com/packages/lf20_ixdvbdcx.json', 'empty', 'lf20_ixdvbdcx'),
    ('https://assets5.lottiefiles.com/packages/lf20_fcfjuwiy.json', 'misc', 'lf20_fcfjuwiy'),
    ('https://assets1.lottiefiles.com/packages/lf20_qlk5g21i.json', 'success', 'lf20_qlk5g21i'),
    ('https://assets15.lottiefiles.com/packages/lf20_wm7uc9er.json', 'misc', 'lf20_wm7uc9er'),
    ('https://assets24.lottiefiles.com/packages/lf20_kk62nxlp.json', 'loading', 'lf20_kk62nxlp'),
    ('https://assets10.lottiefiles.com/packages/lf20_3e_hbY.json', 'misc', 'lf20_3e_hbY'),
    ('https://assets5.lottiefiles.com/packages/lf20_V9t630.json', 'success', 'lf20_V9t630'),
    ('https://assets12.lottiefiles.com/packages/lf20_s2qryh.json', 'loading', 'lf20_s2qryh'),
    ('https://assets1.lottiefiles.com/packages/lf20_fxuotpzo.json', 'empty', 'lf20_fxuotpzo'),
    ('https://assets2.lottiefiles.com/packages/lf20_touohxv0.json', 'empty', 'lf20_touohxv0'),
    ('https://assets3.lottiefiles.com/packages/lf20_kk62nxlp.json', 'loading', 'lf20_kk62nxlp_b'),
    ('https://assets9.lottiefiles.com/packages/lf20_caumc2vh.json', 'misc', 'lf20_caumc2vh'),
    ('https://assets6.lottiefiles.com/packages/lf20_pwawjzwm.json', 'misc', 'lf20_pwawjzwm'),
    ('https://assets4.lottiefiles.com/packages/lf20_5tkzkblw.json', 'loading', 'lf20_5tkzkblw'),
    ('https://assets7.lottiefiles.com/packages/lf20_ckk Gone'.replace(' ',''), 'misc', 'invalid'),
    ('https://lottie.host/4db68bbd-31f6-4cd8-84eb-189571e2dccc/5u2xmKkpCI.lottie', 'misc', 'host_blog_demo'),
]

REPO_ASSETS = []  # 可选：填入本地 clone 的开源 lottie 仓库目录，(dir, category, license)

def is_lottie(b):
    try:
        d = json.loads(b)
        return isinstance(d, dict) and ('layers' in d or 'assets' in d) and 'v' in d
    except Exception:
        return False

def fetch(url, timeout=25):
    req = Request(url, headers={'User-Agent': UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read()

manifest = []

# CDN sweep
for url, cat, name in CDN_CANDIDATES:
    if 'invalid' in name:
        continue
    try:
        b = fetch(url)
        if not is_lottie(b):
            continue
        d = os.path.join(OUT, cat)
        os.makedirs(d, exist_ok=True)
        fn = os.path.join(d, name + ('.lottie' if url.endswith('.lottie') else '.json'))
        open(fn, 'wb').write(b)
        manifest.append({'file': os.path.relpath(fn, ROOT), 'source': url,
                         'category': cat, 'license': 'LottieFiles community free license'})
        print(f'ok  {cat}/{name}  {len(b)}b')
    except Exception as e:
        print(f'--  {name}: {type(e).__name__}')

# repo assets
for src_dir, cat, lic in REPO_ASSETS:
    if not os.path.isdir(src_dir):
        continue
    for dirpath, _dirs, files in os.walk(src_dir):
        for f in files:
            if not f.endswith(('.json', '.lottie')):
                continue
            p = os.path.join(dirpath, f)
            if os.path.getsize(p) < 200:
                continue
            ok = True
            if f.endswith('.json'):
                ok = is_lottie(open(p, 'rb').read())
            if not ok:
                continue
            d = os.path.join(OUT, cat, re.sub(r'[^a-z0-9]+', '-', lic.lower()))
            os.makedirs(d, exist_ok=True)
            base = f
            dest = os.path.join(d, base)
            if os.path.exists(dest):
                continue
            shutil.copy(p, dest)
            manifest.append({'file': os.path.relpath(dest, ROOT), 'source': p,
                             'category': cat, 'license': lic})

# dotlottie fixtures are zip containers; keep as-is
fx = os.environ.get('DOTLOTTIE_FIXTURES', '')
if os.path.isdir(fx):
    d = os.path.join(OUT, 'fixtures', 'dotlottie-web (MIT)')
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(fx):
        if f.endswith('.lottie'):
            dest = os.path.join(d, f)
            if not os.path.exists(dest):
                shutil.copy(os.path.join(fx, f), dest)
                manifest.append({'file': os.path.relpath(dest, ROOT), 'source': os.path.join(fx, f),
                                 'category': 'fixtures', 'license': 'dotlottie-web repo (MIT)'})

json.dump({'collected': len(manifest), 'items': manifest},
          open(os.path.join(OUT, 'MANIFEST.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('TOTAL:', len(manifest))
