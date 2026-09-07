#!/usr/bin/env python3
"""整改自检：Step3 check 门禁、待审库改名、速度字符范围、队列取消。

不依赖 LLM。静态检查始终跑；若本机 8765 服务已启动则再跑 API 用例。

Usage (repo root):
  project\\.venv\\Scripts\\python.exe scripts\\verify_rectify.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
CASE = PROJECT / "trials" / "case-01"
APP = CASE / "app.html"
LOOP = PROJECT / "web" / "loop_session.py"
QUEUE = PROJECT / "web" / "review_queue.py"
SERVER = ROOT / "scripts" / "stage0_server.py"
MANUAL = ROOT / "docs" / "交付" / "产品操作手册.md"
BASE = "http://127.0.0.1:8765"
COOKIE = ""

PASS = 0
FAIL = 0


def ok(name: str, detail: str = "") -> None:
    global PASS
    PASS += 1
    print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))


def bad(name: str, detail: str) -> None:
    global FAIL
    FAIL += 1
    print(f"[FAIL] {name} — {detail}")


def http_json(path: str, method: str = "GET", body: dict | None = None) -> dict:
    global COOKIE
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data else {}
    if COOKIE:
        headers["Cookie"] = COOKIE
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            sc = resp.headers.get("Set-Cookie") or ""
            if "qt_session=" in sc:
                COOKIE = sc.split(";", 1)[0]
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        sc = e.headers.get("Set-Cookie") or ""
        if "qt_session=" in sc:
            COOKIE = sc.split(";", 1)[0]
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"ok": False, "error": raw or str(e)}
        payload.setdefault("http_status", e.code)
        return payload
    except Exception as e:
        return {"ok": False, "error": str(e), "unreachable": True}


def check_static() -> None:
    print("== static ==")
    app = APP.read_text(encoding="utf-8")
    loop = LOOP.read_text(encoding="utf-8")
    queue = QUEUE.read_text(encoding="utf-8")
    srv = SERVER.read_text(encoding="utf-8")
    manual = MANUAL.read_text(encoding="utf-8") if MANUAL.exists() else ""

    if "待审库" in app:
        ok("UI 待审库改名")
    else:
        bad("UI 待审库改名", "app.html 未见「待审库」")

    if "待人审" in app:
        bad("UI 已无待人审", "app.html 仍含「待人审」")
    else:
        ok("UI 已无待人审")

    if "output-len" in app and "updateOutputLen" in app:
        ok("右侧字数显示")
    else:
        bad("右侧字数显示", "缺少 output-len / updateOutputLen")

    if "1200–3499" in app or "1200-3499" in app:
        ok("速度规则标注字符范围")
    else:
        bad("速度规则标注字符范围", "未见 1200–3499")

    if "closeJournalModal()" in app and "async function selectJournal" in app:
        ok("选日志后关窗", "selectJournal 含 closeJournalModal")
    else:
        bad("选日志后关窗", "selectJournal 未关窗")

    if "lastStoriesCheckPassed" in app and "① 运行 check" in app:
        ok("前端 Step3 check 门禁")
    else:
        bad("前端 Step3 check 门禁", "缺 lastStoriesCheckPassed / 按钮文案")

    if "不能定稿入库" in loop and 'run_check(target="stories"' in loop:
        ok("后端 finalize 强制 stories check")
    else:
        bad("后端 finalize 强制 stories check", "loop_session.finalize 未见门禁")

    if "manual-sidebar" in app and "m-flow" in app:
        ok("手册侧栏目录 + 数据流")
    else:
        bad("手册侧栏目录 + 数据流", "缺 manual-sidebar / m-flow")

    if "数据流" in manual and "check" in manual and "待审库" in manual:
        ok("交付手册同步整改")
    else:
        bad("交付手册同步整改", str(MANUAL))

    if "def cancel_item" in queue and "can_cancel_item" in queue:
        ok("队列 cancel_item 函数")
    else:
        bad("队列 cancel_item 函数", "review_queue 缺 cancel")

    if "btn-cancel-q" in app and "/api/queue/cancel" in app:
        ok("前端取消任务按钮")
    else:
        bad("前端取消任务按钮", "缺 btn-cancel-q 或 API 调用")

    if "/api/queue/cancel" in srv and "cancel_item" in srv:
        ok("服务路由 /api/queue/cancel")
    else:
        bad("服务路由 /api/queue/cancel", "stage0_server 未挂载")


def login_demo() -> bool:
    global COOKIE
    COOKIE = ""
    r = http_json("/api/auth/login", "POST", {"username": "demo", "password": "demo1234"})
    if r.get("ok") and COOKIE:
        ok("login demo")
        return True
    http_json(
        "/api/auth/register",
        "POST",
        {"username": "demo", "password": "demo1234", "display_name": "演示账号"},
    )
    r = http_json("/api/auth/login", "POST", {"username": "demo", "password": "demo1234"})
    if r.get("ok") and COOKIE:
        ok("login demo", "ensured")
        return True
    bad("login demo", str(r)[:200])
    return False


def _quote_from_journal(text: str, min_len: int = 8) -> str:
    for line in text.splitlines():
        s = line.strip()
        if len(s) >= min_len and not s.startswith("#") and not s.startswith("```"):
            return s[:80]
    compact = re.sub(r"\s+", "", text)
    return compact[: max(min_len, min(40, len(compact)))] or "日志"


def _write_step3_ready(stories: dict) -> None:
    out = CASE / "output"
    locked = out / "locked"
    out.mkdir(exist_ok=True)
    locked.mkdir(exist_ok=True)
    story_md = "# 需求故事\n\n## 全局故事（一件事）\n整改自检故事\n"
    (out / "requirement-story.md").write_text(story_md, encoding="utf-8")
    (locked / "step1-requirement-story.md").write_text(story_md, encoding="utf-8")
    blob = json.dumps(stories, ensure_ascii=False, indent=2)
    (out / "stories.json").write_text(blob, encoding="utf-8")
    (locked / "step2-approved.json").write_text(blob, encoding="utf-8")
    # 清掉已定稿，避免 phase=done
    (out / "accepted.json").unlink(missing_ok=True)


def check_api() -> None:
    print("== api (server) ==")
    sys.path.insert(0, str(PROJECT))
    sys.path.insert(0, str(PROJECT / "web"))

    ping = http_json("/api/ping")
    if ping.get("unreachable"):
        print("[SKIP] server not running — 仅静态检查已完成；启动服务后可复跑本脚本")
        return
    ok("server reachable")

    if not login_demo():
        return

    from journal_store import read_journal  # noqa: E402
    from review_queue import cancel_item, enqueue, get_item, list_queue  # noqa: E402

    jlist = http_json("/api/journals").get("journals") or []
    q_all = http_json("/api/queue")
    active_jids = {
        x.get("journal_id")
        for x in (q_all.get("items") or [])
        if x.get("status") not in {"done", "cancelled"}
    }
    target = next(
        (j for j in jlist if j.get("usage") == "try" and j.get("id") not in active_jids),
        None,
    ) or next((j for j in jlist if j.get("id") not in active_jids), None) or (
        next((j for j in jlist if j.get("usage") == "try"), None) or (jlist[0] if jlist else None)
    )
    if not target:
        bad("need journal", "empty")
        return
    jid = target["id"]
    me = http_json("/api/auth/me").get("user") or {
        "id": 1,
        "display_name": "演示账号",
        "username": "demo",
    }

    # --- cancel + re-enqueue（优先走 HTTP，与运行中服务同一状态）---
    for it in q_all.get("items") or []:
        if it.get("journal_id") == jid and it.get("status") not in {"done", "cancelled"}:
            http_json("/api/queue/cancel", "POST", {"id": it["id"], "reason": "自检清理"})

    enq = http_json(
        "/api/queue/batch",
        "POST",
        {"journal_ids": [jid], "actor": "自检"},
    )
    created = [x for x in (enq.get("enqueued") or []) if x.get("ok")]
    qid = created[0]["id"] if created else None
    if not qid:
        # 回退：直接库层入队（同进程文件）
        enq_local = enqueue([jid], actor="自检", actor_user_id=me.get("id"))
        created = [x for x in (enq_local.get("enqueued") or []) if x.get("ok")]
        qid = created[0]["id"] if created else None
    if not qid:
        hit = next(
            (
                x
                for x in (http_json("/api/queue").get("items") or [])
                if x.get("journal_id") == jid
                and x.get("status") in {"queued", "ai_running", "pending_step1", "failed"}
            ),
            None,
        )
        qid = (hit or {}).get("id")
    if qid:
        ok("enqueue for cancel test", qid)
    else:
        bad("enqueue for cancel test", str(enq)[:240])
        return

    cancelled = http_json("/api/queue/cancel", "POST", {"id": qid, "reason": "自检测试取消"})
    st = (cancelled.get("item") or {}).get("status")
    if cancelled.get("ok") and st == "cancelled":
        ok("API cancel queue item", qid)
    else:
        active = next(
            (
                x
                for x in (http_json("/api/queue").get("items") or [])
                if x.get("journal_id") == jid and x.get("status") not in {"done", "cancelled"}
            ),
            None,
        )
        if active:
            cancelled = http_json(
                "/api/queue/cancel", "POST", {"id": active["id"], "reason": "自检测试取消"}
            )
        if cancelled.get("ok") and (cancelled.get("item") or {}).get("status") == "cancelled":
            ok("API cancel queue item", (cancelled.get("item") or {}).get("id"))
        else:
            bad("API cancel queue item", str(cancelled)[:240])

    enq2 = http_json(
        "/api/queue/batch",
        "POST",
        {"journal_ids": [jid], "actor": "自检"},
    )
    created2 = [x for x in (enq2.get("enqueued") or []) if x.get("ok")]
    if created2:
        ok("re-enqueue after cancel", created2[0].get("id"))
        http_json(
            "/api/queue/cancel",
            "POST",
            {"id": created2[0]["id"], "reason": "自检收尾"},
        )
    else:
        # 库层再试一次
        enq2b = enqueue([jid], actor="自检", actor_user_id=me.get("id"))
        created2b = [x for x in (enq2b.get("enqueued") or []) if x.get("ok")]
        if created2b:
            ok("re-enqueue after cancel", created2b[0].get("id"))
            cancel_item(created2b[0]["id"], user=me, reason="自检收尾")
        else:
            bad("re-enqueue after cancel", str(enq2)[:240])

    # --- finalize gate via shared output files ---
    http_json("/api/loop/reset", "POST", {"keep_locked": False})
    sel = http_json("/api/journal/select", "POST", {"id": jid, "force_reopen": True})
    if sel.get("ok"):
        ok("select journal for gate", jid)
    else:
        bad("select journal for gate", str(sel)[:200])
        return

    source = read_journal(jid).get("content") or ""

    _write_step3_ready(
        {
            "stories": [
                {
                    "id": "s-bad",
                    "level": "task",
                    "text": "用户要一个原文绝对没有的魔法能力XYZ999",
                    "source_quote": "原文绝对没有的魔法能力XYZ999",
                    "reason": "gate",
                    "approved": False,
                    "revisions": [{"round": 1, "action": "created"}],
                }
            ],
            "coverage": {"coverage_rate": 1.0, "uncovered": []},
            "meta": {},
        }
    )
    st = http_json("/api/state")
    if st.get("phase") == "step3_ready":
        ok("phase step3_ready for bad stories")
    else:
        bad("phase step3_ready for bad stories", str(st.get("phase")))

    fin_bad = http_json(
        "/api/loop/finalize",
        "POST",
        {"approver": "自检员", "note": "应被 check 拒绝"},
    )
    err = fin_bad.get("error") or ""
    if not fin_bad.get("ok") and ("check" in err or "定稿" in err or "编造" in err or "source_quote" in err):
        ok("finalize blocked when check fails", err[:90])
    else:
        bad("finalize blocked when check fails", str(fin_bad)[:300])

    quote = _quote_from_journal(source)
    _write_step3_ready(
        {
            "stories": [
                {
                    "id": "s-ok",
                    "level": "task",
                    "text": "用户要梳理该日志中的需求",
                    "source_quote": quote,
                    "reason": "出自原文",
                    "approved": True,
                    "revisions": [{"round": 1, "action": "created"}],
                }
            ],
            "coverage": {"coverage_rate": 1.0, "uncovered": []},
            "meta": {},
        }
    )
    chk = http_json("/api/check", "POST", {"target": "stories", "actor": "自检员"})
    if chk.get("passed"):
        ok("check passes on grounded stories")
    else:
        bad("check passes on grounded stories", str(chk.get("errors") or chk)[:220])

    fin_ok = http_json(
        "/api/loop/finalize",
        "POST",
        {"approver": "自检员", "note": "门禁通过后定稿"},
    )
    if fin_ok.get("ok"):
        ok("finalize allowed after grounded stories")
    else:
        bad("finalize allowed after grounded stories", str(fin_ok)[:300])

    # 队列列表带 can_cancel 字段
    q = http_json("/api/queue")
    sample = (q.get("items") or [{}])[0] if q.get("items") else {}
    if q.get("ok") and ("can_cancel" in sample or not q.get("items")):
        ok("queue items expose can_cancel")
    else:
        bad("queue items expose can_cancel", str(sample)[:160])


def check_unit_cancel_offline() -> None:
    """无服务时也能测 cancel 状态机（写临时队列文件风险高，跳过若服务在跑）。"""
    print("== unit cancel (import) ==")
    sys.path.insert(0, str(PROJECT))
    sys.path.insert(0, str(PROJECT / "web"))
    try:
        from review_queue import can_cancel_item, cancelable_statuses  # noqa: E402

        assert "queued" in cancelable_statuses()
        assert can_cancel_item(
            {"status": "queued"}, {"id": 1, "display_name": "A"}
        )
        assert not can_cancel_item({"status": "done"}, {"id": 1, "display_name": "A"})
        assert not can_cancel_item(
            {
                "status": "in_review",
                "assignee_user_id": 2,
                "assignee_name": "B",
            },
            {"id": 1, "display_name": "A"},
        )
        ok("can_cancel_item rules")
    except Exception as e:
        bad("can_cancel_item rules", str(e))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    print("== verify_rectify ==")
    check_static()
    check_unit_cancel_offline()
    check_api()
    print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
