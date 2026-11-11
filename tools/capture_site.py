# -*- coding: utf-8 -*-
"""Capture one live site into a uiycs reference pack.

Produces the directory shape the index builder and MCP server expect, and extracts
the semantic layer search actually needs: per-section screenshots, per-line text
with bounding boxes, geometry, and inferred interaction patterns.

  packs/<slug>.json          tokens + typed screens
  media/<slug>/poster.webp   viewport screenshot (1280x800)
  media/<slug>/fullpage.webp full-page screenshot
  media/<slug>/mobile.webp   mobile viewport screenshot (390x844)
  media/<slug>/thumb.webp    list thumbnail (640 wide)
  media/<slug>/section-01.webp … section-NN.webp

Text comes from two places, deliberately:

  DOM  — exact. Every visible text node with its page-space box. Primary source.
  OCR  — fallback. Catches text baked into canvas, images and SVG. Optional.

Usage:
  python tools/capture_site.py https://example.com --name "Example"
  python tools/capture_site.py https://example.com --slug ex --no-ocr
  python tools/capture_site.py https://a.com https://b.com --batch --max-sections 8

Requires:
  pip install playwright pillow
  python -m playwright install chromium
  pip install rapidocr-onnxruntime    # only for OCR fallback
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
SECTION_H = 800
MAX_LINES = 400

# ----------------------------------------------------------------------------- js

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
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 60)
    .map(([k, n]) => { const [value, role] = k.split('|'); return { value, role, count: n }; });
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
      role, family: s.fontFamily, size: Math.round(size * 100) / 100,
      weight: parseInt(s.fontWeight, 10) || 400,
      lineHeight: s.lineHeight === 'normal' ? null : Math.round(parseFloat(s.lineHeight) * 100) / 100,
      letterSpacing: s.letterSpacing === 'normal' ? null : Math.round(parseFloat(s.letterSpacing) * 100) / 100
    };
  };
  return [
    pick('h1', 'Heading'), pick('h2', 'Subheading'), pick('p', 'Body'),
    pick('button, a[role=button], .btn', 'Button'), pick('nav a, header a', 'Nav')
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

META_JS = r"""
() => ({
  title: document.title || '',
  description: (document.querySelector('meta[name=description]') || {}).content || '',
  lang: document.documentElement.lang || '',
  scrollHeight: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
  viewportWidth: window.innerWidth
})
"""

# every visible text node with a page-space box; this is the exact layer
TEXT_JS = r"""
(limit) => {
  const skip = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'svg', 'SVG', 'PATH', 'path']);
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      const t = (n.nodeValue || '').trim();
      if (t.length < 2) return NodeFilter.FILTER_REJECT;
      const p = n.parentElement;
      if (!p || skip.has(p.tagName)) return NodeFilter.FILTER_REJECT;
      const s = getComputedStyle(p);
      if (s.visibility === 'hidden' || s.display === 'none' || parseFloat(s.opacity) < 0.1) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  let node;
  while ((node = walker.nextNode()) && out.length < limit) {
    const el = node.parentElement;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    out.push({
      text: node.nodeValue.replace(/\s+/g, ' ').trim(),
      tag: el.tagName.toLowerCase(),
      x: r.left + window.scrollX,
      y: r.top + window.scrollY,
      width: r.width,
      height: r.height,
      fontSize: parseFloat(getComputedStyle(el).fontSize) || 0
    });
  }
  return out;
}
"""

GEOMETRY_JS = r"""
() => {
  const box = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { width: Math.round(r.width), height: Math.round(r.height), x: Math.round(r.left) };
  };
  const radius = (sel) => {
    const el = document.querySelector(sel);
    return el ? getComputedStyle(el).borderRadius : null;
  };
  const main = document.querySelector('main') || document.body;
  return {
    headingWidth: box('h1') ? box('h1').width : null,
    headingBox: box('h1'),
    buttonShape: radius('button, a[role=button], .btn'),
    buttonBox: box('button, a[role=button], .btn'),
    contentWidth: Math.round(main.getBoundingClientRect().width),
    viewportWidth: window.innerWidth,
    containerMaxWidth: getComputedStyle(main).maxWidth
  };
}
"""

PATTERNS_JS = r"""
() => {
  const has = (sel) => !!document.querySelector(sel);
  const count = (sel) => document.querySelectorAll(sel).length;
  const p = [];
  if (has('nav, header nav, [role=navigation]')) p.push('Navigation');
  if (has('form')) p.push('Form');
  if (has('table, [role=grid], [role=table]')) p.push('Data table');
  if (has('dialog, [role=dialog], [aria-modal=true]')) p.push('Dialog');
  if (has('input[type=search], [role=search]')) p.push('Search');
  if (has('[aria-expanded]')) p.push('Disclosure');
  if (has('input[type=checkbox], input[type=radio]')) p.push('Selection controls');
  if (has('input, textarea, select')) p.push('Input fields');
  if (has('[role=tab], [role=tablist]')) p.push('Tabs');
  if (has('[aria-live]')) p.push('Live region');
  if (has('img, picture, video')) p.push('Media');
  if (count('a') > 8) p.push('Link grid');
  if (has('footer')) p.push('Footer');
  if (has('[class*=card], [class*=Card]')) p.push('Cards');
  return p;
}
"""


# ----------------------------------------------------------------------- helpers

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-') or 'site'


def slug_from_url(url):
    host = re.sub(r'^https?://', '', url).split('/')[0].replace('www.', '')
    return slugify(host.split('.')[0])


def to_hex(value):
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
    if (float(parts[3]) if len(parts) > 3 else 1.0) < 0.25:
        return None
    return '#{:02X}{:02X}{:02X}'.format(r, g, b)


def _ocr_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
        return RapidOCR()
    except Exception:
        return None


def ocr_image(engine, path, offset_y=0):
    """OCR one screenshot. Returns lines in page space."""
    if engine is None:
        return []
    try:
        result, _ = engine(path)
    except Exception:
        return []
    out = []
    for item in result or []:
        try:
            box, text, conf = item[0], item[1], item[2]
        except (IndexError, TypeError):
            continue
        if not text or len(str(text).strip()) < 2:
            continue
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        out.append({
            'text': str(text).strip(),
            'box': {'x': round(min(xs)), 'y': round(min(ys) + offset_y),
                    'width': round(max(xs) - min(xs)), 'height': round(max(ys) - min(ys))},
            'confidence': round(float(conf), 3)
        })
    return out


def section_title(lines):
    if not lines:
        return ''
    best = max(lines, key=lambda l: (l.get('height') or 0) * (l.get('width') or 0))
    return (best.get('text') or '')[:70]


def merge_lines(dom_lines, ocr_lines, section_top, section_bottom):
    """DOM lines win; OCR fills gaps where DOM has no text in that band."""
    def in_band(l):
        y = l.get('y') or l.get('box', {}).get('y', 0)
        return section_top - 40 <= y < section_bottom

    dom = [l for l in dom_lines if in_band(l)]
    covered = [(l['y'], l['y'] + l['height']) for l in dom]
    extra = []
    for o in ocr_lines:
        oy = o['box']['y']
        overlap = any(oy + 20 >= a and oy <= b for a, b in covered)
        if not overlap:
            extra.append({'text': o['text'], 'box': o['box'],
                          'confidence': o['confidence'], 'source': 'ocr'})
    return dom, extra


# ---------------------------------------------------------------------- capture

def scroll_through(page, meta):
    """Trigger lazy loading, then return to top."""
    height = meta.get('scrollHeight') or 0
    step = 700
    y = 0
    while y < height:
        page.evaluate(f'window.scrollTo(0, {y})')
        page.wait_for_timeout(120)
        y += step
        height = page.evaluate('Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)')
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_timeout(500)
    return page.evaluate('Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)')


def capture_one(page, url, slug, name, theme, max_sections, use_ocr, out_packs, out_media):
    from PIL import Image

    print(f'  {url}')
    page.set_viewport_size(DESKTOP)
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=45000)
    except Exception:
        page.goto(url, wait_until='load', timeout=45000)
    try:
        page.wait_for_load_state('networkidle', timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(1200)

    meta = page.evaluate(META_JS)
    total_height = scroll_through(page, meta)
    meta['scrollHeight'] = total_height

    palette_raw = page.evaluate(PALETTE_JS)
    typography = page.evaluate(TYPE_JS)
    fonts = page.evaluate(FONTS_JS)
    geometry = page.evaluate(GEOMETRY_JS)
    patterns = page.evaluate(PATTERNS_JS)
    dom_lines = page.evaluate(TEXT_JS, MAX_LINES)

    media_dir = os.path.join(out_media, slug)
    os.makedirs(media_dir, exist_ok=True)

    def shot(name_, clip=None, fmt='png'):
        tmp = os.path.join(media_dir, '_' + name_ + '.' + fmt)
        if clip:
            page.screenshot(path=tmp, clip=clip)
        else:
            page.screenshot(path=tmp)
        return tmp

    # poster / fullpage
    poster_png = shot('poster')
    page.set_viewport_size({'width': DESKTOP['width'], 'height': min(total_height, 16000)})
    page.wait_for_timeout(400)
    full_png = shot('full')
    page.set_viewport_size(DESKTOP)
    page.wait_for_timeout(400)

    # mobile
    page.set_viewport_size(MOBILE)
    page.wait_for_timeout(600)
    mobile_png = shot('mobile')
    page.set_viewport_size(DESKTOP)
    page.wait_for_timeout(300)

    engine = _ocr_engine() if use_ocr else None
    if use_ocr and engine is None:
        print('    note: rapidocr unavailable, DOM text only')

    # ---- sections: scroll to each band, shoot the viewport, crop the tail
    sections = []
    n = 0
    y = 0
    while y < total_height and n < max_sections:
        page.evaluate(f"window.scrollTo({{top: {y}, behavior: 'instant'}})")
        page.wait_for_timeout(260)
        real_y = page.evaluate('window.scrollY')
        h = min(SECTION_H, total_height - real_y)
        if h < 120:
            break
        n += 1
        sid = f'section-{n:02d}'
        tmp = os.path.join(media_dir, '_' + sid + '.png')
        try:
            page.screenshot(path=tmp)
        except Exception as e:
            print(f'    section {sid} failed: {str(e)[:80]}')
            y += SECTION_H
            continue
        if h < SECTION_H:
            im = Image.open(tmp)
            im.crop((0, 0, im.width, h)).save(tmp)
        dest = os.path.join(media_dir, sid + '.webp')
        Image.open(tmp).convert('RGB').save(dest, 'WEBP', quality=84, method=6)

        ocr_lines = ocr_image(engine, tmp, offset_y=real_y) if engine else []
        os.remove(tmp)

        dom, extra = merge_lines(dom_lines, ocr_lines, real_y, real_y + h)
        text = ' '.join(l['text'] for l in dom)
        if not text and extra:
            text = ' '.join(l['text'] for l in extra)

        sections.append({
            'id': sid,
            'title': section_title(dom) or section_title(ocr_lines) or '',
            'text': text[:2000],
            'lines': [
                {'text': l['text'],
                 'box': {'x': round(l['x']), 'y': round(l['y']),
                         'width': round(l['width']), 'height': round(l['height'])},
                 'confidence': 1.0, 'source': 'dom'}
                for l in dom[:120]
            ] + extra[:60],
            'imageUrl': f'media/{slug}/{sid}.webp',
            'width': DESKTOP['width'], 'height': h, 'scrollY': real_y,
        })
        y = real_y + SECTION_H
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    page.wait_for_timeout(200)

    # ---- webp conversions
    sizes = {}
    for src, dst, quality, cap in (
        (poster_png, 'poster.webp', 86, None),
        (full_png, 'fullpage.webp', 78, 14000),
        (mobile_png, 'mobile.webp', 86, None),
    ):
        path = os.path.join(media_dir, dst)
        im = Image.open(src).convert('RGB')
        if cap and im.height > cap:
            im = im.crop((0, 0, im.width, cap))
        im.save(path, 'WEBP', quality=quality, method=6)
        sizes[dst] = im.size
        os.remove(src)

    thumb = os.path.join(media_dir, 'thumb.webp')
    im = Image.open(os.path.join(media_dir, 'poster.webp')).convert('RGB')
    w = 640
    im.resize((w, int(im.height * w / im.width)), Image.LANCZOS).save(thumb, 'WEBP', quality=82, method=6)

    # ---- palette
    palette, seen = [], set()
    for item in palette_raw:
        hexv = to_hex(item['value'])
        if not hexv or hexv in seen:
            continue
        seen.add(hexv)
        palette.append({'hex': hexv, 'role': item['role']})
        if len(palette) >= 6:
            break

    ocr_total = sum(1 for s in sections for l in s['lines'] if l.get('source') == 'ocr')

    record = {
        'name': name or meta.get('title') or slug,
        'slug': slug,
        'platform': 'web',
        'tagline': (meta.get('description') or '')[:160] or (theme or ''),
        'theme': theme or (meta.get('description') or '')[:160],
        'site': url,
        'lang': meta.get('lang') or '',
        'capturedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'colors': palette,
        'inspector': {
            'version': 2,
            'source': 'computed-style+dom',
            'palette': palette,
            'typography': typography,
            'geometry': geometry,
            'views': [
                {'label': 'Desktop', 'url': f'media/{slug}/poster.webp',
                 'width': sizes['poster.webp'][0], 'height': sizes['poster.webp'][1]},
                {'label': 'Mobile', 'url': f'media/{slug}/mobile.webp',
                 'width': sizes['mobile.webp'][0], 'height': sizes['mobile.webp'][1]},
            ],
        },
        'capture': {
            'capturedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'pageHeight': total_height,
            'sections': sections,
        },
        'typography': typography,
        'fontFamilies': fonts,
        'componentNames': [s['title'] for s in sections if s['title']][:12] + patterns,
        'patterns': patterns,
        'geometry': geometry,
        'summary': f'{len(sections)} sections · {len(dom_lines)} text nodes · {len(patterns)} patterns',
    }

    os.makedirs(out_packs, exist_ok=True)
    pack_path = os.path.join(out_packs, slug + '.json')
    json.dump(record, open(pack_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    media_files = [f for f in os.listdir(media_dir)]
    kb = sum(os.path.getsize(os.path.join(media_dir, f)) for f in media_files)
    print(f'    {len(sections)} sections · {len(dom_lines)} text nodes · {ocr_total} OCR lines')
    print(f'    {len(palette)} colors · {len(typography)} type roles · {len(patterns)} patterns')
    print(f'    media {len(media_files)} files, {kb / 1024:.0f} KB')
    return record


# ------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description='Capture a site into a uiycs reference pack')
    ap.add_argument('urls', nargs='+')
    ap.add_argument('--slug')
    ap.add_argument('--name')
    ap.add_argument('--theme')
    ap.add_argument('--batch', action='store_true')
    ap.add_argument('--max-sections', type=int, default=12)
    ap.add_argument('--no-ocr', action='store_true')
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('playwright missing — run: pip install playwright && python -m playwright install chromium')

    packs_dir = os.path.join(ROOT, 'packs')
    media_dir = os.path.join(ROOT, 'media')
    use_ocr = not args.no_ocr

    if not args.batch and len(args.urls) > 1:
        args.urls = args.urls[:1]
        print('note: multiple URLs need --batch; capturing the first')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport=DESKTOP, device_scale_factor=1,
            user_agent=('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'))
        page = ctx.new_page()
        ok = fail = 0
        for url in args.urls:
            slug = args.slug if (args.slug and len(args.urls) == 1) else slug_from_url(url)
            name = args.name if (args.name and len(args.urls) == 1) else None
            try:
                capture_one(page, url, slug, name, args.theme,
                            args.max_sections, use_ocr, packs_dir, media_dir)
                ok += 1
            except Exception as e:
                fail += 1
                print(f'    FAILED: {type(e).__name__}: {str(e)[:160]}')
        browser.close()

    print(f'\ncaptured {ok} pack(s), {fail} failed')
    print('next: python tools/build_pack_index.py')


if __name__ == '__main__':
    main()
