"""review_queue：评审队列认领 / 取消 / 产物读写（不启后台 worker、不调 LLM）。"""

import json
from pathlib import Path

import pytest

from product_requirement_loop.web import review_queue as rq


@pytest.fixture
def queue_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data = tmp_path / "data"
    items = data / "queue_items"
    data.mkdir()
    items.mkdir()
    monkeypatch.setattr(rq, "DATA_DIR", data)
    monkeypatch.setattr(rq, "QUEUE_PATH", data / "review_queue.json")
    monkeypatch.setattr(rq, "ITEMS_DIR", items)
    monkeypatch.setattr(rq, "_ensure_worker", lambda: None)
    with rq._lock:
        rq._save({"version": 1, "items": []}, upsert_all=False)
    return tmp_path


def _user(uid: int = 1, name: str = "alice") -> dict:
    return {"id": uid, "username": name, "display_name": name}


def test_inject_pending_and_load_artifacts(queue_home: Path):
    res = rq.inject_pending(
        journal_id="j-demo",
        requirement_story="# 全局故事\n背景…",
        stories={"stories": [{"text": "用户要导出"}]},
        journal_title="演示日志",
    )
    assert res["ok"] is True
    item = res["item"]
    assert item["status"] == "pending_human"
    assert item["story_count"] == 1

    got = rq.get_item(item["id"])
    assert got is not None
    assert got["journal_id"] == "j-demo"

    arts = rq.load_artifacts(item["id"])
    assert "全局故事" in arts["requirement_story"]
    assert arts["stories"]["stories"][0]["text"] == "用户要导出"


def test_claim_ownership_and_enrich(queue_home: Path):
    item = rq.inject_pending(
        journal_id="j1",
        requirement_story="story",
        stories={"stories": []},
    )["item"]
    me = _user(1, "alice")
    other = _user(2, "bob")

    assert rq.claim_ownership(item, me) == "unclaimed"
    enriched = rq.enrich_queue_item(item, me)
    assert enriched["can_open"] is True
    assert enriched["claim_ownership"] == "unclaimed"

    claimed = rq.claim_item(item["id"], me)
    assert claimed["ok"] is True
    assert claimed["item"]["claim_ownership"] == "mine"
    assert claimed["item"]["status"] == "in_review"

    blocked = rq.claim_item(item["id"], other)
    assert blocked["ok"] is False
    assert blocked["claim_ownership"] == "others"


def test_cancel_item_releases_slot(queue_home: Path):
    item = rq.inject_pending(
        journal_id="j-cancel",
        requirement_story="s",
        stories={"stories": []},
    )["item"]
    me = _user()
    rq.claim_item(item["id"], me)

    cancelled = rq.cancel_item(item["id"], me, reason="不测了")
    assert cancelled["ok"] is True
    assert cancelled["item"]["status"] == "cancelled"

    # 已取消：同一 journal 可再 inject（不走 enqueue 占位检查也行，这里验状态）
    again = rq.get_item(item["id"])
    assert again["status"] == "cancelled"
    assert again.get("assignee_user_id") is None


def test_mark_done_and_cannot_cancel_done(queue_home: Path):
    item = rq.inject_pending(
        journal_id="j-done",
        requirement_story="s",
        stories={"stories": [{"text": "x"}]},
    )["item"]
    me = _user()
    rq.claim_item(item["id"], me)
    done = rq.mark_done(item["id"])
    assert done["status"] == "done"

    bad = rq.cancel_item(item["id"], me)
    assert bad["ok"] is False
    assert "定稿" in bad["error"]


def test_list_queue_enriched_claim_filter(queue_home: Path):
    a = rq.inject_pending(
        journal_id="ja", requirement_story="a", stories={"stories": []}
    )["item"]
    b = rq.inject_pending(
        journal_id="jb", requirement_story="b", stories={"stories": []}
    )["item"]
    me = _user(1, "alice")
    rq.claim_item(a["id"], me)

    mine = rq.list_queue_enriched(user=me, claim_filter="mine")
    unclaimed = rq.list_queue_enriched(user=me, claim_filter="unclaimed")
    assert {x["id"] for x in mine} == {a["id"]}
    assert {x["id"] for x in unclaimed} == {b["id"]}
    assert rq.actionable_pending_count(me) == 2
