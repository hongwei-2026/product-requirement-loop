"""LLM 提供方配置（阶段 1+ 统一入口）。

默认使用 Agnes（免费试用）。商业部署时改 LLM_PROVIDER，不必改业务代码。

环境变量（project/.env）：
  LLM_PROVIDER=agnes | deepseek | openai | moonshot | zhipu | minimax | mimo
  LLM_TIMEOUT=600          # 秒；长日志/推理模型建议 ≥300
  LLM_DISABLE_THINKING=1   # 默认关闭深度思考链（兼容 Pro）
  LLM_TRUST_ENV=0          # 默认 0：httpx 不读系统代理，避免 macOS SOCKS/缺 socksio

  # Agnes（默认）
  AGNES_API_KEY / AGNES_BASE_URL / AGNES_MODEL

  # DeepSeek（建议日常用 flash，Pro 需加大超时并关思考）
  DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL

  # 其他 OpenAI 兼容
  OPENAI_* / MOONSHOT_* / ZHIPU_* / MINIMAX_* / MIMO_*
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
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
        # 默认 flash：长日志 + Pro 推理易超过原 180s 超时
        "default_model": "deepseek-chat",
    },
    "openai": {
        "api_key": "OPENAI_API_KEY",
        "base_url": "OPENAI_BASE_URL",
        "default_base": "https://api.openai.com/v1",
        "model": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
    },
    "moonshot": {
        "api_key": "MOONSHOT_API_KEY",
        "base_url": "MOONSHOT_BASE_URL",
        "default_base": "https://api.moonshot.cn/v1",
        "model": "MOONSHOT_MODEL",
        "default_model": "moonshot-v1-32k",
    },
    "zhipu": {
        "api_key": "ZHIPU_API_KEY",
        "base_url": "ZHIPU_BASE_URL",
        "default_base": "https://open.bigmodel.cn/api/paas/v4",
        "model": "ZHIPU_MODEL",
        "default_model": "glm-4-flash",
    },
    "minimax": {
        "api_key": "MINIMAX_API_KEY",
        "base_url": "MINIMAX_BASE_URL",
        "default_base": "https://api.minimaxi.com/v1",
        "model": "MINIMAX_MODEL",
        "default_model": "MiniMax-Text-01",
    },
    "mimo": {
        "api_key": "MIMO_API_KEY",
        "base_url": "MIMO_BASE_URL",
        "default_base": "https://api.xiaomimimo.com/v1",
        "model": "MIMO_MODEL",
        "default_model": "mimo-v2.5",
    },
}


def load_dotenv(extra: Path | None = None) -> None:
    """加载 project/.env（及可选 extra）；不覆盖已设置的环境变量。"""
    for path in (ENV_FILE, extra):
        if path is None or not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
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


def get_timeout() -> float:
    load_dotenv()
    raw = os.environ.get("LLM_TIMEOUT", "600").strip()
    try:
        return max(30.0, float(raw))
    except ValueError:
        return 600.0


def thinking_disabled() -> bool:
    load_dotenv()
    return os.environ.get("LLM_DISABLE_THINKING", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def trust_env() -> bool:
    """默认 False：禁止 httpx 读取系统 HTTP/SOCKS 代理（避免缺 socksio 崩成 Connection error）。"""
    load_dotenv()
    return os.environ.get("LLM_TRUST_ENV", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def chat_extra_body() -> dict | None:
    """部分厂商（DeepSeek Pro / MiMo 等）可用 thinking 开关；默认关闭深度思考。"""
    if not thinking_disabled():
        return None
    return {"thinking": {"type": "disabled"}}


def make_client() -> OpenAI:
    """返回 OpenAI 兼容客户端。缺 Key 时抛 RuntimeError（不退出进程）。"""
    load_dotenv()
    provider = get_provider()
    cfg = PROVIDERS[provider]
    key = os.environ.get(cfg["api_key"], "").strip()
    if not key and provider == "deepseek":
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
    timeout = get_timeout()
    http_client = httpx.Client(trust_env=trust_env(), timeout=timeout)
    return OpenAI(api_key=key, base_url=base, http_client=http_client, timeout=timeout)


def provider_summary() -> str:
    load_dotenv()
    p = get_provider()
    return (
        f"{p} model={get_model()} timeout={get_timeout():.0f}s "
        f"trust_env={int(trust_env())} thinking_off={int(thinking_disabled())}"
    )
