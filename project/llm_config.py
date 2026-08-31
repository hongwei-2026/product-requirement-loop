"""LLM 提供方配置（阶段 1+ 统一入口）。

默认使用 Agnes（免费试用）。商业部署时改 LLM_PROVIDER，不必改业务代码。

环境变量（project/.env）：
  LLM_PROVIDER=agnes | deepseek | openai   # 默认 agnes

  # Agnes（默认）
  AGNES_API_KEY / AGNES_BASE_URL / AGNES_MODEL

  # DeepSeek（与官方 implementation.py 原文一致）
  DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL

  # OpenAI 兼容（预留商业）
  OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from openai import OpenAI

PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"

PROVIDERS: dict[str, dict[str, str]] = {
    "agnes": {
        "api_key": "AGNES_API_KEY",
        "base_url": "AGNES_BASE_URL",
        "default_base": "https://apihub.agnes-ai.com/v1",
        "model": "AGNES_MODEL",
        "default_model": "agnes-2.5-flash",
    },
    "deepseek": {
        "api_key": "DEEPSEEK_API_KEY",
        "base_url": "DEEPSEEK_BASE_URL",
        "default_base": "https://api.deepseek.com",
        "model": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "api_key": "OPENAI_API_KEY",
        "base_url": "OPENAI_BASE_URL",
        "default_base": "https://api.openai.com/v1",
        "model": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
    },
}


def load_dotenv() -> None:
    """加载 project/.env；不覆盖已设置的环境变量。"""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_provider() -> str:
    load_dotenv()
    name = os.environ.get("LLM_PROVIDER", "agnes").strip().lower()
    if name not in PROVIDERS:
        raise RuntimeError(f"未知 LLM_PROVIDER={name!r}，可选: {', '.join(PROVIDERS)}")
    return name


def get_model() -> str:
    load_dotenv()
    p = PROVIDERS[get_provider()]
    return os.environ.get(p["model"], p["default_model"])


def make_client() -> OpenAI:
    """返回 OpenAI 兼容客户端（Agnes / DeepSeek / 其他）。缺 Key 时抛 RuntimeError（不退出进程）。"""
    load_dotenv()
    provider = get_provider()
    cfg = PROVIDERS[provider]
    key = os.environ.get(cfg["api_key"], "").strip()
    if not key and provider == "deepseek":
        # 与官方 implementation.py 一致：回退 ~/.hermes/.env
        hermes = Path.home() / ".hermes" / ".env"
        if hermes.exists():
            for line in hermes.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
                    os.environ["DEEPSEEK_API_KEY"] = key
                    break
    if not key:
        raise RuntimeError(
            f"缺少 {cfg['api_key']}（当前 LLM_PROVIDER={provider}）。"
            f"请复制 project/.env.example 为 project/.env 并填写 Key。"
        )
    base = os.environ.get(cfg["base_url"], cfg["default_base"]).rstrip("/")
    return OpenAI(api_key=key, base_url=base, timeout=180.0)


def provider_summary() -> str:
    load_dotenv()
    p = get_provider()
    return f"{p} model={get_model()}"
