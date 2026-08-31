#!/usr/bin/env python3
"""按阶段串联自测（阶段 0～7）。

用法：
  python scripts/verify_all.py
  python scripts/verify_all.py --write-reports
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
REPORTS = ROOT / "docs" / "自测"


def run(cmd: list[str], label: str) -> int:
    print(f"\n{'=' * 60}\n>>> {label}\n{'=' * 60}")
    r = subprocess.run(cmd, cwd=str(ROOT))
    return r.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-reports", action="store_true", help="写入 docs/自测/*.md")
    parser.add_argument(
        "--from-stage",
        type=int,
        default=0,
        help="从该阶段开始（0～7），用于跳过前面已过的层",
    )
    args = parser.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)

    def wr(name: str) -> list[str]:
        if not args.write_reports:
            return []
        return ["--write-report", str(REPORTS / name)]

    all_steps: list[tuple[int, list[str], str]] = [
        (0, [sys.executable, str(SCRIPTS / "verify_stage0.py")] + wr("stage0-self-test-report.md"), "阶段 0 机器层"),
        (0, ["node", str(SCRIPTS / "verify_stage0_ux.mjs")], "阶段 0 体验层"),
        (1, [sys.executable, str(SCRIPTS / "verify_stage1.py")] + wr("stage1-self-test-report.md"), "阶段 1 环境层"),
        (2, [sys.executable, str(SCRIPTS / "verify_stage2.py")] + wr("stage2-self-test-report.md"), "阶段 2 Loop 层"),
        (3, [sys.executable, str(SCRIPTS / "verify_stage3.py")] + wr("stage3-self-test-report.md"), "阶段 3 提示词层"),
        (4, [sys.executable, str(SCRIPTS / "verify_stage4.py")] + wr("stage4-self-test-report.md"), "阶段 4 闭环层"),
        (5, [sys.executable, str(SCRIPTS / "verify_stage5.py")] + wr("stage5-self-test-report.md"), "阶段 5 check 层"),
        (6, [sys.executable, str(SCRIPTS / "verify_stage6.py")] + wr("stage6-self-test-report.md"), "阶段 6 试点报告"),
        (7, [sys.executable, str(SCRIPTS / "verify_stage7.py")] + wr("stage7-self-test-report.md"), "阶段 7 整理提交"),
    ]

    failed = 0
    for stage, cmd, label in all_steps:
        if stage < args.from_stage:
            continue
        if run(cmd, label) != 0:
            failed += 1

    print(f"\n{'=' * 60}")
    if failed:
        print(f"verify_all: {failed} 个阶段未通过")
        return 1
    print("verify_all: 全部阶段通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
