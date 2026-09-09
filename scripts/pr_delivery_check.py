#!/usr/bin/env python3
"""Enterprise PR delivery / design gate checks (CI + /recheck).

Reads:
  PR_TITLE, PR_BODY, PR_AUTHOR  from env
  Optionally GITHUB_WORKSPACE for file tree (design docs)

Exit 0 = pass, 1 = fail. Writes GitHub Job Summary when available.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_WORKSPACE") or Path(__file__).resolve().parent.parent)
SUMMARY = Path(os.environ.get("GITHUB_STEP_SUMMARY") or os.devnull)

URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+", re.I)
# markdown image or raw github user-attachments / uploaded assets
IMG_RE = re.compile(
    r"!\[[^\]]*\]\([^)]+\)|"
    r"https?://(?:user-images\.githubusercontent\.com|github\.com/user-attachments/assets)/[^\s\)\]\>\"']+",
    re.I,
)
VIDEO_HINT = re.compile(
    r"(bilibili\.com|b23\.tv|youtube\.com|youtu\.be|"
    r"feishu\.cn|larksuite\.com|loom\.com|pan\.baidu\.com|"
    r"alipan\.com|quark\.cn|drive\.google\.com|sharepoint\.com|"
    r"vimeo\.com|ixigua\.com)",
    re.I,
)


def classify(title: str, body: str) -> str:
    t, b = title or "", body or ""
    if re.search(r"\[Design\]", t, re.I) or re.search(r"docs/designs/#\d+", b, re.I):
        if re.search(r"\[Impl\]", t, re.I) or re.search(r"(?:Fixes|Closes)\s+#\d+", b, re.I):
            # Impl wins if Fixes present with Impl title
            if re.search(r"\[Impl\]", t, re.I) or (
                re.search(r"(?:Fixes|Closes)\s+#\d+", b, re.I) and not re.search(r"\[Design\]", t, re.I)
            ):
                return "implementation"
        return "design"
    if re.search(r"\[Impl\]", t, re.I) or re.search(r"(?:Fixes|Closes)\s+#\d+", b, re.I):
        return "implementation"
    return "unknown"


def issue_no(title: str, body: str) -> int | None:
    m = re.search(r"(?:Fixes|Closes|Resolves|Related to)\s+#(\d+)", body or "", re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"#(\d+)", title or "")
    return int(m.group(1)) if m else None


def append_summary(lines: list[str]) -> None:
    try:
        with SUMMARY.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


def check_impl(body: str) -> list[str]:
    errors: list[str] = []
    urls = URL_RE.findall(body or "")
    video_urls = [u for u in urls if VIDEO_HINT.search(u)]
    # also accept explicit 「演示视频」section with any http(s) link
    demo_section = re.search(
        r"##\s*演示视频[\s\S]{0,800}?(https?://[^\s\)\]\>\"']+)", body or "", re.I
    )
    if not video_urls and not demo_section:
        errors.append(
            "缺少可识别的演示视频公网链接（请在「演示视频」一节粘贴 B站/飞书/录屏等 URL）"
        )
    imgs = IMG_RE.findall(body or "")
    # count distinct image refs
    if len(imgs) < 2:
        errors.append(f"截图不足 2 处（当前识别到 {len(imgs)}）；请在 PR 正文直接贴图")
    if not re.search(r"(?:Fixes|Closes)\s+#\d+", body or "", re.I):
        errors.append("正文缺少 Fixes #<issue> / Closes #<issue>")
    return errors


def check_design(title: str, body: str) -> list[str]:
    errors: list[str] = []
    n = issue_no(title, body)
    if n is None:
        errors.append("无法解析 Issue 号（标题或正文需含 #N）")
        return errors
    designs = ROOT / "docs" / "designs"
    if not designs.is_dir():
        errors.append("缺少目录 docs/designs/")
        return errors
    hits = list(designs.glob(f"#{n}-*.md")) + list(designs.glob(f"#{n}_*.md"))
    # also allow exact #{n}.md
    exact = designs / f"#{n}.md"
    if exact.exists():
        hits.append(exact)
    hits = [p for p in hits if p.name != "_TEMPLATE.md" and p.name.upper() != "README.MD"]
    if not hits:
        errors.append(
            f"未找到设计文档：请新增 docs/designs/#{n}-简短英文.md（从 _TEMPLATE.md 复制）"
        )
    else:
        text = hits[0].read_text(encoding="utf-8", errors="replace")
        for heading in ("目标", "方案", "验收", "风险"):
            if heading not in text:
                errors.append(f"设计文档 {hits[0].name} 缺少章节关键词：{heading}")
    # Design should not use Fixes (would auto-close)
    if re.search(r"(?:Fixes|Closes)\s+#\d+", body or "", re.I):
        errors.append("Design PR 请用 Related to #N，不要用 Fixes/Closes（避免未实现就关 Issue）")
    return errors


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "auto").lower()
    title = os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY", "")
    kind = classify(title, body)
    if mode == "design":
        kind = "design"
    elif mode == "implementation":
        kind = "implementation"

    lines = [
        f"## PR delivery check (`{mode}` → classified `{kind}`)",
        f"- title: `{title[:120]}`",
    ]
    errors: list[str] = []

    if kind == "implementation":
        errors = check_impl(body)
    elif kind == "design":
        errors = check_design(title, body)
    else:
        errors = [
            "无法识别 PR 类型：标题请用 [Design] #N … 或 [Impl] #N …，并选用对应 PR 模板"
        ]

    if errors:
        lines.append("### ❌ Failed")
        lines.extend(f"- {e}" for e in errors)
        append_summary(lines)
        for e in errors:
            print(f"::error::{e}")
        return 1

    lines.append("### ✅ Passed")
    append_summary(lines)
    print("[OK] delivery/design gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
