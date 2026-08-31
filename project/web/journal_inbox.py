#!/usr/bin/env python3
"""官方研发日志「获取信息」暂存箱：先拉取，人同意后再写入 journals 库。

来源固定为官方仓库（非 fork）：
  https://github.com/quanttide/quanttide-journal-of-product-development
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
INBOX_DIR = DATA_DIR / "journal_inbox"
INBOX_META = INBOX_DIR / "inbox.json"
JOURNALS_DIR = PROJECT_DIR / "journals"
CATALOG = JOURNALS_DIR / "catalog.json"

API_ROOT = "https://api.github.com/repos/quanttide/quanttide-journal-of-product-development/contents"
RAW = "https://raw.githubusercontent.com/quanttide/quanttide-journal-of-product-development/main"
SOURCE_REPO = "https://github.com/quanttide/quanttide-journal-of-product-development"
SOURCE_TREE = f"{SOURCE_REPO}/blob/main"

SKIP_DIRS = {"default", ".github"}
SIMILARITY_CANCEL = 0.92  # 与已有内容高度相似则取消入库候选

_lock = threading.Lock()

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


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "quanttide-product-requirement-inbox"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "quanttide-product-requirement-inbox"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8")


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _similarity(a: str, b: str) -> float:
    x, y = _compact(a), _compact(b)
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0
    if x in y or y in x:
        return max(len(x), len(y)) and min(len(x), len(y)) / max(len(x), len(y))
    # char bigram Jaccard
    def grams(s: str) -> set[str]:
        return {s[i : i + 2] for i in range(max(0, len(s) - 1))}

    A, B = grams(x), grams(y)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    return inter / (len(A) + len(B) - inter)


def _load_inbox() -> dict:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    if not INBOX_META.exists():
        return {"version": 1, "batches": [], "items": []}
    try:
        return json.loads(INBOX_META.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "batches": [], "items": []}


def _save_inbox(data: dict) -> None:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_META.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _existing_library() -> list[tuple[str, str]]:
    """已有日志 (id, content) 列表，用于相似检测。"""
    out: list[tuple[str, str]] = []
    if not JOURNALS_DIR.exists():
        return out
    for path in JOURNALS_DIR.rglob("*.md"):
        if path.name.lower() == "readme.md":
            continue
        try:
            rel = str(path.relative_to(JOURNALS_DIR)).replace("\\", "/")
            text = path.read_text(encoding="utf-8")
            out.append((rel, text))
        except Exception:
            continue
    return out


def fetch_from_official(*, max_per_product: int = 40) -> dict:
    """从官方仓库拉取到暂存箱。不做 journals 入库。"""
    batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    existing = _existing_library()
    items_new: list[dict] = []
    cancelled: list[dict] = []
    errors: list[str] = []

    try:
        root = _http_json(f"{API_ROOT}?ref=main")
    except Exception as e:
        return {"ok": False, "error": f"无法访问官方仓库 API：{e}", "source_repo": SOURCE_REPO}

    products = sorted(
        x["name"]
        for x in root
        if x.get("type") == "dir" and x["name"] not in SKIP_DIRS and not x["name"].startswith(".")
    )

    for product in products:
        label = PRODUCT_LABELS.get(product, product)
        try:
            files = _http_json(f"{API_ROOT}/{product}?ref=main")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            errors.append(f"{product}: HTTP {e.code}")
            continue
        except Exception as e:
            errors.append(f"{product}: {e}")
            continue

        md_files = [
            x
            for x in files
            if x.get("type") == "file"
            and str(x.get("name") or "").endswith(".md")
            and re.match(r"^\d{4}-\d{2}-\d{2}", str(x.get("name") or ""))
        ]
        md_files.sort(key=lambda x: x["name"], reverse=True)
        for f in md_files[: max(1, max_per_product)]:
            name = f["name"]
            date = name[:10]
            rel = f"{product}/{name}"
            jid = f"{product}-{Path(name).stem}"
            try:
                text = _http_text(f"{RAW}/{product}/{name}")
            except Exception as e:
                errors.append(f"{rel}: {e}")
                continue

            # 高度相似 → 取消
            best_sim, best_hit = 0.0, ""
            for erel, etxt in existing:
                sim = _similarity(text, etxt)
                if sim > best_sim:
                    best_sim, best_hit = sim, erel
            if best_sim >= SIMILARITY_CANCEL:
                cancelled.append(
                    {
                        "id": jid,
                        "file": rel,
                        "reason": f"与已有 {best_hit} 相似度 {best_sim:.0%} ≥ {SIMILARITY_CANCEL:.0%}，已取消",
                        "similarity": round(best_sim, 4),
                        "matched": best_hit,
                    }
                )
                continue

            # 已在暂存且未处理则跳过重复写入
            batch_dir = INBOX_DIR / batch_id
            batch_dir.mkdir(parents=True, exist_ok=True)
            dest = batch_dir / product
            dest.mkdir(parents=True, exist_ok=True)
            (dest / name).write_text(text, encoding="utf-8")

            chars = len(text)
            preview = re.sub(r"\s+", " ", text.strip())[:140]
            item = {
                "id": f"{batch_id}::{jid}",
                "batch_id": batch_id,
                "journal_id": jid,
                "title": f"{label} · {date}",
                "product": product,
                "product_label": label,
                "date": date,
                "file": rel,
                "chars": chars,
                "preview": preview,
                "source_url": f"{SOURCE_TREE}/{rel}",
                "local_path": str((dest / name).relative_to(INBOX_DIR)).replace("\\", "/"),
                "status": "pending_import",  # 等人同意入库
                "fetched_at": _now(),
                "suggest_reason": (
                    f"官方日日志 · {label} · {date} · {chars} 字。"
                    f"建议入库到日志库「{product}」目录，便于按产品流筛选与正式定稿。"
                ),
                "similarity_max": round(best_sim, 4),
            }
            items_new.append(item)

    with _lock:
        data = _load_inbox()
        data.setdefault("batches", []).insert(
            0,
            {
                "id": batch_id,
                "fetched_at": _now(),
                "source_repo": SOURCE_REPO,
                "new_count": len(items_new),
                "cancelled_count": len(cancelled),
                "error_count": len(errors),
            },
        )
        data["batches"] = data["batches"][:30]
        # 去掉同 journal_id 仍 pending 的旧项，避免重复
        old = [
            x
            for x in (data.get("items") or [])
            if not (
                x.get("status") == "pending_import"
                and x.get("journal_id") in {i["journal_id"] for i in items_new}
            )
        ]
        data["items"] = items_new + old
        _save_inbox(data)

    return {
        "ok": True,
        "batch_id": batch_id,
        "source_repo": SOURCE_REPO,
        "new_count": len(items_new),
        "cancelled_count": len(cancelled),
        "cancelled": cancelled[:40],
        "errors": errors[:20],
        "message": (
            f"已从官方仓库拉取：新增候选 {len(items_new)} 条；"
            f"因高度相似取消 {len(cancelled)} 条。获取≠入库，请在「获取信息」页逐批确认。"
        ),
    }


def compare_inbox_item(item_id: str, *, top_n: int = 8) -> dict:
    """立刻比对暂存项与「日志库 journals/」（不是定稿档案）。"""
    data = _load_inbox()
    it = next((x for x in (data.get("items") or []) if x.get("id") == item_id), None)
    if not it:
        return {"ok": False, "error": "暂存项不存在"}
    local = INBOX_DIR / (it.get("local_path") or "")
    if not local.is_file():
        return {"ok": False, "error": "暂存文件缺失"}
    text = local.read_text(encoding="utf-8")
    want_jid = (it.get("journal_id") or "").strip()
    want_product = (it.get("product") or "").strip()
    want_date = (it.get("date") or "").strip()
    scored: list[dict] = []

    for rel, etxt in _existing_library():
        parts = rel.split("/")
        jid = Path(rel).stem
        if len(parts) >= 2:
            jid = f"{parts[0]}-{Path(parts[-1]).stem}"
        product = parts[0] if len(parts) >= 2 else ""
        date = ""
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", Path(parts[-1]).stem if parts else "")
        if m:
            date = m.group(1)

        sim = _similarity(text, etxt)
        same_id = bool(want_jid and jid == want_jid)
        same_key = bool(want_product and want_date and product == want_product and date == want_date)
        # 同 id / 同产品同日：一律列入，哪怕正文相似度偏低（怕漏）
        if not same_id and not same_key and sim < 0.28:
            continue
        scored.append(
            {
                "journal_id": jid,
                "file": rel,
                "similarity": round(sim, 4),
                "chars": len(etxt),
                "preview": re.sub(r"\s+", " ", etxt.strip())[:160],
                "identical": sim >= 0.995 or same_id,
                "highly_similar": sim >= SIMILARITY_CANCEL,
                "same_id": same_id,
                "same_product_date": same_key,
                "content": etxt if (sim >= 0.40 or same_id or same_key) else "",
                "in_journal_library": True,
            }
        )

    def _rank(x: dict) -> tuple:
        return (
            1 if x.get("same_id") else 0,
            1 if x.get("same_product_date") else 0,
            x.get("similarity") or 0,
        )

    scored.sort(key=_rank, reverse=True)
    top = scored[: max(1, top_n)]
    best = top[0] if top else None

    if best and best.get("same_id"):
        msg = f"日志库已有同 id：{best['journal_id']}（文件 {best['file']}）"
    elif best and best.get("same_product_date"):
        msg = f"日志库已有同产品流+同日：{best['journal_id']}（相似 {best['similarity']:.0%}）"
    elif best and best["similarity"] >= 0.55:
        msg = f"日志库发现相似全文：{best['journal_id']}（相似度 {best['similarity']:.0%}）"
    else:
        msg = "日志库（journals/）中未发现同 id / 同日或明显相同全文（对比的是日志库，不是「定稿档案」）"

    return {
        "ok": True,
        "compare_target": "journal_library",
        "compare_target_label": "日志库 journals/",
        "item": {
            "id": it.get("id"),
            "journal_id": it.get("journal_id"),
            "title": it.get("title"),
            "chars": len(text),
            "source_url": it.get("source_url"),
            "content": text,
        },
        "matches": top,
        "best": best,
        "has_match": bool(
            best
            and (
                best.get("same_id")
                or best.get("same_product_date")
                or (best.get("similarity") or 0) >= 0.55
            )
        ),
        "message": msg,
    }


def get_inbox_item(item_id: str) -> dict:
    data = _load_inbox()
    it = next((x for x in (data.get("items") or []) if x.get("id") == item_id), None)
    if not it:
        return {"ok": False, "error": "暂存项不存在"}
    local = INBOX_DIR / (it.get("local_path") or "")
    content = local.read_text(encoding="utf-8") if local.is_file() else ""
    return {"ok": True, "item": {**it, "content": content, "chars": len(content)}}


def auto_fetch_if_due(*, force: bool = False) -> dict:
    """每日自动拉取一次（按本机日期）。force=True 时忽略已拉取标记。"""
    marker = INBOX_DIR / "last_auto_fetch_day.txt"
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    if not force and marker.exists():
        try:
            if marker.read_text(encoding="utf-8").strip() == today:
                return {"ok": True, "skipped": True, "reason": f"今日 {today} 已自动拉取过", "day": today}
        except Exception:
            pass
    result = fetch_from_official(max_per_product=20)
    if result.get("ok"):
        marker.write_text(today, encoding="utf-8")
        result["auto"] = True
        result["day"] = today
    return result


def start_auto_fetch_worker() -> None:
    """后台：启动时检查一次，之后每小时看是否跨天。"""

    def _loop() -> None:
        import time

        time.sleep(8)
        while True:
            try:
                auto_fetch_if_due(force=False)
            except Exception:
                pass
            time.sleep(3600)

    t = threading.Thread(target=_loop, name="journal-inbox-auto-fetch", daemon=True)
    t.start()


def list_inbox(*, status: str = "pending_import") -> dict:
    data = _load_inbox()
    items = data.get("items") or []
    if status:
        items = [x for x in items if x.get("status") == status]
    # 按日期分组
    groups: dict[str, list] = {}
    for it in items:
        day = (it.get("fetched_at") or "")[:10] or (it.get("date") or "未知日期")
        groups.setdefault(day, []).append(it)
    ordered_days = sorted(groups.keys(), reverse=True)
    return {
        "ok": True,
        "source_repo": SOURCE_REPO,
        "batches": data.get("batches") or [],
        "groups": [{"date": d, "items": groups[d], "count": len(groups[d])} for d in ordered_days],
        "pending_count": sum(1 for x in (data.get("items") or []) if x.get("status") == "pending_import"),
        "product_labels": PRODUCT_LABELS,
    }


def approve_inbox_items(item_ids: list[str]) -> dict:
    """人同意后写入 journals/ 并刷新 catalog 条目。"""
    if not item_ids:
        return {"ok": False, "error": "未选择任何条目"}
    imported = []
    with _lock:
        data = _load_inbox()
        by_id = {x["id"]: x for x in data.get("items") or []}
        for iid in item_ids:
            it = by_id.get(iid)
            if not it or it.get("status") != "pending_import":
                continue
            local = INBOX_DIR / (it.get("local_path") or "")
            if not local.is_file():
                it["status"] = "failed"
                it["error"] = "暂存文件缺失"
                continue
            text = local.read_text(encoding="utf-8")
            # 再检一次相似
            best = 0.0
            for _rel, etxt in _existing_library():
                best = max(best, _similarity(text, etxt))
            if best >= SIMILARITY_CANCEL:
                it["status"] = "cancelled_similar"
                it["error"] = f"入库前复检相似 {best:.0%}，已取消"
                continue
            dest = JOURNALS_DIR / it["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            _upsert_catalog_entry(it, len(text))
            it["status"] = "imported"
            it["imported_at"] = _now()
            imported.append(it["journal_id"])
        _save_inbox(data)
    return {
        "ok": True,
        "imported": imported,
        "count": len(imported),
        "message": f"已写入日志库 {len(imported)} 条（符合 journals/ 产品流×日期规范）",
    }


def reject_inbox_items(item_ids: list[str], reason: str = "") -> dict:
    with _lock:
        data = _load_inbox()
        want = set(item_ids or [])
        for it in data.get("items") or []:
            if it.get("id") in want and it.get("status") == "pending_import":
                it["status"] = "rejected"
                it["reject_reason"] = reason or "人工拒绝"
                it["rejected_at"] = _now()
        _save_inbox(data)
    return {"ok": True, "message": f"已拒绝 {len(want)} 条"}


def _upsert_catalog_entry(it: dict, chars: int) -> None:
    cat = {"journals": [], "selection_guide": {}}
    if CATALOG.exists():
        try:
            cat = json.loads(CATALOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    journals = cat.get("journals") or []
    jid = it["journal_id"]
    entry = {
        "id": jid,
        "title": it.get("title") or jid,
        "product": it.get("product"),
        "date": it.get("date"),
        "file": it.get("file"),
        "usage": "formal",
        "speed": "快" if chars < 1200 else ("中" if chars < 3500 else "慢"),
        "why": f"官方日日志全文（{chars} 字，获取信息页确认入库）",
        "when": "正式梳理/定稿时选对应产品流 + 日期",
        "source": f"quanttide-journal-of-product-development/{it.get('file')}",
        "source_url": it.get("source_url"),
        "chars": chars,
        "kind": "library",
    }
    journals = [j for j in journals if j.get("id") != jid and j.get("file") != it.get("file")]
    journals.insert(0, entry)
    cat["journals"] = journals
    cat["journal_count"] = len(journals)
    cat["synced_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    guide = cat.get("selection_guide") or {}
    guide["source_repo"] = SOURCE_REPO
    cat["selection_guide"] = guide
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
