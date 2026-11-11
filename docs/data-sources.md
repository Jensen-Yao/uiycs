# Data sources

Every payload in a `uiycs` deployment is rebuilt from a public source by a script in
`tools/`. This document records what each source is, what it yields, its license, and what
the collector actually does.

The repository does not ship payloads. Total data at full size: **8.4 GB / 39,050 files**.

---

## 1. Reference packs — `packs/` + `media/`

**Scale:** 685 products (web + iOS), 763 record files, 7,067 media files, 7.8 GB.

**Shape:** one product per pack.

```text
packs/<slug>.json          design tokens + component inventory + view list
packs/<slug>.capture.json  iOS-specific: per-screen OCR text, patterns, actions
media/<slug>/poster.webp   hero shot
media/<slug>/fullpage.webp full-page capture
media/<slug>/mobile.webp   mobile viewport capture
media/<slug>/section-01..  per-section crops
media/<slug>/motion.webm   scroll/transition recording
media/<slug>/thumb.webp    list thumbnail
media/<slug>/icon.webp     product icon
```

**Per-pack record:**

| Field | Content |
|---|---|
| `colors` | extracted palette with role labels |
| `inspector.typography` | role, family, size, weight, line-height, letter-spacing |
| `inspector.palette` | hex + role |
| `inspector.views` | label, url, width, height for every captured view |
| `componentNames` | named UI components found in the capture |
| `iosCapture.screens[]` | `id`, `title`, `text` (full OCR), `patterns`, `action` |
| `summary` / `theme` | one-line and categorical description |

