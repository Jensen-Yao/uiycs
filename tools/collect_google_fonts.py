# -*- coding: utf-8 -*-
# Font family survey: normalize 1075 raw family names, classify against Google Fonts,
# download every open-source hit as woff2 (400/700) + license; manifest the rest.
import json, os, re, sys, time, collections
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)

from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FDIR = os.path.join(ROOT, 'fonts')
os.makedirs(FDIR, exist_ok=True)
UA_CHROME = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

def fetch(url, timeout=30, binary=False):
    req = Request(url, headers={'User-Agent': UA_CHROME})
    with urlopen(req, timeout=timeout) as r:
        b = r.read()
    return b if binary else b.decode('utf-8', 'replace')

# ---------- 1. survey ----------
idx = json.load(open(os.path.join(ROOT, 'index', 'index.json'), encoding='utf-8'))
raw = collections.Counter()
for e in idx['items']:
    for f in e.get('fontFamilies') or []:
        n = f.strip()
        if n:
            raw[n] += 1

ICON_HINTS = re.compile(r'icon|awesome|codicon|material symbols|material icons|nucleo|swiper|slick|webflow|twemoji|judgeme|mdio|symbols', re.I)
NOISE = re.compile(r'placeholder|__|fallback|variable regular|-[0-9a-f]{10,}', re.I)

def is_stack(n):
    return (',' in n and ('system-ui' in n or 'sans-serif' in n or 'monospace' in n or '-apple-system' in n)) or 'Apple Color Emoji' in n

