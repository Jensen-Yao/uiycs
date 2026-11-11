# 示例参考包

三个真实采集的包，用来验证 schema 和工具链。每一张图、每一个 token 都是
`tools/capture_site.py` 现场从公开站点采的。

| slug | 站点 | 采的是什么 |
|---|---|---|
| `uiycs-site` | 本项目的落地页 | 衬线标题 + 暖中性配色 + 卡片布局 |
| `lucide-dev` | [lucide.dev](https://lucide.dev) | 图标库文档站，紧凑栅格 |
| `heroicons` | [heroicons.com](https://heroicons.com) | 极简单页，大留白 |

三个都是开源项目自己的站点，可以用来验证「采集 → 索引 → MCP 检索」这条链路。

## 装进自己的库

```bash
cp -r examples/demo-packs/packs/* packs/
cp -r examples/demo-packs/media/* media/
python tools/build_pack_index.py
```

`build_pack_index.py` 会扫 `packs/*.json`，把 `media/<slug>/` 下的文件解析成绝对路径，
写进 `index/index.json`。之后 `find_ui_references` 立刻能搜到这三个包。

```jsonc
// find_ui_references { "query": "icon library", "platform": "web" }
// → Lucide / Heroicons，带各自的配色、排版和截图路径
```

## 采自己的

```bash
pip install playwright pillow
python -m playwright install chromium

python tools/capture_site.py https://your-product.com --name "Your Product"
```

输出一个包：

```text
packs/<slug>.json           配色 / 排版 / 组件名 / 采集时间
media/<slug>/poster.webp    1280×800 视口截图
media/<slug>/fullpage.webp  整页长图
media/<slug>/mobile.webp    390×844 移动端
media/<slug>/thumb.webp     640 宽缩略图
```

一次采一批：

```bash
python tools/capture_site.py --batch \
  https://a.example.com \
  https://b.example.com \
  https://c.example.com
```

## 一个包长什么样

```jsonc
{
  "name": "Lucide",
  "slug": "lucide-dev",
  "site": "https://lucide.dev/",
  "capturedAt": "2026-11-11T07:08:12+00:00",
  "colors": [
    { "hex": "#141413", "role": "Text" },
    { "hex": "#FAF9F5", "role": "Surface" }
  ],
  "geometry": {
    "headingWidth": 570,
    "buttonShape": "8px",
    "contentWidth": 1268,
    "containerMaxWidth": "none"
  },
  "patterns": ["Navigation", "Disclosure", "Media", "Cards", "Footer"],
  "inspector": {
    "version": 2,
    "source": "computed-style+dom",
    "palette": [ "…" ],
    "typography": [
      { "role": "Heading", "family": "…", "size": 52, "weight": 400, "lineHeight": 64.48 }
    ],
    "views": [ { "label": "Desktop", "url": "media/lucide-dev/poster.webp" } ]
  },
  "capture": {
    "pageHeight": 2778,
    "sections": [
      {
        "id": "section-01",
        "title": "Beautiful & consistent icons",
        "scrollY": 0,
        "text": "Skip to content Lucide Icons Guide Resources …",
        "imageUrl": "media/lucide-dev/section-01.webp",
        "lines": [
          {
            "text": "Beautiful & consistent icons",
            "box": { "x": 64, "y": 210, "width": 570, "height": 128 },
            "confidence": 1.0,
            "source": "dom"
          },
          {
            "text": "v1.71.0",
            "box": { "x": 1180, "y": 28, "width": 52, "height": 16 },
            "confidence": 0.94,
            "source": "ocr"
          }
        ]
      }
    ]
  }
}
```

**文本是两条路来的，故意分开：**

- `source: "dom"` — 从 DOM 文本节点直接取，坐标是页面绝对坐标（含 scrollY），
  准确率 100%。这是主路径。
- `source: "ocr"` — rapidocr 对截图跑一遍，补 DOM 抓不到的：canvas 里的字、
  图片里的字、SVG `<text>`。只有和 DOM 行不重叠的才保留。

uizze 的 pack 只有 OCR，因为它的采集器只看得到像素。我们有 Playwright，
能读 DOM，所以文本层比它准——但 OCR 兜底仍然必要，纯图站没有 DOM 文本。

**分段**：滚动到每个 800px 带，截视口，裁掉尾部不足的部分。`scrollY` 记录
真实滚动位置，所以相邻段会重叠，这是刻意的——保证没有内容落在缝里。

**配色**从计算样式里按出现频次聚类，`alpha < 0.25` 丢弃（那是悬停光晕，不是设计决策）。

**排版**按语义标签取：`h1` → Heading，`h2` → Subheading，`p` → Body，
`button` → Button，`nav a` → Nav。

**交互模式**从 DOM 结构推断：有 `form` 记 Form，有 `table` 记 Data table，
有 `[aria-expanded]` 记 Disclosure，`a` 超过 8 个记 Link grid。

## 版权

示例包采集的是公开可访问的页面，用于说明 schema 和验证工具链。每个包记录
`site` 字段指向原始站点。采集别人的产品不等于获得它的版权——这些图是**设计参考**，
不是可以复制进自己产品的素材。你自己采集的站点同理。
