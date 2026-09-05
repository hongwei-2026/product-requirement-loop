#!/usr/bin/env python3
"""一键对照立项 6 条验收门槛（给结项审阅）。

在仓库根目录运行：
  python scripts/verify_acceptance.py

会：
  1. 打印 trial-report.md 路径与摘要表（若存在）
  2. 用 accepted.json 绑定的 source 跑 check.py --strict
  3. 检查 uncovered.md / approved / revisions 是否齐
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
CASE = PROJECT / "trials" / "case-01"
GOLDEN = CASE / "golden" / "accepted.json"
ACCEPTED = CASE / "output" / "accepted.json"
UNCOVERED = CASE / "output" / "uncovered.md"
TRIAL = CASE / "trial-report.md"
CHECK = PROJECT / "check.py"


def resolve_python() -> Path:
    win = PROJECT / ".venv" / "Scripts" / "python.exe"
    unix = PROJECT / ".venv" / "bin" / "python"
    if win.exists():
        return win
    if unix.exists():
        return unix
    return Path(sys.executable)


def resolve_source(accepted: dict) -> Path:
    meta = accepted.get("meta") or {}
    # 1) 结项黄金原文（不被冒烟 select_journal 覆盖）
    golden_src = CASE / "golden" / "active-journal.md"
    if golden_src.exists():
        return golden_src
    # 2) journal_id → journals/<stream>/<date>.md（稳定，优于会被改写的 active-journal）
    jid = (meta.get("journal_id") or "").strip()
    if jid:
        parts = jid.rsplit("-", 3)
        if len(parts) >= 4:
            stream = "-".join(parts[:-3])
            date = "-".join(parts[-3:])
            jpath = PROJECT / "journals" / stream / f"{date}.md"
            if jpath.exists():
                return jpath
        # excerpt id: qtcloud-product-2026-08-19-excerpt
        if jid.endswith("-excerpt"):
            base = jid[: -len("-excerpt")]
            parts = base.rsplit("-", 3)
            if len(parts) >= 4:
                stream = "-".join(parts[:-3])
                date = "-".join(parts[-3:])
                # prefer case excerpt file if present
                excerpt = CASE / "input" / "journal-excerpt.md"
                if excerpt.exists():
                    return excerpt
    # 3) meta.source_file relative to case
    rel = meta.get("source_file") or "input/active-journal.md"
    cand = CASE / rel
    if cand.exists():
        return cand
    active = CASE / "input" / "active-journal.md"
    if active.exists():
        return active
    raise FileNotFoundError(
        f"找不到 source。请检查 accepted.meta.source_file={rel!r} 或 journal_id={jid!r}"
    )


def _out(*args: object) -> None:
    print(*args, flush=True)


def print_trial_hint() -> None:
    _out("=" * 60)
    _out("验收实测报告（立项门槛 vs 实测）")
    _out("=" * 60)
    if TRIAL.exists():
        _out(f"[OK] 文件在: {TRIAL.relative_to(ROOT)}")
        _out("     请打开查看「验收门槛 vs 本次实测」整表。")
    else:
        _out(f"[MISS] 未找到 {TRIAL.relative_to(ROOT)}")
    _out()


def summarize_accepted(payload: dict) -> None:
    stories = payload.get("stories") or []
    n = len(stories)
    approved = sum(1 for s in stories if s.get("approved") is True)
    with_rev = sum(1 for s in stories if s.get("revisions"))
    review = payload.get("review") or {}
    _out("accepted.json 快速核对：")
    _out(f"  故事条数: {n}")
    _out(f"  approved=true: {approved}/{n}")
    _out(f"  revisions 非空: {with_rev}/{n}")
    _out(f"  review.approved: {review.get('approved')}")
    comments = (review.get("comments") or "").strip()
    _out(f"  review.comments: {'有' if comments else '无（覆盖率<100%时必须有）'}")
    _out(f"  uncovered.md: {'有' if UNCOVERED.exists() else '无'}")
    _out()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print_trial_hint()

    # 结项验收固定用 golden，避免工作台刚测的其他日志冲掉结果
    if GOLDEN.exists():
        accepted_path = GOLDEN
        _out(f"[INFO] 结项验收使用 golden: {GOLDEN.relative_to(ROOT)}")
        if ACCEPTED.exists():
            try:
                cur = json.loads(ACCEPTED.read_text(encoding="utf-8"))
                g = json.loads(GOLDEN.read_text(encoding="utf-8"))
                cj = (cur.get("meta") or {}).get("journal_id")
                gj = (g.get("meta") or {}).get("journal_id")
                if cj and gj and cj != gj:
                    _out(f"[INFO] 工作台当前定稿是另一篇日志（{cj}），不参与结项门槛核对。")
            except Exception:
                pass
    elif ACCEPTED.exists():
        accepted_path = ACCEPTED
        _out(f"[INFO] 无 golden，改用 output: {ACCEPTED.relative_to(ROOT)}")
    else:
        _out(f"[FAIL] 缺少定稿文件: {GOLDEN}")
        _out(f"       也没有 output: {ACCEPTED}")
        return 1

    payload = json.loads(accepted_path.read_text(encoding="utf-8"))
    summarize_accepted(payload)

    try:
        source = resolve_source(payload)
    except FileNotFoundError as e:
        _out(f"[FAIL] {e}")
        return 1

    _out(f"使用 source: {source.relative_to(ROOT)}")
    _out(f"journal_id: {(payload.get('meta') or {}).get('journal_id')}")
    _out()

    py = resolve_python()
    cmd = [
        str(py),
        str(CHECK),
        str(accepted_path),
        "--source",
        str(source),
        "--strict",
        "--allow-documented-uncovered",
    ]
    if UNCOVERED.parent.exists():
        cmd.extend(["--write-uncovered", str(UNCOVERED)])

    _out("运行 check.py --strict ...")
    _out(" ", " ".join(cmd))
    _out()
    proc = subprocess.run(cmd, cwd=str(ROOT))
    code = proc.returncode

    _out()
    if code == 0:
        _out("[OK] 机器验收通过（编造/出处/定稿字段等，见上方 check 输出）")
        _out("前台使用只能确认流程；6 条硬门槛以本脚本 + trial-report 为准。")
    else:
        _out("[FAIL] check 未通过。常见原因：--source 与定稿原文不一致。")
    return code


if __name__ == "__main__":
    sys.exit(main())
