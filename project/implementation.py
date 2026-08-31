#!/usr/bin/env python3
"""Loop 执行器——基于 specification.yaml 的 LangGraph 实现。

来源：quanttide-devops/loops/devops-code/implementation.py（官方）
本地改动：
  - 读取 product-requirement/specification.yaml
  - LLM 经 llm_config（默认 Agnes，可切换 deepseek/openai）

用法：
  python implementation.py <任务目录> [--task "任务描述"] [--dry-run]
  python implementation.py trials/case-01 --demo --reuse-artifacts

闭环逻辑见 loop_runner.py（阶段 4）：逐步反馈 / 锁定 / accepted.json
LLM 配置：见 project/.env 与 llm_config.py（LLM_PROVIDER 默认 agnes）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import TypedDict

import yaml
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from llm_config import get_model, make_client, provider_summary

PROJECT_DIR = Path(__file__).resolve().parent
SPEC_FILE = PROJECT_DIR / "product-requirement" / "specification.yaml"
PROMPTS_DIR = PROJECT_DIR / "product-requirement" / "prompts"
ARTIFACT_STEP_FILE = "step-{n}-{name}.md"

# yaml 步骤名 → 提示词文件（阶段 3 定稿）
STEP_PROMPT_FILES = {
    "整理需求故事": "step1-story.md",
    "提取用户故事 JSON": "step2-json.md",
}


class LoopState(TypedDict, total=False):
    task: str
    task_dir: str
    round: int
    artifacts: dict
    history: list


class LoopAgent:
    def __init__(self, spec: dict, client):
        self.spec = spec
        self.client = client
        self.model = get_model()
        self.steps = spec["steps"]
        self.feedback_spec = spec.get("feedback", [])
        self.metrics = {"rounds": 0, "corrections": 0, "start": time.time()}

    def write_artifact(self, step: dict, content: str, task_dir: Path) -> str:
        artifact = step.get("artifact", "")
        if not artifact:
            return ""
        path = task_dir / artifact
        if artifact.endswith("/"):
            path.mkdir(parents=True, exist_ok=True)
            path = path / ARTIFACT_STEP_FILE.format(n=step.get("n", 0), name=step["name"])
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def ai_step(self, step: dict, state: LoopState) -> LoopState:
        task_dir = Path(state["task_dir"])
        prompt = self.build_prompt(step, state)
        content = self.llm(prompt)
        # Step2：去掉 markdown 围栏，尽量留下可解析 JSON
        if step.get("name") == "提取用户故事 JSON":
            text = content.strip()
            if text.startswith("```"):
                import re as _re

                text = _re.sub(r"^```(?:json)?\s*", "", text, flags=_re.IGNORECASE)
                text = _re.sub(r"\s*```\s*$", "", text)
                content = text.strip()
        path = self.write_artifact(step, content, task_dir)
        return {"artifacts": {**state.get("artifacts", {}), step["name"]: path}}

    def resolve_prompt_path(self, step: dict, task_dir: Path) -> Path | None:
        """优先 case 内 prompts/，否则 Loop 级 product-requirement/prompts/。"""
        fname = STEP_PROMPT_FILES.get(step.get("name", ""))
        if not fname:
            return None
        for base in (task_dir / "prompts", PROMPTS_DIR):
            path = base / fname
            if path.exists():
                return path
        return None

    def build_prompt(self, step: dict, state: LoopState) -> str:
        """加载 step1/step2 提示词文件并替换占位符；无文件时回退内联模板。"""
        task_dir = Path(state["task_dir"])
        journal = state.get("task") or ""
        path = self.resolve_prompt_path(step, task_dir)

        if path is not None:
            template = path.read_text(encoding="utf-8")
            requirement_story = ""
            art = state.get("artifacts") or {}
            # Step1 产物路径（yaml 步骤名或常见文件名）
            story_path = art.get("整理需求故事") or str(task_dir / "output" / "requirement-story.md")
            if story_path and Path(story_path).exists():
                requirement_story = Path(story_path).read_text(encoding="utf-8")
            return (
                template.replace("{{JOURNAL_RAW}}", journal)
                .replace("{{REQUIREMENT_STORY}}", requirement_story or "（尚无需求故事，请仅根据原始日志推断）")
            )

        return f"""你正在执行「{self.spec['name']}」循环的一个步骤。

循环说明：{self.spec['description']}
任务：{state['task']}
当前步骤：{step['name']}
步骤要求：{step.get('note', '')}
达标标准：{step.get('check', '')}
已完成的产物：{json.dumps(state.get('artifacts', {}), ensure_ascii=False)}

