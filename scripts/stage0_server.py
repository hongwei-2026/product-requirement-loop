#!/usr/bin/env python3
"""product-requirement 本地 Web 服务：产品 UI + Loop API + 验收页。

Usage (from repo root):
  copy project\\.env.example to project\\.env and set AGNES_API_KEY
  python scripts/stage0_server.py

Then open: http://127.0.0.1:8765/
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import traceback
import urllib.error
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
CASE = PROJECT / "trials" / "case-01"
SPEC = PROJECT / "product-requirement" / "specification.yaml"
PROMPT_STEP2 = PROJECT / "product-requirement" / "prompts" / "step2-json.md"
PROMPT_STEP2_CASE = CASE / "prompts" / "step2-json.md"
ENV = PROJECT / ".env"
DEFENSE = ROOT / "docs" / "答辩总报告"
PORT = 8765

if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
if str(PROJECT / "web") not in sys.path:
    sys.path.insert(0, str(PROJECT / "web"))

from loop_session import get_session  # noqa: E402
from loop_runner import STEP1, STEP2  # noqa: E402
from journal_store import list_journals, read_journal, save_pasted, save_upload, PRODUCT_LABELS  # noqa: E402
from audit_store import list_events, list_approved, list_audit_journals, get_registry_detail  # noqa: E402
from journal_inbox import (  # noqa: E402
    approve_inbox_items,
    auto_fetch_if_due,
    compare_inbox_item,
    fetch_from_official,
    get_inbox_item,
    list_inbox,
    reject_inbox_items,
    start_auto_fetch_worker,
)
from review_queue import enqueue, list_queue, inject_pending  # noqa: E402
from db import (  # noqa: E402
    create_session,
    create_user,
    db_stats,
    delete_session,
    ensure_db,
    get_user_by_token,
    migrate_json_registry_once,
    verify_login,
)
from security_guard import (  # noqa: E402
    allow_auth_attempt,
    client_key,
    registration_allowed,
    resolve_bind_host,
    security_headers,
)

COOKIE_NAME = "qt_session"
PUBLIC_API = {
    "/api/ping",
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/me",
}

# 验收页尚无 Step1 产物时，用同一套 Step2 约束做预览
PREVIEW_STORY_STUB = (
    "（验收页预览模式：尚无 Step1「需求故事」产物。"
    "请仅根据下方「原始日志」提取用户故事；约束与正式 Step2 完全相同："
    "禁止编造、text 以「用户要」开头、level 为 activity|task|story、"
    "source_quote 必须能在原始日志中找到。最多 10 条。）"
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def parse_stories_from_content(content: str) -> list[dict]:
    text = strip_markdown_fence(content)

    # 优先：完整 Step2 对象 {"stories": [...]}
    obj_start = text.find("{")
    if obj_start >= 0:
        try:
            dec = json.JSONDecoder()
            obj, _ = dec.raw_decode(text, obj_start)
            if isinstance(obj, dict) and isinstance(obj.get("stories"), list):
                return obj["stories"]
            if isinstance(obj, list):
                return obj
        except json.JSONDecodeError:
            pass

    start = text.find("[")
    if start < 0:
        raise RuntimeError(f"AI 未返回 JSON（对象或数组）: {text[:200]}")

    fragment = text[start : text.rfind("]") + 1] if "]" in text[start:] else text[start:]
    try:
        stories = json.loads(fragment)
    except json.JSONDecodeError:
        dec = json.JSONDecoder()
        idx = start + 1
        stories = []
        while idx < len(text):
            while idx < len(text) and text[idx] in " \n\r\t,":
                idx += 1
            if idx >= len(text) or text[idx] == "]":
                break
            try:
                obj, end = dec.raw_decode(text, idx)
            except json.JSONDecodeError:
                break
            if isinstance(obj, dict):
                stories.append(obj)
            idx = end
        if not stories:
            raise RuntimeError("AI 返回的 JSON 被截断或格式错误，请再点一次试抓")
    if not isinstance(stories, list):
        raise RuntimeError("AI 返回格式错误（不是 stories 数组）")
    return stories


def resolve_step2_prompt_path() -> Path:
    if PROMPT_STEP2.exists():
        return PROMPT_STEP2
    if PROMPT_STEP2_CASE.exists():
        return PROMPT_STEP2_CASE
    raise RuntimeError(
        "找不到 step2-json.md。"
        "请确认 project/product-requirement/prompts/step2-json.md 存在"
    )


def build_step2_prompt(journal: str, requirement_story: str | None = None) -> str:
    """读取 step2-json.md，替换占位符（与正式 Loop / 试点副本同一套规则）。"""
    path = resolve_step2_prompt_path()
    template = path.read_text(encoding="utf-8")
    story = (requirement_story or "").strip() or PREVIEW_STORY_STUB
    return (
        template.replace("{{REQUIREMENT_STORY}}", story)
        .replace("{{JOURNAL_RAW}}", journal[:120000])
    )


def call_agnes(journal: str, requirement_story: str | None = None) -> list[dict]:
    key = os.environ.get("AGNES_API_KEY", "").strip()
    if not key:
        raise RuntimeError("未配置 AGNES_API_KEY。请复制 project/.env.example 为 project/.env 并填入 Key")

    base = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1").rstrip("/")
    model = os.environ.get("AGNES_MODEL", "agnes-2.5-flash")
    prompt = build_step2_prompt(journal, requirement_story)
    prompt_src = resolve_step2_prompt_path().relative_to(ROOT)

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "只输出合法 JSON（优先输出含 stories 数组的对象，"
                        "也可直接输出 stories 数组）。确保可被 json.loads 解析。"
                        f"提示词来源：{prompt_src.as_posix()}"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    content = ""
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"] or ""
            if content.strip():
                break
            last_err = RuntimeError("Agnes API 返回空内容")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Agnes API HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"无法连接 Agnes API: {e.reason}") from e
    else:
        raise last_err or RuntimeError("Agnes API 无响应，请稍后重试")

    return parse_stories_from_content(content)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(CASE), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status: int, payload: dict, set_cookie: str | None = None, clear_cookie: bool = False) -> None:
        out = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        for hk, hv in security_headers():
            self.send_header(hk, hv)
        if set_cookie:
            self.send_header(
                "Set-Cookie",
                f"{COOKIE_NAME}={set_cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800",
            )
        if clear_cookie:
            self.send_header(
                "Set-Cookie",
                f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
            )
        self.end_headers()
        self.wfile.write(out)

    def _parse_cookies(self) -> dict:
        raw = self.headers.get("Cookie") or ""
        out = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    def _current_user(self) -> dict | None:
        cookies = self._parse_cookies()
        token = cookies.get(COOKIE_NAME)
        auth = self.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip() or token
        return get_user_by_token(token)

    def _require_user(self) -> dict | None:
        user = self._current_user()
        if not user:
            self._send_json(401, {"ok": False, "error": "请先登录", "need_login": True})
            return None
        get_session(CASE).set_current_user(user)
        return user

    def _serve_static(self, file_path: Path) -> None:
        if not file_path.is_file():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        for hk, hv in security_headers():
            self.send_header(hk, hv)
        self.end_headers()
        self.wfile.write(content)

    def _serve_defense(self, url_path: str) -> bool:
        """Serve docs/答辩总报告 at /report/ for unified product web entry."""
        if url_path in ("/report", "/report/"):
            self._serve_static(DEFENSE / "index.html")
            return True
        prefix = "/report/"
        if not url_path.startswith(prefix):
            return False
        rel = url_path[len(prefix) :].lstrip("/")
        if not rel:
            self._serve_static(DEFENSE / "index.html")
            return True
        target = (DEFENSE / rel).resolve()
        defense_root = DEFENSE.resolve()
        if defense_root not in target.parents and target != defense_root:
            self.send_error(403)
            return True
        self._serve_static(target)
        return True

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/login", "/login.html"):
            self._serve_static(CASE / "login.html")
            return
        if path in ("/", "/app.html"):
            if not self._current_user():
                self.send_response(302)
                self.send_header("Location", "/login.html")
                self.end_headers()
                return
            self._serve_static(CASE / "app.html")
            return
        if self._serve_defense(path):
            return
        if path == "/api/auth/me":
            user = self._current_user()
            if not user:
                self._send_json(200, {"ok": False, "user": None, "need_login": True})
                return
            self._send_json(200, {"ok": True, "user": user, "db": db_stats()})
            return
        if path.startswith("/api/") and path not in PUBLIC_API:
            if not self._require_user():
                return
        if path == "/api/db/stats":
            self._send_json(200, {"ok": True, **db_stats()})
            return
        if path == "/api/state":
            try:
                st = get_session(CASE).state()
                st["user"] = self._current_user()
                self._send_json(200, st)
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/journal":
            try:
                session = get_session(CASE)
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "content": session.journal,
                        "excerpt": getattr(session, "excerpt", "") or "",
                        "chars": len(session.journal),
                        "excerpt_chars": len(getattr(session, "excerpt", "") or ""),
                        "path": str(session.journal_path.relative_to(CASE)),
                        "id": session.journal_id,
                        "meta": session.journal_meta,
                    },
                )
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/journals":
            try:
                self._send_json(200, list_journals())
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/journals/preview":
            try:
                from urllib.parse import urlparse, parse_qs

                qs = parse_qs(urlparse(self.path).query)
                jid = (qs.get("id") or qs.get("journal_id") or [""])[0].strip()
                if not jid:
                    self._send_json(400, {"ok": False, "error": "缺少 id"})
                    return
                data = read_journal(jid)
                self._send_json(200, data if data.get("ok") is not False else {"ok": True, **data})
            except FileNotFoundError as e:
                self._send_json(404, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/audit":
            try:
                from urllib.parse import urlparse, parse_qs

                qs = parse_qs(urlparse(self.path).query)
                jid = (qs.get("journal_id") or [None])[0]
                group = (qs.get("group") or [""])[0].lower() in {"1", "true", "journal", "journals"}
                q = (qs.get("q") or [""])[0]
                limit = int((qs.get("limit") or ["100"])[0])
                if group and not jid:
                    user = self._current_user()
                    items = list_audit_journals(limit=limit, q=q, current_user=user)
                    self._send_json(200, {"ok": True, "group": "journal", "items": items, "count": len(items)})
                else:
                    events = list_events(journal_id=jid, limit=limit)
                    self._send_json(200, {"ok": True, "events": events, "count": len(events), "journal_id": jid})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/registry":
            try:
                from urllib.parse import urlparse, parse_qs

                qs = parse_qs(urlparse(self.path).query)
                q = (qs.get("q") or [""])[0]
                product = (qs.get("product") or [""])[0]
                items = list_approved(q=q)
                for it in items:
                    if not it.get("product") and it.get("journal_id"):
                        jid = it["journal_id"]
                        for known in sorted(PRODUCT_LABELS.keys(), key=len, reverse=True):
                            if jid.startswith(known):
                                it["product"] = known
                                break
                if product:
                    items = [x for x in items if (x.get("product") or "") == product]
                products = sorted({(x.get("product") or "unknown") for x in list_approved(q="")})
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "items": items,
                        "count": len(items),
                        "products": products,
                        "product_labels": PRODUCT_LABELS,
                    },
                )
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/registry/detail":
            try:
                from urllib.parse import urlparse, parse_qs

                qs = parse_qs(urlparse(self.path).query)
                jid = (qs.get("journal_id") or [""])[0]
                self._send_json(200, get_registry_detail(jid))
            except FileNotFoundError as e:
                self._send_json(404, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/queue":
            try:
                from urllib.parse import urlparse, parse_qs

                from review_queue import actionable_pending_count, list_queue_enriched  # noqa: E402

                qs = parse_qs(urlparse(self.path).query)
                status = (qs.get("status") or [None])[0]
                claim_filter = (qs.get("claim") or ["all"])[0] or "all"
                user = self._current_user()
                items = list_queue_enriched(
                    user=user, status=status, claim_filter=claim_filter
                )
                pending = actionable_pending_count(user)
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "items": items,
                        "count": len(items),
                        "pending_human": pending,
                        "claim_filter": claim_filter,
                        "me": {
                            "id": (user or {}).get("id"),
                            "name": (user or {}).get("display_name")
                            or (user or {}).get("username"),
                        },
                    },
                )
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/journals/fetch":
            try:
                self._send_json(200, list_inbox())
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/journals/fetch/item":
            try:
                from urllib.parse import urlparse, parse_qs

                qs = parse_qs(urlparse(self.path).query)
                iid = (qs.get("id") or [""])[0].strip()
                self._send_json(200, get_inbox_item(iid))
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path == "/api/journals/fetch/compare":
            try:
                from urllib.parse import urlparse, parse_qs

                qs = parse_qs(urlparse(self.path).query)
                iid = (qs.get("id") or [""])[0].strip()
                self._send_json(200, compare_inbox_item(iid))
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return
        if path in ("/api/health", "/api/ping"):
            key_ok = bool(os.environ.get("AGNES_API_KEY", "").strip())
            self._send_json(200, {"ok": True, "ai_configured": key_ok, "port": PORT, "service": "stage0_server"})
            return
        if path == "/api/specification":
            try:
                import yaml

                if not SPEC.exists():
                    self._send_json(404, {"error": f"missing {SPEC.name}"})
                    return
                data = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
                self._send_json(200, {"spec": data, "path": str(SPEC.relative_to(ROOT))})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        payload = self._read_json_body()

        if path == "/api/auth/register":
            if not registration_allowed():
                self._send_json(403, {"ok": False, "error": "已关闭自助注册（SECURITY_DISABLE_REGISTER=1）"})
                return
            if not allow_auth_attempt(client_key(self)):
                self._send_json(429, {"ok": False, "error": "尝试过于频繁，请稍后再试"})
                return
            try:
                user = create_user(
                    username=(payload.get("username") or "").strip(),
                    password=payload.get("password") or "",
                    display_name=(payload.get("display_name") or "").strip(),
                )
                token = create_session(user["id"])
                self._send_json(200, {"ok": True, "user": user, "token": token}, set_cookie=token)
            except ValueError as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/auth/login":
            if not allow_auth_attempt(client_key(self)):
                self._send_json(429, {"ok": False, "error": "尝试过于频繁，请稍后再试"})
                return
            try:
                user = verify_login(
                    (payload.get("username") or "").strip(),
                    payload.get("password") or "",
                )
                token = create_session(user["id"])
                self._send_json(200, {"ok": True, "user": user, "token": token}, set_cookie=token)
            except ValueError as e:
                self._send_json(401, {"ok": False, "error": str(e)})
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/auth/logout":
            token = self._parse_cookies().get(COOKIE_NAME)
            delete_session(token)
            self._send_json(200, {"ok": True}, clear_cookie=True)
            return

        if path.startswith("/api/") and path not in PUBLIC_API:
            if not self._require_user():
                return

        if path == "/api/loop/step1":
            try:
                session = get_session(CASE)
                if session.busy:
                    self._send_json(409, {"ok": False, "error": "Loop 正在运行，请稍候"})
                    return
                note = (payload.get("revise_note") or "").strip()
                self._send_json(200, session.run_step1(revise_note=note))
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/loop/step2":
            try:
                session = get_session(CASE)
                if session.busy:
                    self._send_json(409, {"ok": False, "error": "Loop 正在运行，请稍候"})
                    return
                note = (payload.get("revise_note") or "").strip()
                self._send_json(200, session.run_step2(revise_note=note))
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/loop/feedback":
            try:
                session = get_session(CASE)
                step = payload.get("step") or STEP1
                raw = (payload.get("raw") or "").strip()
                actor = (payload.get("actor") or "").strip()
                user = self._current_user() or {}
                if not actor:
                    actor = user.get("display_name") or user.get("username") or ""
                if not raw:
                    self._send_json(400, {"ok": False, "error": "缺少 raw 反馈"})
                    return
                if session.busy:
                    self._send_json(409, {"ok": False, "error": "Loop 正在运行，请稍候"})
                    return
                result = session.submit_feedback(step, raw, actor=actor)
                self._send_json(200 if result.get("ok") else 400, result)
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/loop/finalize":
            try:
                session = get_session(CASE)
                if session.busy:
                    self._send_json(409, {"ok": False, "error": "Loop 正在运行，请稍候"})
                    return
                approver = (payload.get("approver") or "").strip()
                note = (payload.get("note") or "").strip()
                self._send_json(200, session.finalize(approver, note=note))
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/check":
            try:
                target = (payload.get("target") or "accepted").strip()
                actor = (payload.get("actor") or "").strip()
                self._send_json(200, get_session(CASE).run_check(target=target, actor=actor))
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/loop/reset":
            try:
                from loop_session import reset_session

                keep = bool(payload.get("keep_locked"))
                self._send_json(200, reset_session(CASE, keep_locked=keep))
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/journal/select":
            try:
                jid = (payload.get("id") or "").strip()
                force = bool(payload.get("force_reopen"))
                if not jid:
                    self._send_json(400, {"ok": False, "error": "缺少日志 id"})
                    return
                result = get_session(CASE).select_journal(jid, reset_outputs=True)
                if result.get("approval", {}).get("status") == "approved" and not force:
                    result["hint"] = "该日志已在定稿档案。强制复审请带 force_reopen=true"
                self._send_json(200, result)
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/journal/paste":
            try:
                saved = save_pasted(
                    title=(payload.get("title") or "").strip(),
                    content=payload.get("content") or "",
                    product=(payload.get("product") or "custom").strip(),
                )
                result = get_session(CASE).select_journal(saved["id"], reset_outputs=True)
                result["saved"] = saved
                self._send_json(200, result)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if path == "/api/journal/upload":
            try:
                saved = save_upload(
                    filename=(payload.get("filename") or "upload.md").strip(),
                    content=payload.get("content") or "",
                )
                result = get_session(CASE).select_journal(saved["id"], reset_outputs=True)
                result["saved"] = saved
                self._send_json(200, result)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if path == "/api/journals/fetch/run":
            try:
                max_n = int(payload.get("max_per_product") or 40)
                mode = (payload.get("mode") or "manual").strip()
                if mode == "auto":
                    self._send_json(200, auto_fetch_if_due(force=bool(payload.get("force"))))
                else:
                    self._send_json(200, fetch_from_official(max_per_product=max_n))
            except Exception as e:
                sys.stderr.write(traceback.format_exc())
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/journals/fetch/compare":
            try:
                iid = (payload.get("id") or "").strip()
                self._send_json(200, compare_inbox_item(iid))
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/journals/fetch/approve":
            try:
                ids = payload.get("ids") or []
                self._send_json(200, approve_inbox_items([str(x) for x in ids]))
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/journals/fetch/reject":
            try:
                ids = payload.get("ids") or []
                reason = (payload.get("reason") or "").strip()
                self._send_json(200, reject_inbox_items([str(x) for x in ids], reason=reason))
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/queue/batch":
            try:
                ids = payload.get("journal_ids") or []
                if not isinstance(ids, list) or not ids:
                    self._send_json(400, {"ok": False, "error": "请提供 journal_ids 数组"})
                    return
                user = self._require_user()
                if not user:
                    return
                actor = (
                    (payload.get("actor") or "").strip()
                    or user.get("display_name")
                    or user.get("username")
                    or "批量任务"
                )
                self._send_json(
                    200,
                    enqueue(
                        [str(x) for x in ids],
                        actor=actor,
                        actor_user_id=user.get("id"),
                    ),
                )
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/queue/open":
            try:
                user = self._require_user()
                if not user:
                    return
                qid = (payload.get("id") or "").strip()
                if not qid:
                    self._send_json(400, {"ok": False, "error": "缺少队列 id"})
                    return
                result = get_session(CASE).open_queue_item(qid)
                self._send_json(200 if result.get("ok") else 400, result)
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})
            return

        if path == "/api/queue/inject":
            try:
                result = inject_pending(
                    journal_id=(payload.get("journal_id") or "").strip(),
                    requirement_story=payload.get("requirement_story")
                    or "# 需求故事\n\n## 全局故事（一件事）\n测试\n",
                    stories=payload.get("stories")
                    or {
                        "stories": [
                            {
                                "id": "s1",
                                "level": "task",
                                "text": "用户要测试",
                                "source_quote": "测试",
                                "reason": "自测",
                                "approved": False,
                                "revisions": [],
                            }
                        ]
                    },
                    actor=(payload.get("actor") or "自测").strip(),
                    journal_title=(payload.get("journal_title") or "").strip() or None,
                )
                self._send_json(200, result)
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if path != "/api/draft-stories":
            self.send_error(404)
            return

        try:
            journal_path = CASE / "input" / "journal-official-full.md"
            journal = payload.get("journal") or journal_path.read_text(encoding="utf-8")
            requirement_story = payload.get("requirement_story")  # 可选；无则走预览 stub
            stories = call_agnes(journal, requirement_story)
            self._send_json(
                200,
                {
                    "stories": stories,
                    "count": len(stories),
                    "prompt": str(resolve_step2_prompt_path().relative_to(ROOT)),
                    "mode": "step2" if (requirement_story or "").strip() else "step2-preview",
                },
            )
        except Exception as e:
            sys.stderr.write("draft-stories error:\n" + traceback.format_exc())
            self._send_json(500, {"error": str(e)})


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true", help="do not open browser tab")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    load_dotenv(ENV)
    ensure_db()
    migrate_json_registry_once()
    if not (CASE / "app.html").exists():
        raise SystemExit(f"Missing {CASE / 'app.html'}")

    port = args.port
    try:
        host = resolve_bind_host()
    except RuntimeError as e:
        raise SystemExit(str(e)) from e
    url = f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/"
    login_url = f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/login.html"
    review_url = f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/review.html"
    report_url = f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}/report/"
    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError as e:
        raise SystemExit(
            f"Cannot bind {host}:{port} ({e}).\n"
            f"Close other windows using this port, then start again."
        ) from e

    print(f"Serving {CASE}")
    print(f"Bind: {host}:{port} (localhost-first; set SECURITY_ALLOW_LAN=1 only if needed)")
    print(f"Login: {login_url}  (demo / demo1234)")
    print(f"Product UI: {url}")
    print(f"DB: {PROJECT / 'data' / 'product_requirement.db'}")
    print(f"Review (legacy): {review_url}")
    print(f"Report: {report_url}")
    if not registration_allowed():
        print("Security: self-registration DISABLED")
    if not os.environ.get("AGNES_API_KEY", "").strip():
        print("WARN: AGNES_API_KEY missing — copy project/.env.example to project/.env")
    else:
        print("Loop API: POST /api/loop/step1|step2|feedback|finalize")
        print("Auth API: POST /api/auth/login|register|logout")
    print("Keep this window open while using AI.")
    try:
        start_auto_fetch_worker()
        print("Inbox auto-fetch: daily check started (official repo only; fetch ≠ import).")
    except Exception as e:
        print(f"WARN: auto-fetch worker not started: {e}")
    if not args.no_browser:
        webbrowser.open(login_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
