#!/usr/bin/env python3
"""阶段 5 自测：check.py 两条命令 + uncovered / comments。"""

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
JOURNAL = CASE / "input" / "journal-official-full.md"
VENV_PY = PROJECT / ".venv" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    VENV_PY = PROJECT / ".venv" / "bin" / "python"


def py() -> str:
    return str(VENV_PY) if VENV_PY.exists() else sys.executable


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
        safe = detail.encode("ascii", "replace").decode("ascii")
        print(f"[{'PASS' if ok else 'FAIL'}] {cid} {name} — {safe}")

    run("C00", "check.py 存在", (PROJECT / "check.py").exists(), "project/check.py")

    stories = OUT / "stories.json"
    accepted = OUT / "accepted.json"
    uncovered = OUT / "uncovered.md"

    r1 = subprocess.run(
        [
            py(),
            str(PROJECT / "check.py"),
            str(stories),
            "--source",
            str(JOURNAL),
            "--write-uncovered",
            str(uncovered),
            "--allow-documented-uncovered",
        ],
        cwd=str(PROJECT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    run("C01", "check stories.json", r1.returncode == 0, f"exit={r1.returncode}")

    r2 = subprocess.run(
        [
            py(),
            str(PROJECT / "check.py"),
            str(accepted),
            "--source",
            str(JOURNAL),
            "--strict",
            "--allow-documented-uncovered",
        ],
        cwd=str(PROJECT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    run("C02", "check accepted.json --strict", r2.returncode == 0, f"exit={r2.returncode}")

    run("C03", "uncovered.md", uncovered.exists(), "未覆盖句已落盘")
    payload = json.loads(accepted.read_text(encoding="utf-8")) if accepted.exists() else {}
    fab_ok = True
    journal = JOURNAL.read_text(encoding="utf-8") if JOURNAL.exists() else ""
    for s in payload.get("stories") or []:
        if (s.get("source_quote") or "") not in journal:
            fab_ok = False
    run("C04", "定稿无编造", fab_ok and bool(payload.get("stories")), "source_quote 均在原文")
    comments = (payload.get("review") or {}).get("comments") or ""
    cov = (payload.get("coverage") or {}).get("coverage_rate", 1)
    need = cov >= 1.0 or bool(comments.strip())
    run("C05", "覆盖率或人工确认", need, f"rate={cov}, comments={'Y' if comments else 'N'}")

    print(f"\n合计: {len(results)} 项, 失败 {failed}")
    if args.write_report:
        lines = [
            "# 阶段 5 check.py 自测报告",
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
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
