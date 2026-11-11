<div align="center">

<img src="docs/assets/preview.webp" width="880" alt="uiycs 落地页预览">

<h1>uiycs</h1>

<p><b>给 coding agent 用的本地 UI 参考与设计素材基础设施</b></p>

<p>
<a href="https://jensen-yao.github.io/uiycs/"><img src="https://img.shields.io/badge/live-site-D97757?style=for-the-badge" alt="live site"></a>
<a href="README.en.md"><img src="https://img.shields.io/badge/lang-English-141413?style=for-the-badge" alt="English"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-5C5A54?style=for-the-badge" alt="MIT"></a>
<a href="#三个工具"><img src="https://img.shields.io/badge/MCP-3_tools-8C8880?style=for-the-badge" alt="3 tools"></a>
</p>

<p><sub>本页面由 <code>uiycs-ui</code> skill 一次生成 —— 第一版 HTML 约 <b>30 秒</b>落盘，33 KB</sub></p>

</div>

---


`uiycs` 给 agent 三样它通常没有的东西：可以推理的真实产品界面、带许可的字体目录、可搜索的图标与动效库。全部从本地磁盘提供，一个 MCP server 统一出口。不注册、不要 token、查询时不联网。

```text
685 个参考包        4,223 张截屏        685 段动效
217 个字体族        6,307 个图标名      750 个 Lottie 动画
```

数据很大（8.4 GB），所以本仓库只发布**引擎、schema、清单和采集脚本**，不发布数据本身。每一个数据文件都能由 `tools/` 里的脚本从公开源重建。

---

## 为什么做这个

一个 agent 被要求"把这个 dashboard 做得像个真产品"时，通常有三种翻车方式：

1. 它自己发明一套设计语汇，而不是去看一套。
2. 它按名字选了个字体，然后静默降级成系统字体。
3. 它凭记忆画了个 SVG 图标，描边粗细是错的。

`uiycs` 把这三条都堵掉。`find_ui_references` 返回真实截屏，附提取好的设计 token 和每屏 OCR 文本；`find_ui_materials` 返回字体族、跨四套图标集的图标、或动画的**真实文件路径**，每个都带许可和来源。

---

## 架构

```text
  知识层        skill/uiycs-ui/SKILL.md
                以图为准的 UI 工作流，负责调用 MCP
        │
  服务层        mcp_server.py
                stdio · JSON-RPC 2.0 · MCP 2025-06-18 · 3 个工具
        │
  数据层        packs/  media/  fonts/  fonts-fontshare/  fonts-cjk/
                icons/  animated-icons/  index/
```

三层互相独立。没有 skill，MCP server 照样能用；没有 MCP，skill 退化成一套纯工作流；没有 agent，数据层就是一棵任何工具都能读的目录树。

---

## 快速开始

### 1. 构建数据

```bash
git clone https://github.com/Jensen-Yao/uiycs.git
cd uiycs
export UIYCS_HOME="$PWD"          # 所有脚本和 server 都以它为根

python tools/collect_google_fonts.py     # 114 个 OFL 字族 → fonts/
python tools/collect_fontshare.py        # 100 个免费商用字族 → fonts-fontshare/
python tools/collect_icons.py            # lucide + heroicons + Material Symbols → icons/
python tools/harvest_lottiefiles.py      # LottieFiles 免费层 → animated-icons/
python tools/collect_lottie.py           # 精选 CDN 动画 → animated-icons/
python tools/build_fonts_index.py        # fonts/INDEX.json
python tools/build_icons_index.py        # icons/INDEX.json
python tools/build_pack_index.py         # index/index.json
```

参考包（`packs/`、`media/`）的目录规范见 [docs/data-sources.md](docs/data-sources.md)。它们由独立管线采集，索引构建器接受任何符合该 schema 的目录。

### 2. 注册 MCP server

任何支持 stdio MCP 的客户端都能接。server 只需要一个环境变量：

```jsonc
// .mcp.json  (Claude Code / Cursor / Codex / ZCode / DSH 通用)
{
  "mcpServers": {
    "uiycs": {
      "command": "python",
      "args": ["/绝对路径/uiycs/mcp_server.py"],
      "env": { "UIYCS_HOME": "/绝对路径/uiycs" }
    }
  }
}
```

```toml
# ~/.codex/config.toml
[mcp_servers.uiycs]
command = "python"
args = ["/绝对路径/uiycs/mcp_server.py"]
env = { UIYCS_HOME = "/绝对路径/uiycs" }
```

