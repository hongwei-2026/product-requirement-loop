#!/usr/bin/env python3
"""阶段 1 自动验收：环境 + LLM 抽象 + 官方执行器。

比阶段 0 更严：除文件存在外，还要求 import、--help、--dry-run、LLM 配置可读。

用法：
  python scripts/verify_stage1.py
  python scripts/verify_stage1.py --write-report docs/自测/stage1-self-test-report.md

阶段 2+ 请用 scripts/verify_all.py 串联各阶段（含回归）。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
VENV_PY = PROJECT / ".venv" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    VENV_PY = PROJECT / ".venv" / "bin" / "python"
CASE = PROJECT / "trials" / "case-01"


def venv_python() -> str:
    return str(VENV_PY) if VENV_PY.exists() else sys.executable


def run_py(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [venv_python(), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(PROJECT),
    )


def load_env_keys() -> dict[str, str]:
    env: dict[str, str] = {}
    p = PROJECT / ".env"
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()

    results: list[dict] = []
    failed = 0

    def run(cid: str, name: str, ok: bool, detail: str):
        nonlocal failed
        if not ok:
            failed += 1
        results.append({"id": cid, "name": name, "ok": ok, "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {cid} {name} — {detail}")

    # --- 回归：阶段 0 关键项仍须成立 ---
    run(
        "R01",
        "阶段0 review.html",
        (CASE / "review.html").exists(),
        "project/trials/case-01/review.html",
    )
    run(
        "R02",
        "完整官方原文",
        (CASE / "input/journal-official-full.md").exists()
        and len((CASE / "input/journal-official-full.md").read_text(encoding="utf-8")) > 1500,
        "journal-official-full.md",
    )

    # --- 环境与依赖 ---
    run("E01", "requirements.txt", (PROJECT / "requirements.txt").exists(), "project/requirements.txt")
    run("E02", ".venv 存在", VENV_PY.exists(), str(VENV_PY.relative_to(ROOT)) if VENV_PY.exists() else "运行 setup阶段1环境.bat")

    for mod, cid, label in [
        ("yaml", "E03", "pyyaml"),
        ("langgraph", "E04", "langgraph"),
        ("openai", "E05", "openai"),
    ]:
        try:
            subprocess.run([venv_python(), "-c", f"import {mod}"], check=True, capture_output=True, cwd=str(PROJECT))
            run(cid, f"import {label}", True, "OK")
        except subprocess.CalledProcessError:
            run(cid, f"import {label}", False, "pip install 失败")

    # --- LLM 配置（默认 Agnes，可切换）---
    ex = (PROJECT / ".env.example").read_text(encoding="utf-8") if (PROJECT / ".env.example").exists() else ""
    run("E06", "LLM_PROVIDER 模板", "LLM_PROVIDER" in ex, ".env.example 含 LLM_PROVIDER")
    run("E07", "llm_config.py", (PROJECT / "llm_config.py").exists(), "统一 LLM 入口")
    run("E08", "多提供方预留", "deepseek" in ex and "openai" in ex, "agnes/deepseek/openai")

    env = load_env_keys()
    provider = env.get("LLM_PROVIDER", "agnes")
    key_name = {"agnes": "AGNES_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY"}.get(
        provider, "AGNES_API_KEY"
    )
    has_key = bool(env.get(key_name, "").strip()) and env.get(key_name, "") != "your-key-here"
    run("E09", f".env 已配置 ({provider})", (PROJECT / ".env").exists() and has_key, key_name)

    if (PROJECT / "llm_config.py").exists():
        try:
            r = run_py(["-c", "from llm_config import get_provider, get_model; print(get_provider(), get_model())"])
            ok = r.returncode == 0 and r.stdout.strip()
            run("E10", "llm_config 可导入", ok, r.stdout.strip() or r.stderr[:80])
        except Exception as e:
            run("E10", "llm_config 可导入", False, str(e))

    # --- check.py ---
    if (PROJECT / "check.py").exists():
        try:
            r = run_py([str(PROJECT / "check.py"), "--help"])
            run("E11", "check.py --help", r.returncode == 0, "exit 0")
        except Exception as e:
            run("E11", "check.py --help", False, str(e))

    # --- implementation.py（官方执行器 + 本地适配）---
    impl = PROJECT / "implementation.py"
    run("E12", "implementation.py 存在", impl.exists(), "已从官方复制并适配")
    spec = PROJECT / "product-requirement" / "specification.yaml"
    run("E13", "specification.yaml", spec.exists(), str(spec.relative_to(ROOT)))

    if impl.exists():
        try:
            r = run_py([str(impl), "--help"])
            run("E14", "implementation.py --help", r.returncode == 0, "exit 0")
        except Exception as e:
            run("E14", "implementation.py --help", False, str(e))
        try:
            r = run_py([str(impl), str(CASE.relative_to(PROJECT)), "--dry-run"], timeout=20)
            ok = r.returncode == 0 and "整理需求故事" in (r.stdout + r.stderr)
            run("E15", "implementation.py --dry-run", ok, "打印 product-requirement 步骤")
        except Exception as e:
            run("E15", "implementation.py --dry-run", False, str(e))

    # --- 文档与启动器 ---
    run("E16", "setup阶段1环境.bat", (ROOT / "setup阶段1环境.bat").exists(), "根目录")
    run("E17", "阶段1实现报告", (ROOT / "docs/阶段1/阶段1实现报告.md").exists(), "docs/阶段1/")
    run("E18", "阶段1自测说明", (ROOT / "docs/阶段1/阶段1自测工作流说明.md").exists(), "docs/阶段1/")

    print(f"\n合计: {len(results)} 项, 失败 {failed}")

    if args.write_report:
        lines = [
            "# 阶段 1 环境自测报告",
            "",
            f"**生成时间：** {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %z')}",
            f"**结果：** {'全部通过' if failed == 0 else f'{failed} 项未通过'}",
            "",
            "> 比阶段 0 更严：含阶段 0 回归项 R01～R02、LLM 配置、implementation --dry-run。",
            "",
            "| ID | 检查项 | 结果 | 说明 |",
            "|----|--------|------|------|",
        ]
        for r in results:
            lines.append(f"| {r['id']} | {r['name']} | {'✓' if r['ok'] else '✗'} | {r['detail']} |")
        lines.append("")
        lines.append("由 `python scripts/verify_stage1.py --write-report` 生成。")
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text("\n".join(lines), encoding="utf-8")
        print(f"已写入: {args.write_report}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
