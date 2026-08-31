#!/usr/bin/env python3
"""阶段 7：整理与可复跑检查。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    preadme = (ROOT / "project/README.md").read_text(encoding="utf-8")
    run("S01", "根 README 含复跑说明", "implementation.py" in readme or "闭环" in readme or "阶段 4" in readme, "README")
    run("S02", "project README 可复跑", "implementation.py" in preadme and "check.py" in preadme, "project/README")
    run("S03", "课题申请存在", (ROOT / "docs/申请/课题申请.md").exists(), "docs/申请/")
    run("S04", "流程报告存在", (ROOT / "docs/申请/项目实现流程报告.md").exists(), "路线图")
    run("S05", "资料清单存在", (ROOT / "docs/申请/资料清单.md").exists(), "清单")
    run("S06", "run-stage4-loop.bat", (ROOT / "run-stage4-loop.bat").exists() or (ROOT / "启动阶段4闭环.bat").exists(), "launcher")
    run("S07", "accepted.json 可演示", (ROOT / "project/trials/case-01/output/accepted.json").exists(), "定稿")
    run("S08", "阶段4～7 报告目录", (ROOT / "docs/阶段4").exists() and (ROOT / "docs/阶段7").exists(), "docs/")

    print(f"\n合计: {len(results)} 项, 失败 {failed}")
    if args.write_report:
        lines = [
            "# 阶段 7 整理提交自测",
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
