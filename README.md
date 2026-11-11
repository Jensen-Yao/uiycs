# uiycs

**Local UI reference and design-material infrastructure for coding agents.**

`uiycs` gives an agent three things it normally does not have: real product screens to
reason from, a licensed font catalogue, and a searchable icon/animation library — all
served from local disk through one MCP server. No account, no token, no network at query
time.

```text
685 reference packs   4,223 captured screens   685 motion clips
217 font families     6,307 icon names         750 Lottie animations
```

The data is large (8.4 GB), so this repository ships the **engine, the schemas, the
manifests and the collectors** — not the payloads. Every payload is rebuilt from a public
source by the scripts in `tools/`.

---

## Why

A coding agent asked to "make this dashboard feel like a real product" has three failure
modes:

1. It invents a design vocabulary instead of looking at one.
2. It picks a font by name and silently substitutes a system fallback.
3. It draws an SVG icon from memory and gets the stroke weight wrong.

`uiycs` removes all three. `find_ui_references` returns actual captured screens with
extracted design tokens and per-screen OCR text. `find_ui_materials` returns real file
paths for a font family, an icon across four icon sets, or an animation — with license and
source attached to each.

---

## Architecture

```text
  knowledge layer        skill/uiycs-ui/SKILL.md
                         image-first UI workflow that calls the MCP
        │
  service layer          mcp_server.py
                         stdio · JSON-RPC 2.0 · MCP 2025-06-18 · 3 tools
        │
  data layer             packs/  media/  fonts/  fonts-fontshare/  fonts-cjk/
                         icons/  animated-icons/  index/
```

The three layers are independent. The MCP server is useful without the skill; the skill
degrades to a plain workflow without the MCP; the data layer is a directory tree any tool
can read.

---

## Quick start

### 1. Build the data

```bash
git clone https://github.com/Jensen-Yao/uiycs.git
cd uiycs
export UIYCS_HOME="$PWD"          # all scripts and the server resolve here

python tools/collect_google_fonts.py     # 114 OFL families → fonts/
python tools/collect_fontshare.py        # 100 commercial-free families → fonts-fontshare/
python tools/collect_icons.py            # lucide + heroicons + Material Symbols → icons/
python tools/harvest_lottiefiles.py      # free-tier Lottie animations → animated-icons/
python tools/collect_lottie.py           # curated CDN animations → animated-icons/
python tools/build_fonts_index.py        # fonts/INDEX.json
python tools/build_icons_index.py        # icons/INDEX.json
python tools/build_pack_index.py         # index/index.json
```

Reference packs (`packs/`, `media/`) follow the layout in
[docs/data-sources.md](docs/data-sources.md). They are captured independently; the index
builder accepts any directory that matches the schema.

### 2. Register the MCP server

Any client that speaks stdio MCP works. The server needs one environment variable:

```jsonc
// .mcp.json  (Claude Code, Cursor, Codex, ZCode, DSH, …)
{
  "mcpServers": {
    "uiycs": {
      "command": "python",
      "args": ["/absolute/path/to/uiycs/mcp_server.py"],
      "env": { "UIYCS_HOME": "/absolute/path/to/uiycs" }
    }
  }
}
```

```toml
# ~/.codex/config.toml
[mcp_servers.uiycs]
command = "python"
args = ["/absolute/path/to/uiycs/mcp_server.py"]
env = { UIYCS_HOME = "/absolute/path/to/uiycs" }
```

