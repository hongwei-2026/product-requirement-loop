#!/usr/bin/env python3
"""交付门面 / 文档布局门禁（轻量社区态）。

检查：
  - docs/交付 作为对外唯一门面：必读文件齐全
  - 根 README 含固定入口关键词（跑 / 验 / 结项 / 手册 / 问题）
  - docs/README 标明阶段材料为非结项必读
  - 不把组织章程文件名（public-second-brain.md 等）误当成业务必改名

Usage:
  project\\.venv\\Scripts\\python.exe scripts\\verify_docs_layout.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DELIVERY = ROOT / "docs" / "交付"
DOCS_README = ROOT / "docs" / "README.md"
ROOT_README = ROOT / "README.md"

PASS = 0
FAIL = 0

REQUIRED_DELIVERY = [
    "README.md",
    "结项说明-给审阅同事.md",
    "产品操作手册.md",
    "安全说明.md",
    "问题反馈整理-2026-09-08.md",
    "评审意见与处理情况.md",
    "任务贡献指南.md",
    "任务计分板.md",
    "任务仪表盘.md",
    "任务列表.md",
]


def ok(name: str, detail: str = "") -> None:
    global PASS
    PASS += 1
    print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))


def bad(name: str, detail: str) -> None:
    global FAIL
    FAIL += 1
    print(f"[FAIL] {name} — {detail}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    print("== verify_docs_layout (delivery facade) ==")

    if not DELIVERY.is_dir():
        bad("docs/交付 存在", str(DELIVERY))
        print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
        return 1
    ok("docs/交付 存在")

    for name in REQUIRED_DELIVERY:
        p = DELIVERY / name
        if p.is_file() and p.stat().st_size > 40:
            ok(f"交付必读 {name}")
        else:
            bad(f"交付必读 {name}", "缺失或过短")

    root = ROOT_README.read_text(encoding="utf-8") if ROOT_README.exists() else ""
    need_phrases = [
        ("怎么跑", ["快速开始", "start-with-ai", "怎么跑"]),
        ("怎么验收", ["验收", "trial-report", "verify_acceptance", "验收门槛"]),
        ("结项说明", ["结项说明"]),
        ("操作手册", ["产品操作手册", "操作手册"]),
        ("问题反馈", ["问题反馈"]),
    ]
    for label, alts in need_phrases:
        if any(a in root for a in alts):
            ok(f"根 README 入口·{label}")
        else:
            bad(f"根 README 入口·{label}", f"需含其一: {alts}")

    if "5 个入口" in root or "五个入口" in root or "| 1 |" in root:
        ok("根 README 突出入口表")
    else:
        bad("根 README 突出入口表", "建议保留「5 个入口」表")

    docs_nav = DOCS_README.read_text(encoding="utf-8") if DOCS_README.exists() else ""
    if "过程材料" in docs_nav and "非结项必读" in docs_nav:
        ok("docs/README 标明过程材料非必读")
    else:
        bad("docs/README 标明过程材料非必读", "需写清阶段/自测/答辩非结项必读")

    if "对外交付" in docs_nav and "交付/" in docs_nav:
        ok("docs/README 指向交付门面")
    else:
        bad("docs/README 指向交付门面", "需强调对外只看 交付/")

    facade = (DELIVERY / "README.md").read_text(encoding="utf-8")
    for charter in ("public-second-brain.md", "release.md", "second-brain.md"):
        if charter in facade:
            ok(f"章程文件名已对照说明·{charter}")
        else:
            bad(f"章程文件名已对照说明·{charter}", "交付 README 应注明组织章程文件名，避免误改业务名")

    # 轻量：不要在根目录再堆平行结项 md
    root_md = [p.name for p in ROOT.glob("*.md") if p.name.upper() != "README.MD"]
    clutter = [n for n in root_md if any(k in n for k in ("结项", "手册", "全景", "评审", "问题反馈"))]
    if not clutter:
        ok("根目录无平行结项类 md")
    else:
        bad("根目录无平行结项类 md", f"请下沉到 docs/交付/: {clutter}")

    print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
