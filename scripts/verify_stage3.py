#!/usr/bin/env python3
"""阶段 3 自动验收：提示词定稿 + 试跑产物 + 执行器读 prompt。

用法：
  python scripts/verify_stage3.py
  python scripts/verify_stage3.py --write-report docs/自测/stage3-self-test-report.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
VENV_PY = PROJECT / ".venv" / "Scripts" / "python.exe"
if not VENV_PY.exists():
    VENV_PY = PROJECT / ".venv" / "bin" / "python"
CASE = PROJECT / "trials" / "case-01"
PROMPTS = PROJECT / "product-requirement" / "prompts"
CASE_PROMPTS = CASE / "prompts"
OUT = CASE / "output"
JOURNAL = CASE / "input" / "journal-official-full.md"
IMPL = PROJECT / "implementation.py"


def venv_python() -> str:
    return str(VENV_PY) if VENV_PY.exists() else sys.executable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()

    results: list[dict] = []
    failed = 0

    def run(cid: str, name: str, ok: bool, detail: str):
        nonlocal failed
        if not ok:
            failed += 1
        results.append({"id": cid, "name": name, "ok": ok, "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {cid} {name} — {detail}")

    # --- 回归 ---
    run("R05", "阶段2 yaml 仍在", (PROJECT / "product-requirement/specification.yaml").exists(), "specification.yaml")
    run("R06", "llm_config 仍在", (PROJECT / "llm_config.py").exists(), "llm_config.py")

    # --- 提示词文件 ---
    s1 = PROMPTS / "step1-story.md"
    s2 = PROMPTS / "step2-json.md"
    run("P01", "Loop 级 step1-story.md", s1.exists(), str(s1.relative_to(ROOT)))
    run("P02", "Loop 级 step2-json.md", s2.exists(), str(s2.relative_to(ROOT)))

    t1 = s1.read_text(encoding="utf-8") if s1.exists() else ""
    t2 = s2.read_text(encoding="utf-8") if s2.exists() else ""
    run("P03", "step1 含 JOURNAL_RAW", "{{JOURNAL_RAW}}" in t1, "占位符")
    run(
        "P04",
        "step1 含全局故事与原文摘录",
        "全局故事" in t1 and "原文摘录" in t1,
        "章节齐全",
    )
    run(
        "P05",
        "step2 禁止编造与用户要",
        "禁止编造" in t2 and "用户要" in t2 and "source_quote" in t2,
        "约束齐全",
    )
    run(
        "P06",
        "step2 level 三档",
        "activity" in t2 and "task" in t2 and "story" in t2,
        "activity|task|story",
    )
    run("P07", "step2 含 REQUIREMENT_STORY", "{{REQUIREMENT_STORY}}" in t2, "占位符")

    # 试点副本同步
    c1 = CASE_PROMPTS / "step1-story.md"
    c2 = CASE_PROMPTS / "step2-json.md"
    sync_ok = (
        c1.exists()
        and c2.exists()
        and c1.read_text(encoding="utf-8") == t1
        and c2.read_text(encoding="utf-8") == t2
    )
    run("P08", "case-01 prompts 与 Loop 级同步", sync_ok, "trials/case-01/prompts/")

    # --- 执行器读 prompt ---
    impl_text = IMPL.read_text(encoding="utf-8") if IMPL.exists() else ""
    run(
        "P09",
        "implementation 加载 prompt 文件",
        "STEP_PROMPT_FILES" in impl_text and "resolve_prompt_path" in impl_text,
        "build_prompt 读 md",
    )
    try:
        r = subprocess.run(
            [
                venv_python(),
                "-c",
                (
                    "from pathlib import Path; import yaml; "
                    "from implementation import LoopAgent, STEP_PROMPT_FILES; "
                    f"spec=yaml.safe_load(Path(r'{PROJECT / 'product-requirement/specification.yaml'}').read_text(encoding='utf-8')); "
                    "a=LoopAgent(spec, client=None); "
                    f"td=Path(r'{CASE}'); "
                    "p=a.resolve_prompt_path({'name':'整理需求故事'}, td); "
                    "print('ok' if p and p.exists() else 'missing')"
                ),
            ],
            cwd=str(PROJECT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        run("P10", "resolve_prompt_path 可用", r.returncode == 0 and "ok" in r.stdout, r.stdout.strip() or r.stderr[:80])
    except Exception as e:
        run("P10", "resolve_prompt_path 可用", False, str(e))

    # stage0_server 读 step2
    server = (ROOT / "scripts/stage0_server.py").read_text(encoding="utf-8")
    run(
        "P11",
        "验收页读 step2-json.md",
        "build_step2_prompt" in server and "step2-json.md" in server,
        "stage0_server",
    )
    run("P12", "试跑脚本存在", (ROOT / "scripts/run_stage3_trial.py").exists(), "run_stage3_trial.py")

    # --- 试跑产物 ---
    story_md = OUT / "requirement-story.md"
    stories_json = OUT / "stories.json"
    run("T01", "requirement-story.md 存在", story_md.exists(), "output/")
    story_text = story_md.read_text(encoding="utf-8") if story_md.exists() else ""
    run(
        "T02",
        "故事含全局故事/原文摘录",
        "全局故事" in story_text and "原文摘录" in story_text and len(story_text) > 200,
        f"{len(story_text)} 字",
    )
    run("T03", "stories.json 存在", stories_json.exists(), "output/")

    journal = JOURNAL.read_text(encoding="utf-8") if JOURNAL.exists() else ""
    payload = {}
    stories = []
    if stories_json.exists():
        try:
            payload = json.loads(stories_json.read_text(encoding="utf-8"))
            stories = payload.get("stories") or []
            run("T04", "stories.json 可解析", True, f"{len(stories)} 条")
        except json.JSONDecodeError as e:
            run("T04", "stories.json 可解析", False, str(e))

    fab = 0
    fmt = 0
    for s in stories:
        q = (s.get("source_quote") or "").strip()
        if not q or q not in journal:
            fab += 1
        if not (s.get("text") or "").startswith("用户要"):
            fmt += 1
    run("T05", "编造条数=0", fab == 0 and len(stories) > 0, f"fab={fab}, n={len(stories)}")
    run("T06", "text 均以「用户要」开头", fmt == 0 and len(stories) > 0, f"fmt={fmt}")
    run(
        "T07",
        "每条有 level",
        all(s.get("level") in {"activity", "task", "story"} for s in stories) and len(stories) > 0,
        "activity|task|story",
    )

    # 文档
    run("D01", "阶段3实现报告", (ROOT / "docs/阶段3/阶段3实现报告.md").exists(), "docs/阶段3/")
    run("D02", "阶段3快速验收清单", (ROOT / "docs/阶段3/阶段3快速验收清单.md").exists(), "docs/阶段3/")
    run(
        "D03",
        "阶段3自测工作流说明",
        (ROOT / "docs/阶段3/阶段3自测工作流说明.md").exists(),
        "docs/阶段3/",
    )

    print(f"\n合计: {len(results)} 项, 失败 {failed}")

    if args.write_report:
        lines = [
            "# 阶段 3 提示词自测报告",
            "",
            f"**生成时间：** {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %z')}",
            f"**结果：** {'全部通过' if failed == 0 else f'{failed} 项未通过'}",
            "",
            "> 提示词定稿 + 试跑产物（编造/句式）+ 执行器读 prompt；不要求句覆盖率 100%（阶段 5）。",
            "",
            "| ID | 检查项 | 结果 | 说明 |",
            "|----|--------|------|------|",
        ]
        for r in results:
            lines.append(f"| {r['id']} | {r['name']} | {'✓' if r['ok'] else '✗'} | {r['detail']} |")
        lines.append("")
        lines.append("由 `python scripts/verify_stage3.py --write-report` 生成。")
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text("\n".join(lines), encoding="utf-8")
        print(f"已写入: {args.write_report}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
