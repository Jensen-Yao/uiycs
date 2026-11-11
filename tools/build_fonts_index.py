# -*- coding: utf-8 -*-
"""统一三个字体目录为一个检索索引：fonts/INDEX.json

来源：
  fonts/            Google Fonts 开源字族（每族 400/700 正体 + OFL）
  fonts-fontshare/  Fontshare 免费商用 100 字族（多权重 + italic）
  fonts-cjk/        中文可变字体 / 手写体

用法: python build_fonts_index.py
"""
import os, json, re, time
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)


OUT = os.path.join(R, 'fonts', 'INDEX.json')


def scan_google():
    root = os.path.join(R, 'fonts')
    fams = []
    for entry in sorted(os.listdir(root)):
        d = os.path.join(root, entry)
        if not os.path.isdir(d):
            continue
        files, weights, italics = [], set(), set()
        lic = None
        for f in sorted(os.listdir(d)):
            low = f.lower()
            if low.endswith(('.woff2', '.ttf')):
                files.append(f'fonts/{entry}/{f}')
                m = re.match(r'(\d{3})(i?)-', f)
                if m:
                    weights.add(m.group(1))
                    if m.group(2):
                        italics.add(m.group(1))
            elif low in ('ofl.txt', 'license.txt', 'license'):
                lic = f'fonts/{entry}/{f}'
                try:
                    first = open(os.path.join(d, f), encoding='utf-8', errors='replace').read(400)
                except OSError:
                    first = ''
                if 'SIL OPEN FONT LICENSE' in first.upper() or 'SIL Open Font License' in first:
                    lic = ('OFL', lic)
                else:
                    lic = ('see-file', lic)
        if not files:
            continue
        lic_val, lic_path = (lic if isinstance(lic, tuple) else ('unknown', lic)) if lic else ('unknown', None)
        fams.append({
            'name': entry, 'slug': entry, 'source': 'google-fonts',
            'license': lic_val, 'license_file': lic_path,
            'dir': f'fonts/{entry}', 'files': files,
            'weights': sorted(weights), 'italics': sorted(italics),
            'cjk': False,
        })
    return fams


def scan_fontshare():
    man = os.path.join(R, 'fonts-fontshare', 'MANIFEST.json')
    if not os.path.exists(man):
        return []
    d = json.load(open(man, encoding='utf-8'))
    fams = []
    for f in d.get('fonts', []):
        files = [p.replace('\\', '/') for p in f.get('files', [])]
        weights, italics = set(), set()
        for p in files:
            base = os.path.basename(p)
            m = re.match(r'(\d{3})(i?)-', base)
            if m:
                weights.add(m.group(1))
                if m.group(2):
                    italics.add(m.group(1))
        fams.append({
            'name': f.get('name'), 'slug': f.get('slug'),
            'source': 'fontshare', 'license': f.get('license_type', 'itf_ffl'),
            'license_file': None, 'category': f.get('category'),
            'publisher': f.get('publisher'),
            'dir': f"fonts-fontshare/{f.get('slug')}", 'files': files,
            'weights': sorted(weights), 'italics': sorted(italics), 'cjk': False,
        })
    return fams


def scan_cjk():
    root = os.path.join(R, 'fonts-cjk')
    if not os.path.isdir(root):
        return []
    fams = []
    for entry in sorted(os.listdir(root)):
        d = os.path.join(root, entry)
        if not os.path.isdir(d):
            continue
        files = sorted(f'fonts-cjk/{entry}/{f}' for f in os.listdir(d)
                       if f.lower().endswith(('.ttf', '.otf', '.woff2')))
        if not files:
            continue
        variable = any('VF' in os.path.basename(p) or '[wght]' in p for p in files)
        fams.append({
            'name': entry, 'slug': entry, 'source': 'cjk',
            'license': 'OFL', 'license_file': None,
            'dir': f'fonts-cjk/{entry}', 'files': files,
            'weights': ['variable'] if variable else re.findall(r'(Light|Regular|Medium|Bold|Heavy)', ' '.join(files)),
            'italics': [], 'cjk': True, 'variable': variable,
        })
    return fams


def main():
    fams = scan_google() + scan_fontshare() + scan_cjk()
    meta = {
        'generated': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'total_families': len(fams),
        'by_source': {},
        'variable_cjk': [f['name'] for f in fams if f.get('variable')],
        'families': fams,
    }
    for f in fams:
        meta['by_source'][f['source']] = meta['by_source'].get(f['source'], 0) + 1
    json.dump(meta, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('families', len(fams), meta['by_source'])
    print('variable CJK:', meta['variable_cjk'])
    print('files total', sum(len(f['files']) for f in fams))


if __name__ == '__main__':
    main()
