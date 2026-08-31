#!/usr/bin/env python3
"""阶段 4 自测：闭环产物 + 锁定 + accepted 结构。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
CASE = PROJECT / "trials" / "case-01"
OUT = CASE / "output"
VENV_PY = PROJECT / ".venv" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    VENV_PY = PROJECT / ".venv" / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()
    results = []
    failed = 0

    def run(cid, name, ok, detail):
        nonlocal failed
        if not ok:
            failed += 1
        results.append({"id": cid, "name": name, "ok": ok, "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {cid} {name} — {detail}")

    run("R07", "loop_runner.py", (PROJECT / "loop_runner.py").exists(), "闭环编排器")
    impl = (PROJECT / "implementation.py").read_text(encoding="utf-8")
    run("L01", "implementation 接 loop_runner", "loop_runner" in impl and "--demo" in impl, "默认闭环")
    run("L02", "锁定目录", (OUT / "locked" / "step1-requirement-story.md").exists(), "output/locked/")
    run("A01", "accepted.json", (OUT / "accepted.json").exists(), "定稿")
    run("A01b", "stories.json", (OUT / "stories.json").exists(), "Step2")
    run("A01c", "requirement-story.md", (OUT / "requirement-story.md").exists(), "Step1")

    payload = {}
    if (OUT / "accepted.json").exists():
        payload = json.loads((OUT / "accepted.json").read_text(encoding="utf-8"))
    stories = payload.get("stories") or []
    run("A02", "每条 approved", bool(stories) and all(s.get("approved") is True for s in stories), f"n={len(stories)}")
    run("A03", "revisions 非空", bool(stories) and all(s.get("revisions") for s in stories), "revisions")
    run("A04", "review.approved", payload.get("review", {}).get("approved") is True, "review")
    run(
        "A05",
        "含 revise 痕迹或 feedback",
        (payload.get("loop_metrics") or {}).get("feedback_triggered", 0) >= 1
        or any(
            any(r.get("action") == "revised" for r in (s.get("revisions") or []))
            for s in stories
        ),
        "反馈点",
    )

    # schema
    try:
        from jsonschema import validate

        schema = json.loads((PROJECT / "schemas/accepted.schema.json").read_text(encoding="utf-8"))
        validate(payload, schema)
        run("A06", "accepted.schema 校验", True, "jsonschema OK")
    except Exception as e:
        run("A06", "accepted.schema 校验", False, str(e)[:120])

    # parse_feedback
    try:
        r = subprocess.run(
            [
                str(VENV_PY) if VENV_PY.exists() else sys.executable,
                "-c",
                "from loop_runner import parse_feedback; "
                "a=parse_feedback('revise:编造:多了一条'); "
                "print(a['kind'], a['code'])",
            ],
            cwd=str(PROJECT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        run("L03", "parse_feedback", r.returncode == 0 and "revise" in r.stdout, r.stdout.strip() or r.stderr[:60])
    except Exception as e:
        run("L03", "parse_feedback", False, str(e))

    run("D01", "阶段4实现报告", (ROOT / "docs/阶段4/阶段4实现报告.md").exists(), "docs/阶段4/")

    print(f"\n合计: {len(results)} 项, 失败 {failed}")
    if args.write_report:
        lines = [
            "# 阶段 4 闭环自测报告",
            "",
            f"**生成时间：** {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %z')}",
            f"**结果：** {'全部通过' if failed == 0 else f'{failed} 项未通过'}",
            "",
            "| ID | 检查项 | 结果 | 说明 |",
            "|----|--------|------|------|",
        ]
        for r in results:
            lines.append(f"| {r['id']} | {r['name']} | {'Y' if r['ok'] else 'N'} | {r['detail']} |")
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"已写入: {args.write_report}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
