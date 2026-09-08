#!/usr/bin/env python3
"""多厂商 OpenAI 兼容冒烟（不提交密钥）。

读取（均不入库）：
  - project/.env
  - project/.env.smoke   ← 推荐把多 Key 放这里做矩阵测试

Usage:
  project\\.venv\\Scripts\\python.exe scripts\\smoke_llm_providers.py
  project\\.venv\\Scripts\\python.exe scripts\\smoke_llm_providers.py --long
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
sys.path.insert(0, str(PROJECT))

from llm_config import (  # noqa: E402
    PROVIDERS,
    chat_extra_body,
    load_dotenv,
    make_client,
)

SMOKE = PROJECT / ".env.smoke"

# (显示名, LLM_PROVIDER, model_env, default_model, key_env)
MATRIX = [
    ("deepseek-flash", "deepseek", "DEEPSEEK_MODEL", "deepseek-chat", "DEEPSEEK_API_KEY"),
    ("deepseek-pro", "deepseek", "DEEPSEEK_MODEL", "deepseek-v4-pro", "DEEPSEEK_API_KEY"),
    ("moonshot", "moonshot", "MOONSHOT_MODEL", "moonshot-v1-32k", "MOONSHOT_API_KEY"),
    ("zhipu", "zhipu", "ZHIPU_MODEL", "glm-4-flash", "ZHIPU_API_KEY"),
    ("minimax", "minimax", "MINIMAX_MODEL", "MiniMax-Text-01", "MINIMAX_API_KEY"),
    ("mimo", "mimo", "MIMO_MODEL", "mimo-v2.5", "MIMO_API_KEY"),
]


def _short_prompt() -> str:
    return "只用一句话回答：1+1等于几？不要解释。"


def _long_prompt() -> str:
    body = ("研发日志：" + ("我们要建设用户故事库，从日志里抽取用户要……。" * 80))[:3500]
    return (
        body
        + "\n\n请用三句中文概括上面日志在说什么需求，不要编造原文没有的内容。"
    )


def run_one(label: str, provider: str, model: str, prompt: str) -> tuple[bool, str, float]:
    os.environ["LLM_PROVIDER"] = provider
    cfg = PROVIDERS[provider]
    os.environ[cfg["model"]] = model
    os.environ.setdefault("LLM_TRUST_ENV", "0")
    os.environ.setdefault("LLM_DISABLE_THINKING", "1")
    os.environ.setdefault("LLM_TIMEOUT", "600")
    t0 = time.perf_counter()
    try:
        client = make_client()
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": 0.1,
        }
        extra = chat_extra_body()
        if extra:
            kwargs["extra_body"] = extra
        resp = client.chat.completions.create(**kwargs)
        text = (resp.choices[0].message.content or "").strip().replace("\n", " ")
        dt = time.perf_counter() - t0
        return True, f"{text[:120]}…", dt
    except Exception as e:
        dt = time.perf_counter() - t0
        return False, f"{type(e).__name__}: {e}"[:220], dt


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--long", action="store_true", help="额外跑一段长提示（压超时）")
    ap.add_argument(
        "--only",
        default="",
        help="只跑指定标签，逗号分隔，如 deepseek-flash,zhipu",
    )
    args = ap.parse_args()
    load_dotenv(SMOKE if SMOKE.exists() else None)
    if not SMOKE.exists():
        print(f"[hint] 可选：把多 Key 写入 {SMOKE.relative_to(ROOT)}（已被 .gitignore）")

    allow = {x.strip() for x in args.only.split(",") if x.strip()}
    prompt = _long_prompt() if args.long else _short_prompt()
    print(f"== smoke_llm_providers ({'long' if args.long else 'short'}) ==")
    print(f"trust_env default off; thinking disabled; timeout={os.environ.get('LLM_TIMEOUT', '600')}s\n")

    ok_n = fail_n = skip_n = 0
    for label, provider, _menv, model, key_env in MATRIX:
        if allow and label not in allow:
            continue
        key = os.environ.get(key_env, "").strip()
        if not key or key.startswith("your-"):
            print(f"[SKIP] {label:16} 缺少 {key_env}")
            skip_n += 1
            continue
        # deepseek-pro 与 flash 共用一把 Key，切换模型名
        print(f"[RUN ] {label:16} provider={provider} model={model} …", flush=True)
        ok, detail, dt = run_one(label, provider, model, prompt)
        if ok:
            ok_n += 1
            print(f"[PASS] {label:16} {dt:6.1f}s  {detail}")
        elif "429" in detail or "RateLimit" in detail:
            ok_n += 1
            print(f"[WARN] {label:16} {dt:6.1f}s  rate-limited (key reachable): {detail}")
        elif "404" in detail and ("Permission" in detail or "Not found the model" in detail):
            # Key 往往有效，但当前账号未开通该模型名
            ok_n += 1
            print(f"[WARN] {label:16} {dt:6.1f}s  model not entitled (key reachable): {detail}")
        else:
            fail_n += 1
            print(f"[FAIL] {label:16} {dt:6.1f}s  {detail}")

    print(f"\n== summary PASS={ok_n} FAIL={fail_n} SKIP={skip_n} ==")
    return 1 if fail_n else 0


if __name__ == "__main__":
    raise SystemExit(main())
