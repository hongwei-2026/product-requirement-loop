# -*- coding: utf-8 -*-
"""Sync ops sections on all task Issues from 任务Issue标准块.md. Run: python scripts/sync_task_issue_ops.py"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STD = (ROOT / "docs" / "交付" / "任务Issue标准块.md").read_text(encoding="utf-8")

# Extract the two sections from the standard block (skip title/intro)
m = re.search(
    r"(## 如何接取 / 放弃 / 同步仪表盘[\s\S]*?)(?=## 交付物规范)",
    STD,
)
m2 = re.search(r"(## 交付物规范[\s\S]*)$", STD)
if not m or not m2:
    raise SystemExit("standard block sections not found")
OPS = m.group(1).strip() + "\n\n" + m2.group(1).strip() + "\n"

ISSUE_NOS = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]


def fetch_body(n: int) -> str:
    r = subprocess.run(
        ["gh", "issue", "view", str(n), "--json", "body", "-q", ".body"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return r.stdout or ""


def splice(body: str) -> str:
    # Remove BOM
    body = body.lstrip("\ufeff")
    # Drop old ops / delivery sections if present
    body = re.sub(
        r"\n## 如何接取[\s\S]*?(?=\n## 验收标准|\n## AI /|\n## 非目标|\n总入口:|\Z)",
        "\n",
        body,
        count=1,
    )
    body = re.sub(
        r"\n## 交付物规范[\s\S]*?(?=\n## 验收标准|\n## AI /|\n## 非目标|\n总入口:|\Z)",
        "\n",
        body,
        count=1,
    )
    body = re.sub(
        r"\n## 本任务流水[\s\S]*?(?=\n## 验收标准|\n## 如何接取|\n## 交付物|\n## AI /|\Z)",
        "\n",
        body,
        count=1,
    )
    # Insert OPS before 验收标准 or AI section
    insert_at = None
    for marker in ("\n## 验收标准", "\n## AI /", "\n## 非目标"):
        i = body.find(marker)
        if i >= 0:
            insert_at = i
            break
    block = "\n\n" + OPS
    if insert_at is None:
        return body.rstrip() + block + "\n"
    return body[:insert_at].rstrip() + block + body[insert_at:]


def main() -> None:
    for n in ISSUE_NOS:
        old = fetch_body(n)
        new = splice(old)
        if new.strip() == old.strip():
            print(f"#{n} unchanged")
            continue
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as f:
            f.write(new)
            path = f.name
        subprocess.run(["gh", "issue", "edit", str(n), "--body-file", path], check=True)
        Path(path).unlink(missing_ok=True)
        print(f"#{n} updated")


if __name__ == "__main__":
    main()
