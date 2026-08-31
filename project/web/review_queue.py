#!/usr/bin/env python3
"""待人审队列：批量 AI 生成草稿 → 人工逐条审核。"""

from __future__ import annotations

import json
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
QUEUE_PATH = DATA_DIR / "review_queue.json"
ITEMS_DIR = DATA_DIR / "queue_items"

_lock = threading.Lock()
_worker_started = False


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    ensure_dirs()
    if not QUEUE_PATH.exists():
        return {"version": 1, "items": []}
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "items": []}


def _save(data: dict) -> None:
    ensure_dirs()
    QUEUE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from db import db_queue_upsert  # noqa: E402

        for it in data.get("items") or []:
            db_queue_upsert(it)
    except Exception:
        try:
            from web.db import db_queue_upsert  # noqa: E402

            for it in data.get("items") or []:
                db_queue_upsert(it)
        except Exception:
            pass


def list_queue(status: str | None = None) -> list[dict]:
    try:
        from db import db_queue_list  # noqa: E402

        items = db_queue_list(status=status)
        if items:
            return items
    except Exception:
        try:
            from web.db import db_queue_list  # noqa: E402

            items = db_queue_list(status=status)
            if items:
                return items
        except Exception:
            pass
    items = _load().get("items") or []
    if status:
        items = [x for x in items if x.get("status") == status]
    return sorted(items, key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)


def get_item(item_id: str) -> dict | None:
    try:
        from db import db_queue_get  # noqa: E402

        hit = db_queue_get(item_id)
        if hit:
            return hit
    except Exception:
        try:
            from web.db import db_queue_get  # noqa: E402

            hit = db_queue_get(item_id)
            if hit:
                return hit
        except Exception:
            pass
    for it in _load().get("items") or []:
        if it.get("id") == item_id:
            return it
    return None


def _update_item(item_id: str, **fields) -> dict | None:
    with _lock:
        data = _load()
        for it in data.get("items") or []:
            if it.get("id") == item_id:
                it.update(fields)
                it["updated_at"] = _now()
                _save(data)
                return dict(it)
        # JSON 里没有时，从 DB 取回再写回，避免库与文件脱节
        hit = None
        try:
            from db import db_queue_get  # noqa: E402

            hit = db_queue_get(item_id)
        except Exception:
            try:
                from web.db import db_queue_get  # noqa: E402

                hit = db_queue_get(item_id)
            except Exception:
                hit = None
        if not hit:
            return None
        hit.update(fields)
        hit["updated_at"] = _now()
        data.setdefault("items", []).insert(0, hit)
        _save(data)
        return dict(hit)


def enqueue(journal_ids: list[str], actor: str = "系统") -> dict:
    """将多条日志加入队列（status=queued），后台批量跑 AI。"""
    from journal_store import read_journal  # local import

    ensure_dirs()
    created = []
    blocking = {
        "queued",
        "ai_running",
        "pending_human",
        "pending_step1",
        "pending_step2",
        "in_review",
        "step1_passed",
    }
    with _lock:
        data = _load()
        existing_pending = {
            x.get("journal_id")
            for x in (data.get("items") or [])
            if x.get("status") in blocking
        }
        # Also check DB
        try:
            from db import db_queue_list  # noqa: E402

            for x in db_queue_list() or []:
                if x.get("status") in blocking:
                    existing_pending.add(x.get("journal_id"))
        except Exception:
            pass
        for jid in journal_ids:
            jid = (jid or "").strip()
            if not jid:
                continue
            if jid in existing_pending:
                continue
            try:
                meta = read_journal(jid).get("meta") or {}
            except Exception as e:
                created.append({"ok": False, "journal_id": jid, "error": str(e)})
                continue
            item_id = f"q_{uuid.uuid4().hex[:10]}"
            item = {
                "id": item_id,
                "journal_id": jid,
                "journal_title": meta.get("title") or jid,
                "product": meta.get("product"),
                "status": "queued",
                "actor": actor or "系统",
                "created_at": _now(),
                "updated_at": _now(),
                "error": None,
                "artifact_dir": f"queue_items/{item_id}",
                "story_chars": 0,
                "story_count": 0,
            }
            data.setdefault("items", []).append(item)
            created.append({"ok": True, **item})
        _save(data)
    _ensure_worker()
    return {"ok": True, "enqueued": created, "pending_human": len(list_queue("pending_human"))}


def inject_pending(
    *,
    journal_id: str,
    requirement_story: str,
    stories: dict,
    actor: str = "自测",
    journal_title: str | None = None,
) -> dict:
    """测试/演示：不调 LLM，直接写入待人审。"""
    ensure_dirs()
    item_id = f"q_{uuid.uuid4().hex[:10]}"
    art = ITEMS_DIR / item_id
    art.mkdir(parents=True, exist_ok=True)
    (art / "requirement-story.md").write_text(requirement_story, encoding="utf-8")
    (art / "stories.json").write_text(json.dumps(stories, ensure_ascii=False, indent=2), encoding="utf-8")
    item = {
        "id": item_id,
        "journal_id": journal_id,
        "journal_title": journal_title or journal_id,
        "product": None,
        "status": "pending_human",
        "actor": actor,
        "created_at": _now(),
        "updated_at": _now(),
        "error": None,
        "artifact_dir": f"queue_items/{item_id}",
        "story_chars": len(requirement_story),
        "story_count": len((stories or {}).get("stories") or []),
    }
    with _lock:
        data = _load()
        data.setdefault("items", []).append(item)
        _save(data)
    return {"ok": True, "item": item}


def mark_opened(item_id: str) -> dict | None:
    return _update_item(item_id, status="in_review")


def mark_done(item_id: str) -> dict | None:
    return _update_item(item_id, status="done")


