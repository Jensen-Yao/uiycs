# -*- coding: utf-8 -*-
"""生成 icons/INDEX.json 与 icons/MANIFEST.json。

INDEX.json 面向检索：{name: [relative paths]}，同名跨 set 合并。
MANIFEST.json 面向溯源：每套的来源、版本、许可、数量。

用法: python build_icons_index.py
"""
import os, json, time
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)


ICONS = os.path.join(R, 'icons')

SETS = [
    ('lucide', 'lucide', '1.71.0', 'ISC', 'https://github.com/lucide-icons/lucide', 'stroke, 24px grid, 2px'),
    ('heroicons', 'heroicons', 'master@2026-11', 'MIT', 'https://github.com/tailwindlabs/heroicons', 'fill/stroke, 16/20/24'),
    ('material-symbols', 'material-symbols', '0.48.3', 'Apache-2.0', 'https://github.com/google/material-design-icons', 'filled + outlined, 24px'),
]


def scan():
    index, sets = {}, []
    for name, dirname, ver, lic, src, note in SETS:
        root = os.path.join(ICONS, dirname)
        if not os.path.isdir(root):
            continue
        variants = {}
        flat = [f for f in sorted(os.listdir(root)) if f.endswith('.svg')]
        if flat:
            base_names = set()
            for f in flat:
                stem = f[:-4]
                base_names.add(stem)
                index.setdefault(stem, []).append(f'{dirname}/{f}')
            variants['flat'] = {'files': len(flat), 'unique_icons': len(base_names)}
        for entry in sorted(os.listdir(root)):
            sub = os.path.join(root, entry)
            if not os.path.isdir(sub):
                continue
            files = sorted(f for f in os.listdir(sub) if f.endswith('.svg'))
            # material-symbols 把 filled 变体放在同目录，按文件名后缀区分
            base_names = set()
            for f in files:
                stem = f[:-4]
                if dirname == 'material-symbols' and stem.endswith('-fill'):
                    stem = stem[:-5]
                base_names.add(stem)
                index.setdefault(stem, []).append(f'{dirname}/{entry}/{f}')
            variants[entry] = {'files': len(files), 'unique_icons': len(base_names)}
        sets.append({
            'name': name, 'dir': dirname, 'version': ver, 'license': lic,
            'source': src, 'note': note, 'variants': variants,
            'total_files': sum(v['files'] for v in variants.values()),
        })
    return index, sets


def main():
    index, sets = scan()
    total = sum(s['total_files'] for s in sets)
    meta = {
        'generated': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'total_files': total,
        'unique_names': len(index),
        'sets': sets,
    }
    json.dump(meta, open(os.path.join(ICONS, 'MANIFEST.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    json.dump(index, open(os.path.join(ICONS, 'INDEX.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(f'sets {len(sets)}  files {total}  unique names {len(index)}')
    for s in sets:
        print(' ', s['name'], s['version'], s['license'], s['total_files'], list(s['variants']))


if __name__ == '__main__':
    main()
