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
  "platform": "web",
  "tagline": "…",
  "theme": "Open-source icon library",
  "site": "https://lucide.dev/",
  "capturedAt": "2026-11-11T07:08:12+00:00",
  "colors": [
    { "hex": "#141413", "role": "Text" },
    { "hex": "#FAF9F5", "role": "Surface" }
  ],
  "inspector": {
    "version": 1,
    "source": "computed-style",
    "palette": [ "…" ],
    "typography": [
      { "role": "Heading", "family": "…", "size": 52, "weight": 400, "lineHeight": 64.48 }
    ],
    "views": [
      { "label": "Desktop", "url": "media/lucide-dev/poster.webp", "width": 1280, "height": 800 }
    ]
  },
  "fontFamilies": [ "…" ],
  "componentNames": [ "Navigation", "Hero", "…" ]
}
```

配色从计算样式里按出现频次聚类——每个 `backgroundColor` 和 `color` 计数，
取前六个，`alpha < 0.25` 的丢弃（那是鼠标悬停光晕之类，不是设计决策）。

排版按语义标签取：`h1` → Heading，`h2` → Subheading，`p` → Body，
`button` → Button，`nav a` → Nav。

## 版权

示例包采集的是公开可访问的页面，用于说明 schema 和验证工具链。每个包记录
`site` 字段指向原始站点。采集别人的产品不等于获得它的版权——这些图是**设计参考**，
不是可以复制进自己产品的素材。你自己采集的站点同理。
