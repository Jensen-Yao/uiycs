# MCP reference

`uiycs` exposes one stdio MCP server: `mcp_server.py`, protocol `2025-06-18`,
JSON-RPC 2.0, one JSON object per line on stdin/stdout. Three tools. No authentication —
the server reads local files only.

---

## Transport

```text
stdin   one JSON-RPC request per line
stdout  one JSON-RPC response per line
```

Supported methods: `initialize`, `ping`, `tools/list`, `tools/call`.
`notifications/*` are accepted and ignored (no response is written).

`initialize` echoes the client's `protocolVersion` and advertises:

```json
{
  "protocolVersion": "2025-06-18",
  "capabilities": { "tools": {} },
  "serverInfo": { "name": "uiycs", "version": "2.0.0" }
}
```

---

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `UIYCS_HOME` | repo root | data root; every path resolves under it |
| `DOTLOTTIE_FIXTURES` | *(unset)* | optional `.lottie` zip fixture directory for `collect_lottie.py` |

The server resolves `UIYCS_HOME` at import time and loads `index/index.json`
eagerly. Font, icon and Lottie indexes are lazy-loaded on first use and cached for the
process lifetime — a stdio server is long-lived, so you pay 1.5 MB of parse once.

If `index/index.json` is missing the server exits at import. Build the packs index first.

---

## `find_ui_references`

Search captured products.

```jsonc
{
  "query": "dark dashboard",     // required
  "platform": "web",             // "web" | "ios" | omitted for both
  "limit": 2,                    // 1–3, default 2
  "element": "Table",            // optional: require this component name
  "screenshot": false            // optional: inline the poster as base64 image content
}
```

**Scoring.** Terms are split on whitespace. Each term scores independently against:

| Field | Points |
|---|---|
| exact name match | 100 |
| name substring | 60 |
| tagline / theme / site | 30 |
| component name | 20 |
| screen title | 20 |
| screen pattern | 15 |
| OCR body text | 6 |

A term that scores zero disqualifies the pack. Packs where every term hit get a +40
coverage bonus. Results sort by total, descending.

**Returns** (text content, JSON):

```jsonc
{
  "count": 2,
  "results": [
    {
      "id": "…", "name": "Nuxt Dashboard", "platform": "web",
      "tagline": "Explore dashboard metrics and customer management",
      "theme": "Admin dashboards and customer management",
      "site": "https://dashboard-template.nuxt.dev/",
      "capturedAt": "2026-10-28T15:34:45.991Z",
      "palette":   [{ "hex": "#00C16A", "role": "Button" }],
      "typography": [{ "role": "Heading", "family": "Public Sans", "size": 16, "weight": 600 }],
      "fontFamilies": ["Public Sans"],
      "components": ["Customer management table", "Navigation", "Hero"],
      "screens":   [{ "id": "…", "title": "…", "image": "/abs/path.webp", "patterns": ["…"] }],
      "views":     [{ "label": "Desktop", "image": "/abs/path.webp" }],
      "fullPage": "/abs/fullpage.webp",
      "poster":   "/abs/poster.webp",
      "motion":   "/abs/motion.webm",
      "cover":    "/abs/thumb.webp"
    }
  ]
}
```

With `screenshot: true`, one additional content block of type `image` carries the top
result's poster as base64.

**Empty query** is valid: it returns the most recently captured packs.

---

## `find_ui_materials`

Retrieve material by kind. All four kinds are real search, not metadata stubs.

```jsonc
{
  "query": "satoshi",
  "kind": "font",           // "pack" | "font" | "icon" | "animated_icon"
  "limit": 5                // 1–10, default 5 (pack clamps to 3)
}
```

### `kind: "pack"`

Same matcher as `find_ui_references`, plus `geometry` and `screenTexts` per pack.

```jsonc
{
  "count": 1,
  "packs": [{
    "…": "everything find_ui_references returns, plus",
    "geometry": { "headingWidth": 672, "buttonShape": "0 px" },
    "screenTexts": [{ "title": "Settings", "text": "full OCR body…" }]
  }]
}
```

### `kind: "font"`

```jsonc
{ "query": "satoshi", "kind": "font" }
```

**Matching.** The query is lowercased and tried in three forms — as written, with spaces
replaced by hyphens, and with spaces removed — against family name and slug.
Exact match 100, substring 70, category 40, publisher 25.

**Returns:**

