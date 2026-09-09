#!/usr/bin/env python3
"""Enterprise PR scope guard: oversized diffs / sensitive paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SUMMARY = Path(os.environ.get("GITHUB_STEP_SUMMARY") or os.devnull)

# Soft limits (enterprise: fail unless labeled)
MAX_FILES = int(os.environ.get("PR_MAX_FILES", "45"))
MAX_CHANGED_LINES = int(os.environ.get("PR_MAX_LINES", "2500"))
SENSITIVE_PREFIXES = (
    ".github/workflows/",
    ".github/CODEOWNERS",
    "scripts/verify_security.py",
    "project/web/security_guard.py",
)


def main() -> int:
    files = int(os.environ.get("PR_CHANGED_FILES", "0") or 0)
    additions = int(os.environ.get("PR_ADDITIONS", "0") or 0)
    deletions = int(os.environ.get("PR_DELETIONS", "0") or 0)
    changed = additions + deletions
    names = [n.strip() for n in (os.environ.get("PR_FILENAMES") or "").split("\n") if n.strip()]
    labels = {x.strip().lower() for x in (os.environ.get("PR_LABELS") or "").split(",") if x.strip()}
    allow_large = "large-pr" in labels or "emergency" in labels

    errors: list[str] = []
    warnings: list[str] = []

    if files > MAX_FILES and not allow_large:
        errors.append(f"改动文件数 {files} > {MAX_FILES}：请拆 PR，或由维护者打标签 `large-pr`")
    if changed > MAX_CHANGED_LINES and not allow_large:
        errors.append(
            f"增减行合计 {changed} > {MAX_CHANGED_LINES}：请拆 PR，或打标签 `large-pr`"
        )

    sensitive = [n for n in names if any(n.startswith(p) or n == p.rstrip("/") for p in SENSITIVE_PREFIXES)]
    if sensitive and "security-ok" not in labels and "workflows" not in labels:
        # warn by default for trainees touching workflows — fail only if many
        if len(sensitive) >= 2 or any(n.startswith(".github/workflows/") for n in sensitive):
            if "maintainer-ok" not in labels:
                errors.append(
                    "触及工作流/安全门禁文件："
                    + ", ".join(sensitive[:8])
                    + "。需维护者确认并打标签 `maintainer-ok`"
                )
        else:
            warnings.append("触及敏感路径：" + ", ".join(sensitive))

    lines = [
        "## Scope guard",
        f"- files={files} additions={additions} deletions={deletions}",
        f"- allow_large={allow_large}",
    ]
    if warnings:
        lines.append("### Warnings")
        lines.extend(f"- {w}" for w in warnings)
    try:
        with SUMMARY.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
            if errors:
                f.write("### Failed\n" + "\n".join(f"- {e}" for e in errors) + "\n")
            else:
                f.write("### Passed\n")
    except OSError:
        pass

    for w in warnings:
        print(f"::warning::{w}")
    if errors:
        for e in errors:
            print(f"::error::{e}")
        return 1
    print("[OK] scope guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
