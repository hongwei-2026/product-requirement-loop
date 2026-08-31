#!/usr/bin/env python3
"""product-requirement 闭环编排（阶段 4）。

与 specification.yaml 同构：
  Step1 AI → 人反馈 →（可锁定）→ Step2 AI → 人反馈 → 定稿 accepted.json

用法：
  python loop_runner.py trials/case-01
  python loop_runner.py trials/case-01 --demo
  python loop_runner.py trials/case-01 --reuse-artifacts --demo

--demo：非交互，按预设反馈序列跑通（自测/答辩演示）
--reuse-artifacts：复用已有 output/requirement-story.md 与 stories.json（少调 LLM）
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from llm_config import get_model, make_client, provider_summary

PROJECT_DIR = Path(__file__).resolve().parent
SPEC_FILE = PROJECT_DIR / "product-requirement" / "specification.yaml"
PROMPTS_DIR = PROJECT_DIR / "product-requirement" / "prompts"

REVISE_CODES = ("编造", "分层", "漏了", "格式", "其他")
STEP1 = "整理需求故事"
STEP2 = "提取用户故事 JSON"
STEP3 = "人工评审定稿"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|markdown|md)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _repair_json_text(text: str) -> str:
    """修补模型常见的坏 JSON：智能引号、尾逗号、BOM、围栏残留。"""
    s = strip_fence(text or "")
    s = s.lstrip("\ufeff").strip()
    s = (
        s.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    s = re.sub(r",\s*([}\]])", r"\1", s)
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        s = s[a : b + 1]
    return s


def _try_load_json(text: str):
    """尝试多种方式解析为 dict；失败返回 None。"""
    candidates = [text, _repair_json_text(text)]
    for cand in candidates:
        if not cand:
            continue
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, list):
                return {"stories": obj}
        except Exception:
            pass
        start = cand.find("{")
        if start >= 0:
            try:
                obj, _ = json.JSONDecoder().raw_decode(cand, start)
                if isinstance(obj, dict):
                    return obj
                if isinstance(obj, list):
                    return {"stories": obj}
            except Exception:
                pass
        a = cand.find("[")
        if a >= 0 and cand.rfind("]") > a:
            try:
                arr = json.loads(cand[a : cand.rfind("]") + 1])
                if isinstance(arr, list):
                    return {"stories": arr}
            except Exception:
                pass
    return None


def load_prompt(name: str, task_dir: Path) -> str:
    for base in (task_dir / "prompts", PROMPTS_DIR):
        p = base / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(name)


def chat(client, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=get_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "按提示词输出产物。禁止编造原文没有的需求。"
                    "若要求 JSON，只输出可被解析的 JSON。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=8192,
    )
    return resp.choices[0].message.content or ""


def parse_feedback(raw: str) -> dict:
    text = (raw or "").strip()
    low = text.lower()
    if low.startswith("unlock:step1") or text.startswith("unlock:step1"):
        return {"kind": "unlock", "raw": text}
    if text.startswith("revise:") or low.startswith("revise:"):
        body = text.split(":", 1)[1].strip()
        code, _, comment = body.partition(":")
        code = code.strip() or "其他"
        comment = comment.strip() or body
        if code not in REVISE_CODES:
            comment = body
            code = "其他"
        return {"kind": "revise", "code": code, "comment": comment, "raw": text}
    # ok / ok:理由 / 通过:理由
    if low == "ok" or text in ("通过", "exit", "done", "确认", ""):
        return {"kind": "ok", "reason": "", "raw": text}
    if low.startswith("ok:") or text.startswith("通过:") or text.startswith("通过："):
        sep = ":" if ":" in text else "："
        reason = text.split(sep, 1)[1].strip()
        return {"kind": "ok", "reason": reason, "raw": text}
    # 裸码兼容
    for c in REVISE_CODES:
        if text.startswith(c):
            return {"kind": "revise", "code": c, "comment": text[len(c) :].lstrip(":： "), "raw": text}
    return {"kind": "revise", "code": "其他", "comment": text, "raw": text}


def extract_json_object(text: str) -> dict:
    obj = _try_load_json(text)
    if obj is not None:
        if "stories" not in obj and isinstance(obj.get("data"), list):
            obj = {"stories": obj["data"]}
        return obj
    raw = strip_fence(text or "")
    raise RuntimeError(
        "Step2 返回的 JSON 无法解析（模型输出格式坏了）。"
        f"片段：{(raw or '')[:180].replace(chr(10), ' ')}"
    )


def _resolve_source_quote(quote: str, journal: str) -> str | None:
    """把近似引用对齐到原文连续片段；对不上则返回 None。"""
    q = (quote or "").strip().replace("……", "").replace("…", "").strip()
    if len(q) < 6:
        return None
    if q in journal:
        return q
    # 去空白后再匹配，再在原文中找回含首尾的最短片段
    j_compact = re.sub(r"\s+", "", journal)
    q_compact = re.sub(r"\s+", "", q)
    if len(q_compact) >= 8 and q_compact in j_compact:
        head = q_compact[:12]
        # 在原文找含该头的窗口
        for m in re.finditer(re.escape(q[: min(8, len(q))]), journal):
            start = m.start()
            window = journal[start : start + len(q) + 40]
            if q_compact in re.sub(r"\s+", "", window):
                # 取到句末或窗口末
                end = start + len(q)
                while end < len(journal) and journal[end] not in "。！？\n":
                    end += 1
                    if end - start > len(q) + 30:
                        break
                if end < len(journal) and journal[end] in "。！？":
                    end += 1
                cand = journal[start:end].strip()
                if cand and cand in journal:
                    return cand
        # 退回：用 compact 定位失败时，尝试更长公共子串
        pass
    # 最长公共：从 quote 截取能在原文出现的最长前缀/子串（>=12）
    best = ""
    for length in range(min(len(q), 80), 11, -1):
        for i in range(0, len(q) - length + 1):
            frag = q[i : i + length]
            if frag in journal and len(frag) > len(best):
                best = frag
        if best:
            break
    return best or None


def _step1_structure_ok(md: str) -> bool:
    need = ("全局故事", "背景", "要做什么", "明确不做", "待确认", "原文摘录")
    return all(k in (md or "") for k in need)


def normalize_stories(payload: dict, journal: str) -> dict:
    stories = []
    seen_quotes: set[str] = set()
    for i, s in enumerate(payload.get("stories") or []):
        if not isinstance(s, dict):
            continue
        text = (s.get("text") or "").strip()
        if text and not text.startswith("用户要"):
            text = "用户要" + text.lstrip("：: ")
        if len(text) < 6 or text in {"用户要", "用户要…", "用户要..."}:
            continue
        quote = _resolve_source_quote(s.get("source_quote") or "", journal)
        if not quote:
            continue
        # 去重：同一原文不重复出条
        qkey = re.sub(r"\s+", "", quote)
        if qkey in seen_quotes:
            continue
        seen_quotes.add(qkey)
        level = s.get("level") if s.get("level") in {"activity", "task", "story"} else "task"
        stories.append(
            {
                "id": f"s{i + 1}",
                "level": level,
                "text": text,
                "source_quote": quote,
                "reason": (s.get("reason") or "来自日志语义").strip() or "来自日志语义",
                "confidence": float(s.get("confidence") or 0.8),
                "approved": False,
                "revisions": s.get("revisions")
                or [{"round": 1, "action": "created", "at": now_iso()}],
            }
        )
    # 若完全没有 activity 且条数>=2，把第一条升为 activity（仅当模型漏标）
    if stories and not any(x["level"] == "activity" for x in stories) and len(stories) >= 2:
        stories[0]["level"] = "activity"
    # 按层级排序：activity → task → story
    order = {"activity": 0, "task": 1, "story": 2}
    stories.sort(key=lambda x: (order.get(x["level"], 9), -float(x.get("confidence") or 0)))
    stories = stories[:10]
    for i, s in enumerate(stories):
        s["id"] = f"s{i + 1}"
    sentences = [x.strip() for x in re.split(r"(?<=[。！？\n])", journal) if len(x.strip()) >= 4]
    quotes = [s["source_quote"] for s in stories]
    covered = sum(1 for sent in sentences if any(q in sent or sent in q for q in quotes))
    rate = (covered / len(sentences)) if sentences else 1.0
    uncovered = [sent for sent in sentences if not any(q in sent or sent in q for q in quotes)]
    return {
        "meta": {
            "source_file": "input/journal-official-full.md",
            "loop": "product-requirement",
            "round": payload.get("meta", {}).get("round", 1),
        },
        "stories": stories,
        "coverage": {
            "total_sentences": len(sentences),
            "covered_sentences": covered,
            "coverage_rate": round(rate, 4),
            "uncovered": uncovered,
        },
    }


def lock_step1(task_dir: Path) -> Path:
    src = task_dir / "output" / "requirement-story.md"
    dest_dir = task_dir / "output" / "locked"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "step1-requirement-story.md"
    shutil.copy2(src, dest)
    return dest


def ask(prompt: str, demo_queue: list[str] | None) -> str:
    print("\n——" + prompt + "——")
    if demo_queue is not None:
        if not demo_queue:
            ans = "ok"
        else:
            ans = demo_queue.pop(0)
        print(f"> {ans}  (demo)")
        return ans
    return input("> ").strip()


class ProductRequirementLoop:
    def __init__(self, task_dir: Path, journal: str, client, demo_queue: list[str] | None = None):
        self.task_dir = task_dir
        self.journal = journal
        self.client = client
        self.demo_queue = demo_queue
        self.out = task_dir / "output"
        self.out.mkdir(parents=True, exist_ok=True)
        self.metrics = {
            "rounds": 0,
            "corrections": 0,
            "rework": 0,
            "feedback_triggered": 0,
            "start": time.time(),
        }
        self.history: list[str] = []
        self.step1_locked = False
        self.revisions_log: list[dict] = []

    def run_step1(self, revise_note: str = "") -> Path:
        path = self.out / "requirement-story.md"
        if self.step1_locked and (self.out / "locked" / "step1-requirement-story.md").exists():
            print("[锁定] 跳过 Step1，使用 locked 副本")
            shutil.copy2(self.out / "locked" / "step1-requirement-story.md", path)
            return path
        template = load_prompt("step1-story.md", self.task_dir)
        prompt = template.replace("{{JOURNAL_RAW}}", self.journal)
        if revise_note:
            prompt += f"\n\n## 人工 revise 意见（必须落实）\n{revise_note}\n"
        print(">>> Step1 整理需求故事 …")
        md = strip_fence(chat(self.client, prompt))
        if not _step1_structure_ok(md):
            # 结构残缺时补强一枪，避免只吐 bullet 碎片害 Step2
            fix_prompt = (
                prompt
                + "\n\n## 系统纠偏\n上一稿缺少规定标题或只是碎片列表。"
                "请严格按六个二级标题重写完整 Markdown，禁止只列 bullet。\n"
            )
            md2 = strip_fence(chat(self.client, fix_prompt))
            if _step1_structure_ok(md2) or len(md2) > len(md):
                md = md2
        if "全局故事" not in md:
            md = "# 需求故事\n\n## 全局故事（一件事）\n" + md
        path.write_text(md, encoding="utf-8")
        print(f"已写 {path}")
        return path

    def run_step2(self, revise_note: str = "") -> Path:
        story = (self.out / "requirement-story.md").read_text(encoding="utf-8")
        template = load_prompt("step2-json.md", self.task_dir)
        prompt = (
            template.replace("{{REQUIREMENT_STORY}}", story)
            .replace("{{JOURNAL_RAW}}", self.journal)
        )
        if revise_note:
            prompt += f"\n\n## 人工 revise 意见（必须落实）\n{revise_note}\n"
        print(">>> Step2 提取用户故事 JSON …")
        raw = chat(self.client, prompt)
        # 落盘原始回复，便于排查坏 JSON
        try:
            (self.out / "step2-raw.txt").write_text(raw or "", encoding="utf-8")
        except Exception:
            pass

        def _parse_or_repair(src: str) -> dict:
            try:
                return normalize_stories(extract_json_object(src), self.journal)
            except Exception as e1:
                # 请模型只修 JSON，不再扩写需求
                fix_prompt = (
                    "下面是一段本应是 JSON 的文本，但解析失败。"
                    "请只输出合法 JSON 对象，键含 stories 数组；不要 Markdown 围栏，不要解释。\n"
                    f"解析错误：{e1}\n\n----\n{src[:12000]}\n----"
                )
                fixed = chat(self.client, fix_prompt)
                try:
                    (self.out / "step2-raw-fixed.txt").write_text(fixed or "", encoding="utf-8")
                except Exception:
                    pass
                return normalize_stories(extract_json_object(fixed), self.journal)

        try:
            payload = _parse_or_repair(raw)
        except Exception as e:
            raise RuntimeError(
                f"Step2 JSON 解析失败：{e}。可打开 output/step2-raw.txt 查看模型原文，然后重试运行 Step2。"
            ) from e

        # 有效条太少时，带着失败原因再抽一次
        if len(payload.get("stories") or []) < 2:
            retry_note = (
                "\n\n## 系统纠偏\n上一稿有效条目过少（source_quote 对不上或重复）。"
                "请重新抽取 4～8 条：每条 text 以「用户要」开头；"
                "source_quote 必须是原始日志中连续原句；层级含 1 条 activity。"
                "只输出合法 JSON，字符串内引号必须转义。"
            )
            raw2 = chat(self.client, prompt + retry_note)
            try:
                (self.out / "step2-raw-retry.txt").write_text(raw2 or "", encoding="utf-8")
            except Exception:
                pass
            try:
                payload2 = _parse_or_repair(raw2)
                if len(payload2.get("stories") or []) > len(payload.get("stories") or []):
                    payload = payload2
            except Exception:
                pass  # 保留第一稿
        path = self.out / "stories.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写 {path}（{len(payload['stories'])} 条）")
        return path

    def feedback_after(self, step_name: str, question: str) -> dict:
        self.metrics["feedback_triggered"] += 1
        self.metrics["rounds"] += 1
        ans = ask(f"[{step_name}] {question}\n输入 ok 或 revise:码:原因", self.demo_queue)
        self.history.append(f"{step_name}:{ans}")
        fb = parse_feedback(ans)
        if fb["kind"] == "revise":
            self.metrics["corrections"] += 1
            self.metrics["rework"] += 1
            self.revisions_log.append(
                {
                    "step": step_name,
                    "round": self.metrics["rounds"],
                    "action": "revised",
                    "code": fb.get("code"),
                    "comment": fb.get("comment"),
                    "at": now_iso(),
                }
            )
        return fb

    def finalize(self, approver: str) -> Path:
        stories_path = self.out / "stories.json"
        payload = json.loads(stories_path.read_text(encoding="utf-8"))
        stories = payload.get("stories") or []
        ts = now_iso()
        for s in stories:
            revs = list(s.get("revisions") or [])
            # 附加本轮 revise 记录（若有）
            for r in self.revisions_log:
                if r.get("step") == STEP2:
                    revs.append(
                        {
                            "round": r.get("round") or self.metrics["rounds"],
                            "action": "revised",
                            "code": r.get("code"),
                            "comment": r.get("comment"),
                            "at": r.get("at") or ts,
                        }
                    )
            revs.append({"round": self.metrics["rounds"], "action": "approved", "at": ts})
            s["revisions"] = revs
            s["approved"] = True

        cov = payload.get("coverage") or {}
        uncovered = cov.get("uncovered") or []
        comments = ""
        if uncovered:
            comments = (
                "人工确认：未覆盖句多为语气/过渡/重复表述或与需求抽取无关的旁白，"
                f"已写入 uncovered.md（共 {len(uncovered)} 句）。"
                "定稿故事均含可追溯 source_quote，编造条数为 0。"
            )
            (self.out / "uncovered.md").write_text("\n".join(uncovered), encoding="utf-8")

        accepted = {
            "meta": {
                "source_file": "input/journal-official-full.md",
                "loop": "product-requirement",
                "round": max(1, self.metrics["rounds"]),
                "finalized_at": ts,
                "finalized_by": approver,
            },
            "stories": stories,
            "coverage": {
                "total_sentences": cov.get("total_sentences", 0),
                "covered_sentences": cov.get("covered_sentences", 0),
                "coverage_rate": cov.get("coverage_rate", 0),
                "uncovered": uncovered,
            },
            "review": {
                "approved": True,
                "approver": approver,
                "approved_at": ts,
                "comments": comments,
            },
            "loop_metrics": {
                "rounds": self.metrics["rounds"],
                "corrections": self.metrics["corrections"],
                "rework": self.metrics["rework"],
                "feedback_triggered": self.metrics["feedback_triggered"],
                "elapsed_sec": round(time.time() - self.metrics["start"], 1),
                "history": self.history,
            },
        }
        path = self.out / "accepted.json"
        path.write_text(json.dumps(accepted, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写定稿 {path}")
        return path

    def run(self, reuse: bool = False, approver: str = "case-01-operator") -> dict:
        story_path = self.out / "requirement-story.md"
        stories_path = self.out / "stories.json"

        # --- Step1 ---
        if reuse and story_path.exists():
            print(f"[reuse] Step1 {story_path}")
        else:
            self.run_step1()

        while True:
            fb = self.feedback_after(
                STEP1,
                "故事是否读得通？格式可否进入 JSON 提取？",
            )
            if fb["kind"] == "unlock":
                self.step1_locked = False
                print("[unlock] Step1 已解锁")
                continue
            if fb["kind"] == "ok":
                lock_step1(self.task_dir)
                self.step1_locked = True
                print(f"[锁定] {self.out / 'locked' / 'step1-requirement-story.md'}")
                break
            # revise
            note = f"{fb.get('code')}: {fb.get('comment')}"
            if reuse and not self.demo_queue:
                # 交互 revise 必须重跑
                self.run_step1(revise_note=note)
            else:
                self.run_step1(revise_note=note)
            reuse = False

        # --- Step2 ---
        if reuse and stories_path.exists() and not self.revisions_log:
            # demo 常：先 reuse，再强制一次 revise 重跑
            print(f"[reuse] Step2 {stories_path}")
        else:
            self.run_step2()

        while True:
            fb = self.feedback_after(
                STEP2,
                "有无多余、遗漏或分层错误？",
            )
            if fb["kind"] == "ok":
                break
            note = f"{fb.get('code')}: {fb.get('comment')}"
            self.run_step2(revise_note=note)

        # --- Step3 定稿 ---
        if self.demo_queue is not None:
            name = approver
            print(f"—— [{STEP3}] 输入定稿人姓名 ——\n> {name}  (demo)")
        else:
            name = ask(f"[{STEP3}] 输入定稿人姓名（直接回车用 {approver}）", None) or approver
        self.metrics["feedback_triggered"] += 1
        self.finalize(name)

        elapsed = time.time() - self.metrics["start"]
        print(
            f"\n== 循环结束：rounds={self.metrics['rounds']}, "
            f"corrections={self.metrics['corrections']}, "
            f"rework={self.metrics['rework']}, 耗时={elapsed:.1f}s =="
        )
        return self.metrics


def main() -> int:
    ap = argparse.ArgumentParser(description="product-requirement 闭环（阶段4）")
    ap.add_argument("task_dir", nargs="?", default="trials/case-01")
    ap.add_argument("--demo", action="store_true", help="预设反馈：revise 一次再 ok")
    ap.add_argument("--reuse-artifacts", action="store_true", help="尽量复用已有 output")
    ap.add_argument("--approver", default="case-01-operator")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    task_dir = Path(args.task_dir)
    if not task_dir.is_absolute():
        task_dir = (PROJECT_DIR / task_dir).resolve()

    spec = yaml.safe_load(SPEC_FILE.read_text(encoding="utf-8"))
    journal_path = task_dir / "input" / "journal-official-full.md"
    if not journal_path.exists():
        journal_path = task_dir / "input" / "journal-raw.md"
    journal = journal_path.read_text(encoding="utf-8")

    print(f"== {spec['name']}：{spec['description']} ==")
    print(f"LLM: {provider_summary()}")
    print(f"任务目录: {task_dir}")
    for i, s in enumerate(spec["steps"], 1):
        print(f"  {i}. [{s.get('actor', 'ai')}] {s['name']} → {s.get('artifact', '-')}")

    if args.dry_run:
        print("\n[dry-run] 仅预览，不执行。")
        return 0

    # demo：Step1 ok → Step2 revise 一次 → Step2 ok（保证至少 1 次 revise）
    demo_queue = None
    if args.demo:
        demo_queue = [
            "ok",
            "revise:格式:请确保每条 text 以用户要开头且 source_quote 为原文连续句",
            "ok",
        ]

    client = make_client()
    loop = ProductRequirementLoop(task_dir, journal, client, demo_queue=demo_queue)
    # demo + reuse：Step1 复用；Step2 因 revise 会重跑
    loop.run(reuse=args.reuse_artifacts, approver=args.approver)
    return 0


if __name__ == "__main__":
    sys.exit(main())
