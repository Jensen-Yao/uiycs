# -*- coding: utf-8 -*-
"""Capture one live site into a uiycs reference pack.

Produces the exact directory shape the index builder and MCP server expect:

  packs/<slug>.json          design tokens extracted from computed style
  media/<slug>/poster.webp   viewport screenshot (1280x800)
  media/<slug>/fullpage.webp full-page screenshot
  media/<slug>/mobile.webp   mobile viewport screenshot (390x844)
  media/<slug>/thumb.webp    list thumbnail (640 wide)

No account, no API. You point it at a URL you have the right to view.

Usage:
  python tools/capture_site.py https://example.com --name "Example"
  python tools/capture_site.py https://example.com --slug example --theme "Docs site"
  python tools/capture_site.py https://a.com https://b.com --batch

Requires:
  pip install playwright pillow
  python -m playwright install chromium
"""
import argparse
import datetime
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('UIYCS_HOME') or (
    os.path.dirname(_HERE) if os.path.basename(_HERE) == 'tools' else _HERE)

DESKTOP = {'width': 1280, 'height': 800}
MOBILE = {'width': 390, 'height': 844}


def slugify(text):
    s = re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
    return s or 'site'


def slug_from_url(url):
    host = re.sub(r'^https?://', '', url).split('/')[0]
    host = host.replace('www.', '')
    return slugify(host.split('.')[0])


PALETTE_JS = r"""
() => {
  const counts = {};
  const bump = (v, role) => {
    if (!v || v === 'rgba(0, 0, 0, 0)' || v === 'transparent' || v === 'none') return;
    const key = v + '|' + role;
    counts[key] = (counts[key] || 0) + 1;
  };
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    const s = getComputedStyle(el);
    bump(s.backgroundColor, 'Surface');
    bump(s.color, 'Text');
  }
  const body = getComputedStyle(document.body);
  bump(body.backgroundColor, 'Surface');
  bump(body.color, 'Text');
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 60)
    .map(([k, n]) => {
      const [value, role] = k.split('|');
      return { value, role, count: n };
    });
}
"""

TYPE_JS = r"""
() => {
  const pick = (sel, role) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const s = getComputedStyle(el);
    const size = parseFloat(s.fontSize);
    if (!size) return null;
    return {
      role,
      family: s.fontFamily,
      size: Math.round(size * 100) / 100,
      weight: parseInt(s.fontWeight, 10) || 400,
      lineHeight: s.lineHeight === 'normal' ? null : Math.round(parseFloat(s.lineHeight) * 100) / 100,
      letterSpacing: s.letterSpacing === 'normal' ? null : Math.round(parseFloat(s.letterSpacing) * 100) / 100
    };
  };
  return [
    pick('h1', 'Heading'),
    pick('h2', 'Subheading'),
    pick('p', 'Body'),
    pick('button, a[role=button], .btn', 'Button'),
    pick('nav a, header a', 'Nav')
  ].filter(Boolean);
}
"""

FONTS_JS = r"""
() => {
  const fams = new Set();
  for (const el of document.querySelectorAll('h1,h2,h3,p,button,a,nav,span')) {
    const f = getComputedStyle(el).fontFamily;
    if (!f) continue;
    const first = f.split(',')[0].replace(/["']/g, '').trim();
    if (first) fams.add(first);
  }
  return [...fams].slice(0, 12);
}
"""

COMPONENTS_JS = r"""
() => {
  const out = new Set();
  const add = (t) => { t = (t || '').trim(); if (t && t.length < 60) out.add(t); };
  for (const el of document.querySelectorAll('nav,header,footer,main,form,table,dialog')) {
    const label = el.getAttribute('aria-label') || el.getAttribute('role') || el.tagName.toLowerCase();
    add(label);
  }
  for (const el of document.querySelectorAll('h1,h2')) {
    add(el.textContent);
  }
  return [...out].slice(0, 20);
}
"""

META_JS = r"""
() => ({
  title: document.title || '',
  description: (document.querySelector('meta[name=description]') || {}).content || '',
  lang: document.documentElement.lang || ''
})
"""


def to_hex(value):
    """rgba()/rgb() → #RRGGBB, dropping alpha < 1 as a lighter tint of itself."""
    m = re.match(r'rgba?\(([^)]+)\)', value or '')
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split(',')]
    if len(parts) < 3:
        return None
    try:
        r, g, b = (int(float(p)) for p in parts[:3])
    except ValueError:
        return None
    alpha = float(parts[3]) if len(parts) > 3 else 1.0
    if alpha < 0.25:
        return None
    return '#{:02X}{:02X}{:02X}'.format(r, g, b)