def normalize(n):
    m = {
        'inter': 'Inter', 'inter variable': 'Inter', 'inter var': 'Inter', 'intervariable': 'Inter',
        'intervar': 'Inter', 'interfont': 'Inter', 'inter lf': 'Inter', 'inter regular': 'Inter',
        'inter medium': 'Inter', 'inter semibold': 'Inter', 'interdisplay': 'Inter Display',
        'interdisplay': 'Inter Display', 'inter tight': 'Inter Tight',
        'geistmono': 'Geist Mono', 'geistsans': 'Geist', 'geist sans': 'Geist',
        'jetbrainsmono': 'JetBrains Mono', 'jetbrains mono variable': 'JetBrains Mono',
        'ibmplexmono': 'IBM Plex Mono', 'ibmplexsans': 'IBM Plex Sans', 'sourcecodepro': 'Source Code Pro',
        'instrumentserif': 'Instrument Serif', 'instrumentsans': 'Instrument Sans',
        'instrumentsans variable': 'Instrument Sans', 'spacegrotesk': 'Space Grotesk',
        'spacegrotesk variable': 'Space Grotesk', 'opensans': 'Open Sans', 'dmsans': 'DM Sans',
        'lexend variable': 'Lexend', 'figtree variable': 'Figtree', 'roboto mono variable': 'Roboto Mono',
        'spline sans mono variable': 'Spline Sans Mono', 'recursive variable': 'Recursive',
        'bricolage grotesque variable': 'Bricolage Grotesque', 'bricolage grotesque': 'Bricolage Grotesque',
        'ppneuemontreal': 'PP Neue Montreal', 'neue montreal': 'PP Neue Montreal',
        'suisseintl': 'Suisse Intl', 'suisse': 'Suisse Intl', 'suisse international': 'Suisse Intl',
        'soehne': 'Söhne', 'sohne-var': 'Söhne', 'söhne': 'Söhne',
        'untitledsans': 'Untitled Sans', 'gtamerica': 'GT America',
        'gt america regular': 'GT America', 'gt america medium': 'GT America',
        'gt america extended': 'GT America', 'gt america trial md': 'GT America',
        'gt america trial rg': 'GT America', 'abc diatype': 'ABC Diatype', 'abcdiatype': 'ABC Diatype',
        'muoto var': 'Muoto', 'muoto': 'Muoto', 'centrano2': 'Centra No2', 'centra no2': 'Centra No2',
        'saans vf': 'Saans', 'saansmono': 'Saans Mono', 'saans': 'Saans',
        'berkeleymono': 'Berkeley Mono', 'commitmono': 'Commit Mono', 'commit mono': 'Commit Mono',
        'suisse intl': 'Suisse Intl', 'suissese': 'Suisse Intl',
        'times': 'Times', 'serrif': 'Serif', 'family': None, 'icons': None, 'icon': None,
        'grotesk': None, 'denim': None, 'greed': None, 'rules': None, 'exact': None,
        'flecha': None, 'rotina': None, 'on': None, 'on mono': None, 'on semi mono': None,
        'plain': None, 'heading font': None, 'secondary heading font': None, 'body font': None,
        'vcr': None, 'seasonmix': 'Season Mix', 'season mix': 'Season Mix',
        'helvetica now text': 'Helvetica Now', 'helvetica now display': 'Helvetica Now',
        'helvetica now text medium': 'Helvetica Now', 'helvetica now display medium': 'Helvetica Now',
        'sf pro display': 'SF Pro', 'sf pro text': 'SF Pro', 'sf pro icons': 'SF Pro',
        'neue haas grotesk tx pro': 'Neue Haas Grotesk', 'neue haas grotesk ds pro': 'Neue Haas Grotesk',
        'nhahasgrotesk bold': 'Neue Haas Grotesk', 'nhahasgrotesk medium': 'Neue Haas Grotesk',
        'nhahasgrotesk light': 'Neue Haas Grotesk', 'neue-haas-grotesk-display': 'Neue Haas Grotesk',
        'tiempos headline': 'Tiempos', 'tiempos text': 'Tiempos', 'tiempos-headline': 'Tiempos',
        'tiempos-text': 'Tiempos', 'publico': 'Publico', 'publico text': 'Publico',
        'lyon text': 'Lyon', 'heldanetext': 'Heldane', 'editorial new': 'Editorial New',
        'gtstandard-m': 'GT Standard', 'gt standard l': 'GT Standard', 'gt standard m': 'GT Standard',
        'apkapk protocol': 'APK Protocol', 'apk protocol700': 'APK Protocol',
        'figmasans': 'Figma Sans', 'figmamono': 'Figma Mono', 'notioninter': 'Notion Inter',
        'slack-lato': 'Slack Lato', 'salesforce-sans': 'Salesforce Sans',
        'airbnb cereal vf': 'Airbnb Cereal', 'spotifymixui': 'Spotify Mix UI',
        'spotifymixuititle': 'Spotify Mix UI', 'spotifymixuititlevariable': 'Spotify Mix UI',
        'binancenova': 'Binance Nova', 'canva sans variable': 'Canva Sans',
        'coheretext': 'Cohere Text', 'coheremono': 'Cohere Mono', 'unica77 cohere web': 'Unica77',
        'p22mackinacpro-medium': 'Mackinac Pro', 'museo-sans': 'Museo Sans', 'effra': 'Effra',
        'futura-pt': 'Futura PT', 'graphik web': 'Graphik', 'colfax': 'Colfax',
        'akkuratll': 'Akkurat', 'akkurat mono': 'Akkurat Mono', 'interstate': 'Interstate',
        'tradegothicboldcondtwenty': 'Trade Gothic', 'linotype univers w01': 'Univers',
        'optima-lt-pro': 'Optima', 'menodisplay': 'Meno Display', 'meno-display': 'Meno Display',
        'mercurydisplayregular': 'Mercury Display', 'stkbureau Serif'.lower(): 'STK Bureau Serif',
        'stkbureauserif': 'STK Bureau Serif', 'roslindale': 'Roslindale',
        'iamreal': 'Real', 'really sans large': 'Really Sans', 'hem sans': 'Hem Sans',
        'austin': 'Austin', 'republic': 'Republic', 'garnett': 'Garnett',
        'matter variable thin': 'Matter', 'matter-trial semibold': 'Matter',
        'jokker regular': 'Jokker', 'jokker semibold': 'Jokker', 'jokker medium': 'Jokker',
        'aeonik pro': 'Aeonik', 'aeonik': 'Aeonik', 'aeonik fono': 'Aeonik Fono', 'aeoniksoft': 'Aeonik Soft',
        'geograph': 'Geograph', 'self modern': 'Self Modern', 'gt alpina': 'GT Alpina',
        'gt zirkon': 'GT Zirkon', 'gtultra': 'GT Ultra', 'gtplanar': 'GT Planar',
        'nuckle': 'Nuckle', 'stolzl': 'Stolzl', 'utara variable': 'Utara',
        'obviously': 'Obviously', 'agrandir-0cfc125464d8d15e': 'Agrandir',
        'euclidflex': 'Euclid Flex', 'euclid light': 'Euclid', 'euclid bold': 'Euclid',
        'motiva sans': 'Motiva Sans', 'fellix': 'Fellix', 'marlin': 'Marlin',
        'pp fraktion mono': 'PP Fraktion Mono', 'foundersgroteskmono': 'Founders Grotesk Mono',
        'nbinternationalpro': 'NB International Pro', 'waldenburg': 'Waldenburg',
        'waldenburg': 'Waldenburg', 'overused grotesk': 'Overused Grotesk',
        'open runde': 'Open Runde', 'roobert mono': 'Roobert', 'roobert': 'Roobert',
        'basiersquare webfont': 'Basier Square', 'hk nova medium': 'HK Nova', 'hk nova regular': 'HK Nova',
        'charlie display': 'Charlie Display', 'charlie text': 'Charlie Text', 'clarkson': 'Clarkson',
        'atlas grotesk': 'Atlas Grotesk', 'universal sans': 'Universal Sans', 'universalsans': 'Universal Sans',
        'abc favorit mono': 'ABC Favorit Mono', 'abc favorit': 'ABC Favorit',
        'abc monument grotesk mono': 'ABC Monument Grotesk Mono', 'abc oracle': 'ABC Oracle',
        'abc gravity normal': 'ABC Gravity', 'abc gravity': 'ABC Gravity',
        'gds transport': 'GDS Transport', 'porsche next': 'Porsche Next',
        'astronomartinsans': 'Aston Martin Sans', 'astonmartinsans': 'Aston Martin Sans',
        'astonmartinflare': 'Aston Martin Flare', 'ttnormspro': 'TT Norms Pro',
        'lufga': 'Lufga', 'lufga search pricing': 'Lufga', 'moma sans': 'MoMA Sans',
        'moma sans bold': 'MoMA Sans', 'sana sans': 'Sana Sans', 'sana serif': 'Sana Serif',
        'nike futura nd': 'Nike Futura', 'ritual vf variable': 'Ritual VF', 'lfe sans': 'LFE Sans',
        'excalifont': 'Excalifont', 'nata sans variable': 'Nata Sans', 'nata sans': 'Nata Sans',
        'tasa orbiter': 'TASA Orbiter', 'neuealte grotesk': 'Neue Alte Grotesk', 'neuealtegrotesk': 'Neue Alte Grotesk',
        'chivomono': 'Chivo Mono', 'judgemestar': None, 'judgemeicons': None,
        'spacemono': 'Space Mono', 'plany Mono'.lower(): None, 'papermono': None,
        'areal': None, 'areal': None, 'little amps': 'Little Amps', 'littleampsregular': 'Little Amps',
        'littleampsserif': 'Little Amps', 'sf mono': 'SF Mono', 'sf soft time': None,
        'department': None, 'cereal': 'Airbnb Cereal', 'vin': None, 'sintony': None,
        'pragmatapro vf variable regular': 'PragmataPro', 'departuremono': 'Departure Mono',
        'berkeley mono': 'Berkeley Mono', 'kh teka mono': 'KH Teka Mono', 'kh teka': 'KH Teka',
        'boat house': 'Boathouse', 'boathouse': 'Boathouse', 'moniker': 'Moniker',
        'shantell sans': 'Shantell Sans', 'caveat': 'Caveat', 'pixelify sans': 'Pixelify Sans',
        'jersey 10': 'Jersey 10', 'homemade apple': 'Homemade Apple', 'besley': 'Besley',
        'assistant': 'Assistant', 'albert sans': 'Albert Sans', 'schibsted grotesk': 'Schibsted Grotesk',
        'hedvig letters sans': 'Hedvig Letters Sans', 'axeptio source sans 3': 'Source Sans 3',
        'source sans pro': 'Source Sans Pro', 'montserrat': 'Montserrat', 'rubik': 'Rubik',
        'jost': 'Jost', 'zilla slab': 'Zilla Slab', 'barlow': 'Barlow', 'orbitron': 'Orbitron',
        'tomorrow': 'Tomorrow', 'fraunces': 'Fraunces', 'lora': 'Lora', 'bitter': 'Bitter',
        'manrope': 'Manrope', 'manrope-79d1da00e5f47c83': 'Manrope', 'sora': 'Sora',
        'archivo': 'Archivo', 'bebas neue': 'Bebas Neue', 'cormorant garamond': 'Cormorant Garamond',
        'work sans': 'Work Sans', 'fira sans': 'Fira Sans', 'fira code': 'Fira Code',
        'young serif': 'Young Serif', 'playfair display': 'Playfair Display',
        'dm serif display': 'DM Serif Display', 'eb garamond': 'EB Garamond',
        'libre baskerville': 'Libre Baskerville', 'merriweather': 'Merriweather',
        'spectral': 'Spectral', 'pt serif': 'PT Serif', 'martian mono': 'Martian Mono',
        'jetbrains mono': 'JetBrains Mono', 'svitlo': None, 'svitlo': None,
    }
    key = n.strip().lower()
    if key in m:
        return m[key]
    return n.strip()

