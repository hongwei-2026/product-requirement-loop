#!/usr/bin/env python3
"""防入侵 / 访问控制静态自检（不需要启动服务）。

检查重点：
  - 默认只绑本机，避免误暴露公网/局域网
  - 密码哈希存储，禁止明文
  - Cookie HttpOnly
  - API 默认需登录（公开入口白名单极小）
  - 报告路径有目录穿越防护
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "scripts" / "stage0_server.py"
DB = ROOT / "project" / "web" / "db.py"
PASSWORDS = ROOT / "project" / "web" / "auth_passwords.py"
GUARD = ROOT / "project" / "web" / "security_guard.py"

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


def main() -> int:
    print("== security / anti-intrusion static checks ==")

    server = SERVER.read_text(encoding="utf-8")
    db = DB.read_text(encoding="utf-8")
    pw = PASSWORDS.read_text(encoding="utf-8")
    guard = GUARD.read_text(encoding="utf-8") if GUARD.exists() else ""

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
        # plaintext column assignment would be bad; seed via hash_password is OK
        if "hash_password(\"demo1234\")" in db or "hash_password('demo1234')" in db:
            ok("demo seed hashes password")
        else:
            bad("demo seed", "demo password must be hashed at rest")
    else:
        ok("no obvious plaintext password column write")

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

    # PUBLIC_API must stay small
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

    # 7) session token entropy
    if "uuid.uuid4()" in db or "token_urlsafe" in db or "secrets." in db:
        ok("session tokens use strong random generator")
    else:
        bad("session token", "create_session should use uuid4/secrets")

    print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