def capture_one(page, url, slug, name, theme, out_packs, out_media):
    print(f'  {url}')
    page.set_viewport_size(DESKTOP)
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=45000)
    except Exception:
        page.goto(url, wait_until='load', timeout=45000)
    try:
        page.wait_for_load_state('networkidle', timeout=8000)
    except Exception:
        pass  # long-poll / websocket / analytics keep the connection open
    page.wait_for_timeout(1500)

    meta = page.evaluate(META_JS)
    palette_raw = page.evaluate(PALETTE_JS)
    typography = page.evaluate(TYPE_JS)
    fonts = page.evaluate(FONTS_JS)
    components = page.evaluate(COMPONENTS_JS)

    media_dir = os.path.join(out_media, slug)
    os.makedirs(media_dir, exist_ok=True)

    poster_png = os.path.join(media_dir, '_poster.png')
    full_png = os.path.join(media_dir, '_full.png')
    page.screenshot(path=poster_png)
    page.screenshot(path=full_png, full_page=True)

    page.set_viewport_size(MOBILE)
    page.wait_for_timeout(600)
    mobile_png = os.path.join(media_dir, '_mobile.png')
    page.screenshot(path=mobile_png)

    # convert to webp and drop the png intermediates
    from PIL import Image
    sizes = {}
    for src, dst, quality in ((poster_png, 'poster.webp', 86),
                              (full_png, 'fullpage.webp', 80),
                              (mobile_png, 'mobile.webp', 86)):
        dst_path = os.path.join(media_dir, dst)
        im = Image.open(src).convert('RGB')
        if dst == 'fullpage.webp' and im.height > 12000:
            im = im.crop((0, 0, im.width, 12000))
        im.save(dst_path, 'WEBP', quality=quality, method=6)
        sizes[dst] = im.size
        os.remove(src)

    # thumbnail from the poster
    thumb_path = os.path.join(media_dir, 'thumb.webp')
    im = Image.open(os.path.join(media_dir, 'poster.webp')).convert('RGB')
    w = 640
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    im.save(thumb_path, 'WEBP', quality=82, method=6)

    palette, seen = [], set()
    for item in palette_raw:
        hexv = to_hex(item['value'])
        if not hexv or hexv in seen:
            continue
        seen.add(hexv)
        palette.append({'hex': hexv, 'role': item['role']})
        if len(palette) >= 6:
            break

    record = {
        'name': name or meta.get('title') or slug,
        'slug': slug,
        'platform': 'web',
        'tagline': meta.get('description', '')[:160] or (theme or ''),
        'theme': theme or meta.get('description', '')[:160] or '',
        'site': url,
        'capturedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'colors': palette,
        'inspector': {
            'version': 1,
            'source': 'computed-style',
            'palette': palette,
            'typography': typography,
            'views': [
                {'label': 'Desktop', 'url': f'media/{slug}/poster.webp',
                 'width': sizes['poster.webp'][0], 'height': sizes['poster.webp'][1]},
                {'label': 'Mobile', 'url': f'media/{slug}/mobile.webp',
                 'width': sizes['mobile.webp'][0], 'height': sizes['mobile.webp'][1]},
            ],
            'geometry': {}
        },
        'typography': typography,
        'fontFamilies': fonts,
        'componentNames': components,
        'summary': f'{len(components)} named regions, {len(palette)} palette roles',
    }

    os.makedirs(out_packs, exist_ok=True)
    pack_path = os.path.join(out_packs, slug + '.json')
    json.dump(record, open(pack_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    kb = sum(os.path.getsize(os.path.join(media_dir, f)) for f in os.listdir(media_dir))
    print(f'    pack  {pack_path}')
    print(f'    media {len(os.listdir(media_dir))} files, {kb / 1024:.0f} KB')
    print(f'    {len(palette)} colors · {len(typography)} type roles · {len(fonts)} families')
    return record


def main():
    ap = argparse.ArgumentParser(description='Capture a site into a uiycs reference pack')
    ap.add_argument('urls', nargs='+', help='one or more http(s) URLs')
    ap.add_argument('--slug', help='pack slug (default: derived from host)')
    ap.add_argument('--name', help='display name')
    ap.add_argument('--theme', help='one-line theme/category')
    ap.add_argument('--batch', action='store_true', help='capture every URL in one browser session')
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('playwright missing — run: pip install playwright && python -m playwright install chromium')

    packs_dir = os.path.join(ROOT, 'packs')
    media_dir = os.path.join(ROOT, 'media')

    if not args.batch and len(args.urls) > 1:
        args.urls = args.urls[:1]
        print('note: multiple URLs need --batch; capturing the first')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport=DESKTOP,
            device_scale_factor=1,
            user_agent=('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
        )
        page = ctx.new_page()
        ok, fail = 0, 0
        for i, url in enumerate(args.urls):
            slug = (args.slug if (args.slug and len(args.urls) == 1)
                    else slug_from_url(url))
            name = args.name if (args.name and len(args.urls) == 1) else None
            try:
                capture_one(page, url, slug, name, args.theme, packs_dir, media_dir)
                ok += 1
            except Exception as e:
                fail += 1
                print(f'    FAILED: {type(e).__name__}: {str(e)[:160]}')
        browser.close()

    print(f'\ncaptured {ok} pack(s), {fail} failed')
    print('next: python tools/build_pack_index.py')


if __name__ == '__main__':
    main()
