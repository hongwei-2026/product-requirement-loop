#!/usr/bin/env python3
"""Web 驱动的 product-requirement 闭环会话（交付级）。"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from check import (  # noqa: E402
    check_accepted,
    check_coverage,
    check_fabrication,
    check_text_format,
)
from loop_runner import (  # noqa: E402
    STEP1,
    STEP2,
    STEP3,
    ProductRequirementLoop,
    lock_step1,
    now_iso,
    parse_feedback,
)
from llm_config import make_client, provider_summary  # noqa: E402
try:
    from journal_store import read_journal  # noqa: E402
    from audit_store import (  # noqa: E402
        append_event,
        approval_status,
        fingerprint,
        list_events,
        register_approved,
    )
    from review_queue import load_artifacts, mark_done, mark_opened, human_openable_statuses  # noqa: E402
except ImportError:  # when imported as project.web.loop_session
    from web.journal_store import read_journal  # noqa: E402
    from web.audit_store import (  # noqa: E402
        append_event,
        approval_status,
        fingerprint,
        list_events,
        register_approved,
    )
    from web.review_queue import load_artifacts, mark_done, mark_opened, human_openable_statuses  # noqa: E402

_lock = threading.Lock()


class LoopWebSession:
    """单 case 会话；逐步 API 驱动 loop_runner。"""

    def __init__(self, task_dir: Path):
        self.task_dir = task_dir.resolve()
        self.out = self.task_dir / "output"
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "locked").mkdir(parents=True, exist_ok=True)
        self.journal_id: str | None = None
        self.journal_meta: dict = {}
        self.journal_path = self._resolve_journal()
        self.journal = self.journal_path.read_text(encoding="utf-8")
        self.excerpt: str = self._load_excerpt()
        self.client = None
        self.loop: ProductRequirementLoop | None = None
        self.busy = False
        self.last_error: str | None = None
        self.queue_item_id: str | None = None
        self.current_user: dict | None = None
        self._load_session_meta()

    def _session_path(self) -> Path:
        return self.out / "session.json"

    def _step2_marker(self) -> Path:
        return self.out / "locked" / "step2-approved.json"

    def _save_session_meta(self) -> None:
        payload = {
            "journal_id": self.journal_id,
            "journal_meta": self.journal_meta,
            "history": (self.loop.history if self.loop else []),
            "metrics": (self.loop.metrics if self.loop else {}),
        }
        self._session_path().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load_session_meta(self) -> None:
        path = self._session_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.journal_id = data.get("journal_id") or self.journal_id
            self.journal_meta = data.get("journal_meta") or self.journal_meta
        except Exception:
            pass
        # 若当前选的是摘录，启动时自动改用同日全文做对比
        if self.journal_id:
            try:
                data = read_journal(self.journal_id)
                if data.get("meta", {}).get("has_full"):
                    active = self.task_dir / "input" / "active-journal.md"
                    excerpt_path = self.task_dir / "input" / "active-excerpt.md"
                    active.write_text(data["content"], encoding="utf-8")
                    self.journal_path = active
                    self.journal = data["content"]
                    self.excerpt = (data.get("excerpt") or "").strip()
                    self.journal_meta = data.get("meta") or self.journal_meta
                    if self.excerpt:
                        excerpt_path.write_text(self.excerpt, encoding="utf-8")
                    self._save_session_meta()
            except Exception:
                pass

    def _load_excerpt(self) -> str:
        p = self.task_dir / "input" / "active-excerpt.md"
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
        return ""

    def _resolve_journal(self) -> Path:
        active = self.task_dir / "input" / "active-journal.md"
        if active.exists():
            return active
        for name in ("journal-official-full.md", "journal-raw.md"):
            p = self.task_dir / "input" / name
            if p.exists():
                return p
        raise FileNotFoundError("找不到 input/journal-official-full.md")

    def select_journal(self, journal_id: str, reset_outputs: bool = True) -> dict:
        with _lock:
            if self.busy:
                return {"ok": False, "error": "系统正忙，请稍候再切换日志"}
            data = read_journal(journal_id)
            active = self.task_dir / "input" / "active-journal.md"
            excerpt_path = self.task_dir / "input" / "active-excerpt.md"
            active.parent.mkdir(parents=True, exist_ok=True)
            # 对比与闭环一律写全文（若有）；摘要另存
            active.write_text(data["content"], encoding="utf-8")
            excerpt = (data.get("excerpt") or "").strip()
            if excerpt:
                excerpt_path.write_text(excerpt, encoding="utf-8")
            elif excerpt_path.exists():
                excerpt_path.unlink()
            self.journal_path = active
            self.journal = data["content"]
            self.excerpt = excerpt
            self.journal_id = journal_id
            self.journal_meta = data.get("meta") or {}
            self.loop = None
            self.client = None
            self.queue_item_id = None
            approval = approval_status(journal_id, data["content"])
            if reset_outputs:
                self._reset_outputs(keep_locked=False)
            self._save_session_meta()
            msg = f"已切换日志：{self.journal_meta.get('title') or journal_id}"
            if self.journal_meta.get("has_full") and excerpt:
                msg += f"（左侧对比用全文 {len(self.journal)} 字；摘要另栏展示）"
            if approval["status"] == "approved":
                msg += "（该日志已在定稿档案；如需重做请确认「强制复审」）"
            elif approval["status"] == "stale":
                msg += "（定稿档案与当前原文不一致，建议复审）"
            return {
                "ok": True,
                "id": journal_id,
                "meta": self.journal_meta,
                "chars": len(self.journal),
                "excerpt_chars": len(excerpt),
                "excerpt": excerpt,
                "phase": self._infer_phase(),
                "approval": approval,
                "message": msg,
            }

    def _reset_outputs(self, keep_locked: bool = False) -> None:
        for name in (
            "requirement-story.md",
            "stories.json",
            "accepted.json",
            "uncovered.md",
            "session.json",
        ):
            p = self.out / name
            if p.exists():
                p.unlink()
        if not keep_locked:
            locked_dir = self.out / "locked"
            if locked_dir.exists():
                for p in locked_dir.glob("*"):
                    if p.is_file():
                        p.unlink()
        self.loop = None
        self.client = None
        self.last_error = None

    def reset(self, keep_locked: bool = False) -> dict:
        with _lock:
            if self.busy:
                return {"ok": False, "error": "系统正忙，请稍候再重置"}
            self.busy = True
            try:
                jid, jmeta = self.journal_id, self.journal_meta
                self._reset_outputs(keep_locked=keep_locked)
                self.journal_id, self.journal_meta = jid, jmeta
                self._save_session_meta()
                return {"ok": True, "phase": "idle", "message": "已清空本轮产物，可从 Step1 重新开始"}
            except Exception as e:
                self.last_error = str(e)
                return {"ok": False, "error": str(e)}
            finally:
                self.busy = False

    def _ensure_loop(self) -> ProductRequirementLoop:
        if self.loop is None:
            self.loop = ProductRequirementLoop(self.task_dir, self.journal, self._client())
            locked = self.out / "locked" / "step1-requirement-story.md"
            if locked.exists():
                self.loop.step1_locked = True
        return self.loop

    def _client(self):
        if self.client is None:
            self.client = make_client()
        return self.client

    def _story_path(self) -> Path:
        return self.out / "requirement-story.md"

    def _stories_path(self) -> Path:
        return self.out / "stories.json"

    def _accepted_path(self) -> Path:
        return self.out / "accepted.json"

    def _infer_phase(self) -> str:
        if self._accepted_path().exists():
            return "done"
        locked = (self.out / "locked" / "step1-requirement-story.md").exists()
        has_story = self._story_path().exists()
        has_stories = self._stories_path().exists()
        # Step2/定稿必须以 Step1 锁定为前提；解锁后即使 stories.json 残留也不再停在 Step2
        if locked and self._step2_marker().exists() and has_stories:
            return "step3_ready"
        if locked and has_stories:
            return "step2_review"
        if locked and has_story:
            return "step2_ready"
        if has_story:
            return "step1_review"
        return "idle"

    def state(self) -> dict:
        loop = self.loop
        metrics = loop.metrics if loop else {}
        history = loop.history if loop else []
        locked = (self.out / "locked" / "step1-requirement-story.md").exists()
        phase = self._infer_phase()

        story_md = ""
        if self._story_path().exists():
            story_md = self._story_path().read_text(encoding="utf-8")

        stories_payload = None
        if self._stories_path().exists():
            stories_payload = json.loads(self._stories_path().read_text(encoding="utf-8"))

        accepted_payload = None
        if self._accepted_path().exists():
            accepted_payload = json.loads(self._accepted_path().read_text(encoding="utf-8"))

        return {
            "ok": True,
            "task_dir": str(self.task_dir.relative_to(PROJECT_DIR.parent)),
            "phase": phase,
            "busy": self.busy,
            "last_error": self.last_error,
            "llm": provider_summary(),
            "journal_chars": len(self.journal),
            "journal_path": str(self.journal_path.relative_to(self.task_dir)),
            "journal_id": self.journal_id,
            "journal_meta": self.journal_meta,
            "excerpt": self.excerpt,
            "excerpt_chars": len(self.excerpt or ""),
            "step1_locked": locked,
            "metrics": metrics,
            "history": history,
            "audit_timeline": list_events(journal_id=self.journal_id, limit=80),
            "approval": approval_status(self.journal_id or "", self.journal) if self.journal_id else {"status": "new", "label": "未选日志"},
            "queue_item_id": self.queue_item_id,
            "artifacts": {
                "requirement_story": story_md,
                "stories": stories_payload,
                "accepted": accepted_payload,
            },
            "questions": {
                "step1": "故事是否读得通？通过时请写通过理由；打叉请写原因。",
                "step2": "有无多余、遗漏或分层错误？通过/打叉都要写人话理由。",
                "step3": "输入定稿人姓名后生成 accepted.json 并写入定稿档案",
            },
        }

    def run_step1(self, revise_note: str = "") -> dict:
        with _lock:
            if self.busy:
                return {"ok": False, "error": "系统正忙，请稍候"}
            self.busy = True
            self.last_error = None
            try:
                # 重跑 Step1 时清掉 Step2 通过标记
                if self._step2_marker().exists():
                    self._step2_marker().unlink()
                loop = self._ensure_loop()
                path = loop.run_step1(revise_note=revise_note)
                content = path.read_text(encoding="utf-8")
                self._save_session_meta()
                return {
                    "ok": True,
                    "step": STEP1,
                    "phase": "step1_review",
                    "content": content,
                    "path": str(path.relative_to(self.task_dir)),
                }
            except Exception as e:
                self.last_error = str(e)
                return {"ok": False, "error": str(e)}
            finally:
                self.busy = False

    def run_step2(self, revise_note: str = "") -> dict:
        with _lock:
            if self.busy:
                return {"ok": False, "error": "系统正忙，请稍候"}
            self.busy = True
            self.last_error = None
            try:
                loop = self._ensure_loop()
                if not loop.step1_locked and not (self.out / "locked" / "step1-requirement-story.md").exists():
                    return {"ok": False, "error": "请先通过 Step1 并锁定，再运行 Step2"}
                if self._step2_marker().exists():
                    self._step2_marker().unlink()
                path = loop.run_step2(revise_note=revise_note)
                payload = json.loads(path.read_text(encoding="utf-8"))
                stories = payload.get("stories") or []
                if not stories:
                    return {
                        "ok": False,
                        "error": "Step2 未抽出任何有效故事（可能 source_quote 对不上原文）。请打叉重跑或换日志。",
                    }
                # 队列项：同步 Step2 产物，等人审 Step2（仍不自动定稿）
                if self.queue_item_id:
                    try:
                        from review_queue import _update_item  # noqa: E402

                        qdir = PROJECT_DIR / "data" / "queue_items" / self.queue_item_id
                        qdir.mkdir(parents=True, exist_ok=True)
                        (qdir / "stories.json").write_text(
                            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                        )
                        _update_item(
                            self.queue_item_id,
                            status="pending_step2",
                            phase="step2",
                            story_count=len(stories),
                        )
                    except Exception:
                        pass
                self._save_session_meta()
                return {
                    "ok": True,
                    "step": STEP2,
                    "phase": "step2_review",
                    "stories": payload,
                    "path": str(path.relative_to(self.task_dir)),
                    "count": len(stories),
                    "message": f"Step2 已抽出 {len(stories)} 条，请人审。可随时「解锁 Step1」回到故事层。",
                }
            except Exception as e:
                self.last_error = str(e)
                return {"ok": False, "error": str(e)}
            finally:
                self.busy = False

    def submit_feedback(self, step: str, raw: str, actor: str = "", user_id: int | None = None) -> dict:
        with _lock:
            if self.busy:
                return {"ok": False, "error": "系统正忙，请稍候"}
            self.busy = True
            self.last_error = None
            try:
                fb = parse_feedback(raw)
                if fb["kind"] == "ok" and not (fb.get("reason") or "").strip():
                    return {
                        "ok": False,
                        "error": "通过时请填写通过理由（格式：ok:理由），便于事后回溯",
                    }
                if fb["kind"] == "revise" and not (fb.get("comment") or "").strip():
                    return {"ok": False, "error": "打叉时请填写原因"}
                who = (actor or "").strip() or "审核人"
                loop = self._ensure_loop()
                loop.metrics["feedback_triggered"] += 1
                loop.metrics["rounds"] += 1
                loop.history.append(f"{step}:{raw}")

                # unlock 始终走 Step1 处理，避免前端 step 传成 Step2 时没反应
                if fb["kind"] == "unlock":
                    result = self._feedback_step1(loop, fb, raw, who)
                elif step == STEP1:
                    result = self._feedback_step1(loop, fb, raw, who)
                elif step == STEP2:
                    result = self._feedback_step2(loop, fb, raw, who)
                else:
                    result = {"ok": False, "error": f"未知步骤: {step}"}
                self._save_session_meta()
                if result.get("ok"):
                    result["audit_timeline"] = list_events(journal_id=self.journal_id, limit=40)
                return result
            except Exception as e:
                self.last_error = str(e)
                return {"ok": False, "error": str(e)}
            finally:
                self.busy = False

    def set_current_user(self, user: dict | None) -> None:
        self.current_user = user

    def _audit(self, *, actor: str, step: str, action: str, reason: str = "", code: str | None = None, artifact: dict | None = None, phase_after: str | None = None, user_id: int | None = None) -> dict:
        uid = user_id
        if uid is None and self.current_user:
            uid = self.current_user.get("id")
        who = actor
        if (not who or who in ("审核人", "未署名")) and self.current_user:
            who = self.current_user.get("display_name") or self.current_user.get("username") or who
        return append_event(
            actor=who,
            user_id=uid,
            journal_id=self.journal_id,
            journal_title=(self.journal_meta or {}).get("title"),
            journal_fingerprint=fingerprint(self.journal),
            step=step,
            action=action,
            reason=reason,
            code=code,
            artifact=artifact,
            phase_after=phase_after,
        )

    def _feedback_step1(self, loop: ProductRequirementLoop, fb: dict, raw: str, actor: str) -> dict:
        if fb["kind"] == "unlock":
            loop.step1_locked = False
            # 彻底清掉 Step1 锁 + Step2 产物，避免界面仍停在 Step2
            for p in (
                self.out / "locked" / "step1-requirement-story.md",
                self._step2_marker(),
                self._stories_path(),
                self.out / "uncovered.md",
            ):
                try:
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass
            # 队列副本里的 Step2 一并清掉，防止再次打开又带回来
            if self.queue_item_id:
                try:
                    from review_queue import _update_item  # noqa: E402

                    qdir = PROJECT_DIR / "data" / "queue_items" / self.queue_item_id
                    qs = qdir / "stories.json"
                    if qs.exists():
                        qs.unlink()
                    qout = qdir / "output" / "stories.json"
                    if qout.exists():
                        qout.unlink()
                    _update_item(self.queue_item_id, status="pending_step1", phase="step1", story_count=0)
                except Exception:
                    pass
            self.loop = None  # 丢掉内存中的 loop，避免旧状态
            evt = self._audit(actor=actor, step=STEP1, action="unlock", reason="解锁 Step1 以便重做", phase_after="step1_review")
            return {
                "ok": True,
                "action": "unlock",
                "phase": "step1_review",
                "message": "Step1 已解锁，已撤掉 Step2 草稿。请重新确认需求故事。",
                "event": evt,
            }

        if fb["kind"] == "ok":
            lock_step1(self.task_dir)
            loop.step1_locked = True
            reason = fb.get("reason") or ""
            evt = self._audit(
                actor=actor,
                step=STEP1,
                action="ok",
                reason=reason,
                artifact={"locked": "output/locked/step1-requirement-story.md"},
                phase_after="step2_ready",
            )
            # 队列来的：只标记 Step1 已通过，绝不自动跑 Step2（人要自己点「运行 Step2」，也可先解锁 Step1）
            if self.queue_item_id:
                from review_queue import _update_item  # noqa: E402

                try:
                    _update_item(self.queue_item_id, status="step1_passed", phase="step1_passed")
                except Exception:
                    pass
                try:
                    qdir = PROJECT_DIR / "data" / "queue_items" / self.queue_item_id
                    qdir.mkdir(parents=True, exist_ok=True)
                    if self._story_path().exists():
                        (qdir / "requirement-story.md").write_text(
                            self._story_path().read_text(encoding="utf-8"), encoding="utf-8"
                        )
                except Exception:
                    pass
            return {
                "ok": True,
                "action": "ok",
                "phase": "step2_ready",
                "locked_path": "output/locked/step1-requirement-story.md",
                "message": "Step1 已通过并锁定。下一步请你自己点「运行 Step2」；若要改 Step1，先点「解锁 Step1」。",
                "event": evt,
            }

        note = f"{fb.get('code')}: {fb.get('comment')}"
        loop.metrics["corrections"] += 1
        loop.metrics["rework"] += 1
        loop.revisions_log.append(
            {
                "step": STEP1,
                "round": loop.metrics["rounds"],
                "action": "revised",
                "code": fb.get("code"),
                "comment": fb.get("comment"),
                "raw": raw,
                "at": now_iso(),
            }
        )
        path = loop.run_step1(revise_note=note)
        content = path.read_text(encoding="utf-8")
        evt = self._audit(
            actor=actor,
            step=STEP1,
            action="revise",
            reason=fb.get("comment") or "",
            code=fb.get("code"),
            artifact={"path": str(path.relative_to(self.task_dir))},
            phase_after="step1_review",
        )
        return {
            "ok": True,
            "step": STEP1,
            "phase": "step1_review",
            "content": content,
            "path": str(path.relative_to(self.task_dir)),
            "message": "已按反馈重跑 Step1",
            "event": evt,
        }

    def _feedback_step2(self, loop: ProductRequirementLoop, fb: dict, raw: str, actor: str) -> dict:
        if fb["kind"] == "ok":
            (self.out / "locked").mkdir(parents=True, exist_ok=True)
            reason = fb.get("reason") or ""
            self._step2_marker().write_text(
                json.dumps({"approved": True, "raw": raw, "reason": reason, "actor": actor}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            count = 0
            if self._stories_path().exists():
                count = len(json.loads(self._stories_path().read_text(encoding="utf-8")).get("stories") or [])
            evt = self._audit(
                actor=actor,
                step=STEP2,
                action="ok",
                reason=reason,
                artifact={"story_count": count},
                phase_after="step3_ready",
            )
            return {
                "ok": True,
                "action": "ok",
                "phase": "step3_ready",
                "message": "Step2 已通过，请进入 Step3：填写定稿人并点「生成定稿并归档」（不会自动归档）",
                "event": evt,
            }

        note = f"{fb.get('code')}: {fb.get('comment')}"
        loop.metrics["corrections"] += 1
        loop.metrics["rework"] += 1
        loop.revisions_log.append(
            {
                "step": STEP2,
                "round": loop.metrics["rounds"],
                "action": "revised",
                "code": fb.get("code"),
                "comment": fb.get("comment"),
                "raw": raw,
                "at": now_iso(),
            }
        )
        if self._step2_marker().exists():
            self._step2_marker().unlink()
        path = loop.run_step2(revise_note=note)
        payload = json.loads(path.read_text(encoding="utf-8"))
        stories = payload.get("stories") or []
        if not stories:
            return {
                "ok": False,
                "error": "重跑后仍无有效故事，请换原因或换日志",
            }
        evt = self._audit(
            actor=actor,
            step=STEP2,
            action="revise",
            reason=fb.get("comment") or "",
            code=fb.get("code"),
            artifact={"story_count": len(stories)},
            phase_after="step2_review",
        )
        return {
            "ok": True,
            "step": STEP2,
            "phase": "step2_review",
            "stories": payload,
            "path": str(path.relative_to(self.task_dir)),
            "count": len(stories),
            "message": "已按反馈重跑 Step2",
            "event": evt,
        }

    def finalize(self, approver: str, note: str = "") -> dict:
        with _lock:
            if self.busy:
                return {"ok": False, "error": "系统正忙，请稍候"}
            self.busy = True
            self.last_error = None
            try:
                loop = self._ensure_loop()
                if not self._stories_path().exists():
                    return {"ok": False, "error": "缺少 stories.json，请先完成 Step2"}
                if not self._step2_marker().exists() and self._infer_phase() not in ("step3_ready", "done"):
                    return {"ok": False, "error": "请先在 Step2 点「通过」，再定稿"}
                name = (approver or "").strip()
                if not name:
                    return {"ok": False, "error": "请填写定稿人姓名"}
                loop.metrics["feedback_triggered"] += 1
                loop.history.append(f"{STEP3}:{name}")
                path = loop.finalize(name)
                payload = json.loads(path.read_text(encoding="utf-8"))
                meta = payload.setdefault("meta", {})
                meta["source_file"] = str(self.journal_path.relative_to(self.task_dir)).replace("\\", "/")
                meta["journal_id"] = self.journal_id
                if self.journal_meta:
                    meta["journal_title"] = self.journal_meta.get("title")
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                # 把 Step1 需求故事一并定稿保存，便于事后定位「故事层」错误
                if self._story_path().exists():
                    payload["requirement_story"] = self._story_path().read_text(encoding="utf-8")
                    locked = self.out / "locked" / "step1-requirement-story.md"
                    if locked.exists():
                        payload["requirement_story_locked"] = locked.read_text(encoding="utf-8")
                    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                story_count = len(payload.get("stories") or [])
                reason = (note or "").strip() or f"定稿人 {name} 确认归档"
                evt = self._audit(
                    actor=name,
                    step=STEP3,
                    action="finalize",
                    reason=reason,
                    artifact={
                        "accepted_path": str(path.relative_to(self.task_dir)).replace("\\", "/"),
                        "story_count": story_count,
                        "has_requirement_story": bool(payload.get("requirement_story")),
                    },
                    phase_after="done",
                )
                reg = None
                if self.journal_id:
                    # 归档副本到 data/accepted/
                    archive_dir = PROJECT_DIR / "data" / "accepted"
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    archive_name = f"{self.journal_id}-{path.stat().st_mtime_ns}.json"
                    archive_path = archive_dir / archive_name
                    archive_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
                    rel_archive = str(archive_path.relative_to(PROJECT_DIR)).replace("\\", "/")
                    reg = register_approved(
                        journal_id=self.journal_id,
                        journal_title=(self.journal_meta or {}).get("title") or self.journal_id,
                        journal_fingerprint=fingerprint(self.journal),
                        approver=name,
                        approver_user_id=(self.current_user or {}).get("id"),
                        accepted_relpath=rel_archive,
                        story_count=story_count,
                        product=(self.journal_meta or {}).get("product"),
                        audit_event_id=evt.get("id"),
                        accepted_json=json.dumps(payload, ensure_ascii=False),
                    )
                if self.queue_item_id:
                    mark_done(self.queue_item_id)
                    self.queue_item_id = None
                self._save_session_meta()
                return {
                    "ok": True,
                    "step": STEP3,
                    "phase": "done",
                    "approver": name,
                    "accepted": payload,
                    "path": str(path.relative_to(self.task_dir)),
                    "event": evt,
                    "registry": reg,
                    "audit_timeline": list_events(journal_id=self.journal_id, limit=40),
                }
            except Exception as e:
                self.last_error = str(e)
                return {"ok": False, "error": str(e)}
            finally:
                self.busy = False

    def open_queue_item(self, item_id: str) -> dict:
        """从待人审队列加载到工作台。先认领，再载入 Step1/Step2 草稿。"""
        with _lock:
            if self.busy:
                return {"ok": False, "error": "系统正忙，请稍候"}
            from review_queue import claim_item, enrich_queue_item, get_item as rq_get  # local

            user = self.current_user
            claimed = claim_item(item_id, user)
            if not claimed.get("ok"):
                return claimed
            prior_status = claimed.get("prior_status") or ""
            data = load_artifacts(item_id)
            item = data["item"]
            if not (data.get("requirement_story") or "").strip():
                return {"ok": False, "error": "队列里还没有 Step1 需求故事（AI 可能失败）。请看失败原因后重试。"}
            jid = item["journal_id"]
            jdata = read_journal(jid)
            active = self.task_dir / "input" / "active-journal.md"
            active.write_text(jdata["content"], encoding="utf-8")
            self.journal_path = active
            self.journal = jdata["content"]
            self.journal_id = jid
            self.journal_meta = jdata.get("meta") or {}
            self.loop = None
            self.client = None
            self.queue_item_id = item_id
            self._reset_outputs(keep_locked=False)
            self._story_path().write_text(data["requirement_story"], encoding="utf-8")
            who = (claimed.get("item") or {}).get("assignee_name") or (
                (user or {}).get("display_name") or (user or {}).get("username") or "审核人"
            )
            phase = "step1_review"
            msg = (
                f"已认领并载入「{item.get('journal_title') or jid}」（审核人：{who}）。"
                f"请先审 Step1 需求故事（通过/打叉都要写理由）。"
            )
            has_stories = bool((data.get("stories") or {}).get("stories"))
            if prior_status == "step1_passed":
                locked = self.out / "locked"
                locked.mkdir(parents=True, exist_ok=True)
                (locked / "step1-requirement-story.md").write_text(
                    data["requirement_story"], encoding="utf-8"
                )
                phase = "step2_ready"
                msg = (
                    f"已由「{who}」继续。Step1 已通过并锁定。"
                    f"请自己点「运行 Step2」，或先「解锁 Step1」重审。"
                )
            elif prior_status in {"pending_step2", "pending_human", "in_review"} and has_stories:
                self._stories_path().write_text(
                    json.dumps(data["stories"], ensure_ascii=False, indent=2), encoding="utf-8"
                )
                locked = self.out / "locked"
                locked.mkdir(parents=True, exist_ok=True)
                (locked / "step1-requirement-story.md").write_text(
                    data["requirement_story"], encoding="utf-8"
                )
                phase = "step2_review"
                n = len(data["stories"].get("stories") or [])
                msg = f"已认领并载入 Step2 草稿（{n} 条），当前由「{who}」审核；可随时解锁 Step1。"
            self._save_session_meta()
            return {
                "ok": True,
                "phase": phase,
                "queue_item_id": item_id,
                "journal_id": jid,
                "message": msg,
                "claim": enrich_queue_item(rq_get(item_id) or item, user),
            }

    def run_check(self, target: str = "accepted", actor: str = "") -> dict:
        self.last_error = None
        source = self.journal
        errors: list[str] = []

        if target == "stories":
            path = self._stories_path()
            if not path.exists():
                return {"ok": False, "error": "stories.json 不存在"}
            payload = json.loads(path.read_text(encoding="utf-8"))
            stories = payload.get("stories") or []
            strict = False
        else:
            path = self._accepted_path()
            if not path.exists():
                return {"ok": False, "error": "accepted.json 不存在，请先定稿"}
            payload = json.loads(path.read_text(encoding="utf-8"))
            stories = payload.get("stories") or []
            strict = True

        errors.extend(check_fabrication(stories, source))
        errors.extend(check_text_format(stories))
        rate, uncovered = check_coverage(stories, source)
        warnings: list[str] = []

        if rate < 1.0:
            msg = f"句覆盖率 {rate:.0%} < 100%，未覆盖 {len(uncovered)} 句"
            if strict:
                # 定稿阶段由 check_accepted 看是否已写人工说明
                pass
            else:
                # 全文很长时覆盖率天然偏低：Step2 只作提示，不挡人审
                warnings.append(msg + "（提示：对照原文抽检即可，不作为本阶段硬门槛）")

        if strict:
            errors.extend(check_accepted(payload))

        fabrication = len([e for e in errors if "不在原文" in e or "缺少 source_quote" in e])
        passed = len(errors) == 0
        try:
            self._audit(
                actor=(actor or "").strip() or "系统",
                step="check",
                action="check",
                reason=(
                    "全部通过"
                    if passed and not warnings
                    else (
                        f"未通过 {len(errors)} 项：{errors[0]}"
                        if errors
                        else f"通过（有提示）：{warnings[0]}"
                    )
                ),
                artifact={"passed": passed, "error_count": len(errors), "warning_count": len(warnings)},
                phase_after=self._infer_phase(),
            )
        except Exception:
            pass
        return {
            "ok": passed,
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "story_count": len(stories),
                "fabrication_count": fabrication,
                "coverage_rate": round(rate, 4),
                "uncovered_count": len(uncovered),
            },
            "file": str(path.relative_to(self.task_dir)),
        }


_session: LoopWebSession | None = None


def get_session(task_dir: Path | None = None) -> LoopWebSession:
    global _session
    if _session is None:
        _session = LoopWebSession(task_dir or PROJECT_DIR / "trials" / "case-01")
    return _session


def reset_session(task_dir: Path | None = None, keep_locked: bool = False) -> dict:
    return get_session(task_dir).reset(keep_locked=keep_locked)