请直接输出本步骤的产物内容（Markdown 或 JSON，按步骤要求）。"""

    def llm(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是量潮智能体工程循环的执行者。"
                        "按用户提示词要求输出产物：Markdown 或 JSON。"
                        "禁止编造原文没有的需求；JSON 须可被解析。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""

    def build(self):
        return self._build_graph().compile(checkpointer=MemorySaver())

    def _build_graph(self):
        g = StateGraph(LoopState)

        for i, step in enumerate(self.steps):
            step["n"] = i + 1
            if step.get("actor") == "human":

                def node(state, step=step):
                    answer = interrupt({
                        "ask": f"人类步骤：{step['name']}（{step.get('note', '')}）\n请完成并输入产物内容或路径：",
                    })
                    path = self.write_artifact(step, str(answer), Path(state["task_dir"]))
                    return {"artifacts": {**state.get("artifacts", {}), step["name"]: path}}

            elif step.get("actor") == "human+ai":

                def node(state, step=step):
                    task_dir = Path(state["task_dir"])
                    draft = self.llm(self.build_prompt(step, state))
                    path = self.write_artifact(step, draft, task_dir)
                    comment = interrupt({
                        "ask": f"AI 已生成 {step['name']}（{path}）。请评审：输入意见（追加）或 ok（通过）：",
                    })
                    if str(comment).strip().lower() not in ("ok", "通过", ""):
                        self.metrics["corrections"] += 1
                        draft = draft + f"\n\n## 人类评审意见\n{comment}"
                        path = self.write_artifact(step, draft, task_dir)
                    return {"artifacts": {**state.get("artifacts", {}), step["name"]: path}}

            else:

                def node(state, step=step):
                    return self.ai_step(step, state)

            step["_node"] = f"step_{i}"
            g.add_node(f"step_{i}", node)

        def feedback_node(state: LoopState):
            ask = self.feedback_spec[0]["ask"] if self.feedback_spec else "本轮完成。继续（重做）还是退出？"
            answer = interrupt({"ask": ask, "artifacts": state.get("artifacts", {})})
            self.metrics["rounds"] += 1
            text = str(answer).strip().lower()
            if text in ("exit", "ok", "done", "退出", "确认", ""):
                return Command(goto=END, update={"history": state.get("history", []) + [str(answer)]})
            target = str(answer).strip()
            for s in self.steps:
                if target in (s["name"], str(s["n"])):
                    self.metrics["corrections"] += 1
                    return Command(
                        goto=s["_node"],
                        update={
                            "round": state.get("round", 0) + 1,
                            "history": state.get("history", []) + [str(answer)],
                        },
                    )
            self.metrics["corrections"] += 1
            return Command(
                goto=self.steps[0]["_node"],
                update={
                    "round": state.get("round", 0) + 1,
                    "history": state.get("history", []) + [str(answer)],
                },
            )

        g.add_node("feedback", feedback_node)

        prev = START
        for s in self.steps:
            g.add_edge(prev, s["_node"])
            prev = s["_node"]
        g.add_edge(prev, "feedback")

        return g

    def run(self, initial: LoopState):
        graph = self.build()
        config = {"configurable": {"thread_id": "product-requirement-loop"}}
        state: object = initial
        while True:
            interrupted = False
            for chunk in graph.stream(state, config, stream_mode="updates"):
                for node, update in chunk.items():
                    if node == "__interrupt__":
                        interrupted = True
                        for it in update:
                            self.present(it.value)
                            answer = input("> ").strip()
                            state = Command(resume=answer)
            if not interrupted:
                break
        return graph.get_state(config).values

    def present(self, value: object) -> None:
        if isinstance(value, dict):
            print("\n——", value.get("ask", "请确认"), "——")
            arts = value.get("artifacts")
            if arts:
                print("本轮产物：")
                for name, path in arts.items():
                    print(f"  {name}: {path}")
        else:
            print("\n——", value, "——")


def main():
    ap = argparse.ArgumentParser(description="product-requirement / devops-code 循环智能体")
    ap.add_argument("task_dir", help="任务目录（产物将写入其中）")
    ap.add_argument("--task", default="", help="任务描述（缺省读取 <任务目录>/task.md）")
    ap.add_argument("--dry-run", action="store_true", help="只打印循环计划，不执行")
    ap.add_argument("--demo", action="store_true", help="阶段4：非交互预设反馈（含一次 revise）")
    ap.add_argument("--reuse-artifacts", action="store_true", help="复用已有 output 草稿")
    ap.add_argument("--approver", default="case-01-operator")
    ap.add_argument(
        "--legacy-graph",
        action="store_true",
        help="使用旧版 LangGraph 连跑（无逐步锁定）；默认走 loop_runner 闭环",
    )
    args = ap.parse_args()

    if not SPEC_FILE.exists():
        sys.exit(f"缺少 {SPEC_FILE}")

    spec = yaml.safe_load(SPEC_FILE.read_text(encoding="utf-8"))
    task_dir = Path(args.task_dir).resolve()
    task_dir.mkdir(parents=True, exist_ok=True)

    task = args.task
    if not task:
        task_file = task_dir / "task.md"
        if task_file.exists():
            task = task_file.read_text(encoding="utf-8")
        else:
            journal = task_dir / "input" / "journal-official-full.md"
            if journal.exists():
                task = journal.read_text(encoding="utf-8")
            else:
                task = "(未提供任务描述)"

    print(f"== {spec['name']}：{spec['description']} ==")
    print(f"LLM: {provider_summary()}")
    print(f"入口：{spec['entry']}")
    for i, s in enumerate(spec["steps"], 1):
        print(f"  {i}. [{s.get('actor', 'ai')}] {s['name']} → {s.get('artifact', '-')}")
    print(f"出口：{spec['exit']}")

    if args.dry_run:
        print("\n[dry-run] 仅预览，不执行。")
        return

    # 阶段 4 默认：与 yaml feedback/locking 同构的编排器
    if not args.legacy_graph:
        from loop_runner import ProductRequirementLoop

        demo_queue = None
        if args.demo:
            demo_queue = [
                "ok",
                "revise:格式:请确保每条 text 以用户要开头且 source_quote 为原文连续句",
                "ok",
            ]
        client = make_client()
        loop = ProductRequirementLoop(task_dir, task, client, demo_queue=demo_queue)
        loop.run(reuse=args.reuse_artifacts, approver=args.approver)
        return

    agent = LoopAgent(spec, make_client())
    result = agent.run({
        "task": task,
        "task_dir": str(task_dir),
        "round": 0,
        "artifacts": {},
        "history": [],
    })
    elapsed = time.time() - agent.metrics["start"]
    print(
        f"\n== 循环结束：rounds={agent.metrics['rounds']}, "
        f"corrections={agent.metrics['corrections']}, 耗时={elapsed:.1f}s =="
    )
    print("产物：")
    for name, path in (result or {}).get("artifacts", {}).items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
