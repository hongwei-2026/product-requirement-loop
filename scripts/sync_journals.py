#!/usr/bin/env python3
"""从官方 GitHub 同步研发日志到 project/journals/，并重建 catalog.json。

Usage (repo root):
  python scripts/sync_journals.py
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNALS = ROOT / "project" / "journals"
CATALOG = JOURNALS / "catalog.json"

API_ROOT = "https://api.github.com/repos/quanttide/quanttide-journal-of-product-development/contents"
RAW = "https://raw.githubusercontent.com/quanttide/quanttide-journal-of-product-development/main"

# 跳过非产品流目录
SKIP_DIRS = {"default", ".github"}

PRODUCT_LABELS = {
    "qtcloud-product": "产品云",
    "qtcloud-agent": "Agent 云",
    "qtcloud-devops": "研运云",
    "qtcloud-business": "业务云",
    "qtcloud-connect": "连接云",
    "qtcloud-asset": "资产云",
    "qtcloud-data": "数据云",
    "qtcloud-finance": "财务云",
    "qtcloud-collab": "协作云",
    "qtclass": "量潮课堂",
}


def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "quanttide-journal-sync"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "quanttide-journal-sync"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def list_product_dirs() -> list[str]:
    items = http_json(f"{API_ROOT}?ref=main")
    return sorted(
        x["name"]
        for x in items
        if x.get("type") == "dir" and x["name"] not in SKIP_DIRS and not x["name"].startswith(".")
    )


def list_md_files(product: str) -> list[dict]:
    try:
        items = http_json(f"{API_ROOT}/{product}?ref=main")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    out = []
    for x in items:
        if x.get("type") == "file" and x["name"].endswith(".md") and re.match(r"^\d{4}-\d{2}-\d{2}", x["name"]):
            out.append(x)
    return sorted(out, key=lambda x: x["name"], reverse=True)


def first_line_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^#+\s*", "", s)
        s = re.sub(r"\s+", " ", s)
        return (s[:48] + "…") if len(s) > 48 else s
    return fallback


def speed_for(chars: int) -> str:
    if chars < 1200:
        return "快"
    if chars < 3500:
        return "中"
    return "慢"


def sync() -> dict:
    JOURNALS.mkdir(parents=True, exist_ok=True)
    (JOURNALS / "custom").mkdir(parents=True, exist_ok=True)

    products = list_product_dirs()
    journals = []
    synced = 0

    # 保留本地摘录（试跑用）
    excerpt = JOURNALS / "qtcloud-product" / "2026-08-19-excerpt.md"
    if excerpt.exists():
        text = excerpt.read_text(encoding="utf-8")
        journals.append(
            {
                "id": "qtcloud-product-2026-08-19-excerpt",
                "title": "产品云 · 捕捉用户故事（聚焦摘录）",
                "product": "qtcloud-product",
                "date": "2026-08-19",
                "file": "qtcloud-product/2026-08-19-excerpt.md",
                "usage": "try",
                "speed": "快",
                "why": "本期课题聚焦段落，试跑/拍视频最快。",
                "when": "想快速验证闭环时",
                "chars": len(text),
                "kind": "library",
            }
        )

    for product in products:
        label = PRODUCT_LABELS.get(product, product)
        dest_dir = JOURNALS / product
        dest_dir.mkdir(parents=True, exist_ok=True)
        files = list_md_files(product)
        print(f"[{product}] {len(files)} day logs")
        for f in files:
            name = f["name"]
            date = name[:10]
            rel = f"{product}/{name}"
            dest = JOURNALS / rel
            try:
                text = http_text(f"{RAW}/{product}/{name}")
            except Exception as e:
                print(f"  FAIL {rel}: {e}")
                continue
            dest.write_text(text, encoding="utf-8")
            synced += 1
            chars = len(text)
            title_snip = first_line_title(text, date)
            journals.append(
                {
                    "id": f"{product}-{date}",
                    "title": f"{label} · {date}",
                    "product": product,
                    "date": date,
                    "file": rel,
                    "usage": "formal",
                    "speed": speed_for(chars),
                    "why": f"官方日日志全文（{chars} 字）：{title_snip}",
                    "when": "正式梳理/定稿时选对应产品流 + 日期",
                    "source": f"quanttide-journal-of-product-development/{rel}",
                    "chars": chars,
                    "kind": "library",
                }
            )
            print(f"  OK {rel} ({chars})")

    # 日期新的在前；摘录置顶
    excerpts = [j for j in journals if j.get("usage") == "try"]
    formals = [j for j in journals if j.get("usage") != "try"]
    formals.sort(key=lambda j: (j.get("date") or "", j.get("product") or ""), reverse=True)
    ordered = excerpts + formals

    catalog = {
        "selection_guide": {
            "principle": "先定今天要梳理的一件事 → 选产品流 → 选日期。字少试跑快，全文用于正式定稿。",
            "filters": ["产品流", "日期", "用途（试跑/定稿）", "字数/速度"],
            "source_repo": "https://github.com/quanttide/quanttide-journal-of-product-development",
        },
        "synced_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "product_count": len(products),
        "journal_count": len(ordered),
        "journals": ordered,
    }
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSynced {synced} files → {CATALOG}")
    print(f"Products: {len(products)}, Journals: {len(ordered)}")
    return catalog


if __name__ == "__main__":
    sync()
