#!/usr/bin/env python3
"""Fix relative paths after docs/ reorganization."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (folder_under_docs, replacements as list of (old, new))
RULES: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "阶段0",
        [
            ("](./screenshots/", "](../../screenshots/"),
            ("](./screenshots/", "](../../screenshots/"),
            ("[资料清单.md](./资料清单.md)", "[资料清单.md](../申请/资料清单.md)"),
            ("[项目实现流程报告.md](./项目实现流程报告.md)", "[项目实现流程报告.md](../申请/项目实现流程报告.md)"),
            ("[项目实现流程报告 —", "[项目实现流程报告 —"),  # keep anchor links
            ("](./项目实现流程报告.md", "](../申请/项目实现流程报告.md"),
            ("[FORK与仓库说明.md](./FORK与仓库说明.md)", "[FORK与仓库说明.md](../指南/FORK与仓库说明.md)"),
            ("](./FORK与仓库说明.md", "](../指南/FORK与仓库说明.md"),
            ("[GITHUB推送说明.md](./GITHUB推送说明.md)", "[GITHUB推送说明.md](../指南/GITHUB推送说明.md)"),
            ("[课题申请.md](./课题申请.md)", "[课题申请.md](../申请/课题申请.md)"),
        ],
    ),
    (
        "申请",
        [
            ("](./screenshots/", "](../../screenshots/"),
            ("[阶段0实现报告.md](./阶段0实现报告.md)", "[阶段0实现报告.md](../阶段0/阶段0实现报告.md)"),
            ("[阶段0验收操作手册.md](./阶段0验收操作手册.md)", "[阶段0验收操作手册.md](../阶段0/阶段0验收操作手册.md)"),
            ("[阶段0快速验收清单.md](./阶段0快速验收清单.md)", "[阶段0快速验收清单.md](../阶段0/阶段0快速验收清单.md)"),
            ("[项目实现流程报告.md](./项目实现流程报告.md)", "[项目实现流程报告.md](./项目实现流程报告.md)"),
            ("[图文预览.html](./图文预览.html)", "[图文预览.html](../阶段0/图文预览.html)"),
            ("[FORK与仓库说明.md](./FORK与仓库说明.md)", "[FORK与仓库说明.md](../指南/FORK与仓库说明.md)"),
        ],
    ),
    (
        "指南",
        [
            ("[阶段0验收操作手册.md](./阶段0验收操作手册.md)", "[阶段0验收操作手册.md](../阶段0/阶段0验收操作手册.md)"),
            ("](./阶段0", "](../阶段0/阶段0"),
        ],
    ),
]


def fix_html_preview(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text2 = text.replace('src="./screenshots/', 'src="../../screenshots/')
    text2 = text2.replace('href="阶段0实现报告.md"', 'href="阶段0实现报告.md"')
    if text2 != text:
        path.write_text(text2, encoding="utf-8")
        print(f"fixed html: {path.name}")


def main() -> None:
    for folder, reps in RULES:
        d = ROOT / "docs" / folder
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.suffix not in (".md", ".html"):
                continue
            text = f.read_text(encoding="utf-8")
            orig = text
            for old, new in reps:
                text = text.replace(old, new)
            # generic screenshot fix if still wrong in 阶段0/申请
            if folder in ("阶段0", "申请"):
                text = re.sub(r"\(\./screenshots/", "(../../screenshots/", text)
                text = re.sub(r'src="./screenshots/', 'src="../../screenshots/', text)
            if text != orig:
                f.write_text(text, encoding="utf-8")
                print(f"fixed: {f.relative_to(ROOT)}")

    preview = ROOT / "docs/阶段0/图文预览.html"
    if preview.exists():
        fix_html_preview(preview)


if __name__ == "__main__":
    main()