def classify(name):
    if name is None:
        return 'skip'
    if is_stack(name):
        return 'system-stack'
    if NOISE.search(name):
        return 'noise'
    if ICON_HINTS.search(name):
        return 'icon-font'
    return 'family'

survey = {}
for n, cnt in raw.items():
    norm = normalize(n)
    cls = classify(norm)
    if cls == 'skip' or norm is None:
        cls = 'skip'
    survey[n] = {'count': cnt, 'normalized': norm, 'class': cls}

fams = collections.Counter()
for n, v in survey.items():
    if v['class'] == 'family':
        fams[v['normalized']] += v['count']
print(f'raw={len(raw)} distinct normalized families={len(fams)}')

# ---------- 2. google fonts match ----------
meta_raw = fetch('https://fonts.google.com/metadata/fonts')
meta_raw = meta_raw.lstrip(")]}'\n ")
meta = json.loads(meta_raw)
gf = {}
for f in meta.get('familyMetadataList', []):
    key = re.sub(r'[^a-z0-9]', '', f['family'].lower())
    gf[key] = f['family']
print(f'google fonts catalog: {len(gf)} families')

def gf_lookup(name):
    return gf.get(re.sub(r'[^a-z0-9]', '', name.lower()))

open_fams, other_fams = {}, {}
for name, cnt in fams.items():
    hit = gf_lookup(name)
    if hit:
        open_fams[name] = {'gf': hit, 'count': cnt}
    else:
        other_fams[name] = cnt