Verify:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | UIYCS_HOME="$PWD" python mcp_server.py
# → serverInfo: {"name": "uiycs", "version": "2.0.0"}
```

### 3. Install the skill

```bash
cp -r skill/uiycs-ui ~/.agents/skills/
```

The skill is a workflow, not a dependency. It tells the agent when to reach for a
reference instead of inventing one.

---

## The three tools

### `find_ui_references`

```jsonc
{ "query": "dark dashboard", "platform": "web", "limit": 2, "element": "Table" }
```

Weighted term search over pack metadata and per-screen OCR text. Weights:
name `100` › tagline/theme/site `30` › component names `20` › screen titles `20` ›
patterns `15` › OCR body `6`. Multi-term queries require every term to hit at least once
and add a coverage bonus.

Returns each pack's palette, typography scale, component inventory, screen list with
patterns, and local paths to poster / full-page / motion assets.

### `find_ui_materials`

Four `kind` values, each a real search:

| `kind` | Corpus | Returns |
|---|---|---|
| `pack` | 685 packs | full design system: palette, typography, geometry, components, screen text |
| `font` | 217 families | local `.woff2` / `.ttf` paths, weights, italics, license |
| `icon` | 6,307 names | every matching SVG across lucide, heroicons, Material Symbols |
| `animated_icon` | 750 Lottie files | local path, category, source, license |

```jsonc
{ "query": "satoshi",       "kind": "font" }          // → 8 woff2, 300–700 + italic
{ "query": "arrow-right",   "kind": "icon" }          // → 5 SVGs across 2 sets
{ "query": "noto sans sc",  "kind": "font" }          // → variable TTF + 202 web shards
{ "query": "copy success",  "kind": "animated_icon" } // → matching Lottie JSON
```

### `get_pack_detail`

```jsonc
{ "id": "nominal" }   // accepts id, slug, or exact app name
```

Full record for one pack, including every screen and its OCR text.

---

## Where the data comes from

Full detail, sizes and collector behaviour: [docs/data-sources.md](docs/data-sources.md).

| Layer | Source | License |
|---|---|---|
| Reference packs | public product-interface capture collections (web + iOS), 685 apps | see per-pack record |
| Web fonts | [Google Fonts](https://fonts.google.com) via the CSS2 API | OFL / Apache / per-family |
| Commercial-free fonts | [Fontshare](https://www.fontshare.com) CSS API | ITF Free Font License / OFL |
| CJK fonts | Noto Sans SC, Noto Serif SC (variable), LXGW WenKai | OFL |
| Icons | [lucide](https://lucide.dev) · [heroicons](https://heroicons.com) · [Material Symbols](https://fonts.google.com/icons) | ISC · MIT · Apache-2.0 |
| Animations | [LottieFiles](https://lottiefiles.com) free tier + community repos | LottieFiles free / MIT / Apache-2.0 |

Every record in every manifest carries a `source` and a `license` field. The integrity
check at the end of [docs/rebuild.md](docs/rebuild.md) fails if any path is dangling.

---

## Repository layout

```text
uiycs/
├── mcp_server.py               MCP server (stdio, JSON-RPC 2.0, MCP 2025-06-18)
├── skill/
│   └── uiycs-ui/
│       ├── SKILL.md            image-first UI workflow
│       └── references/
│           └── workflow.md     the six-step procedure
├── tools/
│   ├── collect_google_fonts.py
│   ├── collect_fontshare.py
│   ├── collect_icons.py
│   ├── collect_lottie.py
│   ├── harvest_lottiefiles.py
│   ├── build_fonts_index.py
│   ├── build_icons_index.py
│   └── build_pack_index.py
├── manifests/
│   ├── fonts.index.json        217 families, 2,292 files
│   ├── icons.index.json        6,307 names → 27,278 SVG paths
│   ├── icons.manifest.json     per-set version / license / source
│   ├── fontshare.manifest.json 100 families
│   └── animated-icons.manifest.json
└── docs/
    ├── data-sources.md
    ├── mcp-reference.md
    └── rebuild.md
```

The `manifests/` copies are reference snapshots so the repository documents its own scale
without shipping payloads. The live indexes are regenerated by `tools/build_*.py` and live
next to the data.

---

## Environment

```text
UIYCS_HOME              data root. Defaults to the repo root, or one level up when
                        running a script from tools/.
DOTLOTTIE_FIXTURES      optional. Directory of .lottie zip fixtures to fold in.
```

Python 3.9+. Standard library only — no `pip install` needed for the server or any
collector. The optional image tooling in the skill is whatever your host provides.

---

## Design decisions

**Local files, not URLs.** Every material result is an absolute path on disk. An agent
that has to fetch a URL will eventually ship a broken link or a hotlinked asset.

**Manifests carry rights.** A font without its license is a liability. Every collector
writes `source` and `license` next to every file, and every index builder preserves them.

**Indexes are rebuildable, never authoritative.** `packs/`, `fonts/`, `icons/` are the
truth. `INDEX.json` is a cache. Re-running the builder after adding files is always safe.

**Search is weighted, not fuzzy.** A query term that hits nothing scores zero and the pack
drops out. Silent near-matches are how an agent ends up citing the wrong reference.

---

## License

MIT — see [LICENSE](LICENSE). Bundled fonts, icons and animations retain their own
licenses; see the manifest next to each set.
