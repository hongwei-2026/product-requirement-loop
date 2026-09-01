"""Smoke: two users claim exclusivity on queue items."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "project"))
sys.path.insert(0, str(ROOT / "project" / "web"))

from db import create_user, ensure_db, verify_login  # noqa: E402
from review_queue import (  # noqa: E402
    claim_item,
    clear_queue_for_tests,
    enrich_queue_item,
    inject_pending,
    list_queue_enriched,
)


def main() -> int:
    ensure_db()
    clear_queue_for_tests()
    # users
    try:
        u1 = create_user("claim_a", "pass1234", display_name="甲审员")
    except Exception:
        u1 = verify_login("claim_a", "pass1234")
    try:
        u2 = create_user("claim_b", "pass1234", display_name="乙审员")
    except Exception:
        u2 = verify_login("claim_b", "pass1234")
    assert u1 and u1.get("id")
    assert u2 and u2.get("id")

    inj = inject_pending(
        journal_id="custom-demo-j1",
        requirement_story="# 需求故事\n\n## 全局故事（一件事）\n测试认领\n",
        stories={"stories": []},
        actor="系统",
        journal_title="认领自测日志",
    )
    assert inj.get("ok"), inj
    qid = inj["item"]["id"]

    items = list_queue_enriched(user=u2, claim_filter="all")
    hit = next(x for x in items if x["id"] == qid)
    assert hit["claim_ownership"] == "unclaimed"
    assert hit["can_open"] is True

    c1 = claim_item(qid, u1)
    assert c1.get("ok"), c1
    assert c1["item"]["assignee_name"] == "甲审员"

    c2 = claim_item(qid, u2)
    assert not c2.get("ok"), c2
    assert "甲审员" in (c2.get("error") or "")

    mine = list_queue_enriched(user=u1, claim_filter="mine")
    assert any(x["id"] == qid for x in mine)
    others = list_queue_enriched(user=u2, claim_filter="others")
    assert any(x["id"] == qid for x in others)
    blocked = next(x for x in list_queue_enriched(user=u2) if x["id"] == qid)
    assert blocked["can_open"] is False
    assert "甲审员" in (blocked.get("claim_short") or blocked.get("claim_label") or "")

    # u1 can reopen
    c1b = claim_item(qid, u1)
    assert c1b.get("ok"), c1b

    print("OK claim exclusivity")
    print(json.dumps({"qid": qid, "u1": u1["id"], "u2": u2["id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