print(f'open-source hits: {len(open_fams)}   commercial/system/other: {len(other_fams)}')

# ---------- 3. download ----------
def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def dl_family(gf_name):
    d = os.path.join(FDIR, slug(gf_name))
    os.makedirs(d, exist_ok=True)
    fam = gf_name.replace(' ', '+')
    got = []
    for wght in (400, 700):
        try:
            css = fetch(f'https://fonts.googleapis.com/css2?family={fam}:wght@{wght}&display=swap')
        except Exception:
            continue
        urls = re.findall(r'src:\s*url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)', css)
        urls += re.findall(r'url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)', css)
        seen = set()
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            base = u.rsplit('/', 1)[-1]
            dest = os.path.join(d, f'{wght}-{base}')
            if not (os.path.exists(dest) and os.path.getsize(dest) > 0):
                try:
                    open(dest, 'wb').write(fetch(u, binary=True))
                except Exception:
                    continue
            got.append(os.path.basename(dest))
        time.sleep(0.15)
    # license
    for lic in ('OFL.txt', 'LICENSE.txt', 'UFL.txt', 'APACHE.txt', 'AUTHORS.txt'):
        u = f'https://raw.githubusercontent.com/google/fonts/main/ofl/{slug(gf_name)}/{lic}'
        try:
            open(os.path.join(d, lic), 'wb').write(fetch(u, binary=True))
            break
        except Exception:
            continue
    return got

