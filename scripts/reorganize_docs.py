#!/usr/bin/env python3
"""One-time reorganize repo docs into docs/ subfolders."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MOVES: dict[str, str] = {
    "课题申请.md": "docs/申请",
    "课题申请-详细版.html": "docs/申请",
    "资料清单.md": "docs/申请",
    "项目实现流程报告.md": "docs/申请",
    "提交邮件正文.txt": "docs/申请",
    "阶段0实现报告.md": "docs/阶段0",
    "阶段0验收操作手册.md": "docs/阶段0",
    "阶段0快速验收清单.md": "docs/阶段0",
    "阶段0自测工作流说明.md": "docs/阶段0",
    "人机确认操作指南.md": "docs/阶段0",
    "复核关键词卡-case01.md": "docs/阶段0",
    "图文预览.html": "docs/阶段0",
    "FORK与仓库说明.md": "docs/指南",
    "GITHUB推送说明.md": "docs/指南",
    "stage0-self-test-report.md": "docs/自测",
    "stage0-ux-self-test-report.md": "docs/自测",
    "build_md.py": "scripts",
    "build_report.py": "scripts",
}

for name, dest_rel in MOVES.items():
    src = ROOT / name
    dest_dir = ROOT / dest_rel
    dest_dir.mkdir(parents=True, exist_ok=True)
    if src.exists():
        target = dest_dir / name
        if target.exists():
            print(f"skip exists: {target}")
        else:
            shutil.move(str(src), str(target))
            print(f"moved: {name} -> {dest_rel}/")

print("done")
