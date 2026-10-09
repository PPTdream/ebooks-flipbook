#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电子画册构建脚本（全静态）

用法：
  1. 把 PDF 放到  _source/<分类名>/xxx.pdf           （每个 PDF = 一本画册）
     或把图片放到 _source/<分类名>/<画册名>/*.jpg|png （一个文件夹 = 一本画册）
  2. 运行：  python build.py            # 增量：源未变则跳过
             python build.py --force    # 强制重渲染
  3. 产物：books/<分类slug>/<画册slug>/page-001.webp ... + cover.webp + meta.json
            catalog.json（索引，UTF-8）
  4. 本地预览：python -m http.server 8080

依赖：PyMuPDF、Pillow、pypinyin（见 requirements.txt）
"""
from __future__ import print_function
import os
import io
import sys
import json
import time
import shutil
import hashlib

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("缺少 PyMuPDF，请先 pip install -r requirements.txt")

from PIL import Image
from pypinyin import lazy_pinyin

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(ROOT, "_source")
BOOKS_DIR = os.path.join(ROOT, "books")
CATALOG = os.path.join(ROOT, "catalog.json")

SITE_TITLE = "企业电子画册"
SITE_SUBTITLE = "翻页阅读 · 分类书架"

ZOOM = 3.0          # 72*3 = 216 dpi（高清）
QUALITY = 86        # webp 质量
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
FORCE = "--force" in sys.argv


def slugify(name, fallback="book"):
    parts = lazy_pinyin(name)
    ascii_name = "".join(parts).lower()
    keep = []
    for ch in ascii_name:
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_":
            keep.append("-")
    s = "".join(keep).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    if not s:
        s = fallback + "-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return s


def ensure_dir(p):
    if not os.path.isdir(p):
        os.makedirs(p)


def save_webp(pil_img, out_path):
    if pil_img.mode not in ("RGB", "L"):
        pil_img = pil_img.convert("RGB")
    pil_img.save(out_path, "WEBP", quality=QUALITY, method=6)


def render_pdf(pdf_path, out_dir):
    doc = fitz.open(pdf_path)
    n = doc.page_count
    for i in range(n):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        save_webp(img, os.path.join(out_dir, "page-%03d.webp" % (i + 1)))
    doc.close()
    return n


def render_images(img_paths, out_dir):
    n = 0
    for i, p in enumerate(img_paths, 1):
        img = Image.open(p)
        save_webp(img, os.path.join(out_dir, "page-%03d.webp" % i))
        n += 1
    return n


def natural_key(s):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def process_book(cat_name, cat_slug, title, src_key, src_mtime, render):
    book_slug = slugify(title, "book")
    # 保证同分类内唯一
    base = book_slug
    k = 2
    while True:
        out_dir = os.path.join(BOOKS_DIR, cat_slug, book_slug)
        meta_path = os.path.join(out_dir, "meta.json")
        if not os.path.isdir(out_dir):
            break
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    m = json.load(f)
                if m.get("_src_key") == src_key:
                    break  # 同一源，复用该目录
            except Exception:
                pass
        book_slug = "%s-%d" % (base, k)
        k += 1

    out_dir = os.path.join(BOOKS_DIR, cat_slug, book_slug)
    meta_path = os.path.join(out_dir, "meta.json")

    prev = None
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                prev = json.load(f)
        except Exception:
            prev = None

    unchanged = (
        not FORCE and prev is not None
        and prev.get("_src_mtime") == src_mtime
        and os.path.isfile(os.path.join(out_dir, "page-001.webp"))
    )
    if unchanged:
        print("  跳过(未变): %s" % title)
        return book_slug, prev.get("pages", 0), False

    ensure_dir(out_dir)
    # 清理旧页
    for fn in os.listdir(out_dir):
        if fn.startswith("page-") and fn.endswith(".webp"):
            os.remove(os.path.join(out_dir, fn))

    print("  渲染: %s" % title)
    pages = render(out_dir)

    # 封面 = 第一页
    first = os.path.join(out_dir, "page-001.webp")
    if os.path.isfile(first):
        shutil.copyfile(first, os.path.join(out_dir, "cover.webp"))

    meta = {
        "id": "%s/%s" % (cat_slug, book_slug),
        "title": title,
        "category": cat_slug,
        "categoryName": cat_name,
        "dir": "books/%s/%s/" % (cat_slug, book_slug),
        "cover": "books/%s/%s/cover.webp" % (cat_slug, book_slug),
        "pages": pages,
        "updated": time.strftime("%Y-%m-%d"),
        "_src_key": src_key,
        "_src_mtime": src_mtime,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return book_slug, pages, True


def scan_source():
    if not os.path.isdir(SOURCE_DIR):
        ensure_dir(SOURCE_DIR)
    ensure_dir(BOOKS_DIR)
    rendered = 0
    for cat_name in sorted(os.listdir(SOURCE_DIR)):
        cat_path = os.path.join(SOURCE_DIR, cat_name)
        if not os.path.isdir(cat_path) or cat_name.startswith("."):
            continue
        cat_slug = slugify(cat_name, "category")
        print("[分类] %s -> %s" % (cat_name, cat_slug))
        for entry in sorted(os.listdir(cat_path), key=natural_key):
            full = os.path.join(cat_path, entry)
            if entry.startswith("."):
                continue
            if os.path.isfile(full) and entry.lower().endswith(".pdf"):
                title = os.path.splitext(entry)[0]
                src_key = os.path.relpath(full, ROOT)
                mtime = os.path.getmtime(full)
                _, _, did = process_book(
                    cat_name, cat_slug, title, src_key, mtime,
                    lambda d, p=full: render_pdf(p, d))
                rendered += 1 if did else 0
            elif os.path.isdir(full):
                imgs = [os.path.join(full, x) for x in sorted(os.listdir(full), key=natural_key)
                        if x.lower().endswith(IMG_EXTS)]
                if not imgs:
                    continue
                title = entry
                src_key = os.path.relpath(full, ROOT)
                mtime = max(os.path.getmtime(x) for x in imgs)
                _, _, did = process_book(
                    cat_name, cat_slug, title, src_key, mtime,
                    lambda d, im=imgs: render_images(im, d))
                rendered += 1 if did else 0
    return rendered


def build_catalog():
    cats = {}
    order = []
    for cat_slug in sorted(os.listdir(BOOKS_DIR)) if os.path.isdir(BOOKS_DIR) else []:
        cat_dir = os.path.join(BOOKS_DIR, cat_slug)
        if not os.path.isdir(cat_dir):
            continue
        books = []
        for book_slug in sorted(os.listdir(cat_dir)):
            meta_path = os.path.join(cat_dir, book_slug, "meta.json")
            if not os.path.isfile(meta_path):
                continue
            with open(meta_path, "r", encoding="utf-8") as f:
                m = json.load(f)
            books.append({
                "id": m["id"],
                "title": m["title"],
                "category": m["category"],
                "dir": m["dir"],
                "cover": m["cover"],
                "pages": m["pages"],
                "updated": m["updated"],
            })
        if not books:
            continue
        cat_name = books[0].get("category", cat_slug)
        # categoryName 存在 meta 内
        with open(os.path.join(cat_dir, books[0]["id"].split("/")[1], "meta.json"),
                  "r", encoding="utf-8") as f:
            cat_name = json.load(f).get("categoryName", cat_slug)
        cats[cat_slug] = {
            "id": cat_slug,
            "name": cat_name,
            "books": sorted(books, key=lambda b: b["title"]),
        }
        order.append(cat_slug)

    catalog = {
        "site": {"title": SITE_TITLE, "subtitle": SITE_SUBTITLE},
        "updated": time.strftime("%Y-%m-%d"),
        "categories": [cats[c] for c in order],
    }
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    total = sum(len(c["books"]) for c in catalog["categories"])
    print("catalog.json 已生成：%d 个分类 / %d 本画册" % (len(order), total))


def main():
    print("== 扫描源目录 ==")
    rendered = scan_source()
    print("== 生成索引 ==")
    build_catalog()
    print("完成。本次新渲染 %d 本。" % rendered)


if __name__ == "__main__":
    main()
