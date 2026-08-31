#!/usr/bin/env python3
"""阶段 6：trial-report 已填写。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "project/trials/case-01/trial-report.md"


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

    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    run("T01", "trial-report.md 存在", REPORT.exists(), str(REPORT.relative_to(ROOT)))
    run("T02", "区分门槛与实测", "验收门槛" in text and "本次实测" in text, "表格")
    run("T03", "填了 Loop metrics", "rounds" in text and "corrections" in text, "对比表")
    run("T04", "有结论", "建议" in text or "有效性" in text, "第五节")
    run("T05", "非空模板", "（填写）" not in text and len(text) > 500, "已填实测")

    print(f"\n合计: {len(results)} 项, 失败 {failed}")
    if args.write_report:
        lines = [
            "# 阶段 6 试点报告自测",
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
