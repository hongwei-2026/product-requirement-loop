#!/usr/bin/env python3
"""交付级自检（企业冒烟）：不调 LLM，验证 API / 阶段机 / 日志库。

Usage (repo root):
  project\\.venv\\Scripts\\python.exe scripts\\verify_delivery.py
"""

from __future__ import annotations

import json
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
JOURNALS = PROJECT / "journals"
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
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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
        ok("auth login demo", r.get("user", {}).get("username"))
        return True
    # try register then login
    http_json(
        "/api/auth/register",
        "POST",
        {"username": "demo", "password": "demo1234", "display_name": "演示账号"},
    )
    r = http_json("/api/auth/login", "POST", {"username": "demo", "password": "demo1234"})
    if r.get("ok") and COOKIE:
        ok("auth login after ensure demo", r.get("user", {}).get("username"))
        return True
    bad("auth login demo", str(r)[:200])
    return False


def main() -> int:
    print("== delivery smoke ==")
    print(f"ROOT={ROOT}")

    # --- filesystem ---
    if (PROJECT / "web" / "loop_session.py").exists():
        ok("loop_session.py exists")
    else:
        bad("loop_session.py exists", "missing")

    if (CASE / "app.html").exists():
        ok("app.html exists")
    else:
        bad("app.html exists", "missing")

    catalog = JOURNALS / "catalog.json"
    if catalog.exists():
        cat = json.loads(catalog.read_text(encoding="utf-8"))
        n = len(cat.get("journals") or [])
        if n >= 20:
            ok("journals catalog size", f"{n} entries")
        else:
            bad("journals catalog size", f"only {n}, run scripts/sync_journals.py")
    else:
        bad("journals catalog", "missing catalog.json")

    handbook = ROOT / "docs" / "交付" / "产品操作手册.md"
    if handbook.exists():
        ok("delivery handbook exists")
    else:
        bad("delivery handbook", "missing docs/交付/产品操作手册.md")

    # --- llm_config must not sys.exit on import path for raise ---
    sys.path.insert(0, str(PROJECT))
    from llm_config import make_client  # noqa: E402

    # ensure make_client raises instead of exiting when key missing
    import os

    old = os.environ.pop("AGNES_API_KEY", None)
    try:
        try:
            make_client()
            # if key exists in .env via load_dotenv, that's fine
            ok("make_client", "key present via .env (ok for delivery)")
        except RuntimeError as e:
            if "缺少" in str(e) or "AGNES" in str(e):
                ok("make_client raises RuntimeError", str(e)[:80])
            else:
                bad("make_client raises", str(e))
        except SystemExit as e:
            bad("make_client must not sys.exit", str(e))
    finally:
        if old is not None:
            os.environ["AGNES_API_KEY"] = old

    # --- live HTTP (server must be running) ---
    try:
        ping = http_json("/api/ping")
        if ping.get("ok"):
            ok("GET /api/ping", f"ai_configured={ping.get('ai_configured')}")
        else:
            bad("GET /api/ping", str(ping))
    except Exception as e:
        bad("GET /api/ping", f"server down? {e}")
        print("\nStart server first: start-with-ai.bat")
        print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
        return 1 if FAIL else 0

    if not login_demo():
        print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
        return 1

    try:
        journals = http_json("/api/journals")
        total = (journals.get("stats") or {}).get("total") or len(journals.get("journals") or [])
        if total >= 20:
            ok("GET /api/journals", f"total={total} products={len(journals.get('products') or [])}")
        else:
            bad("GET /api/journals", f"total={total}")
    except Exception as e:
        bad("GET /api/journals", str(e))

    try:
        st = http_json("/api/state")
        if st.get("ok") and st.get("phase") in {
            "idle",
            "step1_review",
            "step2_ready",
            "step2_review",
            "step3_ready",
            "done",
        }:
            ok("GET /api/state", f"phase={st.get('phase')}")
        else:
            bad("GET /api/state", str(st)[:200])
    except Exception as e:
        bad("GET /api/state", str(e))

    # phase machine unit (no LLM): select excerpt + infer after fake markers
    try:
        from web.loop_session import LoopWebSession  # noqa: E402

        # pick a short journal if available
        jlist = http_json("/api/journals").get("journals") or []
        target = next((j for j in jlist if j.get("usage") == "try"), None) or (jlist[0] if jlist else None)
        if not target:
            bad("select journal", "no journals")
        else:
            session = LoopWebSession(CASE)
            # reset first
            r = session.reset(keep_locked=False)
            if not r.get("ok"):
                bad("reset", str(r))
            else:
                ok("reset", r.get("phase"))
            r = session.select_journal(target["id"], reset_outputs=True)
            if r.get("ok") and session._infer_phase() == "idle":
                ok("select_journal → idle", target["id"])
            else:
                bad("select_journal", str(r)[:200])

            # simulate step2 approved marker persistence
            (CASE / "output").mkdir(exist_ok=True)
            (CASE / "output" / "locked").mkdir(exist_ok=True)
            # create minimal story files without LLM
            (CASE / "output" / "requirement-story.md").write_text("# 需求故事\n\n## 全局故事（一件事）\nx\n", encoding="utf-8")
            lock_step1 = CASE / "output" / "locked" / "step1-requirement-story.md"
            lock_step1.write_text((CASE / "output" / "requirement-story.md").read_text(encoding="utf-8"), encoding="utf-8")
            (CASE / "output" / "stories.json").write_text(
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
                                "revisions": [],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            session2 = LoopWebSession(CASE)
            if session2._infer_phase() == "step2_review":
                ok("infer phase step2_review")
            else:
                bad("infer phase step2_review", session2._infer_phase())

            (CASE / "output" / "locked" / "step2-approved.json").write_text(
                '{"approved": true}', encoding="utf-8"
            )
            session3 = LoopWebSession(CASE)
            if session3._infer_phase() == "step3_ready":
                ok("infer phase step3_ready (marker)")
            else:
                bad("infer phase step3_ready", session3._infer_phase())

            # cleanup markers from unit test so UI not stuck oddly
            session3.reset(keep_locked=False)
            ok("cleanup after phase unit test")
    except Exception as e:
        bad("phase machine unit", f"{e}\n{traceback.format_exc()}")

    # home page
    try:
        req = urllib.request.Request(BASE + "/", headers={"Cookie": COOKIE} if COOKIE else {})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            need = ["日志库", "工作台", "使用手册", "view-manual", "assets/manual/manual-01-workbench.png", "btn-logout"]
            missing = [x for x in need if x not in body]
            if not missing:
                ok("GET / contains 工作台+日志库+使用手册+退出")
            else:
                bad("GET / UI markers", "missing: " + ",".join(missing))
    except Exception as e:
        bad("GET /", str(e))

    print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