```jsonc
{
  "kind": "font",
  "count": 1,
  "families": [{
    "name": "Satoshi", "slug": "satoshi",
    "source": "fontshare",
    "license": "itf_ffl",
    "license_file": null,
    "category": "Sans",
    "publisher": "Indian Type Foundry",
    "cjk": false,
    "variable": null,
    "weights": ["300", "400", "500", "700"],
    "italics": ["300", "400", "500", "700"],
    "dir": "/abs/uiycs/fonts-fontshare/satoshi",
    "files": ["/abs/…/300-XXX.woff2", "/abs/…/400-YYY.woff2"]
  }]
}
```

`cjk: true` families carry `variable: true` when the file is a variable TTF rather than
weight-sharded woff2.

`query: "any"`, `"all"` or `""` returns the first N families — useful for enumeration.

### `kind: "icon"`

```jsonc
{ "query": "arrow-right", "kind": "icon" }
```

**Matching.** The query is lowercased and `_` is normalized to `-`. Exact hit scores 1000;
prefix hits 700; substring hits 400. Shorter names win ties.

**Returns:**

```jsonc
{
  "kind": "icon",
  "count": 1,
  "icons": [{
    "name": "arrow-right",
    "files": [
      "/abs/uiycs/icons/lucide/arrow-right.svg",
      "/abs/uiycs/icons/heroicons/16-solid/arrow-right.svg",
      "/abs/uiycs/icons/heroicons/20-solid/arrow-right.svg",
      "/abs/uiycs/icons/heroicons/24-outline/arrow-right.svg",
      "/abs/uiycs/icons/heroicons/24-solid/arrow-right.svg",
      "/abs/uiycs/icons/material-symbols/outlined/arrow_right.svg"
    ]
  }]
}
```

One name can span four sets and eleven files. The caller picks by grid and stroke
convention — the server does not rank sets.

### `kind: "animated_icon"`

```jsonc
{ "query": "copy success", "kind": "animated_icon" }
```

**Matching.** Query is lowercased; filename hit 60, category hit 40. Empty query returns
the first N.

**Returns:**

```jsonc
{
  "kind": "animated_icon",
  "count": 2,
  "animations": [{
    "file": "/abs/uiycs/animated-icons/success/copy-success.json",
    "category": "success",
    "source": "https://assets…/packages/lf20_xxx.json",
    "license": "LottieFiles free license"
  }]
}
```

---

## `get_pack_detail`

Exact lookup by id, slug or name.

```jsonc
{ "id": "nominal" }     // or the UUID, or "Nominal"
```

Returns the same shape as one `find_ui_references` result plus `geometry`. Unknown id
returns `{"error": "not found", "id": "…"}`.

---

## Errors

Every tool call returns either a normal result or a text block with `isError: true`.
Failures are reported per-call, never as a JSON-RPC error, so a client that only checks
`result.content` will see the message rather than a transport fault.

| Cause | Message |
|---|---|
| unknown tool | `{"error": "unknown tool <name>"}` |
| missing index file | server exits at import |
| malformed args | `error: <exception>` inside the tool result |

---

## Client configuration

### Claude Code / Cursor / Zed

```jsonc
{
  "mcpServers": {
    "uiycs": {
      "command": "python",
      "args": ["/abs/uiycs/mcp_server.py"],
      "env": { "UIYCS_HOME": "/abs/uiycs" }
    }
  }
}
```

### Codex

```toml
[mcp_servers.uiycs]
command = "python"
args = ["/abs/uiycs/mcp_server.py"]
env = { UIYCS_HOME = "/abs/uiycs" }
```

### ZCode

```jsonc
// .zcode/cli/config.json
{
  "mcp": {
    "servers": {
      "uiycs": {
        "command": "/abs/python",
        "args": ["/abs/uiycs/mcp_server.py"],
        "env": { "UIYCS_HOME": "/abs/uiycs" }
      }
    }
  }
}
```

### DSH

```yaml
# ~/.dsh/cordis.patch.yml
- id: uiycs-mcp
  type: stdio
  command: python
  args: [/abs/uiycs/mcp_server.py]
  env:
    UIYCS_HOME: /abs/uiycs
```

Restart the host after editing. Verify first:

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | UIYCS_HOME=/abs/uiycs python mcp_server.py
```

---

## Performance notes

- Startup: ~120 ms (loads `index/index.json`, 1.7 MB).
- First `kind=font` call: +40 ms (fonts index, 273 KB). Cached after.
- First `kind=icon` call: +90 ms (icons index, 1.3 MB). Cached after.
- Steady-state lookups: sub-millisecond over 685 packs / 6,307 icon names.

The icon matcher scans all 6,307 keys per query and stops collecting after `limit × 6`
candidates. That bound is what keeps an empty-ish query from walking the whole map.
