#!/usr/bin/env python3
"""本地服务安全护栏：登录限流、绑定地址校验。"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque


_lock = threading.Lock()
_attempts: dict[str, deque[float]] = defaultdict(deque)

# 同一来源：60 秒内最多 20 次登录/注册尝试
WINDOW_SEC = 60.0
MAX_ATTEMPTS = 20


def client_key(handler) -> str:
    try:
        return handler.client_address[0] or "unknown"
    except Exception:
        return "unknown"


def allow_auth_attempt(key: str) -> bool:
    now = time.time()
    with _lock:
        q = _attempts[key]
        while q and now - q[0] > WINDOW_SEC:
            q.popleft()
        if len(q) >= MAX_ATTEMPTS:
            return False
        q.append(now)
        return True


def resolve_bind_host() -> str:
    """默认只绑 127.0.0.1，防止误暴露到局域网。"""
    host = (os.environ.get("BIND_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    allow_lan = (os.environ.get("SECURITY_ALLOW_LAN") or "").strip() in {"1", "true", "TRUE", "yes"}
    loopback = {"127.0.0.1", "localhost", "::1"}
    if host not in loopback and host != "0.0.0.0":
        # 明确的局域网 IP 也需要开关
        if not allow_lan:
            raise RuntimeError(
                f"拒绝绑定 {host}：默认仅本机可访问。"
                f"若确需局域网访问，请设置 SECURITY_ALLOW_LAN=1（有被旁人访问风险）。"
            )
    if host == "0.0.0.0" and not allow_lan:
        raise RuntimeError(
            "拒绝绑定 0.0.0.0：会暴露到所有网卡。"
            "请保持默认 127.0.0.1，或显式设置 SECURITY_ALLOW_LAN=1。"
        )
    return host


def security_headers() -> list[tuple[str, str]]:
    return [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "no-referrer"),
        ("Cache-Control", "no-store"),
        ("X-Product-Security", "localhost-first"),
    ]


def registration_allowed() -> bool:
    # 默认允许实训自助注册；上锁后仅已有账号可登录
    return (os.environ.get("SECURITY_DISABLE_REGISTER") or "").strip() not in {
        "1",
        "true",
        "TRUE",
        "yes",
    }
