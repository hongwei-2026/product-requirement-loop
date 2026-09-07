#!/usr/bin/env python3
"""审核事件 + 定稿档案台账（可回溯、可检索）。"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
EVENTS_PATH = DATA_DIR / "audit_events.jsonl"
REGISTRY_PATH = DATA_DIR / "approved_registry.json"

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def fingerprint(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_event(
    *,
    actor: str,
    journal_id: str | None,
    journal_title: str | None,
    journal_fingerprint: str | None,
    step: str,
    action: str,
    reason: str = "",
    code: str | None = None,
    summary: str = "",
    artifact: dict | None = None,
    phase_after: str | None = None,
    user_id: int | None = None,
) -> dict:
    """追加一条人可读审核事件（写 SQLite + 文件备份）。"""
    ensure_data_dir()
    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "at": _now(),
        "actor": (actor or "未署名").strip() or "未署名",
        "user_id": user_id,
        "journal_id": journal_id,
        "journal_title": journal_title or journal_id or "（未选日志）",
        "journal_fingerprint": journal_fingerprint,
        "step": step,
        "action": action,
        "code": code,
        "reason": (reason or "").strip(),
        "summary": summary or _default_summary(step, action, reason, code),
        "artifact": artifact or {},
        "phase_after": phase_after,
    }
    line = json.dumps(event, ensure_ascii=False)
    with _lock:
        with EVENTS_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    try:
        from db import db_append_event  # noqa: E402

        db_append_event(event)
    except Exception:
        try:
            from web.db import db_append_event  # noqa: E402

            db_append_event(event)
        except Exception:
            pass
    return event


def _default_summary(step: str, action: str, reason: str, code: str | None) -> str:
    if action == "ok":
        return f"「{step}」通过：{reason or '（无理由）'}"
    if action == "revise":
        return f"「{step}」打叉[{code or '其他'}]并重跑：{reason or '（无理由）'}"
    if action == "unlock":
        return f"「{step}」解锁重做"
    if action == "finalize":
        return f"定稿归档：{reason or '已生成 accepted.json'}"
    if action == "check":
        return f"机器验收：{reason or action}"
    if action == "ai_ready":
        return f"AI 已生成待审库草稿（{step}）"
    if action == "reopen":
        return f"强制复审：{reason or '人工重新打开'}"
    return f"{step}/{action}: {reason or ''}".strip()


def list_events(
    *,
    journal_id: str | None = None,
    limit: int = 200,
    dedupe: bool = True,
) -> list[dict]:
    rows: list[dict] = []
    try:
        from db import db_list_events  # noqa: E402

        rows = list(db_list_events(journal_id=journal_id, limit=max(limit * 3, 50)) or [])
    except Exception:
        try:
            from web.db import db_list_events  # noqa: E402

            rows = list(db_list_events(journal_id=journal_id, limit=max(limit * 3, 50)) or [])
        except Exception:
            rows = []
    if not rows:
        ensure_data_dir()
        if EVENTS_PATH.exists():
            file_rows: list[dict] = []
            with EVENTS_PATH.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        file_rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            if journal_id:
                file_rows = [r for r in file_rows if r.get("journal_id") == journal_id]
            rows = list(reversed(file_rows[-(limit * 3) :]))
    if journal_id:
        rows = [r for r in rows if (r.get("journal_id") or "") == journal_id]
    if dedupe:
        rows = _dedupe_events(rows)
    return rows[:limit]


def _dedupe_events(rows: list[dict]) -> list[dict]:
    """去掉同日志连续重复的「同一步骤同动作同理由」噪声（自测重复写入）。"""
    out: list[dict] = []
    prev_key = None
    for ev in rows:
        key = (
            ev.get("journal_id"),
            ev.get("step"),
            ev.get("action"),
            (ev.get("reason") or "").strip(),
            ev.get("code"),
        )
        if key == prev_key:
            continue
        out.append(ev)
        prev_key = key
    return out


def list_audit_journals(*, limit: int = 80, q: str = "", current_user: dict | None = None) -> list[dict]:
    """按日志聚合：列表一行一个日志，阶段明细点开再看。并标注「现在在哪」与认领/可否继续。"""
    events = list_events(limit=max(400, limit * 12))
    order: list[str] = []
    groups: dict[str, dict] = {}
    for ev in events:
        jid = (ev.get("journal_id") or "").strip()
        title = (ev.get("journal_title") or jid or "（未选日志）").strip()
        key = jid or f"__title__:{title}"
        if key not in groups:
            groups[key] = {
                "journal_id": jid or None,
                "journal_title": title,
                "last_at": ev.get("at"),
                "last_summary": ev.get("summary") or "",
                "last_actor": ev.get("actor") or "",
                "last_action": ev.get("action") or "",
                "event_count": 0,
                "ok_count": 0,
                "revise_count": 0,
                "finalize_count": 0,
                "actors": [],
            }
            order.append(key)
        g = groups[key]
        g["event_count"] += 1
        act = ev.get("action") or ""
        if act == "ok":
            g["ok_count"] += 1
        elif act == "revise":
            g["revise_count"] += 1
        elif act == "finalize":
            g["finalize_count"] += 1
        actor = (ev.get("actor") or "").strip()
        if actor and actor not in g["actors"]:
            g["actors"].append(actor)
    items = [groups[k] for k in order]

    # 台账
    try:
        approved_ids = {x.get("journal_id") for x in list_approved(q="") if x.get("journal_id")}
    except Exception:
        approved_ids = set()

    # 待人审队列（按 journal 取最新一条未完成）
    queue_by_jid: dict[str, dict] = {}
    try:
        from review_queue import claim_ownership, enrich_queue_item, list_queue  # noqa: E402

        openable = {
            "queued",
            "ai_running",
            "pending_human",
            "pending_step1",
            "pending_step2",
            "in_review",
            "step1_passed",
            "failed",
        }
        for qi in list_queue() or []:
            jid = (qi.get("journal_id") or "").strip()
            if not jid or qi.get("status") not in openable:
                continue
            prev = queue_by_jid.get(jid)
            if not prev or (qi.get("updated_at") or "") >= (prev.get("updated_at") or ""):
                queue_by_jid[jid] = enrich_queue_item(qi, current_user)
    except Exception:
        pass

    # 当前工作台 session
    session_jid = ""
    session_phase = ""
    try:
        case_session = PROJECT_DIR / "trials" / "case-01" / "output" / "session.json"
        if case_session.is_file():
            meta = json.loads(case_session.read_text(encoding="utf-8"))
            session_jid = (meta.get("journal_id") or "").strip()
        out = PROJECT_DIR / "trials" / "case-01" / "output"
        if (out / "accepted.json").exists():
            session_phase = "done"
        elif (out / "locked" / "step2-approved.json").exists() and (out / "stories.json").exists():
            session_phase = "step3_ready"
        elif (out / "stories.json").exists():
            session_phase = "step2_review"
        elif (out / "requirement-story.md").exists():
            session_phase = "step1_review"
        else:
            session_phase = "idle"
    except Exception:
        pass

    status_zh = {
        "queued": "排队等 AI",
        "ai_running": "AI 正在写",
        "pending_step1": "等人审 Step1",
        "pending_step2": "等人审 Step2",
        "pending_human": "等人审",
        "in_review": "人审进行中",
        "step1_passed": "Step1 已过，跑 Step2",
        "failed": "失败可重开",
        "step3_ready": "工作台 · 待定稿",
        "step2_review": "工作台 · 审 Step2",
        "step1_review": "工作台 · 审 Step1",
        "done": "工作台 · 已定稿产物",
    }

    for it in items:
        jid = it.get("journal_id") or ""
        it["in_registry"] = bool(jid and jid in approved_ids)
        if it["in_registry"] and not it.get("finalize_count"):
            it["finalize_count"] = 1

        loc = "history_only"
        loc_label = "仅有历史（不在待审库/定稿档案）"
        continue_action = "reopen"
        queue_id = None

        if it["in_registry"]:
            loc = "registry"
            loc_label = "定稿档案"
            continue_action = "registry"
        elif jid and jid in queue_by_jid:
            qi = queue_by_jid[jid]
            loc = "queue"
            queue_id = qi.get("id")
            st = qi.get("status") or ""
            claim_short = qi.get("claim_short") or ""
            base = f"待审库 · {status_zh.get(st, st)}"
            if claim_short:
                loc_label = f"{base} · {claim_short}"
            else:
                loc_label = base
            ownership = qi.get("claim_ownership") or "unclaimed"
            # 他人已认领：可看不可继续打开队列
            if ownership == "others":
                continue_action = "view_only"
                it["can_continue"] = False
                it["continue_blocked_reason"] = qi.get("claim_label") or "已被他人认领"
            else:
                continue_action = "queue"
                it["can_continue"] = True
            it["queue_status"] = st
            it["claim_ownership"] = ownership
            it["claim_label"] = qi.get("claim_label")
            it["assignee_name"] = qi.get("assignee_name")
        elif jid and jid == session_jid and session_phase not in {"", "idle", "done"}:
            loc = "workbench"
            loc_label = status_zh.get(session_phase, f"工作台 · {session_phase}")
            continue_action = "workbench"
            it["workbench_phase"] = session_phase
            it["can_continue"] = True
        elif jid and jid == session_jid and session_phase == "done":
            # 工作台有定稿产物但台账可能已写；若未进定稿档案仍提示去定稿
            if not it["in_registry"]:
                loc = "workbench"
                loc_label = "工作台 · 有定稿产物未同步？"
                continue_action = "workbench"
                it["can_continue"] = True
            else:
                loc = "registry"
                loc_label = "定稿档案"
                continue_action = "registry"
                it["can_continue"] = True

        if "can_continue" not in it:
            # registry / history_only / reopen
            it["can_continue"] = continue_action != "view_only"

        it["location"] = loc
        it["location_label"] = loc_label
        it["continue_action"] = continue_action
        it["queue_id"] = queue_id

    qq = (q or "").strip().lower()
    if qq:
        items = [
            it
            for it in items
            if qq in (it.get("journal_id") or "").lower()
            or qq in (it.get("journal_title") or "").lower()
            or qq in (it.get("location_label") or "").lower()
            or qq in (it.get("claim_label") or "").lower()
            or any(qq in a.lower() for a in (it.get("actors") or []))
        ]
    return items[:limit]


def load_registry() -> dict:
    try:
        from db import db_approved_map  # noqa: E402

        items = db_approved_map()
        if items:
            return {"version": 1, "items": items, "source": "sqlite"}
    except Exception:
        try:
            from web.db import db_approved_map  # noqa: E402

            items = db_approved_map()
            if items:
                return {"version": 1, "items": items, "source": "sqlite"}
        except Exception:
            pass
    ensure_data_dir()
    if not REGISTRY_PATH.exists():
        return {"version": 1, "items": {}}
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if "items" not in data:
            data = {"version": 1, "items": data if isinstance(data, dict) else {}}
        return data
    except Exception:
        return {"version": 1, "items": {}}


def save_registry(data: dict) -> None:
    ensure_data_dir()
    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def register_approved(
    *,
    journal_id: str,
    journal_title: str,
    journal_fingerprint: str,
    approver: str,
    accepted_relpath: str,
    story_count: int,
    product: str | None = None,
    audit_event_id: str | None = None,
    approver_user_id: int | None = None,
    accepted_json: str | None = None,
) -> dict:
    # 先查库：同一 journal_id 再定稿应是「更新」而不是「新增一条」
    prev_db = None
    try:
        prev_db = get_approved(journal_id)
    except Exception:
        prev_db = None
    rec = {
        "journal_id": journal_id,
        "title": journal_title or journal_id,
        "product": product,
        "fingerprint": journal_fingerprint,
        "status": "approved",
        "approver": approver,
        "approver_user_id": approver_user_id,
        "approved_at": _now(),
        "accepted_path": accepted_relpath,
        "story_count": story_count,
        "audit_event_ids": [audit_event_id] if audit_event_id else [],
        "accepted_json": accepted_json,
    }
    was_update = bool(prev_db)
    prev_file: dict = {}
    with _lock:
        ensure_data_dir()
        file_data = {"version": 1, "items": {}}
        if REGISTRY_PATH.exists():
            try:
                file_data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
                if "items" not in file_data:
                    file_data = {"version": 1, "items": {}}
            except Exception:
                file_data = {"version": 1, "items": {}}
        prev_file = file_data["items"].get(journal_id) or {}
        was_update = bool(prev_db) or bool(prev_file)
        event_ids = list(
            prev_file.get("audit_event_ids")
            or (prev_db or {}).get("audit_event_ids")
            or []
        )
        for eid in rec["audit_event_ids"]:
            if eid and eid not in event_ids:
                event_ids.append(eid)
        rec["audit_event_ids"] = event_ids
        # JSON 台账不写 accepted_json（太大）；完整 JSON 在 SQLite
        file_data["items"][journal_id] = {
            k: v for k, v in rec.items() if k not in {"accepted_json"}
        }
        save_registry(file_data)
    try:
        from db import db_register_approved  # noqa: E402

        saved = db_register_approved(rec)
    except Exception:
        try:
            from web.db import db_register_approved  # noqa: E402

            saved = db_register_approved(rec)
        except Exception:
            saved = rec
    saved = dict(saved or rec)
    saved["updated"] = was_update
    if was_update:
        saved["previous_approved_at"] = (prev_db or prev_file or {}).get("approved_at")
    return saved


def get_approved(journal_id: str) -> dict | None:
    try:
        from db import db_get_approved  # noqa: E402

        hit = db_get_approved(journal_id)
        if hit:
            return hit
    except Exception:
        try:
            from web.db import db_get_approved  # noqa: E402

            hit = db_get_approved(journal_id)
            if hit:
                return hit
        except Exception:
            pass
    ensure_data_dir()
    if not REGISTRY_PATH.exists():
        return None
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return (data.get("items") or {}).get(journal_id)
    except Exception:
        return None


def list_approved(q: str = "") -> list[dict]:
    items: list[dict] = []
    try:
        from db import db_list_approved  # noqa: E402

        items = db_list_approved(q="")
    except Exception:
        try:
            from web.db import db_list_approved  # noqa: E402

            items = db_list_approved(q="")
        except Exception:
            items = []
    if not items:
        ensure_data_dir()
        if REGISTRY_PATH.exists():
            try:
                data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
                items = list((data.get("items") or {}).values())
            except Exception:
                items = []
    items.sort(key=lambda x: x.get("approved_at") or "", reverse=True)
    qq = (q or "").strip().lower()
    if not qq:
        return items
    out = []
    for it in items:
        blob = " ".join(
            str(it.get(k) or "") for k in ("journal_id", "title", "approver", "product", "status")
        ).lower()
        if qq in blob:
            out.append(it)
    return out


def approval_status(journal_id: str, content: str | None = None) -> dict:
    """返回该日志相对台账的状态。"""
    rec = get_approved(journal_id)
    if not rec:
        return {"status": "new", "label": "未定稿", "record": None}
    fp = fingerprint(content) if content is not None else None
    if fp and rec.get("fingerprint") and fp != rec.get("fingerprint"):
        return {
            "status": "stale",
            "label": "已定稿但原文已变（需复审）",
            "record": rec,
        }
    return {"status": "approved", "label": "已定稿", "record": rec}


def get_registry_detail(journal_id: str) -> dict:
    """定稿档案详情：台账 + 定稿 JSON（含需求故事）+ 该日志审核阶段。"""
    jid = (journal_id or "").strip()
    if not jid:
        raise ValueError("缺少 journal_id")
    rec = get_approved(jid)
    if not rec:
        raise FileNotFoundError(f"未找到定稿档案: {jid}")
    accepted = None
    # 1) SQLite 里存的完整 JSON（复审后会更新）
    raw_json = rec.get("accepted_json")
    if raw_json:
        try:
            accepted = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except Exception:
            accepted = None
    # 2) 归档文件
    if accepted is None:
        accepted_path = rec.get("accepted_path") or ""
        if accepted_path:
            path = PROJECT_DIR / accepted_path
            if path.is_file():
                try:
                    accepted = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    accepted = None
    # 3) 同 journal_id 最新归档兜底
    if accepted is None:
        archive_dir = PROJECT_DIR / "data" / "accepted"
        if archive_dir.is_dir():
            cands = sorted(
                archive_dir.glob(f"{jid}-*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for p in cands:
                try:
                    accepted = json.loads(p.read_text(encoding="utf-8"))
                    break
                except Exception:
                    continue
    events = list_events(journal_id=jid, limit=100)
    # 严格只保留本 journal_id，避免串日志
    events = [e for e in events if (e.get("journal_id") or "") == jid]
    return {
        "ok": True,
        "record": rec,
        "accepted": accepted,
        "requirement_story": (accepted or {}).get("requirement_story") or "",
        "events": events,
        "event_count": len(events),
    }


def clear_events_for_tests() -> None:
    """仅测试用。"""
    ensure_data_dir()
    with _lock:
        if EVENTS_PATH.exists():
            EVENTS_PATH.write_text("", encoding="utf-8")


def clear_registry_for_tests() -> None:
    ensure_data_dir()
    with _lock:
        save_registry({"version": 1, "items": {}})
