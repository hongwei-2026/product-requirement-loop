#!/usr/bin/env python3
"""阶段 2 自动验收：Loop 定义 yaml 定稿 + 与 dry-run / review 对齐。

比阶段 1 更严：解析 specification.yaml 语义、锁定规则一致性、验收页可读 yaml。

用法：
  python scripts/verify_stage2.py
  python scripts/verify_stage2.py --write-report docs/自测/stage2-self-test-report.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
VENV_PY = PROJECT / ".venv" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    VENV_PY = PROJECT / ".venv" / "bin" / "python"
CASE = PROJECT / "trials" / "case-01"
SPEC = PROJECT / "product-requirement" / "specification.yaml"
REVIEW = CASE / "review.html"
IMPL = PROJECT / "implementation.py"

EXPECTED_STEPS = ("整理需求故事", "提取用户故事 JSON", "人工评审定稿")
REVISE_CODES = ("编造", "分层", "漏了", "格式", "其他")


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


def load_spec() -> dict | None:
    if not yaml or not SPEC.exists():
        return None
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


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

    # --- 回归：阶段 1 关键项 ---
    run("R03", "llm_config 仍可用", (PROJECT / "llm_config.py").exists(), "project/llm_config.py")
    if (PROJECT / "llm_config.py").exists():
        try:
            r = run_py(["-c", "from llm_config import get_provider; print(get_provider())"])
            run("R03b", "llm_config 可导入", r.returncode == 0, r.stdout.strip() or r.stderr[:80])
        except Exception as e:
            run("R03b", "llm_config 可导入", False, str(e))

    run(
        "R04",
        "implementation --dry-run 仍可用",
        IMPL.exists(),
        str(IMPL.relative_to(ROOT)),
    )

    # --- yaml 存在与解析 ---
    run("Y01", "specification.yaml 存在", SPEC.exists(), str(SPEC.relative_to(ROOT)))
    if not yaml:
        run("Y01b", "pyyaml 可解析", False, "pip install pyyaml")
        spec = None
    else:
        try:
            spec = load_spec()
            run("Y01b", "yaml.safe_load", spec is not None and isinstance(spec, dict), "parse OK")
        except Exception as e:
            spec = None
            run("Y01b", "yaml.safe_load", False, str(e))

    if spec:
        required_top = {"name", "description", "entry", "exit", "steps", "feedback", "loop", "metrics", "acceptance", "locking"}
        missing = required_top - set(spec.keys())
        run(
            "Y02",
            "顶层字段齐全",
            not missing,
            f"缺少 {missing}" if missing else "含 locking/metrics 等",
        )

        steps = spec.get("steps") or []
        names = [s.get("name", "") for s in steps]
        run(
            "Y03",
            "恰好 3 步且名称一致",
            len(steps) == 3 and tuple(names) == EXPECTED_STEPS,
            " → ".join(names) if names else "无 steps",
        )

        step_ok = all(
            s.get("actor") and s.get("artifact") and s.get("check") for s in steps
        )
        run("Y04", "每步 actor/artifact/check", step_ok, "三步字段完整" if step_ok else "有缺项")

        fb = spec.get("feedback") or []
        fb_after = [f.get("after") for f in fb]
        run(
            "Y05",
            "feedback 在 step1/step2 后",
            EXPECTED_STEPS[0] in fb_after and EXPECTED_STEPS[1] in fb_after,
            str(fb_after),
        )

        acc = spec.get("acceptance") or {}
        run(
            "Y06",
            "fabrication_count=0",
            acc.get("fabrication_count") == 0,
            f"fabrication_count={acc.get('fabrication_count')}",
        )
        run(
            "Y07",
            "source_quote_pass_rate=1.0",
            acc.get("source_quote_pass_rate") == 1.0,
            f"rate={acc.get('source_quote_pass_rate')}",
        )

        locking = spec.get("locking") or {}
        loop_text = str(spec.get("loop", {}).get("condition", ""))
        lock_keys = {"on_ok_step1", "on_ok_story", "preserve_approved"}
        lock_ok = lock_keys <= set(locking.keys())
        loop_ok = all(k in loop_text for k in ("revise", "locked", "approved"))
        revise_ok = all(c in loop_text for c in REVISE_CODES)
        run(
            "Y08",
            "locking 与 loop 不矛盾",
            lock_ok and loop_ok and revise_ok,
            f"locking={list(locking.keys())}; loop 含 revise/locked/approved/快捷码",
        )

        metrics = spec.get("metrics") or []
        run(
            "Y09",
            "metrics 含 rounds/time",
            "rounds" in metrics and "time" in metrics,
            str(metrics),
        )

        run(
            "Y10",
            "deferred 声明 SQL 本期不做",
            any("SQL" in str(d) for d in (spec.get("deferred") or [])),
            "deferred 块记录 JSON→SQL",
        )

    # --- dry-run 与 yaml 一致 ---
    if IMPL.exists():
        try:
            r = run_py([str(IMPL), str(CASE.relative_to(PROJECT)), "--dry-run"], timeout=20)
            out = r.stdout + r.stderr
            dry_ok = r.returncode == 0 and all(n in out for n in EXPECTED_STEPS)
            run("Y11", "dry-run 打印三步", dry_ok, "含整理需求故事/提取用户故事 JSON/人工评审定稿")
        except Exception as e:
            run("Y11", "dry-run 打印三步", False, str(e))

    # --- 验收 UI 读 yaml ---
    review_text = REVIEW.read_text(encoding="utf-8") if REVIEW.exists() else ""
    run("Y12", "review.html Loop 面板", "loadSpec" in review_text and "spec-panel" in review_text, "含 loadSpec/spec-panel")
    run(
        "Y13",
        "review revise 码与 yaml 一致",
        all(f'data-code="{c}"' in review_text for c in REVISE_CODES),
        "|".join(REVISE_CODES),
    )
    run(
        "Y14",
        "spec-embedded 内嵌",
        'id="spec-embedded"' in review_text,
        "双击 file:// 可兜底",
    )
    if spec and 'id="spec-embedded"' in review_text:
        import base64
        import re

        m = re.search(
            r'(<script type="application/json" id="spec-embedded"[^>]*>)(.*?)</script>',
            review_text,
            re.DOTALL,
        )
        embed_ok = False
        if m:
            try:
                tag, body = m.group(1), m.group(2).strip()
                raw = body
                if 'data-encoding="base64"' in tag:
                    raw = base64.b64decode(body).decode("utf-8")
                embedded = json.loads(raw)
                embed_ok = (
                    embedded.get("name") == spec.get("name")
                    and len(embedded.get("steps", [])) == 3
                )
            except (json.JSONDecodeError, ValueError):
                embed_ok = False
        run("Y15", "内嵌 spec 与 yaml 同步", embed_ok, "跑 sync_spec_embed.py 可修复")

    server_py = (ROOT / "scripts/stage0_server.py").read_text(encoding="utf-8")
    run(
        "Y16",
        "API /api/specification",
        "/api/specification" in server_py,
        "stage0_server.py",
    )
    run(
        "Y17",
        "sync_spec_embed.py",
        (ROOT / "scripts/sync_spec_embed.py").exists(),
        "scripts/sync_spec_embed.py",
    )

    # --- 阶段 2 文档 ---
    run(
        "Y18",
        "阶段2实现报告",
        (ROOT / "docs/阶段2/阶段2实现报告.md").exists(),
        "docs/阶段2/",
    )
    run(
        "Y19",
        "阶段2快速验收清单",
        (ROOT / "docs/阶段2/阶段2快速验收清单.md").exists(),
        "docs/阶段2/",
    )
    run(
        "Y20",
        "阶段2自测工作流说明",
        (ROOT / "docs/阶段2/阶段2自测工作流说明.md").exists(),
        "docs/阶段2/",
    )

    print(f"\n合计: {len(results)} 项, 失败 {failed}")

    if args.write_report:
        lines = [
            "# 阶段 2 Loop 定义自测报告",
            "",
            f"**生成时间：** {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %z')}",
            f"**结果：** {'全部通过' if failed == 0 else f'{failed} 项未通过'}",
            "",
            "> yaml 语义 + dry-run 对齐 + review 读 spec；不含真 LLM Loop。",
            "",
            "| ID | 检查项 | 结果 | 说明 |",
            "|----|--------|------|------|",
        ]
        for r in results:
            lines.append(f"| {r['id']} | {r['name']} | {'✓' if r['ok'] else '✗'} | {r['detail']} |")
        lines.append("")
        lines.append("由 `python scripts/verify_stage2.py --write-report` 生成。")
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text("\n".join(lines), encoding="utf-8")
        print(f"已写入: {args.write_report}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
