#!/usr/bin/env python3
"""研发日志库：列表 / 选择 / 粘贴 / 上传（扫描 journals/ 全量）。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
JOURNALS_DIR = PROJECT_DIR / "journals"
CATALOG = JOURNALS_DIR / "catalog.json"
CUSTOM_DIR = JOURNALS_DIR / "custom"

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
    "custom": "自定义",
}


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _estimate_speed(chars: int) -> str:
    if chars < 1200:
        return "快"
    if chars < 3500:
        return "中"
    return "慢"


def _safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(JOURNALS_DIR.resolve())).replace("\\", "/")
    except ValueError:
        return path.name


def _load_catalog() -> dict:
    if CATALOG.exists():
        return json.loads(CATALOG.read_text(encoding="utf-8"))
    return {"selection_guide": {}, "journals": []}


def _resolve_file(rel: str) -> Path:
    path = (JOURNALS_DIR / rel).resolve()
    root = JOURNALS_DIR.resolve()
    if root not in path.parents and path != root:
        raise ValueError("非法日志路径")
    if not path.is_file():
        raise FileNotFoundError(f"日志不存在: {rel}")
    return path


def _preview(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())[:140]


def _scan_disk() -> list[dict]:
    """扫描 journals/**/*.md，补全 catalog 未登记的文件。"""
    items = []
    if not JOURNALS_DIR.exists():
        return items
    for path in JOURNALS_DIR.rglob("*.md"):
        if path.name.lower() in {"readme.md"}:
            continue
        rel = _safe_rel(path)
        parts = Path(rel).parts
        if not parts:
            continue
        product = parts[0] if len(parts) > 1 else "custom"
        stem = path.stem
        date = stem[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", stem) else ""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        chars = len(text)
        label = PRODUCT_LABELS.get(product, product)
        is_excerpt = "excerpt" in stem.lower()
        usage = "try" if is_excerpt else ("custom" if product == "custom" else "formal")
        jid = f"{product}-{stem}"
        title = f"{label} · 捕捉用户故事（聚焦摘录）" if is_excerpt else (
            f"{label} · {date}" if date else f"{label} · {stem}"
        )
        items.append(
            {
                "id": jid,
                "title": title,
                "product": product,
                "date": date,
                "file": rel,
                "usage": usage,
                "speed": _estimate_speed(chars),
                "why": "官方日日志全文" if usage == "formal" else (
                    "聚焦摘要；选用后左侧对比自动加载同日全文" if usage == "try" else "自定义上传/粘贴"
                ),
                "when": "正式定稿" if usage == "formal" else (
                    "试跑/拍视频（摘要提示关注点）" if usage == "try" else "临时材料"
                ),
                "chars": chars,
                "preview": _preview(text),
                "kind": "custom" if product == "custom" else "library",
            }
        )
    return items


def list_journals() -> dict:
    cat = _load_catalog()
    by_file: dict[str, dict] = {}

    for j in cat.get("journals") or []:
        rel = (j.get("file") or "").replace("\\", "/")
        if not rel:
            continue
        try:
            path = _resolve_file(rel)
            text = path.read_text(encoding="utf-8")
            chars = len(text)
            preview = _preview(text)
        except Exception:
            chars = int(j.get("chars") or 0)
            preview = "（文件缺失）"
        by_file[rel] = {
            **j,
            "file": rel,
            "chars": chars,
            "speed": j.get("speed") or _estimate_speed(chars),
            "preview": preview,
            "kind": j.get("kind") or "library",
        }

    for j in _scan_disk():
        rel = j["file"]
        if rel not in by_file:
            by_file[rel] = j
        else:
            # 用磁盘字数刷新
            by_file[rel]["chars"] = j["chars"]
            by_file[rel]["preview"] = j["preview"]
            by_file[rel]["speed"] = j.get("speed") or by_file[rel].get("speed")

    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)

    items = list(by_file.values())
    items.sort(
        key=lambda x: (
            0 if x.get("usage") == "try" else 1,
            x.get("date") or "",
            x.get("product") or "",
        ),
        reverse=True,
    )
    # try 摘录置顶：再排一次
    tries = [x for x in items if x.get("usage") == "try"]
    others = [x for x in items if x.get("usage") != "try"]
    others.sort(key=lambda x: (x.get("date") or "", x.get("product") or ""), reverse=True)
    items = tries + others

    products = sorted({x.get("product") or "unknown" for x in items})
    # 合并定稿档案状态（不读全文，仅按 journal_id）
    try:
        from audit_store import load_registry  # noqa: E402
    except ImportError:
        from web.audit_store import load_registry  # noqa: E402
    approved_map = (load_registry().get("items") or {})
    approved_n = 0
    for it in items:
        rec = approved_map.get(it["id"])
        if rec:
            it["review_status"] = "approved"
            it["review_label"] = "已定稿"
            it["approved_at"] = rec.get("approved_at")
            it["approver"] = rec.get("approver")
            approved_n += 1
        else:
            it["review_status"] = "new"
            it["review_label"] = "未定稿"

    # 已定稿但书架上没有的（如历史演示 id）也要能看见
    known_ids = {x["id"] for x in items}
    for jid, rec in approved_map.items():
        if not jid or jid in known_ids:
            continue
        product = rec.get("product") or "custom"
        items.insert(
            0,
            {
                "id": jid,
                "title": rec.get("title") or jid,
                "product": product,
                "date": "",
                "file": "",
                "usage": "custom",
                "speed": "快",
                "why": "定稿档案（台账同步到日志库，便于复审）",
                "when": "查看定稿档案 / 强制复审",
                "chars": 0,
                "preview": "来自定稿档案",
                "kind": "registry",
                "review_status": "approved",
                "review_label": "已定稿",
                "approved_at": rec.get("approved_at"),
                "approver": rec.get("approver"),
            },
        )
        approved_n += 1
        known_ids.add(jid)
    return {
        "ok": True,
        "guide": cat.get("selection_guide")
        or {
            "principle": "先定今天要梳理的一件事 → 选产品流 → 选日期。已定稿日志可检索，默认不必重审。",
            "filters": ["产品流", "日期", "用途", "速度", "定稿状态"],
        },
        "journals": items,
        "products": products,
        "product_labels": PRODUCT_LABELS,
        "stats": {
            "total": len(items),
            "products": len(products),
            "formal": sum(1 for x in items if x.get("usage") == "formal"),
            "try": sum(1 for x in items if x.get("usage") == "try"),
            "custom": sum(1 for x in items if x.get("usage") == "custom"),
            "approved": approved_n,
            "synced_at": cat.get("synced_at"),
            "source_repo": (cat.get("selection_guide") or {}).get("source_repo")
            or "https://github.com/quanttide/quanttide-journal-of-product-development",
        },
    }


def _resolve_full_sibling(rel_file: str) -> Path | None:
    """摘录文件对应的同日全文：xxx-excerpt.md → xxx.md"""
    rel = (rel_file or "").replace("\\", "/")
    p = Path(rel)
    stem = p.stem
    if "excerpt" not in stem.lower():
        return None
    full_stem = re.sub(r"[-_]?excerpt$", "", stem, flags=re.IGNORECASE)
    if not full_stem or full_stem == stem:
        return None
    cand = (JOURNALS_DIR / p.parent / f"{full_stem}.md").resolve()
    root = JOURNALS_DIR.resolve()
    if root not in cand.parents and cand != root:
        return None
    return cand if cand.is_file() else None


def _clean_excerpt_display(text: str) -> str:
    """摘要展示：去掉「非全文 / 不要当原文」等说明头，只留人读的关注点。"""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    out: list[str] = []
    skip_meta = True
    for line in lines:
        t = line.strip()
        if skip_meta:
            if not t or t.startswith("#") and ("摘录" in t or "非全文" in t):
                continue
            if t.startswith(">"):
                continue
            if t.startswith("摘自") or "journal-official-full" in t or ".md" in t and "见同目录" in t:
                continue
            if t == "---" or t.startswith("---"):
                continue
            skip_meta = False
        if "不要" in t and "原始日志" in t:
            continue
        if "journal-official-full" in t:
            continue
        out.append(line)
    body = "\n".join(out).strip()
    return body or (text or "").strip()


def read_journal(journal_id: str) -> dict:
    data = list_journals()
    for j in data["journals"]:
        if j["id"] == journal_id:
            # 台账同步的空壳：用已归档 accepted / 演示文件还原可读原文
            if not j.get("file"):
                try:
                    from audit_store import get_registry_detail  # noqa: E402
                except ImportError:
                    from web.audit_store import get_registry_detail  # noqa: E402
                detail = get_registry_detail(journal_id)
                accepted = detail.get("accepted") or {}
                story = accepted.get("requirement_story") or ""
                quotes = [
                    (s.get("source_quote") or "")
                    for s in (accepted.get("stories") or [])
                    if s.get("source_quote")
                ]
                content = story.strip() or ("\n\n".join(quotes) if quotes else f"# {j.get('title') or journal_id}\n\n（仅有定稿档案，原文文件未登记）\n")
                return {
                    "ok": True,
                    "id": journal_id,
                    "meta": {**j, "compare_source": "registry", "has_full": False},
                    "content": content,
                    "excerpt": "",
                    "chars": len(content),
                    "path": (detail.get("record") or {}).get("accepted_path") or "",
                    "selected_file": "",
                }
            path = _resolve_file(j["file"])
            raw = path.read_text(encoding="utf-8")
            is_excerpt = "excerpt" in Path(j["file"]).stem.lower()
            full_path = _resolve_full_sibling(j["file"]) if is_excerpt else None
            if full_path and full_path.is_file():
                full_text = full_path.read_text(encoding="utf-8")
                excerpt_text = _clean_excerpt_display(raw)
                meta = {
                    **j,
                    "compare_source": "full",
                    "has_full": True,
                    "full_file": _safe_rel(full_path),
                    "excerpt_chars": len(excerpt_text),
                    "full_chars": len(full_text),
                }
                return {
                    "ok": True,
                    "id": journal_id,
                    "meta": meta,
                    # 闭环 / 对比默认用全文
                    "content": full_text,
                    "excerpt": excerpt_text,
                    "chars": len(full_text),
                    "path": meta["full_file"],
                    "selected_file": j["file"],
                }
            # 无全文可解：本身就是全文或自定义
            return {
                "ok": True,
                "id": journal_id,
                "meta": {**j, "compare_source": "self", "has_full": not is_excerpt, "full_chars": len(raw)},
                "content": raw,
                "excerpt": "",
                "chars": len(raw),
                "path": j["file"],
                "selected_file": j["file"],
            }
    raise FileNotFoundError(f"未找到日志: {journal_id}")


def save_pasted(title: str, content: str, product: str = "custom") -> dict:
    text = (content or "").strip()
    if len(text) < 20:
        raise ValueError("粘贴内容太短（至少约 20 字）")
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", (title or "paste").strip())[:40] or "paste"
    name = f"{_now_slug()}-{slug}.md"
    path = CUSTOM_DIR / name
    header = f"# {title or '粘贴日志'}\n\n> 来源：前端粘贴 · product={product}\n\n"
    path.write_text(header + text, encoding="utf-8")
    return {
        "ok": True,
        "id": f"custom-{path.stem}",
        "path": _safe_rel(path),
        "chars": len(path.read_text(encoding="utf-8")),
        "message": "已保存到自定义日志库，并可选中使用",
    }


def save_upload(filename: str, content: str) -> dict:
    text = (content or "").strip()
    if len(text) < 20:
        raise ValueError("上传内容太短")
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    base = Path(filename or "upload.md").name
    base = re.sub(r"[^\w.\u4e00-\u9fff-]+", "-", base)
    if not base.lower().endswith(".md"):
        base += ".md"
    path = CUSTOM_DIR / f"{_now_slug()}-{base}"
    path.write_text(text, encoding="utf-8")
    return {
        "ok": True,
        "id": f"custom-{path.stem}",
        "path": _safe_rel(path),
        "chars": len(text),
        "message": "上传成功",
    }
