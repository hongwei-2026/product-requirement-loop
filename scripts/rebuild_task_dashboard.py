#!/usr/bin/env python3
"""根据计分板 + 认领状态重建任务仪表盘 / 任务列表 / Issue #7 正文。

Usage:
  python scripts/rebuild_task_dashboard.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORE = ROOT / "docs" / "交付" / "任务计分板.md"
CLAIMS = ROOT / "docs" / "交付" / "任务认领状态.json"
OUT = ROOT / "docs" / "交付" / "任务仪表盘.md"
LIST = ROOT / "docs" / "交付" / "任务列表.md"
HUB = ROOT / "docs" / "交付" / "任务总览-issue7.body.md"
HTML = ROOT / "docs" / "dashboard" / "index.html"

SEED = ["hongwei-2026", "hl019", "Jerrybao99", "likexin105"]
ISSUE_BASE = "https://github.com/hongwei-2026/product-requirement-loop/issues"

TASKS = [
    {"num": 1, "diff": "简单", "pts": 10, "title": "工作台顶栏展示 LLM provider/model/超时摘要", "short": "顶栏 LLM 摘要", "tier": "base"},
    {"num": 2, "diff": "简单", "pts": 15, "title": "统一「服务宕机」与「AI 超时」提示文案", "short": "服务宕机 vs AI 超时", "tier": "base"},
    {"num": 3, "diff": "中等", "pts": 30, "title": "Step1/Step2 请求心跳与超时重试", "short": "心跳与重试", "tier": "base"},
    {"num": 4, "diff": "中等", "pts": 35, "title": "待审库轻量搜索与状态过滤", "short": "待审库轻量搜索", "tier": "base"},
    {"num": 5, "diff": "难", "pts": 60, "title": "Step1/Step2 异步任务 + 轮询/SSE", "short": "异步 Step1/2", "tier": "base"},
    {"num": 6, "diff": "难", "pts": 50, "title": "长日志压力测试流水（脚本+CI，无真实 Key）", "short": "长日志压测 CI", "tier": "base"},
    {"num": 8, "diff": "难", "pts": 55, "title": "待审库「工作台级」全部分组 + 搜索", "short": "待审库工作台级分组", "tier": "base"},
    {"num": 9, "diff": "特难", "pts": 75, "title": "定稿导出产品云可对齐的 requirement.json 包", "short": "requirement.json 导出包", "tier": "extreme"},
    {"num": 10, "diff": "特难", "pts": 80, "title": "第二大脑 Context 导出包", "short": "第二大脑 Context 导出包", "tier": "extreme"},
    {"num": 11, "diff": "特难", "pts": 70, "title": "SemVer 发布门禁（标签+CHANGELOG）", "short": "SemVer 发布门禁", "tier": "extreme"},
    {"num": 12, "diff": "特难", "pts": 75, "title": "工作台覆盖率/uncovered 面板 + 人确认", "short": "覆盖率 uncovered 面板", "tier": "extreme"},
    {"num": 13, "diff": "特难", "pts": 70, "title": "故事/定稿修订时间线 UI", "short": "修订时间线 UI", "tier": "extreme"},
    {"num": 14, "diff": "特难", "pts": 75, "title": "打叉理由分析看板", "short": "打叉理由分析看板", "tier": "extreme"},
    {"num": 15, "diff": "特难", "pts": 80, "title": "待审库指派/交接/超时回收（SLA）", "short": "待审库指派/SLA", "tier": "extreme"},
    {"num": 16, "diff": "特难", "pts": 80, "title": "官方日志 Inbox 强去重+冲突处理台", "short": "Inbox 去重+冲突台", "tier": "extreme"},
    {"num": 17, "diff": "特难", "pts": 85, "title": "批量 Step1 通过后入队 Step2 草稿", "short": "Step1 后入队 Step2 草稿", "tier": "extreme"},
    {"num": 18, "diff": "特难", "pts": 85, "title": "Prompt 版本钉死 + prompt_sha 审计", "short": "Prompt 版本 / prompt_sha", "tier": "extreme"},
    {"num": 19, "diff": "特难", "pts": 90, "title": "多 trial 矩阵 case-02+ 与 CI 金标", "short": "多 trial 矩阵", "tier": "extreme"},
    {"num": 20, "diff": "特难", "pts": 90, "title": "运行时安全切换 LLM + 健康探测", "short": "运行时切换 LLM", "tier": "extreme"},
    {"num": 21, "diff": "特难", "pts": 75, "title": "错误分类回流 verify_lessons", "short": "错误分类回流 lessons", "tier": "extreme"},
    {"num": 22, "diff": "特难", "pts": 85, "title": "待审库/定稿 JSON↔SQLite 单一数据源", "short": "JSON↔SQLite 单一数据源", "tier": "extreme"},
]

STATUS_CN = {
    "open": "开放可接",
    "claim-pending": "已 /claim（等设计/accept）",
    "locked": "已锁定实现中",
    "done": "已完成计分",
}


def parse_scores(text: str) -> list[tuple[str, str, int, str]]:
    rows = []
    for m in re.finditer(
        r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*\|\s*#?(\d+)\s*\|\s*(\d+)\s*\|\s*([^|]*)\|",
        text,
    ):
        date, user, issue, pts, note = m.groups()
        user = user.strip()
        if user in {"—", "-", "GitHub ID"}:
            continue
        rows.append((date, user, int(issue), int(pts), note.strip()))
    return rows


def load_claims() -> dict:
    if not CLAIMS.exists():
        return {}
    data = json.loads(CLAIMS.read_text(encoding="utf-8"))
    return data.get("claims") or {}


def claim_of(claims: dict, n: int) -> dict:
    c = claims.get(str(n)) or claims.get(n) or {}
    return c if isinstance(c, dict) else {}


def claimant_md(claims: dict, n: int, *, with_status: bool = True) -> str:
    """接取人栏：仅在维护者 /accept（locked）或已计分（done）后显示 GitHub ID。"""
    c = claim_of(claims, n)
    user = (c.get("user") or "").strip()
    st = c.get("status") or ""
    # claim-pending：意向阶段，接取人栏仍为空
    if st == "claim-pending" or not user:
        return "—"
    if st not in {"locked", "done"}:
        return "—"
    link = f"[@{user}](https://github.com/{user})"
    if not with_status:
        return link
    if st == "locked":
        return f"{link}（已锁定）"
    if st == "done":
        return f"{link}（已完成）"
    return link


def claimant_html(claims: dict, n: int) -> str:
    c = claim_of(claims, n)
    user = (c.get("user") or "").strip()
    st = c.get("status") or ""
    if st == "claim-pending" or not user or st not in {"locked", "done"}:
        return "—"
    tip = {"locked": "已锁定", "done": "已完成"}.get(st, "")
    base = f"<a href='https://github.com/{user}'>@{user}</a>"
    return f"{base}（{tip}）" if tip else base


def build_md(rows: list[tuple[str, str, int, str]], claims: dict) -> str:
    totals: dict[str, int] = {u: 0 for u in SEED}
    by_issue: dict[int, list[str]] = {}
    for date, user, issue, pts, note in rows:
        totals[user] = totals.get(user, 0) + pts
        by_issue.setdefault(issue, []).append(f"{user}+{pts}")

    ranked = sorted(totals.items(), key=lambda x: (-x[1], x[0].lower()))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# 实训任务仪表盘",
        "",
        f"> 自动生成：{now}  ·  [计分板](./任务计分板.md)  ·  [认领状态 JSON](./任务认领状态.json)  ·  [总入口 #7](https://github.com/hongwei-2026/product-requirement-loop/issues/7)",
        "",
        "## 积分排行榜",
        "",
        "| 排名 | GitHub ID | 总分 |",
        "|------|-----------|------|",
    ]
    for i, (user, pts) in enumerate(ranked, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, str(i))
        lines.append(f"| {medal} | [{user}](https://github.com/{user}) | **{pts}** |")

    lines += [
        "",
        "## 进行中的认领（同步自 `/claim` `/accept`；放弃后自动清除）",
        "",
        "| Issue | 状态 | 接取人 | 更新时间 |",
        "|-------|------|--------|----------|",
    ]
    active = [
        (k, v)
        for k, v in claims.items()
        if isinstance(v, dict) and v.get("status") in {"claim-pending", "locked"}
    ]
    if not active:
        lines.append("| — | 当前无人认领进行中 | — | — |")
    else:
        for k, v in sorted(active, key=lambda x: int(x[0])):
            st = STATUS_CN.get(v.get("status", ""), v.get("status"))
            user = v.get("user", "—")
            url = f"{ISSUE_BASE}/{k}"
            lines.append(
                f"| [#{k}]({url}) | {st} | [@{user}](https://github.com/{user}) | {v.get('updated', '—')} |"
            )

    lines += [
        "",
        "## 任务看板",
        "",
        "| Issue | 难度 | 分值 | 标题 | 认领状态 | 接取人 | 已计分 |",
        "|-------|------|------|------|----------|--------|--------|",
    ]
    for t in TASKS:
        n = t["num"]
        c = claim_of(claims, n)
        if c.get("status"):
            st = STATUS_CN.get(c["status"], c["status"])
        else:
            st = STATUS_CN["open"]
        who = claimant_md(claims, n)
        scored = ", ".join(by_issue.get(n, [])) or "—"
        url = f"{ISSUE_BASE}/{n}"
        lines.append(
            f"| [#{n}]({url}) | {t['diff']} | {t['pts']} | {t['title']} | {st} | {who} | {scored} |"
        )

    lines += [
        "",
        "## 同步与放弃（命令）",
        "",
        "| 你想做什么 | 在任务 Issue 评论 | 仪表盘 / #7 表会怎样 |",
        "|------------|-------------------|----------------------|",
        "| 接任务意向 | `/claim` | **接取人栏仍为空**；仅记意向 |",
        "| 维护者合并 Design PR 后批准 | `/accept @用户` | **接取人栏写入该 ID** |",
        "| **自己放弃** | `/release` 或 `/cancel` | **接取人清空为 —** |",
        "| 维护者清掉别人的认领 | `/reject-claim` | 同上 |",
        "| 完成后记分 | `/score N` | 排行榜加分；接取人标已完成 |",
        "| **超 30 天无 PR 更新** | （自动） | **自动释放**，接取人清空 |",
        "",
        "> **一账号同时只能 1 个进行中任务。**",
        "",
        "必审人：`hongwei-2026` · `hl019` · `Jerrybao99` · `likexin105`",
        "",
    ]
    return "\n".join(lines)


def build_list_md(claims: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 实训任务列表（Issue 索引）",
        "",
        "维护者：[@hongwei-2026](https://github.com/hongwei-2026)  ",
        "流程：[任务贡献指南.md](./任务贡献指南.md) · **仪表盘**：[任务仪表盘.md](./任务仪表盘.md) · [HTML](../dashboard/index.html) · 计分板：[任务计分板.md](./任务计分板.md)",
        "",
        f"> 自动同步接取人：{now}（数据源 [任务认领状态.json](./任务认领状态.json)）  ",
        "> 接取：`/claim` → Design **Merge** → `/accept`（接取人栏才写入）→ Impl（代码+视频+截图）→ `/score`。  ",
        "> **一账号一题**；关联 PR 超 **30 天**无更新自动释放；放弃：`/cancel` 或 `/release`。",
        "",
        f"**总入口：** [#7 实训任务总览]({ISSUE_BASE}/7)",
        "",
        "## 基础 / 进阶（#1–#8）",
        "",
        "| 难度 | 积分 | Issue | 标题 | 接取人 |",
        "|------|------|-------|------|--------|",
    ]
    for t in TASKS:
        if t["tier"] != "base":
            continue
        n = t["num"]
        lines.append(
            f"| {t['diff']} | {t['pts']} | [#{n}]({ISSUE_BASE}/{n}) | [{t['short']}]({ISSUE_BASE}/{n}) | {claimant_md(claims, n)} |"
        )

    lines += [
        "",
        "## 特难扩展（#9–#22，对齐量潮）",
        "",
        "| 难度 | 积分 | Issue | 标题 | 接取人 |",
        "|------|------|-------|------|--------|",
    ]
    for t in TASKS:
        if t["tier"] != "extreme":
            continue
        n = t["num"]
        lines.append(
            f"| {t['diff']} | {t['pts']} | [#{n}]({ISSUE_BASE}/{n}) | [{t['short']}]({ISSUE_BASE}/{n}) | {claimant_md(claims, n)} |"
        )

    lines += [
        "",
        "## 必审人 / 可记分人",
        "",
        "`hongwei-2026` · `hl019` · `Jerrybao99` · `likexin105`",
        "",
        "PR 须四人全部 Approve；记分评论：`/score N`",
        "",
    ]
    return "\n".join(lines)


def build_issue7_body(claims: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 实训任务总览（跳转入口）",
        "",
        "维护者：@hongwei-2026  ",
        "必审人（PR 须 **四人全部 Approve**）：@hongwei-2026 @hl019 @Jerrybao99 @likexin105  ",
        "",
        "- 同学：[任务贡献指南](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E4%BB%BB%E5%8A%A1%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97.md)",
        "- **审核员**：[审核员指南](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E5%AE%A1%E6%A0%B8%E5%91%98%E6%8C%87%E5%8D%97.md)",
        "- 汇报稿：[实训贡献机制-同学汇报稿](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E5%AE%9E%E8%AE%AD%E8%B4%A1%E7%8C%AE%E6%9C%BA%E5%88%B6-%E5%90%8C%E5%AD%A6%E6%B1%87%E6%8A%A5%E7%A8%BF.md)",
        "- 任务列表：[任务列表](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E4%BB%BB%E5%8A%A1%E5%88%97%E8%A1%A8.md)",
        "- Design 提交位：[docs/designs](https://github.com/hongwei-2026/product-requirement-loop/tree/main/docs/designs)",
        "",
        "## 硬性规则",
        "",
        "1. **同一 GitHub 账号同时只能接 1 个进行中任务**（`/claim` 或已 `/accept` 锁定期间）。换题先 `/cancel`。",
        "2. 实现 PR 必须：**代码 + 演示视频链接 + 截图≥2**。",
        "3. Design 方案落库：`docs/designs/#N-….md`。",
        "4. **接取人**列：仅在维护者 **合并 Design PR 之后** 评论 `/accept @ID` 才写入（单独 `/claim` 不会写）。",
        "5. **30 天无关联 PR 更新 → 自动释放**（接取人清空，任务重开）。",
        "",
        f"_接取人表上次同步：{now}_",
        "",
        "## 子任务列表",
        "",
        "### 基础 / 进阶",
        "",
        "| 难度 | 积分 | Issue | 标题 | 接取人 |",
        "|------|------|-------|------|--------|",
    ]
    for t in TASKS:
        if t["tier"] != "base":
            continue
        n = t["num"]
        lines.append(
            f"| {t['diff']} | {t['pts']} | [#{n}]({ISSUE_BASE}/{n}) | [{t['short']}]({ISSUE_BASE}/{n}) | {claimant_md(claims, n)} |"
        )

    lines += [
        "",
        "### 特难扩展（量潮对齐）",
        "",
        "| 难度 | 积分 | Issue | 标题 | 接取人 |",
        "|------|------|-------|------|--------|",
    ]
    for t in TASKS:
        if t["tier"] != "extreme":
            continue
        n = t["num"]
        lines.append(
            f"| {t['diff']} | {t['pts']} | [#{n}]({ISSUE_BASE}/{n}) | [{t['short']}]({ISSUE_BASE}/{n}) | {claimant_md(claims, n)} |"
        )

    lines += [
        "",
        "接取：目标 Issue 评论 `/claim` → Design PR → 维护者 **Merge** → 维护者 `/accept @你` → **接取人栏才出现你的 ID**。",
        "",
    ]
    return "\n".join(lines)


def build_html(rows: list, claims: dict) -> str:
    totals: dict[str, int] = {u: 0 for u in SEED}
    for _, user, _, pts, _ in rows:
        totals[user] = totals.get(user, 0) + pts
    ranked = sorted(totals.items(), key=lambda x: (-x[1], x[0].lower()))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rank_rows = "".join(
        f"<tr><td>{i}</td><td><a href='https://github.com/{u}'>@{u}</a></td><td><b>{p}</b></td></tr>"
        for i, (u, p) in enumerate(ranked, 1)
    )

    active = [
        (k, v)
        for k, v in claims.items()
        if isinstance(v, dict) and v.get("status") in {"claim-pending", "locked"}
    ]
    if active:
        claim_rows = "".join(
            "<tr>"
            f"<td><a href='{ISSUE_BASE}/{k}'>#{k}</a></td>"
            f"<td>{STATUS_CN.get(v.get('status'), v.get('status'))}</td>"
            f"<td><a href='https://github.com/{v.get('user')}'>@{v.get('user')}</a></td>"
            f"<td>{v.get('updated','')}</td>"
            "</tr>"
            for k, v in sorted(active, key=lambda x: int(x[0]))
        )
    else:
        claim_rows = "<tr><td colspan='4'>当前无人认领进行中</td></tr>"

    task_rows = "".join(
        "<tr>"
        f"<td><a href='{ISSUE_BASE}/{t['num']}'>#{t['num']}</a></td>"
        f"<td>{t['diff']}</td><td>{t['pts']}</td><td>{t['short']}</td>"
        f"<td>{STATUS_CN.get(claim_of(claims, t['num']).get('status'), '开放可接')}</td>"
        f"<td>{claimant_html(claims, t['num'])}</td>"
        "</tr>"
        for t in TASKS
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>实训任务仪表盘</title>
  <style>
    :root {{ --bg:#0f1419; --card:#1a2332; --text:#e7ecf3; --muted:#9aa7b8; --accent:#3d8bfd; --line:#2a3545; }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:linear-gradient(160deg,#0f1419,#152033); color:var(--text); }}
    main {{ max-width:1100px; margin:0 auto; padding:32px 20px 64px; }}
    h1 {{ margin:0 0 8px; font-size:1.6rem; }}
    .sub {{ color:var(--muted); margin:0 0 22px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin:0 0 16px; overflow-x:auto; }}
    table {{ width:100%; border-collapse:collapse; font-size:0.94rem; }}
    th,td {{ text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:var(--muted); font-size:0.78rem; }}
    a {{ color:var(--accent); text-decoration:none; }}
  </style>
</head>
<body>
<main>
  <h1>实训任务仪表盘</h1>
  <p class="sub">{now} · <a href="{ISSUE_BASE}/7">#7 总入口</a>（接取人随 /claim 自动更新）</p>
  <section class="card"><h2>积分排行榜</h2>
    <table><thead><tr><th>#</th><th>GitHub</th><th>总分</th></tr></thead><tbody>{rank_rows}</tbody></table>
  </section>
  <section class="card"><h2>进行中的认领</h2>
    <table><thead><tr><th>Issue</th><th>状态</th><th>接取人</th><th>更新</th></tr></thead><tbody>{claim_rows}</tbody></table>
    <p class="sub">放弃请在 Issue 评论 <code>/release</code> 或 <code>/cancel</code>，接取人会自动清空。</p>
  </section>
  <section class="card"><h2>任务看板（含接取人）</h2>
    <table><thead><tr><th>Issue</th><th>难度</th><th>分</th><th>标题</th><th>状态</th><th>接取人</th></tr></thead><tbody>{task_rows}</tbody></table>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    text = SCORE.read_text(encoding="utf-8") if SCORE.exists() else ""
    rows = parse_scores(text)
    claims = load_claims()
    OUT.write_text(build_md(rows, claims), encoding="utf-8")
    LIST.write_text(build_list_md(claims), encoding="utf-8")
    HUB.write_text(build_issue7_body(claims), encoding="utf-8")
    HTML.parent.mkdir(parents=True, exist_ok=True)
    HTML.write_text(build_html(rows, claims), encoding="utf-8")
    print(f"[OK] {OUT.relative_to(ROOT)}")
    print(f"[OK] {LIST.relative_to(ROOT)}")
    print(f"[OK] {HUB.relative_to(ROOT)}")
    print(f"[OK] {HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
