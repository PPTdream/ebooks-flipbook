# 电子画册 FlipBook（全静态）

上传 PDF / 图片，自动转成可翻页的电子画册；带分类书架，纯静态站点，可挂在任意网站服务器上，也能放进微信公众号自定义菜单。

> 自用向，轻量：**无后端、无数据库、无构建工具链**。PDF 在本地一次性渲染成图片，产物是纯静态文件。

## 特性

- **PDF / 图片 → 翻页画册**：`build.py` 把 PDF 每页渲染为 WebP（默认 216 dpi），或把一文件夹图片直接转成画册
- **分类书架**：按 `_source/<分类>/` 目录组织，首页按分类分组展示
- **仿真翻页**：基于 [StPageFlip](https://github.com/Nodlik/StPageFlip)（MIT），支持鼠标拖拽 / 触摸翻页、键盘方向键、全屏
- **高清屏友好**：画布按 `devicePixelRatio` 渲染，手机高分屏不糊
- **微信适配**：资源全部自托管（不走 CDN），适配微信内置浏览器

## 目录结构

```
.
├── index.html            书架首页
├── viewer.html           翻页阅读器 ?book=<id>
├── assets/
│   ├── page-flip.browser.js   StPageFlip（本地自带）
│   ├── style.css / app.js / viewer.js
├── _source/<分类>/       投料目录：放 PDF 或图片文件夹
│   └── 示例分类/示例画册.pdf
├── books/<分类>/<书>/    构建产物：page-001.webp … + cover.webp + meta.json
├── catalog.json          自动生成的索引
├── build.py              构建脚本（PDF → WebP + 生成索引）
├── serve.py              本地预览用静态服务器（规避 Windows 中文主机名问题）
├── requirements.txt
└── deploy/
    └── iis-web.config.example   IIS 站点配置示例（含 .webp MIME + 反代）
```

## 快速开始

```bash
# 1. 建虚拟环境并装依赖（Python 3.8+）
uv venv .venv --python 3.11       # 或 python -m venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# 2. 构建（把 _source 下的 PDF/图片渲染成 books/ 并生成 catalog.json）
.venv/Scripts/python.exe build.py          # 增量：源未变则跳过
.venv/Scripts/python.exe build.py --force  # 强制重渲染

# 3. 本地预览
.venv/Scripts/python.exe serve.py 8099
# 浏览器打开 http://127.0.0.1:8099
```

## 添加画册

两种投料方式（放到 `_source/<分类名>/` 下）：

- **单个 PDF**：`_source/产品画册/某产品.pdf` → 一本画册（文件名即标题）
- **图片文件夹**：`_source/产品画册/某产品/`（内含 `1.jpg` `2.png` … 自然排序）→ 一本画册

改完重新跑 `build.py` 即可；`catalog.json` 会按 `books/` 现状重建。

## 站点信息定制

编辑 `build.py` 顶部：

```python
SITE_TITLE = "企业电子画册"
SITE_SUBTITLE = "翻页阅读 · 分类书架"
ZOOM = 3.0     # 渲染倍率，72*3 ≈ 216 dpi；调高更清晰、文件更大
QUALITY = 86   # WebP 质量
```

改完重新 `build.py`（`catalog.json` 里的站点标题会同步更新）。

## 部署

产物是纯静态文件，把以下内容上传到网站任意子目录即可：

```
index.html  viewer.html  catalog.json  assets/  books/
```

**IIS（Windows Server）**：参考 `deploy/iis-web.config.example`，注意：

- 必须注册 `.webp` 的 MIME（`image/webp`），否则 IIS 返回 404
- 若同域还有后端反代，把画册目录加入白名单、不走反代

**Nginx / 宝塔**：直接当静态目录托管即可，无需特殊配置。

**微信公众号**：已认证服务号 → 自定义菜单 → 「跳转网页」→ 填画册公网 HTTPS 地址（建议域名已备案、证书有效）。

## 技术栈

- 前端：原生 HTML/CSS/JS + [StPageFlip](https://github.com/Nodlik/StPageFlip)（MIT）
- 构建：[PyMuPDF](https://pymupdf.readthedocs.io/)（渲染 PDF，自带引擎、无需 poppler）、[Pillow](https://python-pillow.org/)（转 WebP）、[pypinyin](https://github.com/mozillazg/python-pinyin)（中文名转拼音 slug）

## 说明

- 画册页以图片形式呈现（不保留 PDF 文字层），适合企业画册/产品目录类阅读场景
- `deploy/*.tgz`、`.venv/` 已加入 `.gitignore`