验证：

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | UIYCS_HOME="$PWD" python mcp_server.py
# → serverInfo: {"name": "uiycs", "version": "2.0.0"}
```

### 3. 安装 skill

```bash
cp -r skill/uiycs-ui ~/.agents/skills/
```

skill 是一套工作流，不是依赖。它告诉 agent 什么时候该去找参考，而不是凭空发明。

---

## 三个工具

### `find_ui_references`

```jsonc
{ "query": "dark dashboard", "platform": "web", "limit": 2, "element": "Table" }
```

在包的元数据和每屏 OCR 文本上做加权词检索。权重：名称 `100` › tagline/主题/站点 `30` › 组件名 `20` › 屏标题 `20` › 交互模式 `15` › OCR 正文 `6`。多词查询要求每个词至少命中一次，全命中另加覆盖奖励。

返回每个包的配色、排版比例、组件清单、带交互模式的屏列表，以及 poster / 整页 / 动效的本地路径。

### `find_ui_materials`

四个 `kind`，每一个都是真检索：

| `kind` | 语料 | 返回 |
|---|---|---|
| `pack` | 685 个包 | 完整设计系统：配色、排版、几何、组件、屏文本 |
| `font` | 217 个字族 | 本地 `.woff2` / `.ttf` 路径、字重、斜体、许可 |
| `icon` | 6,307 个名字 | 跨 lucide、heroicons、Material Symbols 的全部 SVG |
| `animated_icon` | 750 个 Lottie | 本地路径、分类、来源、许可 |

```jsonc
{ "query": "satoshi",       "kind": "font" }          // → 8 个 woff2，300–700 + 斜体
{ "query": "arrow-right",   "kind": "icon" }          // → 跨两套的 5 个 SVG
{ "query": "noto sans sc",  "kind": "font" }          // → 可变字体 TTF + 202 个网页分片
{ "query": "copy success",  "kind": "animated_icon" } // → 命中的 Lottie JSON
```

### `get_pack_detail`

```jsonc
{ "id": "nominal" }   // 接受 id、slug 或精确名称
```

单个包的完整记录，含每一屏和它的 OCR 文本。

---

## 数据从哪来

完整细节、体积、采集器行为见 [docs/data-sources.md](docs/data-sources.md)。

| 层 | 来源 | 许可 |
|---|---|---|
| 参考包 | 公开的产品界面采集集合（web + iOS），685 个应用 | 见单包记录 |
| 网页字体 | [Google Fonts](https://fonts.google.com)，走 CSS2 API | OFL / Apache / 按字族 |
| 免费商用字体 | [Fontshare](https://www.fontshare.com) CSS API | ITF Free Font License / OFL |
| 中文字体 | Noto Sans SC、Noto Serif SC（可变）、霞鹜文楷 | OFL |
| 图标 | [lucide](https://lucide.dev) · [heroicons](https://heroicons.com) · [Material Symbols](https://fonts.google.com/icons) | ISC · MIT · Apache-2.0 |
| 动效 | [LottieFiles](https://lottiefiles.com) 免费层 + 社区仓库 | LottieFiles free / MIT / Apache-2.0 |

每一份清单里的每一条记录都带 `source` 和 `license`。文末的完整性自检会校验所有路径，悬空即报错。

---

## 仓库结构

```text
uiycs/
├── mcp_server.py               MCP server（stdio, JSON-RPC 2.0, MCP 2025-06-18）
├── skill/
│   └── uiycs-ui/
│       ├── SKILL.md            以图为准的 UI 工作流
│       └── references/
│           └── workflow.md     六步流程
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
│   ├── fonts.index.json        217 字族 / 2,292 文件
│   ├── icons.index.json        6,307 个名字 → 27,278 条 SVG 路径
│   ├── icons.manifest.json     每套的版本 / 许可 / 来源
│   ├── fontshare.manifest.json 100 字族
│   └── animated-icons.manifest.json
└── docs/
    ├── data-sources.md
    ├── mcp-reference.md
    └── rebuild.md
```

`manifests/` 里是参考快照，让仓库能自证规模而不必携带数据。线上索引由 `tools/build_*.py` 重建，跟数据放在一起。

---

## 环境

```text
UIYCS_HOME             数据根目录。默认取仓库根；从 tools/ 里运行时自动上溯一级。
DOTLOTTIE_FIXTURES     可选。要一并纳入的 .lottie zip 样本目录。
```

Python 3.9+。只用标准库——server 和所有采集器都不需要 `pip install`。

---

## 设计取舍

**给本地路径，不给 URL。** 每个素材结果都是磁盘上的绝对路径。一个必须去 fetch URL 的 agent，迟早会发出死链或者热链别人的资源。

**清单必须带权利信息。** 没有许可的字体是负债。每个采集器都在文件旁边写 `source` 和 `license`，每个索引构建器都原样保留。

**索引可重建，永不作为事实源。** `packs/`、`fonts/`、`icons/` 才是事实。`INDEX.json` 只是缓存，加完文件重跑构建器永远安全。

**检索是加权，不是模糊。** 一个词完全打不中的包直接出局。静默的"差不多匹配"正是 agent 引错参考的原因。

---

## 许可

MIT — 见 [LICENSE](LICENSE)。随附的字体、图标、动画保留各自的许可；见每套旁边的 manifest。

---

[English](README.md)
