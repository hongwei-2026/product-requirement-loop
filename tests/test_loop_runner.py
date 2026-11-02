"""loop_runner：闭环入口的纯函数与产物规范化（不调 LLM）。"""

import json
from pathlib import Path

import pytest

from product_requirement_loop import loop_runner as lr


def test_strip_fence_removes_markdown_wrapper():
    raw = "```json\n{\"stories\": []}\n```"
    assert lr.strip_fence(raw) == '{"stories": []}'


def test_parse_feedback_ok_revise_unlock():
    assert lr.parse_feedback("ok")["kind"] == "ok"
    assert lr.parse_feedback("通过:没问题")["kind"] == "ok"
    assert lr.parse_feedback("通过:没问题")["reason"] == "没问题"

    rev = lr.parse_feedback("revise:编造:多写了登录")
    assert rev["kind"] == "revise"
    assert rev["code"] == "编造"
    assert "登录" in rev["comment"]

    assert lr.parse_feedback("unlock:step1")["kind"] == "unlock"
    assert lr.parse_feedback("漏了某某")["kind"] == "revise"
    assert lr.parse_feedback("漏了某某")["code"] == "漏了"


def test_extract_json_object_repairs_fenced_and_trailing_comma():
    raw = '```json\n{"stories": [{"text": "x", "source_quote": "abcdefghijklmn"}],}\n```'
    obj = lr.extract_json_object(raw)
    assert "stories" in obj
    assert isinstance(obj["stories"], list)


def test_extract_json_object_raises_on_garbage():
    with pytest.raises(RuntimeError, match="无法解析"):
        lr.extract_json_object("这不是 JSON {{{")


def test_step1_structure_ok_requires_all_sections():
    good = "\n".join(["全局故事", "背景", "要做什么", "明确不做", "待确认", "原文摘录"])
    assert lr._step1_structure_ok(good) is True
    assert lr._step1_structure_ok("只有全局故事") is False


def test_normalize_stories_keeps_quotes_in_journal_and_prefixes_text():
    journal = "用户需要导出报表。管理员可配置字段。"
    payload = {
        "stories": [
            {
                "text": "导出报表",
                "source_quote": "用户需要导出报表。",
                "level": "task",
                "confidence": 0.9,
            },
            {
                "text": "编造的一条",
                "source_quote": "原文里根本没有这段话xxxxx",
                "level": "task",
            },
        ]
    }
    out = lr.normalize_stories(payload, journal)
    assert len(out["stories"]) == 1
    assert out["stories"][0]["text"].startswith("用户要")
    assert out["stories"][0]["source_quote"] == "用户需要导出报表。"
    assert "coverage" in out


def test_lock_step1_copies_story(tmp_path: Path):
    out = tmp_path / "output"
    out.mkdir()
    src = out / "requirement-story.md"
    src.write_text("# 故事\n全局故事\n", encoding="utf-8")
    dest = lr.lock_step1(tmp_path)
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    assert dest.parent.name == "locked"