def load_artifacts(item_id: str) -> dict:
    item = get_item(item_id)
    if not item:
        raise FileNotFoundError(f"队列项不存在: {item_id}")
    art = ITEMS_DIR / item_id
    story_path = art / "requirement-story.md"
    if not story_path.exists():
        story_path = art / "output" / "requirement-story.md"
    stories_path = art / "stories.json"
    if not stories_path.exists():
        stories_path = art / "output" / "stories.json"
    story = story_path.read_text(encoding="utf-8") if story_path.exists() else ""
    stories = {}
    if stories_path.exists():
        stories = json.loads(stories_path.read_text(encoding="utf-8"))
    return {"item": item, "requirement_story": story, "stories": stories}


def human_openable_statuses() -> set[str]:
    return {
        "pending_human",  # 兼容旧数据
        "pending_step1",
        "pending_step2",
        "step1_passed",  # Step1 人审过，等人自己点跑 Step2 / 解锁
        "in_review",
        "failed",
    }


def _process_one(item_id: str) -> None:
    """批量 AI：只跑 Step1 需求故事，等人审通过后再跑 Step2。"""
    from journal_store import read_journal
    from llm_config import make_client
    from loop_runner import ProductRequirementLoop

    item = get_item(item_id)
    if not item:
        return
    _update_item(item_id, status="ai_running", error=None, phase="step1")
    try:
        jid = item["journal_id"]
        data = read_journal(jid)
        journal = data["content"]
        work = ITEMS_DIR / item_id
        work.mkdir(parents=True, exist_ok=True)
        (work / "input").mkdir(exist_ok=True)
        (work / "output").mkdir(exist_ok=True)
        (work / "output" / "locked").mkdir(exist_ok=True)
        (work / "input" / "journal-raw.md").write_text(journal, encoding="utf-8")
        client = make_client()
        loop = ProductRequirementLoop(work, journal, client)
        story_path = loop.run_step1()
        story_text = story_path.read_text(encoding="utf-8")
        if "全局故事" not in story_text and len(story_text.strip()) < 40:
            raise RuntimeError("Step1 需求故事过短或结构不完整，请重试")
        (work / "requirement-story.md").write_text(story_text, encoding="utf-8")
        # 故意不写 stories.json，避免工作台跳过 Step1 人审
        _update_item(
            item_id,
            status="pending_step1",
            phase="step1",
            story_chars=len(story_text),
            story_count=0,
            error=None,
        )
        try:
            from audit_store import append_event, fingerprint

            append_event(
                actor=item.get("actor") or "系统",
                journal_id=jid,
                journal_title=item.get("journal_title"),
                journal_fingerprint=fingerprint(journal),
                step="批量AI·Step1",
                action="ai_ready",
                reason="已生成需求故事，等待人审 Step1（尚未跑 Step2）",
                artifact={"queue_id": item_id},
                phase_after="pending_step1",
            )
        except Exception:
            pass
    except Exception as e:
        _update_item(item_id, status="failed", error=str(e))
        traceback.print_exc()


def run_queue_step2(item_id: str) -> dict:
    """Step1 人审通过后，对队列项跑 Step2。"""
    from journal_store import read_journal
    from llm_config import make_client
    from loop_runner import ProductRequirementLoop, lock_step1

    item = get_item(item_id)
    if not item:
        return {"ok": False, "error": "队列项不存在"}
    allowed = {"pending_step1", "step1_passed", "in_review", "pending_step2_ai", "failed"}
    if item.get("status") not in allowed:
        return {"ok": False, "error": f"当前状态不可跑 Step2: {item.get('status')}"}
    _update_item(item_id, status="ai_running", phase="step2", error=None)
    try:
        jid = item["journal_id"]
        data = read_journal(jid)
        journal = data["content"]
        work = ITEMS_DIR / item_id
        if not (work / "requirement-story.md").exists() and not (work / "output" / "requirement-story.md").exists():
            return {"ok": False, "error": "缺少 Step1 需求故事，无法跑 Step2"}
        # 确保 output 有故事
        src = work / "requirement-story.md"
        if not src.exists():
            src = work / "output" / "requirement-story.md"
        (work / "output").mkdir(parents=True, exist_ok=True)
        (work / "output" / "requirement-story.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        (work / "input").mkdir(exist_ok=True)
        (work / "input" / "journal-raw.md").write_text(journal, encoding="utf-8")
        client = make_client()
        loop = ProductRequirementLoop(work, journal, client)
        lock_step1(work)
        loop.step1_locked = True
        stories_path = loop.run_step2()
        stories_payload = json.loads(stories_path.read_text(encoding="utf-8"))
        count = len(stories_payload.get("stories") or [])
        if count == 0:
            raise RuntimeError("Step2 未抽出有效故事")
        (work / "stories.json").write_text(
            json.dumps(stories_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _update_item(
            item_id,
            status="pending_step2",
            phase="step2",
            story_count=count,
            error=None,
        )
        return {"ok": True, "story_count": count, "status": "pending_step2"}
    except Exception as e:
        _update_item(item_id, status="failed", error=str(e))
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


def _worker_loop() -> None:
    while True:
        try:
            queued = [x for x in list_queue() if x.get("status") == "queued"]
            if not queued:
                import time

                time.sleep(1.5)
                continue
            _process_one(queued[0]["id"])
        except Exception:
            traceback.print_exc()
            import time

            time.sleep(2)


def _ensure_worker() -> None:
    global _worker_started
    with _lock:
        if _worker_started:
            return
        t = threading.Thread(target=_worker_loop, name="review-queue-worker", daemon=True)
        t.start()
        _worker_started = True


def clear_queue_for_tests() -> None:
    ensure_dirs()
    with _lock:
        _save({"version": 1, "items": []})
