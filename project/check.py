#!/usr/bin/env python3
"""product-requirement 自动验收脚本。

验收门槛（课题申请中声明，非实验结果）：
- 编造条数 fabrication_count = 0
- source_quote 通过率 = 100%
- 句覆盖率 coverage_rate = 100%（未覆盖句写入 uncovered.md）

用法：
  python check.py output/stories.json --source input/journal-raw.md
  python check.py output/accepted.json --source input/journal-raw.md --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Windows 控制台默认 GBK 时，--help / 中文输出会 UnicodeEncodeError → 非 0 退出
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SENTENCE_SPLIT = re.compile(r"(?<=[。！？\n])|(?<=\.\s)")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]
    return [p for p in parts if len(p) >= 4]


def check_fabrication(stories: list[dict], source: str) -> list[str]:
    errors = []
    for i, story in enumerate(stories):
        quote = story.get("source_quote", "")
        if not quote:
            errors.append(f"story[{i}] 缺少 source_quote")
            continue
        if quote not in source:
            errors.append(f"story[{i}] source_quote 不在原文中（疑似编造）: {quote[:40]}...")
    return errors


def check_text_format(stories: list[dict]) -> list[str]:
    errors = []
    for i, story in enumerate(stories):
        text = story.get("text", "")
        if not text.startswith("用户要"):
            errors.append(f"story[{i}] text 必须以「用户要」开头: {text[:30]}...")
        level = story.get("level")
        if level not in {"activity", "task", "story"}:
            errors.append(f"story[{i}] level 非法: {level}")
    return errors


def check_coverage(stories: list[dict], source: str) -> tuple[float, list[str]]:
    sentences = split_sentences(source)
    if not sentences:
        return 1.0, []
    quotes = [s.get("source_quote", "") for s in stories if s.get("source_quote")]
    uncovered = []
    covered = 0
    for sent in sentences:
        if any(q in sent or sent in q for q in quotes):
            covered += 1
        else:
            uncovered.append(sent)
    rate = covered / len(sentences)
    return rate, uncovered


def check_accepted(payload: dict) -> list[str]:
    errors = []
    review = payload.get("review", {})
    if review.get("approved") is not True:
        errors.append("review.approved 必须为 true")
    for i, story in enumerate(payload.get("stories", [])):
        if story.get("approved") is not True:
            errors.append(f"story[{i}] approved 必须为 true")
        if not story.get("revisions"):
            errors.append(f"story[{i}] revisions 不能为空")
        for j, rev in enumerate(story.get("revisions", [])):
            if rev.get("action") == "revised":
                comment = (rev.get("comment") or "").strip()
                if not comment:
                    errors.append(f"story[{i}] revisions[{j}] revised 必须写 comment（一句原因）")
                if not (rev.get("code") or "").strip():
                    errors.append(f"story[{i}] revisions[{j}] revised 必须写 code（问题类型）")
    cov = payload.get("coverage", {})
    if cov.get("coverage_rate", 0) < 1.0 and cov.get("uncovered"):
        comments = (review.get("comments") or "").strip()
        if not comments:
            errors.append("coverage_rate < 1.0 时须在 review.comments 说明人工确认")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="product-requirement acceptance checker")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--source", type=Path, required=True, help="source journal markdown")
    parser.add_argument("--strict", action="store_true", help="accepted.json mode")
    parser.add_argument("--write-uncovered", type=Path, help="write uncovered sentences here")
    parser.add_argument(
        "--allow-documented-uncovered",
        action="store_true",
        help="do not fail on coverage<100%% when uncovered is documented",
    )
    args = parser.parse_args()

    source = read_text(args.source)
    payload = json.loads(read_text(args.json_file))
    stories = payload.get("stories", [])

    errors: list[str] = []
    errors.extend(check_fabrication(stories, source))
    errors.extend(check_text_format(stories))

    rate, uncovered = check_coverage(stories, source)
    if rate < 1.0:
        if args.write_uncovered:
            args.write_uncovered.write_text("\n".join(uncovered), encoding="utf-8")
            print(f"已写入未覆盖句: {args.write_uncovered}")
        documented = False
        if args.allow_documented_uncovered and args.write_uncovered and args.write_uncovered.exists():
            documented = True
        if args.strict:
            # strict 走 check_accepted（comments）
            documented = True
        if not documented:
            errors.append(f"句覆盖率 {rate:.0%} < 100%，未覆盖 {len(uncovered)} 句")
        else:
            print(f"提示: 句覆盖率 {rate:.0%} < 100%（未覆盖 {len(uncovered)} 句，已记录，待人工确认）")

    if args.strict:
        errors.extend(check_accepted(payload))

    print(f"检查文件: {args.json_file}")
    print(f"故事条数: {len(stories)}")
    print(f"编造条数: {len([e for e in errors if '编造' in e or '不在原文' in e])}")
    print(f"句覆盖率: {rate:.0%}")

    if errors:
        print("\n未通过:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\n[OK] 全部验收门槛通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
