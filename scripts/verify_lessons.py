#!/usr/bin/env python3
"""项目踩坑 → 回归门禁（不依赖 LLM / 可不启服务）。

把做产品时真实出过的问题固化成流水检测，防止回潮。
每条用例旁注明「当时现象」，便于审阅同事理解为什么要卡。

Usage (repo root):
  project\\.venv\\Scripts\\python.exe scripts\\verify_lessons.py
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"
CASE = PROJECT / "trials" / "case-01"
APP = CASE / "app.html"
LOOP_WEB = PROJECT / "web" / "loop_session.py"
LOOP_RUN = PROJECT / "loop_runner.py"
QUEUE = PROJECT / "web" / "review_queue.py"
SERVER = ROOT / "scripts" / "stage0_server.py"
GUARD = PROJECT / "web" / "security_guard.py"
INBOX = PROJECT / "web" / "journal_inbox.py"
MANUAL = ROOT / "docs" / "交付" / "产品操作手册.md"
FLOW_SVG = CASE / "assets" / "manual" / "manual-06-dataflow.svg"
JOURNAL_STORE = PROJECT / "web" / "journal_store.py"

PASS = 0
FAIL = 0


def ok(name: str, detail: str = "") -> None:
    global PASS
    PASS += 1
    print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))


def bad(name: str, detail: str) -> None:
    global FAIL
    FAIL += 1
    print(f"[FAIL] {name} — {detail}")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def check_lessons() -> None:
    print("== lessons-learned regression gates ==")
    print("（以下每条对应项目过程中真实踩过的坑）\n")

    app = _read(APP)
    loop_web = _read(LOOP_WEB)
    loop_run = _read(LOOP_RUN)
    queue = _read(QUEUE)
    server = _read(SERVER)
    guard = _read(GUARD)
    inbox = _read(INBOX)
    manual = _read(MANUAL)
    jstore = _read(JOURNAL_STORE)

    # --- UX / 交互 ---
    print("-- UX / 交互 --")

    # 坑：快速换日志点卡片像没反应——确认框被日志窗挡住
    if re.search(r"\.confirm-modal\s*\{[^}]*z-index\s*:\s*(\d+)", app):
        m = re.search(r"\.confirm-modal\s*\{[^}]*z-index\s*:\s*(\d+)", app)
        zc = int(m.group(1)) if m else 0
        mj = re.search(r"(?<!confirm-)\.modal\s*\{[^}]*z-index\s*:\s*(\d+)", app)
        zj = int(mj.group(1)) if mj else 400
        if zc > zj:
            ok("确认框高于日志弹窗", f"confirm={zc} > modal={zj}")
        else:
            bad("确认框高于日志弹窗", f"confirm z-index {zc} 未高于 modal {zj}（点选会像失灵）")
    else:
        bad("确认框高于日志弹窗", "未见 .confirm-modal z-index")

    # 坑：快速更换选中后不关窗
    if "function pickJournalFromModal" in app and "closeJournalModal()" in app:
        ok("快速更换先关窗再切换", "pickJournalFromModal")
    else:
        bad("快速更换先关窗再切换", "缺 pickJournalFromModal / closeJournalModal")

    # 坑：已定稿时仍提示「清空未定稿产物」
    if "已经定稿入库" in app and "定稿档案里的记录不会丢" in app:
        ok("已定稿切换文案区分未定稿")
    else:
        bad("已定稿切换文案", "selectJournal 需对 phase===done 使用专用提示")

    # 坑：刷新页面反复弹「上次错误」
    if "function updateToolbar" not in app:
        bad("刷新不弹上次错误", "无 updateToolbar")
    else:
        chunk = app.split("function updateToolbar", 1)[1].split("\nasync function ", 1)[0]
        if re.search(r"last_error[\s\S]{0,120}toast\(", chunk) or re.search(
            r"toast\([\s\S]{0,100}last_error", chunk
        ):
            bad("刷新不弹上次错误", "updateToolbar 仍在 toast last_error")
        else:
            ok("刷新不弹上次错误")

    # 坑：右侧 AI 产物看不到字数
    if 'id="output-len"' in app and "function updateOutputLen" in app:
        ok("AI 输出右侧字数")
    else:
        bad("AI 输出右侧字数", "缺 #output-len / updateOutputLen")

    # 坑：速度快/中/慢看不懂对应字数
    if ("1200–3499" in app or "1200-3499" in app) and "≥3500" in app.replace(">=", "≥"):
        ok("速度规则标注字符范围")
    elif "1200" in app and "3500" in app:
        ok("速度规则标注字符范围", "含 1200/3500")
    else:
        bad("速度规则标注字符范围", "日志库速度筛选项需写清字符范围")

    if "_estimate_speed" in jstore and "1200" in jstore and "3500" in jstore:
        ok("后端速度估算阈值与前端一致")
    else:
        bad("后端速度估算阈值", "journal_store._estimate_speed 需含 1200/3500")

    # --- Step3 / 入库门禁 ---
    print("-- Step3 / 入库门禁 --")

    # 坑：没跑 check 也能点入库（曾误放开 disabled）
    if "fin.disabled = !lastStoriesCheckPassed" in app or "fin.disabled=!lastStoriesCheckPassed" in app:
        ok("入库键未 check 时禁用")
    else:
        bad("入库键未 check 时禁用", "btn-finalize 必须 disabled=!lastStoriesCheckPassed")

    # 坑：点入库会偷偷代跑 check，用户感觉「没检查就能入库」
    fin_fn = ""
    if "async function finalize" in app:
        fin_fn = app.split("async function finalize", 1)[1].split("\nasync function ", 1)[0]
    if fin_fn:
        if "await runCheck()" in fin_fn:
            bad("入库不代跑 check", "finalize() 内不应 await runCheck()，须用户先手动 check")
        elif "lastStoriesCheckPassed" in fin_fn and ("return" in fin_fn):
            ok("入库不代跑 check", "未通过则直接 return")
        else:
            bad("入库不代跑 check", "finalize 门禁逻辑不完整")
    else:
        bad("入库不代跑 check", "未见 finalize()")

    if 'run_check(target="stories"' in loop_web and "不能定稿入库" in loop_web:
        ok("后端 finalize 强制 stories check")
    else:
        bad("后端 finalize 强制 stories check", "loop_session.finalize 缺门禁")

    # --- 待审库 ---
    print("-- 待审库 --")

    if "待审库" in app and "待人审" not in app:
        ok("待人审已更名待审库且无残留")
    else:
        bad("待审库改名", "app.html 应有待审库且无待人审")

    # 坑：排队中无法取消，再勾选像「隐性覆盖」
    if "def cancel_item" in queue and "btn-cancel-q" in app and "/api/queue/cancel" in server:
        ok("待审库可取消占用任务")
    else:
        bad("待审库可取消占用任务", "需 cancel_item + UI + /api/queue/cancel")

    if 'status="cancelled"' in queue.replace(" ", "") or 'status="cancelled"' in queue:
        ok("取消后状态为 cancelled 可再入队")
    else:
        # softer
        if '"cancelled"' in queue:
            ok("取消后状态为 cancelled 可再入队")
        else:
            bad("cancelled 状态", "cancel_item 应写入 cancelled")

    # --- Step2 / AI 失败体验 ---
    print("-- Step2 / AI 失败体验 --")

    # 坑：模型 JSON 截断导致 Step2 永远解析失败
    if "def _close_truncated_json" in loop_run and "_extract_complete_story_objects" in loop_run:
        ok("Step2 截断 JSON 本地修复")
    else:
        bad("Step2 截断 JSON 本地修复", "loop_runner 缺 _close_truncated_json 等")

    # 单元：截断样例必须能修
    try:
        sys.path.insert(0, str(PROJECT))
        from loop_runner import extract_json_object, normalize_stories  # noqa: E402

        truncated = (
            '{\n  "stories": [\n'
            '    {"id":"s1","level":"activity","text":"用户要建设用户故事库",'
            '"source_quote":"我们要建设用户故事库","reason":"顶层","confidence":0.9},\n'
            '    {"id":"s2","level":"task","text":"用户要捕捉'
        )
        journal = "我们要建设用户故事库，从研发日志里捕捉需求。"
        obj = extract_json_object(truncated)
        norm = normalize_stories(obj, journal)
        if (norm.get("stories") or []) and any("建设" in (s.get("text") or "") for s in norm["stories"]):
            ok("截断 JSON 样例可解析出完整条目", f"{len(norm['stories'])} 条")
        else:
            bad("截断 JSON 样例可解析", str(norm)[:160])
    except Exception as e:
        bad("截断 JSON 样例可解析", str(e))

    # 坑：只弹英文 Connection error，看不懂
    if "_friendly_llm_error" in loop_run and "AI 接口连不上" in loop_run:
        ok("AI 连接失败有中文人话")
    else:
        bad("AI 连接失败人话", "loop_runner._friendly_llm_error 缺中文提示")

    # --- 手册 / 交付 ---
    print("-- 手册 / 交付 --")

    if FLOW_SVG.exists() and "manual-06-dataflow.svg" in app and "manual-06-dataflow.svg" in manual:
        ok("手册数据流必须有图", str(FLOW_SVG.relative_to(ROOT)))
    else:
        bad("手册数据流必须有图", "缺 SVG 或 app/手册未引用")

    if "manual-sidebar" in app and 'id="m-flow"' in app:
        ok("手册侧栏目录可定位到数据流")
    else:
        bad("手册侧栏目录", "缺 manual-sidebar / #m-flow")

    # --- 安全（过程中暴露的口子）---
    print("-- 安全加固回潮防护 --")

    if "Permissions-Policy" in guard and "Cross-Origin-Opener-Policy" in guard:
        ok("安全响应头含 Permissions-Policy / COOP")
    else:
        bad("安全响应头", "security_guard.security_headers 缺加固项")

    if re.search(r"MAX_ATTEMPTS\s*=\s*(\d+)", guard):
        n = int(re.search(r"MAX_ATTEMPTS\s*=\s*(\d+)", guard).group(1))
        if n <= 15:
            ok("登录限流足够紧", str(n))
        else:
            bad("登录限流", f"MAX_ATTEMPTS={n} 过松")
    else:
        bad("登录限流", "未见 MAX_ATTEMPTS")

    if "_require_https" in inbox or 'startswith("https://")' in inbox:
        ok("出站拉取强制 https")
    else:
        bad("出站拉取强制 https", "journal_inbox 应对 URL 做 https 校验")

    # --- 2026-09 实测：代理 / 超时 / UI 手册 ---
    print("-- 2026-09 network & manual UX --")
    llm = _read(ROOT / "project" / "llm_config.py")
    if "trust_env=False" in llm.replace(" ", "") or "trust_env=trust_env()" in llm:
        if "httpx.Client" in llm and "LLM_TRUST_ENV" in llm:
            ok("LLM 默认不读系统代理", "httpx + LLM_TRUST_ENV")
        else:
            bad("LLM 默认不读系统代理", "llm_config 需 httpx.Client + LLM_TRUST_ENV")
    else:
        bad("LLM 默认不读系统代理", "未见 trust_env 控制")

    if "LLM_TIMEOUT" in llm and "get_timeout" in llm:
        ok("LLM 超时可配置", "LLM_TIMEOUT")
    else:
        bad("LLM 超时可配置", "缺 LLM_TIMEOUT / get_timeout")

    if "chat_extra_body" in llm and "thinking" in llm:
        ok("可关闭深度思考链", "chat_extra_body")
    else:
        bad("可关闭深度思考链", "缺 chat_extra_body / thinking")

    if "socksio" in loop_run and "推理超时" in loop_run:
        ok("友好报错区分代理与超时")
    else:
        bad("友好报错区分代理与超时", "loop_runner._friendly_llm_error 需覆盖 socksio/超时")

    if "manual-combo" in app and "wireManualToc" in app:
        ok("UI 手册：侧栏+数据流截图结合")
    else:
        bad("UI 手册：侧栏+数据流截图结合", "app.html 需 manual-combo / wireManualToc")

    # 侧栏应与正文分栏滚动，而不是整页 overflow 把目录滚走
    if "manual-page" in app and "overflow:hidden" in app and "manual-body" in app:
        # crude: manual-page overflow hidden appears near manual styles
        chunk = app
        if ".manual-page{" in chunk and "overflow:hidden" in chunk.split(".manual-page{", 1)[1][:200]:
            ok("UI 手册目录栏不随正文滚走")
        else:
            bad("UI 手册目录栏不随正文滚走", ".manual-page 应为 overflow:hidden + body 自滚")
    else:
        bad("UI 手册目录栏不随正文滚走", "样式结构不符")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    print("== verify_lessons (project regression pipeline) ==")
    check_lessons()
    print(f"\n== summary: PASS={PASS} FAIL={FAIL} ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
