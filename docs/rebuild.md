# Rebuilding the data

Nothing in `uiycs` is committed as a payload. Everything is produced by the scripts in
`tools/`. This is the full rebuild procedure, what each step costs, and how to verify the
result.

---

## Preconditions

```bash
python --version          # 3.9+
export UIYCS_HOME="$PWD"  # or let each script default to the repo root
```

The collectors use `urllib` from the standard library only. No `pip install`, no API keys.
Network access is needed for collection; querying the built data is fully offline.

---

## Rebuild order

Dependencies flow upward: collectors produce files, index builders consume them.

```text
collect_google_fonts.py ─┐
collect_fontshare.py ────┼─→ build_fonts_index.py ─→ fonts/INDEX.json
                         │
collect_icons.py ────────┴─→ build_icons_index.py ─→ icons/INDEX.json

harvest_lottiefiles.py ─┐
collect_lottie.py ──────┴─────────────────────────→ animated-icons/MANIFEST.json

packs/ + media/ ──────────────────────────────────→ build_pack_index.py ─→ index/index.json
```

The MCP server needs `index/index.json` before it will start. The other indexes are lazy —
a missing `fonts/INDEX.json` fails only `kind=font` calls.

---

## Fonts

### Google Fonts — 114 families, ~27 MB, 8–15 min

```bash
python tools/collect_google_fonts.py
```

Reads `index/index.json`, collects every `fontFamilies` name across all packs, normalizes
them, checks each against Google Fonts, downloads the hits at weights 400/700 plus
`OFL.txt`.

Slow because it makes one metadata request per family plus one request per weight. The
script prints a running tally; a family that 404s is skipped rather than fatal.

Output: `fonts/<family>/`, plus `fonts/MANIFEST.json` recording the commercial families
that were *not* downloaded and an open-source substitution for each.

### Fontshare — 100 families, ~20 MB, 3–6 min

```bash
python tools/collect_fontshare.py
```

Two requests per family: one CSS fetch for upright weights, one for italics, then one
download per returned `@font-face` URL.

Output: `fonts-fontshare/<slug>/`, plus `fonts-fontshare/MANIFEST.json`.

### Unify the font index

```bash
python tools/build_fonts_index.py
```

Scans all three font directories (`fonts/`, `fonts-fontshare/`, `fonts-cjk/`) and writes
`fonts/INDEX.json`. Detects weight from the filename prefix (`400-…`, `700i-…`), reads
`OFL.txt` to classify license, and marks variable CJK TTFs with `variable: true`.

Any family directory you add by hand is picked up automatically — the builder walks the
filesystem, not a fixed list.

---

## Icons — 27,278 SVG, ~17 MB, 2–5 min

```bash
python tools/collect_icons.py             # all three sets
python tools/collect_icons.py lucide      # or one at a time
```

Downloads complete tarballs rather than per-file requests:

| Set | Source | Size |
|---|---|---|
| lucide | `registry.npmjs.org/lucide-static/latest` → `dist.tarball` | 7.4 MB |
| heroicons | `codeload.github.com/tailwindlabs/heroicons/tar.gz/refs/heads/master` | 0.7 MB |
| Material Symbols | `registry.npmjs.org/@material-symbols/svg-400/latest` → `dist.tarball` | 1.9 MB |

Each is extracted in memory with `tarfile` and only the `.svg` members matching the expected
paths are written out.

```bash
python tools/build_icons_index.py
```

Writes `icons/INDEX.json` (`{name: [relative paths]}`, one key per unique icon name, values
across every set and variant) and `icons/MANIFEST.json` (per-set version, license, source,
file count).

The set registry lives in `SETS` at the top of `build_icons_index.py`. To add a fourth set,
drop its SVGs under `icons/<set>/` and add one tuple.

---

## Animations — 750 items, ~67 MB, 10–20 min

### Free-tier harvest

```bash
python tools/harvest_lottiefiles.py
```

Requires a URL list: `index/lf_urls.json`, produced by walking the free classification
pages and extracting `assets-v2.lottiefiles.com/…` URLs. The script downloads each asset,
unpacks the dotLottie zip, keeps `animations/*.json` as well as the original `.lottie`.

### Curated CDN list

```bash
python tools/collect_lottie.py
```

Downloads the URLs in `URLS` at the top of the script, validates each as real Lottie JSON
(`layers` or `assets` plus a `v` field — this rejects HTML error pages that return 200),
and files them by category.

Optional: set `DOTLOTTIE_FIXTURES` to a directory of `.lottie` zip fixtures to fold those
in as well.

Output: `animated-icons/MANIFEST.json`, one record per file with `source` and `license`.

