#!/usr/bin/env python3
"""阶段 3 试跑：用定稿提示词跑 Step1 → Step2，写入 case-01/output/。

用法（仓库根或 project 目录均可）：
  python scripts/run_stage3_trial.py
  python scripts/run_stage3_trial.py --skip-step1   # 已有 requirement-story.md 时只跑 Step2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
CASE = PROJECT / "trials" / "case-01"
PROMPTS = PROJECT / "product-requirement" / "prompts"
OUT = CASE / "output"
JOURNAL = CASE / "input" / "journal-official-full.md"

sys.path.insert(0, str(PROJECT))
from llm_config import get_model, make_client, provider_summary  # noqa: E402


def strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|markdown|md)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def fill(template: str, **kw: str) -> str:
    out = template
    for k, v in kw.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def chat(client, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=get_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "按用户提示词输出产物。禁止编造原文没有的需求。"
                    "若要求 JSON，只输出可被 json.loads 的内容。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=8192,
    )
    return resp.choices[0].message.content or ""


def extract_json_object(text: str) -> dict:
    raw = strip_fence(text)
    start = raw.find("{")
    if start < 0:
        # 仅数组时包一层
        a = raw.find("[")
        if a >= 0:
            arr = json.loads(raw[a : raw.rfind("]") + 1])
            return {"meta": {"loop": "product-requirement", "round": 1}, "stories": arr, "coverage": {}}
        raise RuntimeError(f"无 JSON 对象: {raw[:200]}")
    dec = json.JSONDecoder()
    obj, _ = dec.raw_decode(raw, start)
    if not isinstance(obj, dict):
        raise RuntimeError("顶层须为 JSON 对象")
    if "stories" not in obj and isinstance(obj.get("data"), list):
        obj = {"stories": obj["data"], **{k: v for k, v in obj.items() if k != "data"}}
    return obj


def normalize_stories(payload: dict, journal: str) -> dict:
    stories = payload.get("stories") or []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fixed = []
    for i, s in enumerate(stories):
        if not isinstance(s, dict):
            continue
        text = (s.get("text") or "").strip()
        if text and not text.startswith("用户要"):
            text = "用户要" + text.lstrip("：: ")
        quote = (s.get("source_quote") or "").strip().replace("……", "").replace("…", "")
        if quote and quote not in journal:
            # 丢弃无法在原文定位的条目（阶段 3 宁缺毋滥）
            print(f"  drop story[{i}]: source_quote 不在原文")
            continue
        if not quote:
            print(f"  drop story[{i}]: 无 source_quote")
            continue
        item = {
            "id": s.get("id") or f"s{i + 1}",
            "level": s.get("level") if s.get("level") in {"activity", "task", "story"} else "task",
            "text": text,
            "source_quote": quote,
            "reason": s.get("reason") or "来自日志语义",
            "confidence": float(s.get("confidence") or 0.8),
            "approved": False,
            "revisions": s.get("revisions")
            or [{"round": 1, "action": "created", "at": now}],
        }
        fixed.append(item)
    for i, item in enumerate(fixed):
        item["id"] = f"s{i + 1}"
    payload["stories"] = fixed
    payload.setdefault("meta", {})
    payload["meta"].setdefault("loop", "product-requirement")
    payload["meta"].setdefault("source_file", "input/journal-official-full.md")
    payload["meta"]["round"] = 1
    payload["meta"]["trial"] = "stage3"
    # 粗算覆盖（供人工看；严格 100% 留给阶段 5）
    sentences = [x.strip() for x in re.split(r"(?<=[。！？\n])", journal) if len(x.strip()) >= 4]
    quotes = [s["source_quote"] for s in fixed if s.get("source_quote")]
    covered = sum(1 for sent in sentences if any(q in sent or sent in q for q in quotes))
    rate = (covered / len(sentences)) if sentences else 1.0
    uncovered = [sent for sent in sentences if not any(q in sent or sent in q for q in quotes)]
    payload["coverage"] = {
        "total_sentences": len(sentences),
        "covered_sentences": covered,
        "coverage_rate": round(rate, 4),
        "uncovered": uncovered[:30],
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-step1", action="store_true")
    args = parser.parse_args()

    if not JOURNAL.exists():
        raise SystemExit(f"缺少 {JOURNAL}")
    journal = JOURNAL.read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)

    print(f"LLM: {provider_summary()}")
    client = make_client()

    story_path = OUT / "requirement-story.md"
    if not args.skip_step1:
        t1 = (PROMPTS / "step1-story.md").read_text(encoding="utf-8")
        print(">>> Step1 整理需求故事 …")
        md = strip_fence(chat(client, fill(t1, JOURNAL_RAW=journal)))
        if "全局故事" not in md and "# 需求故事" not in md:
            md = "# 需求故事\n\n## 全局故事（一件事）\n" + md
        story_path.write_text(md, encoding="utf-8")
        print(f"已写 {story_path.relative_to(ROOT)} ({len(md)} 字)")
    else:
        if not story_path.exists():
            raise SystemExit("无 requirement-story.md，不能 --skip-step1")
        print(f"跳过 Step1，使用已有 {story_path.name}")

    story_md = story_path.read_text(encoding="utf-8")
    t2 = (PROMPTS / "step2-json.md").read_text(encoding="utf-8")
    print(">>> Step2 提取用户故事 JSON …")
    raw = chat(client, fill(t2, REQUIREMENT_STORY=story_md, JOURNAL_RAW=journal))
    payload = normalize_stories(extract_json_object(raw), journal)
    stories_path = OUT / "stories.json"
    stories_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写 {stories_path.relative_to(ROOT)} ({len(payload['stories'])} 条)")

    # 阶段 3：盯编造 + 句式（覆盖率提示但不作为本脚本失败条件）
    fab = []
    fmt = []
    for i, s in enumerate(payload["stories"]):
        q = s.get("source_quote") or ""
        if not q or q not in journal:
            fab.append(i)
        if not (s.get("text") or "").startswith("用户要"):
            fmt.append(i)
    print(f"编造嫌疑条数: {len(fab)}  句式问题: {len(fmt)}")
    print(f"句覆盖率(粗算): {payload['coverage']['coverage_rate']:.0%}")
    if fab or fmt:
        print("提示: 可再跑本脚本，或微调 prompts 后重试")
        return 1
    print("阶段 3 试跑：编造=0 且句式 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