results = {}
for i, (name, info) in enumerate(sorted(open_fams.items(), key=lambda x: -x[1]['count']), 1):
    gf_name = info['gf']
    try:
        files = dl_family(gf_name)
        results[gf_name] = {'files': files, 'ok': bool(files)}
    except Exception as e:
        results[gf_name] = {'files': [], 'ok': False, 'err': str(e)}
    if i % 25 == 0:
        print(f'[dl] {i}/{len(open_fams)}')

ok_n = sum(1 for v in results.values() if v['ok'])
print(f'downloaded families ok: {ok_n}/{len(results)}')

# ---------- 4. manifest ----------
COMMERCIAL_NOTES = {
    'Söhne': 'Klim Type — alt: Inter / Instrument Sans', 'PP Neue Montreal': 'Pangram Pangram — alt: Archivo / Inter Tight',
    'Suisse Intl': 'Swiss Typefaces — alt: Inter / Schibsted Grotesk', 'GT America': 'Grilli Type — alt: Archivo / Public Sans',
    'Muoto': 'Displaay — alt: Schibsted Grotesk', 'Tiempos': 'Klim — alt: Source Serif 4 / PT Serif',
    'Editorial New': 'Pangram Pangram — alt: EB Garamond', 'Berkeley Mono': 'Berkeley Graphics — alt: JetBrains Mono',
    'Commit Mono': 'paid, OFL-like EULA unavailable — alt: JetBrains Mono', 'Untitled Sans': 'Klim — alt: Inter',
    'Helvetica Now': 'Monotype — alt: Inter / Roboto', 'Neue Haas Grotesk': 'Monotype — alt: Inter',
    'Roobert': 'Displaay — alt: Manrope', 'Switzer': 'Fontshare free — see itt icon', 'Satoshi': 'Fontshare free — indian type foundry',
    'General Sans': 'Fontshare free', 'Matter': 'Displaay TR — alt: Inter', 'ABC Diatype': 'Dinamo — alt: Inter',
    'ABC Favorit': 'Dinamo — alt: Space Grotesk', 'ABC Favorit Mono': 'Dinamo — alt: Space Mono',
    'Aeonik': 'CoType — alt: Manrope', 'Graphik': 'Commercial Type — alt: Public Sans',
    'Atlas Grotesk': 'Commercial Type — alt: Roboto', 'Akzent': None,
}
manifest = {
    'survey_date': time.strftime('%Y-%m-%d'),
    'raw_names': len(raw), 'normalized_families': len(fams),
    'open_source': {name: {'google_fonts': info['gf'], 'packs_using': info['count'],
                            'downloaded': results.get(info['gf'], {}).get('files', [])}
                    for name, info in sorted(open_fams.items())},
    'not_open_source': {name: {'packs_using': cnt, 'note': COMMERCIAL_NOTES.get(name, 'commercial/system font — not redistributed')}
                        for name, cnt in sorted(other_fams.items(), key=lambda x: -x[1])},
    'icon_fonts': {n: v['count'] for n, v in survey.items() if v['class'] == 'icon-font'},
    'system_stacks': {n: v['count'] for n, v in survey.items() if v['class'] == 'system-stack'},
}
json.dump(manifest, open(os.path.join(FDIR, 'MANIFEST.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('manifest written')
