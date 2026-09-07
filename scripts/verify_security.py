#!/usr/bin/env python3
"""防入侵 / 访问控制静态自检（不需要启动服务）。

检查重点：
  - 默认只绑本机，避免误暴露公网/局域网
  - 密码哈希存储，禁止明文
  - Cookie HttpOnly
  - API 默认需登录（公开入口白名单极小）
  - 报告路径有目录穿越防护
  - 危险 API / 注入面 / 响应头 / 限流阈值
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "scripts" / "stage0_server.py"
DB = ROOT / "project" / "web" / "db.py"
PASSWORDS = ROOT / "project" / "web" / "auth_passwords.py"
GUARD = ROOT / "project" / "web" / "security_guard.py"
LOOP = ROOT / "project" / "web" / "loop_session.py"
QUEUE = ROOT / "project" / "web" / "review_queue.py"
WEB_DIR = ROOT / "project" / "web"

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


def _scan_dangerous_calls(py_files: list[Path]) -> list[str]:
    """禁止在 web/server 路径直接出现高危原语（静态近似）。"""
    hits: list[str] = []
    patterns = [
        (r"\beval\s*\(", "eval("),
        (r"\bexec\s*\(", "exec("),
        (r"\bpickle\.loads\s*\(", "pickle.loads("),
        (r"\byaml\.load\s*\((?!.*Loader)", "yaml.load without Loader"),
        (r"shell\s*=\s*True", "subprocess shell=True"),
    ]
    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        for pat, label in patterns:
            for m in re.finditer(pat, text):
                # 允许注释行
                line_start = text.rfind("\n", 0, m.start()) + 1
                line = text[line_start : text.find("\n", m.start())]
                if line.lstrip().startswith("#"):
                    continue
                hits.append(f"{rel}: {label}")
    return hits


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    print("== security / anti-intrusion static checks ==")

    server = SERVER.read_text(encoding="utf-8")
    db = DB.read_text(encoding="utf-8")
    pw = PASSWORDS.read_text(encoding="utf-8")
    guard = GUARD.read_text(encoding="utf-8") if GUARD.exists() else ""
    loop = LOOP.read_text(encoding="utf-8") if LOOP.exists() else ""
    queue = QUEUE.read_text(encoding="utf-8") if QUEUE.exists() else ""

    # 1) bind localhost
    if 'ThreadingHTTPServer(("127.0.0.1"' in server or "resolve_bind_host" in server:
        ok("server bind is localhost-first")
    else:
        bad("server bind", "expected 127.0.0.1 or resolve_bind_host()")

    if "0.0.0.0" in server and "SECURITY_ALLOW_LAN" not in server and "SECURITY_ALLOW_LAN" not in guard:
        bad("open bind", "0.0.0.0 present without LAN gate")
    else:
        ok("no ungated 0.0.0.0 bind")

    # 2) password hashing
    if "pbkdf2" in pw and "hash_password" in pw and "verify_password" in pw:
        ok("passwords use pbkdf2 hashing")
    else:
        bad("password hashing", "auth_passwords.py missing pbkdf2 helpers")

    if "password_hash" in db and "hash_password(" in db:
        ok("users table stores password_hash via hash_password")
    else:
        bad("password storage", "db.py should hash passwords")

    if re.search(r'password\s*=\s*["\']demo1234["\']', db):
        if "hash_password(\"demo1234\")" in db or "hash_password('demo1234')" in db:
            ok("demo seed hashes password")
        else:
            bad("demo seed", "demo password must be hashed at rest")
    else:
        ok("no obvious plaintext password column write")

    # PBKDF2 iterations must stay reasonably high
    n = None
    for m2 in re.finditer(r"pbkdf2_hmac\((.*)\)", pw, re.S):
        nums = re.findall(r"([0-9]{3,}(?:_[0-9]+)?)", m2.group(1))
        for raw in nums:
            try:
                v = int(raw.replace("_", ""))
            except ValueError:
                continue
            if v >= 50_000:
                n = max(n or 0, v)
    if n and n >= 100_000:
        ok("pbkdf2 iterations >= 100k", str(n))
    else:
        bad("pbkdf2 iterations", f"expected >=100000, got {n}")

    # 3) cookie flags
    if "HttpOnly" in server and "SameSite=Lax" in server:
        ok("session cookie HttpOnly + SameSite=Lax")
    else:
        bad("cookie flags", "Set-Cookie must include HttpOnly; SameSite=Lax")

    # 4) API auth gate
    if "_require_user" in server and "PUBLIC_API" in server:
        ok("API auth gate present")
    else:
        bad("API auth", "missing _require_user / PUBLIC_API")

    m = re.search(r"PUBLIC_API\s*=\s*\{([^}]+)\}", server, re.S)
    if not m:
        bad("PUBLIC_API parse", "cannot find PUBLIC_API set")
    else:
        pubs = re.findall(r'"(/api/[^"]+)"', m.group(1))
        allowed = {
            "/api/ping",
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/me",
        }
        extra = set(pubs) - allowed
        if extra:
            bad("PUBLIC_API too wide", f"unexpected public routes: {sorted(extra)}")
        else:
            ok("PUBLIC_API whitelist minimal", ",".join(pubs))

    # Sensitive routes must not be public; global POST/GET API gate covers them
    sensitive = [
        "/api/loop/finalize",
        "/api/queue/batch",
        "/api/queue/cancel",
        "/api/queue/open",
        "/api/check",
        "/api/loop/step1",
        "/api/loop/step2",
    ]
    for route in sensitive:
        if f'"{route}"' not in server and f"'{route}'" not in server:
            bad(f"route present {route}", "missing")
            continue
        pub_block = m.group(1) if m else ""
        if route in pub_block:
            bad(f"sensitive not public {route}", "listed in PUBLIC_API")
        else:
            ok(f"sensitive not public {route}")

    if (
        'path.startswith("/api/") and path not in PUBLIC_API' in server
        and server.count("_require_user()") >= 2
    ):
        ok("global API auth gate on GET/POST")
    else:
        bad("global API auth gate", "expected _require_user for non-public /api/")

    # 5) path traversal guard on /report/
    if "defense_root not in target.parents" in server or "send_error(403)" in server:
        ok("report path has traversal guard")
    else:
        bad("path traversal", "report handler should reject paths outside defense root")

    # 6) login rate limit / security headers module
    if GUARD.exists() and "allow_auth_attempt" in guard and "security_headers" in guard:
        ok("security_guard rate-limit + headers module present")
    else:
        bad("security_guard", "missing project/web/security_guard.py helpers")

    if "allow_auth_attempt" in server and "security_headers" in server:
        ok("server wires rate-limit and security headers")
    else:
        bad("server wiring", "stage0_server.py should call security_guard helpers")

    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Cache-Control",
        "Permissions-Policy",
        "Cross-Origin-Opener-Policy",
    ]
    missing_h = [h for h in required_headers if h not in guard]
    if missing_h:
        bad("security headers set", f"missing {missing_h}")
    else:
        ok("security headers complete", ",".join(required_headers))

    # Rate limit must stay strict
    max_m = re.search(r"MAX_ATTEMPTS\s*=\s*(\d+)", guard)
    win_m = re.search(r"WINDOW_SEC\s*=\s*([0-9.]+)", guard)
    max_n = int(max_m.group(1)) if max_m else 999
    win_n = float(win_m.group(1)) if win_m else 0
    if max_n <= 15 and win_n <= 120:
        ok("auth rate limit strict enough", f"{max_n}/{win_n}s")
    else:
        bad("auth rate limit", f"MAX_ATTEMPTS={max_n} WINDOW_SEC={win_n} too loose")

    if "registration_allowed" in guard and "SECURITY_DISABLE_REGISTER" in guard:
        ok("registration can be disabled via env")
    else:
        bad("registration lock", "SECURITY_DISABLE_REGISTER gate missing")

    # 7) session token entropy
    if "uuid.uuid4()" in db or "token_urlsafe" in db or "secrets." in db:
        ok("session tokens use strong random generator")
    else:
        bad("session token", "create_session should use uuid4/secrets")

    # 8) Step3 finalize must re-check stories
    if 'run_check(target="stories"' in loop and "不能定稿入库" in loop:
        ok("finalize enforces stories check gate")
    else:
        bad("finalize check gate", "loop_session.finalize must block on failed check")

    # 9) queue cancel exists and clears claim
    if "def cancel_item" in queue and "cancelled" in queue:
        ok("queue cancel_item available")
    else:
        bad("queue cancel", "review_queue.cancel_item missing")

    # 10) dangerous primitives in web + server
    py_files = list(WEB_DIR.rglob("*.py")) + [SERVER]
    dang = _scan_dangerous_calls(py_files)
    if dang:
        bad("dangerous primitives", "; ".join(dang[:8]))
    else:
        ok("no eval/exec/pickle.loads/shell=True in web/server")

    # 11) AST: web modules parse cleanly
    ast_fail = []
    for p in WEB_DIR.rglob("*.py"):
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as e:
            ast_fail.append(f"{p.name}:{e.lineno}")
    if ast_fail:
        bad("web AST parse", str(ast_fail))
    else:
        ok("web package AST parseable")

    print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
