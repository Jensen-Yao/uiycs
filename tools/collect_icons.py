# -*- coding: utf-8 -*-
"""Collect the three static icon sets into icons/.

  lucide            npm  lucide-static            (ISC)
  heroicons         GitHub tailwindlabs/heroicons (MIT)
  Material Symbols  npm  @material-symbols/svg-400 (Apache-2.0)

Output layout:
  icons/lucide/*.svg
  icons/heroicons/{16-solid,20-solid,24-solid,24-outline}/*.svg
  icons/material-symbols/{outlined,rounded,sharp}/*.svg

Run tools/build_icons_index.py afterwards to build icons/INDEX.json.

Usage:
  python tools/collect_icons.py            # all three
  python tools/collect_icons.py lucide     # one set
"""
import io
import json
import os
import sys
import tarfile
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)
ICONS = os.path.join(ROOT, 'icons')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) uiycs-collector/1.0'


def fetch(url, timeout=180, tries=3):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:      # network flake; retry
            last = e
    raise RuntimeError(f'fetch failed: {url}: {last}')


def untar(data):
    return tarfile.open(fileobj=io.BytesIO(data), mode='r:gz')


def write_svg(relpath, payload):
    dest = os.path.join(ICONS, relpath)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'wb') as f:
        f.write(payload)


def collect_lucide():
    meta = json.loads(fetch('https://registry.npmjs.org/lucide-static/latest'))
    url = meta['dist']['tarball']
    print(f'lucide-static {meta["version"]} ({url.rsplit("/", 1)[-1]})')
    tf = untar(fetch(url))
    n = 0
    for m in tf.getmembers():
        if not m.isfile():
            continue
        # package/icons/<name>.svg
        parts = m.name.split('/')
        if len(parts) == 3 and parts[0] == 'package' and parts[1] == 'icons' and parts[2].endswith('.svg'):
            write_svg('lucide/' + parts[2], tf.extractfile(m).read())
            n += 1
    print(f'  lucide: {n} svg')
    return {'name': 'lucide', 'version': meta['version'], 'license': 'ISC',
            'source': 'https://github.com/lucide-icons/lucide', 'files': n}


def collect_heroicons():
    url = 'https://codeload.github.com/tailwindlabs/heroicons/tar.gz/refs/heads/master'
    print('heroicons master')
    tf = untar(fetch(url))
    n = 0
    for m in tf.getmembers():
        if not m.isfile() or not m.name.endswith('.svg'):
            continue
        parts = m.name.split('/')
        # <repo>/src/<size>/<style>/<name>.svg
        if len(parts) == 5 and parts[1] == 'src' and parts[2] in ('16', '20', '24') \
                and parts[3] in ('solid', 'outline'):
            rel = f'heroicons/{parts[2]}-{parts[3]}/{parts[4]}'
            write_svg(rel, tf.extractfile(m).read())
            n += 1
    print(f'  heroicons: {n} svg')
    return {'name': 'heroicons', 'version': 'master', 'license': 'MIT',
            'source': 'https://github.com/tailwindlabs/heroicons', 'files': n}


def collect_material_symbols():
    pkg = '@material-symbols/svg-400'
    meta = json.loads(fetch(f'https://registry.npmjs.org/{pkg.replace("/", "%2F")}/latest'))
    url = meta['dist']['tarball']
    print(f'{pkg} {meta["version"]} ({url.rsplit("/", 1)[-1]})')
    tf = untar(fetch(url, timeout=300))
    n = 0
    for m in tf.getmembers():
        if not m.isfile() or not m.name.endswith('.svg'):
            continue
        parts = m.name.split('/')
        # package/<style>/<name>.svg
        if len(parts) == 3 and parts[0] == 'package' and parts[1] in ('outlined', 'rounded', 'sharp'):
            rel = f'material-symbols/{parts[1]}/{parts[2]}'
            write_svg(rel, tf.extractfile(m).read())
            n += 1
    print(f'  material-symbols: {n} svg')
    return {'name': 'material-symbols', 'version': meta['version'], 'license': 'Apache-2.0',
            'source': 'https://github.com/google/material-design-icons', 'files': n}


SETS = {'lucide': collect_lucide, 'heroicons': collect_heroicons,
        'material-symbols': collect_material_symbols}


def main():
    want = sys.argv[1:] or list(SETS)
    os.makedirs(ICONS, exist_ok=True)
    results = []
    for name in want:
        fn = SETS.get(name)
        if not fn:
            print(f'unknown set: {name} (choose from {", ".join(SETS)})')
            continue
        results.append(fn())
    total = sum(r['files'] for r in results)
    print(f'total {total} svg in {ICONS}')
    print('next: python tools/build_icons_index.py')


if __name__ == '__main__':
    main()