---

## Reference packs

The pack collectors are not part of this repository — capture is a separate pipeline.
`tools/build_pack_index.py` consumes whatever that pipeline produces, as long as it matches
the layout in [data-sources.md](data-sources.md):

```text
packs/<slug>.json                     design tokens + components + views
packs/<slug>.capture.json             optional iOS screen flow
media/<slug>/<role>.webp|webm         poster, fullpage, mobile, section-NN, motion, thumb, icon
index/previews.json                   {"items": [{id, name, …}]}
index/rename_map.json                 {id: {slug, files: {<original basename>: {…}}}}
```

```bash
python tools/build_pack_index.py
```

Emits `index/index.json`:

```jsonc
{
  "version": 2,
  "count": 685,
  "items": [{
    "id": "…", "slug": "nominal", "name": "Nominal", "platform": "web",
    "tagline": "…", "theme": "…", "site": "https://nominal.io/",
    "capturedAt": "2026-10-21T11:39:52.032Z",
    "colors": [{ "hex": "#000000", "role": "Surface" }],
    "typography": [{ "role": "Heading", "family": "muoto", "size": 72, "weight": 400 }],
    "fontFamilies": ["Inter", "muoto"],
    "geometry": { "headingWidth": 672, "buttonShape": "0 px" },
    "components": ["Landing page", "Hero", "Navigation"],
    "screens": [{ "id": "…", "title": "…", "image": "/abs/…", "patterns": ["…"] }],
    "views":   [{ "label": "Desktop", "image": "/abs/…" }],
    "fullPage": "/abs/…", "poster": "/abs/…", "motion": "/abs/…", "cover": "/abs/…"
  }]
}
```

Paths are absolute and resolved at build time. Rebuild after moving the data root.

---

## Integrity check

Run after any rebuild. All four counts must be zero.

```bash
python - <<'PY'
import json, os
R = os.environ.get('UIYCS_HOME') or os.getcwd()
rows = []

for name, rel in (('lottie', 'animated-icons/MANIFEST.json'),
                  ('fontshare', 'fonts-fontshare/MANIFEST.json')):
    m = json.load(open(os.path.join(R, rel), encoding='utf-8'))
    paths = ([x['file'] for x in m['items']] if 'items' in m
             else [f for x in m['fonts'] for f in x['files']])
    rows.append((name, paths, R))

fi = json.load(open(os.path.join(R, 'fonts/INDEX.json'), encoding='utf-8'))
rows.append(('fonts', [f for fam in fi['families'] for f in fam['files']], R))

ii = json.load(open(os.path.join(R, 'icons/INDEX.json'), encoding='utf-8'))
rows.append(('icons', [p for ps in ii.values() for p in ps], os.path.join(R, 'icons')))

for name, paths, base in rows:
    dangling = sum(1 for p in paths if not os.path.exists(os.path.join(base, p)))
    print(f'{name:10} entries {len(paths):>6}  dangling {dangling}')
PY
```

Expected:

```text
lottie     entries    750  dangling 0
fontshare  entries    697  dangling 0
fonts      entries   2292  dangling 0
icons      entries  27278  dangling 0
```

A non-zero count means a manifest references a file that is not on disk — either the
collector was interrupted or the data root moved without rebuilding the index.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| server exits immediately | `index/index.json` missing | run `build_pack_index.py` |
| `kind=font` returns nothing | `fonts/INDEX.json` missing or stale | run `build_fonts_index.py` |
| icon paths point at nothing | index built before icons landed | run `build_icons_index.py` |
| font family found, `files: []` | directory exists but holds no woff2/ttf | re-run the collector for that family |
| Fontshare 404 on every file | you used `styles[].file` instead of the CSS API | use the CSS2 path in `collect_fontshare.py` |
| Lottie file is HTML | upstream returned an error page with 200 | the validator in `collect_lottie.py` rejects it; re-download |
| CJK family has 200 shards | Google CSS2 splits by `unicode-range` | intended; use `fonts-cjk/` for a single-file variable TTF |

---

## Cost summary

| Step | Time | Disk |
|---|---|---|
| Google Fonts | 8–15 min | 27 MB |
| Fontshare | 3–6 min | 21 MB |
| Icons | 2–5 min | 17 MB |
| Animations | 10–20 min | 67 MB |
| CJK fonts | 2–4 min | 69 MB |
| Reference packs | — (external pipeline) | 7.8 GB |
| **Total** | **~30–50 min** | **~8.0 GB** |

Longest single step is the LottieFiles harvest, which is rate-limited by design and
degrades gracefully — an interrupted run leaves a valid manifest for whatever already
landed.