The OCR text and the pattern labels are what make search work on content ("cancellation
policy", "tab bar") rather than only on names.

**Capture is a first-class tool.** `tools/capture_site.py` drives Chromium through
Playwright, extracts palette and typography from computed style, writes the screenshots
as webp, and emits this exact layout. Three worked examples live in
[`examples/demo-packs/`](../examples/README.md). `tools/build_pack_index.py` reads only
`packs/` and `media/` — legacy `index/previews.json` / `rename_map.json` are merged when
present but are no longer required.

**Rights.** A pack is a capture of a third-party product made for design study. It is not
a license to reuse that product's branding, logotype, copy or imagery. See the note in
[`../skill/uiycs-ui/SKILL.md`](../skill/uiycs-ui/SKILL.md).

---

## 2. Web fonts — `fonts/`

**Scale:** 114 families, ~2,000 files, 27 MB.

**Source:** [Google Fonts](https://fonts.google.com), two endpoints:

```text
https://fonts.googleapis.com/css2?family=<Family>:wght@400;700   → woff2 shard URLs
https://raw.githubusercontent.com/google/fonts/main/ofl/<dir>/    → OFL.txt
```

**Collector:** `tools/collect_google_fonts.py`. It reads `index/index.json`, collects every
`fontFamilies` name across all packs, normalizes them (strips fallback stacks and
build-tool artifacts), checks each against Google Fonts, and downloads the hits as woff2
shards at weights 400 and 700 plus the license file.

**Output layout:**

```text
fonts/<family>/
├── 400-<hash>.woff2      Latin shard
├── 400-<hash>.1.woff2    additional unicode-range shard
├── 700-<hash>.woff2
└── OFL.txt
```

A CJK family downloaded this way produces 100+ shards — that is the CSS2 API splitting by
`unicode-range`, not an error. For a single-file CJK font, see §3.

**Rights:** OFL / Apache-2.0 / per-family. The collector records which in `MANIFEST.json`.

---

## 3. CJK fonts — `fonts-cjk/`

**Scale:** 3 families, 68.8 MB.

| Family | File | Coverage |
|---|---|---|
| Noto Sans SC | `NotoSansSC-VF.ttf` (17.7 MB) | variable weight 100–900, Simplified Chinese |
| Noto Serif SC | `NotoSerifSC-VF.ttf` (25.1 MB) | variable weight 200–900 |
| LXGW WenKai | `LXGWWenKai-Regular.ttf` (25.9 MB) | 霞鹜文楷, handwriting-style |

**Source:** `raw.githubusercontent.com/google/fonts/main/ofl/…` for the Noto families,
GitHub releases for LXGW WenKai.

**Why variable TTF and not woff2 shards:** a Chinese UI needs a single file the CSS can
subset, not 200 network requests. Variable also means one file covers every weight.

**Rights:** all three are OFL.

---

## 4. Commercial-free fonts — `fonts-fontshare/`

**Scale:** 100 families, 698 woff2, 20.5 MB.

**Source:** [Fontshare](https://www.fontshare.com) v2 API.

```text
GET https://api.fontshare.com/v2/fonts
    → full family metadata, license_type ∈ {itf_ffl, sil_ofl}, all free for commercial use

GET https://api.fontshare.com/v2/css?f[]=<slug>@300,400,500,600,700,800
    → @font-face blocks with //cdn.fontshare.com/wf/…woff2 URLs
GET https://api.fontshare.com/v2/css?f[]=<slug>@300i,400i,500i,600i,700i
    → italic set
```

**Collector:** `tools/collect_fontshare.py`.

**Gotcha worth recording:** `styles[].file` in the `/v2/fonts` response is an internal ID
and returns 404 if fetched directly. The only working path is the CSS API. This burned a
full day during the original build.

**Rights:** ITF Free Font License (64 families) or SIL OFL (36 families). Both permit
commercial use and embedding; neither permits reselling the font files themselves.

---

## 5. Static icons — `icons/`

**Scale:** 27,278 SVG / 6,307 unique names / 16.8 MB.

| Set | Count | Style | License |
|---|---|---|---|
| lucide | 2,350 | 24px grid, 2px stroke | ISC |
| heroicons | 1,288 | 16/20/24 solid + 24 outline | MIT |
| Material Symbols | 23,640 | outlined / rounded / sharp, plus `-fill` variants | Apache-2.0 |

**Collectors:** `tools/collect_icons.py` downloads all three straight from npm and GitHub
tarballs — no API keys, no rate limits:

```text
npm  lucide-static                  → package/icons/*.svg
npm  @material-symbols/svg-400      → package/{outlined,rounded,sharp}/*.svg
gh   tailwindlabs/heroicons (main)  → src/<size>/<style>/*.svg
```

Material Symbols counts high because each name ships in three optical styles plus a fill
variant. The name index deduplicates across all of them.

**Output layout:**

```text
icons/lucide/*.svg
icons/heroicons/{16-solid,20-solid,24-solid,24-outline}/*.svg
icons/material-symbols/{outlined,rounded,sharp}/*.svg
icons/INDEX.json      {name: [relative paths]}  ← search target
icons/MANIFEST.json   per-set version / license / source / counts
```

**Rights:** ISC, MIT, Apache-2.0. All permit commercial use without attribution in the
product; keep the license text in the distribution if you redistribute the icon set.

---

## 6. Animations — `animated-icons/`

**Scale:** 750 items, 1,231 files, 66.8 MB.

| Batch | Count | Origin | License |
|---|---|---|---|
| `lottiefiles-official/` | 485 | LottieFiles free tier, 21 UI categories | LottieFiles free license |
| `community/` | 223 | airbnb/lottie-android snapshot | Apache-2.0 |
| `toggle/`, `misc/`, `demo/`, `empty/`, `loading/`, `success/` | 42 | curated CDN URLs + open-source repos | MIT / Apache-2.0 |

**Two collectors, two strategies:**

`tools/harvest_lottiefiles.py` — the free-tier classification pages
(`/free-animations/<category>?pricing=free`) embed the asset CDN URLs in their HTML/RSC
payload. Collect the category and tag pages, extract `assets-v2.lottiefiles.com/…` URLs,
download with no auth, unpack the dotLottie zip, keep `animations/*.json` plus the original
`.lottie`.

`tools/collect_lottie.py` — a curated list of `assets2…9.lottiefiles.com/packages/*.json`
and `lottie.host` URLs, downloaded and validated as real Lottie JSON (`layers` or `assets`
plus a `v` field).

**Note on the free tier:** the classification pages yield ~25 items each and go stale.
Logging in adds nothing — search results are gated and detail pages have no download
button. 485 was the ceiling at collection time.

**Rights:** LottieFiles free-tier works are community-authored and carry the LottieFiles
free license; community repo snapshots carry Apache-2.0. Each manifest entry records both
`source` and `license`. Check per item before commercial use.

---

## Manifests

Every collector writes a manifest alongside its data:

| File | Records |
|---|---|
| `fonts/MANIFEST.json` | font survey: raw names, normalized families, open-source hits, commercial registry with substitution suggestions |
| `fonts-fontshare/MANIFEST.json` | 100 families: name, slug, category, license_type, publisher, files |
| `fonts/INDEX.json` | unified index across all three font directories |
| `icons/INDEX.json` + `icons/MANIFEST.json` | name → paths, and per-set provenance |
| `animated-icons/MANIFEST.json` | every animation: file, source URL, category, license |

Reference snapshots of these live in [`../manifests/`](../manifests/) so the repository
documents its own scale without shipping payloads.
