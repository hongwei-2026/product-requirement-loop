#!/usr/bin/env python3
"""企业级自测：审核理由、可读回溯、入库台账、待人审队列（默认不调 LLM）。

Usage (repo root, server running):
  project\\.venv\\Scripts\\python.exe scripts\\verify_enterprise.py
"""

from __future__ import annotations

import json
import shutil
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
CASE = PROJECT / "trials" / "case-01"
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
            return json.loads(raw)
        except Exception:
            return {"ok": False, "error": raw or str(e), "http_status": e.code}


def login_demo() -> bool:
    r = http_json("/api/auth/login", "POST", {"username": "demo", "password": "demo1234"})
    if r.get("ok") and COOKIE:
        ok("login demo", r.get("user", {}).get("display_name"))
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


def main() -> int:
    print("== enterprise audit/registry/queue ==")
    sys.path.insert(0, str(PROJECT))
    sys.path.insert(0, str(PROJECT / "web"))

    # --- unit: parse_feedback ok reason ---
    try:
        from loop_runner import parse_feedback

        fb = parse_feedback("ok")
        if fb["kind"] == "ok" and not fb.get("reason"):
            ok("parse ok bare → empty reason")
        else:
            bad("parse ok bare", str(fb))
        fb = parse_feedback("ok:与原文一致，一件事清楚")
        if fb["kind"] == "ok" and "原文" in (fb.get("reason") or ""):
            ok("parse ok:reason")
        else:
            bad("parse ok:reason", str(fb))
        fb = parse_feedback("revise:编造:多写了支付能力")
        if fb["kind"] == "revise" and fb.get("code") == "编造":
            ok("parse revise")
        else:
            bad("parse revise", str(fb))
    except Exception as e:
        bad("parse_feedback unit", f"{e}\n{traceback.format_exc()}")

    # --- unit: audit_store ---
    try:
        from audit_store import (
            append_event,
            approval_status,
            clear_events_for_tests,
            clear_registry_for_tests,
            fingerprint,
            list_events,
            list_approved,
            register_approved,
        )

        clear_events_for_tests()
        clear_registry_for_tests()
        ev = append_event(
            actor="自测员",
            journal_id="demo-j1",
            journal_title="演示日志",
            journal_fingerprint=fingerprint("hello"),
            step="整理需求故事",
            action="ok",
            reason="与原文一致",
            phase_after="step2_ready",
        )
        if "通过" in (ev.get("summary") or "") and "与原文一致" in (ev.get("summary") or ""):
            ok("audit summary readable", ev["summary"][:60])
        else:
            bad("audit summary readable", str(ev))
        events = list_events(journal_id="demo-j1")
        if events and events[0]["id"] == ev["id"]:
            ok("audit list by journal")
        else:
            bad("audit list", str(events)[:200])

        rec = register_approved(
            journal_id="demo-j1",
            journal_title="演示日志",
            journal_fingerprint=fingerprint("hello"),
            approver="自测员",
            accepted_relpath="data/accepted/demo.json",
            story_count=2,
            audit_event_id=ev["id"],
        )
        st = approval_status("demo-j1", "hello")
        if st["status"] == "approved" and list_approved("演示"):
            ok("registry approved + search")
        else:
            bad("registry", str(st))
        st2 = approval_status("demo-j1", "hello-changed")
        if st2["status"] == "stale":
            ok("registry stale when content changes")
        else:
            bad("registry stale", str(st2))
    except Exception as e:
        bad("audit_store unit", f"{e}\n{traceback.format_exc()}")

    # --- live HTTP ---
    try:
        ping = http_json("/api/ping")
        if not ping.get("ok"):
            bad("server ping", str(ping))
            print("Start start-with-ai.bat first")
            print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
            return 1
        ok("server ping")
    except Exception as e:
        bad("server ping", str(e))
        print("Start start-with-ai.bat first")
        print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
        return 1

    # unauth should be blocked
    global COOKIE
    old = COOKIE
    COOKIE = ""
    blocked = http_json("/api/journals")
    if blocked.get("need_login") or blocked.get("http_status") == 401 or "登录" in (blocked.get("error") or ""):
        ok("API requires login")
    else:
        bad("API requires login", str(blocked)[:160])
    COOKIE = old

    if not login_demo():
        print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
        return 1

    me = http_json("/api/auth/me")
    if me.get("ok") and me.get("user"):
        ok("auth me", me["user"].get("username"))
    else:
        bad("auth me", str(me)[:160])

    stats = http_json("/api/db/stats")
    if stats.get("ok") and "users" in stats:
        ok("db stats", f"users={stats.get('users')} approved={stats.get('approved')}")
    else:
        bad("db stats", str(stats)[:160])

    # register unique user
    uname = "tester_" + str(int(__import__("time").time()))[-6:]
    reg = http_json(
        "/api/auth/register",
        "POST",
        {"username": uname, "password": "test1234", "display_name": "自测员乙"},
    )
    if reg.get("ok"):
        ok("register new user", uname)
    else:
        bad("register", str(reg)[:160])

    # journals API has review_status
    try:
        journals = http_json("/api/journals")
        sample = (journals.get("journals") or [None])[0]
        if sample and "review_status" in sample:
            ok("journals carry review_status", sample.get("review_label"))
        else:
            bad("journals review_status", str(sample)[:120] if sample else "empty")
    except Exception as e:
        bad("journals", str(e))

    # pick try journal
    jlist = http_json("/api/journals").get("journals") or []
    target = next((j for j in jlist if j.get("usage") == "try"), None) or (jlist[0] if jlist else None)
    if not target:
        bad("need journal", "empty library")
        print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
        return 1 if FAIL else 0

    # reset + select
    http_json("/api/loop/reset", "POST", {"keep_locked": False})
    sel = http_json("/api/journal/select", "POST", {"id": target["id"], "force_reopen": True})
    if sel.get("ok"):
        ok("select journal", target["id"])
    else:
        bad("select journal", str(sel)[:200])

    # prepare fake artifacts without LLM
    out = CASE / "output"
    locked = out / "locked"
    out.mkdir(exist_ok=True)
    locked.mkdir(exist_ok=True)
    (out / "requirement-story.md").write_text(
        "# 需求故事\n\n## 全局故事（一件事）\n企业自测用故事\n", encoding="utf-8"
    )
    shutil.copy2(out / "requirement-story.md", locked / "step1-requirement-story.md")
    # replace lock file only after ok path — for step1_review leave unlocked
    (locked / "step1-requirement-story.md").unlink(missing_ok=True)

    # reject bare ok
    r = http_json(
        "/api/loop/feedback",
        "POST",
        {"step": "整理需求故事", "raw": "ok", "actor": "自测员"},
    )
    if not r.get("ok") and "理由" in (r.get("error") or ""):
        ok("reject ok without reason", r.get("error", "")[:80])
    else:
        bad("reject ok without reason", str(r)[:200])

    # accept ok with reason
    r = http_json(
        "/api/loop/feedback",
        "POST",
        {"step": "整理需求故事", "raw": "ok:故事与原文一致，可进入提取", "actor": "自测员"},
    )
    if r.get("ok") and r.get("phase") == "step2_ready":
        ok("ok with reason → step2_ready")
    else:
        bad("ok with reason", str(r)[:240])

    # audit API readable
    audit = http_json(f"/api/audit?journal_id={target['id']}&limit=20")
    evs = audit.get("events") or []
    if evs and any("通过" in (e.get("summary") or "") for e in evs):
        ok("GET /api/audit readable", evs[0].get("summary", "")[:70])
    else:
        bad("GET /api/audit", str(audit)[:240])

    # step2 fake + ok
    (out / "stories.json").write_text(
        json.dumps(
            {
                "stories": [
                    {
                        "id": "s1",
                        "level": "task",
                        "text": "用户要测试",
                        "source_quote": "测试",
                        "reason": "t",
                        "approved": False,
                        "revisions": [{"round": 1, "action": "created"}],
                    }
                ],
                "coverage": {"coverage_rate": 1.0, "uncovered": []},
                "meta": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # unlock step1 lock was created by ok; stories exist → need step2_review
    # After step1 ok we have lock; writing stories → phase step2_review if no step2 marker
    r = http_json(
        "/api/loop/feedback",
        "POST",
        {"step": "提取用户故事 JSON", "raw": "ok:条目均可追溯原文", "actor": "自测员"},
    )
    if r.get("ok") and r.get("phase") == "step3_ready":
        ok("step2 ok with reason → step3_ready")
    else:
        bad("step2 ok", str(r)[:240])

    # finalize → registry
    fin = http_json(
        "/api/loop/finalize",
        "POST",
        {"approver": "自测员", "note": "企业自测定稿入库"},
    )
    if fin.get("ok") and fin.get("registry"):
        ok("finalize registers approved", fin["registry"].get("journal_id"))
    else:
        bad("finalize registry", str(fin)[:300])

    reg = http_json(f"/api/registry?q={target['id']}")
    if any(x.get("journal_id") == target["id"] for x in (reg.get("items") or [])):
        ok("GET /api/registry searchable")
    else:
        bad("registry search", str(reg)[:200])

    # queue inject + open
    inj = http_json(
        "/api/queue/inject",
        "POST",
        {
            "journal_id": target["id"],
            "journal_title": target.get("title"),
            "actor": "自测",
            "requirement_story": "# 需求故事\n\n## 全局故事（一件事）\n队列自测\n",
            "stories": {
                "stories": [
                    {
                        "id": "s1",
                        "level": "task",
                        "text": "用户要队列自测",
                        "source_quote": "队列",
                        "reason": "t",
                        "approved": False,
                        "revisions": [],
                    }
                ]
            },
        },
    )
    qid = (inj.get("item") or {}).get("id")
    if inj.get("ok") and qid:
        ok("queue inject pending_human", qid)
    else:
        bad("queue inject", str(inj)[:200])
        qid = None

    q = http_json("/api/queue?status=pending_human")
    if qid and any(x.get("id") == qid for x in (q.get("items") or [])):
        ok("GET /api/queue lists pending")
    else:
        bad("queue list", str(q)[:200])

    if qid:
        opened = http_json("/api/queue/open", "POST", {"id": qid})
        if opened.get("ok") and opened.get("phase") == "step1_review":
            ok("queue open → workbench step1_review")
        else:
            bad("queue open", str(opened)[:240])

    # UI markers
    try:
        req = urllib.request.Request(BASE + "/", headers={"Cookie": COOKIE} if COOKIE else {})
        home = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="replace")
        need = ["待人审", "定稿档案", "审核历史", "audit-timeline", "批量 AI", "使用手册", "view-manual", "btn-logout"]
        missing = [x for x in need if x not in home]
        if not missing:
            ok("UI has queue/registry/audit/manual/logout")
        else:
            bad("UI markers", "missing " + ",".join(missing))
        login_page = urllib.request.urlopen(BASE + "/login.html", timeout=10).read().decode("utf-8", errors="replace")
        if "注册" in login_page and "demo1234" in login_page:
            ok("login page exists")
        else:
            bad("login page", "missing markers")
    except Exception as e:
        bad("UI", str(e))

    # cleanup workbench outputs so user not stuck in done
    http_json("/api/loop/reset", "POST", {"keep_locked": False})
    ok("cleanup reset")

    print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
