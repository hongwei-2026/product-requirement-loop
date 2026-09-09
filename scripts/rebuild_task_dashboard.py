#!/usr/bin/env python3
"""根据计分板 + 认领状态重建「任务仪表盘」。

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
HTML = ROOT / "docs" / "dashboard" / "index.html"

SEED = ["hongwei-2026", "hl019", "Jerrybao99", "likexin105"]

TASKS = [
    {"num": 1, "diff": "简单", "pts": 10, "title": "工作台顶栏展示 LLM provider/model/超时摘要", "why": "排障可观测"},
    {"num": 2, "diff": "简单", "pts": 15, "title": "统一「服务宕机」与「AI 超时」提示文案", "why": "减少误报连不上服务"},
    {"num": 3, "diff": "中等", "pts": 30, "title": "Step1/Step2 请求心跳与超时重试", "why": "同步长请求体验"},
    {"num": 4, "diff": "中等", "pts": 35, "title": "待审库轻量搜索与状态过滤", "why": "短队列增强，非重型分组"},
    {"num": 5, "diff": "难", "pts": 60, "title": "Step1/Step2 异步任务 + 轮询/SSE", "why": "根治同步超时断连"},
    {"num": 6, "diff": "难", "pts": 50, "title": "长日志压力测试流水（脚本+CI，无真实 Key）", "why": "压测与回归门禁"},
    {
        "num": 8,
        "diff": "难",
        "pts": 55,
        "title": "待审库「工作台级」全部分组 + 搜索",
        "why": "此前结项「本期不做」；现为可选难题",
    },
    {"num": 9, "diff": "特难", "pts": 75, "title": "定稿导出产品云可对齐的 requirement.json 包", "why": "量潮下游文件级闭环"},
    {"num": 10, "diff": "特难", "pts": 80, "title": "第二大脑 Context 导出包", "why": "对齐 second-brain 资产观"},
    {"num": 11, "diff": "特难", "pts": 70, "title": "SemVer 发布门禁（标签+CHANGELOG）", "why": "对齐 release 章程"},
    {"num": 12, "diff": "特难", "pts": 75, "title": "工作台覆盖率/uncovered 面板 + 人确认", "why": "人审质量门扩展"},
    {"num": 13, "diff": "特难", "pts": 70, "title": "故事/定稿修订时间线 UI", "why": "审核可审计"},
    {"num": 14, "diff": "特难", "pts": 75, "title": "打叉理由分析看板", "why": "理由码回流运营"},
    {"num": 15, "diff": "特难", "pts": 80, "title": "待审库指派/交接/超时回收（SLA）", "why": "多人协作扩展"},
    {"num": 16, "diff": "特难", "pts": 80, "title": "官方日志 Inbox 强去重+冲突处理台", "why": "量潮日志入口质量"},
    {"num": 17, "diff": "特难", "pts": 85, "title": "批量 Step1 通过后入队 Step2 草稿", "why": "吞吐且守人审"},
    {"num": 18, "diff": "特难", "pts": 85, "title": "Prompt 版本钉死 + prompt_sha 审计", "why": "Agent Loop 可复现"},
    {"num": 19, "diff": "特难", "pts": 90, "title": "多 trial 矩阵 case-02+ 与 CI 金标", "why": "证据链厚度"},
    {"num": 20, "diff": "特难", "pts": 90, "title": "运行时安全切换 LLM + 健康探测", "why": "运维扩展，禁 Key 进仓"},
    {"num": 21, "diff": "特难", "pts": 75, "title": "错误分类回流 verify_lessons", "why": "踩坑回流 CI"},
    {"num": 22, "diff": "特难", "pts": 85, "title": "待审库/定稿 JSON↔SQLite 单一数据源", "why": "扩展前收敛双写"},
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
        "| Issue | 状态 | 当前人 | 更新时间 |",
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
            url = f"https://github.com/hongwei-2026/product-requirement-loop/issues/{k}"
            lines.append(
                f"| [#{k}]({url}) | {st} | [@{user}](https://github.com/{user}) | {v.get('updated', '—')} |"
            )

    lines += [
        "",
        "## 任务看板",
        "",
        "| Issue | 难度 | 分值 | 标题 | 认领状态 | 当前人 | 已计分 |",
        "|-------|------|------|------|----------|--------|--------|",
    ]
    for t in TASKS:
        n = t["num"]
        c = claims.get(str(n)) or claims.get(n) or {}
        if isinstance(c, dict) and c.get("status"):
            st = STATUS_CN.get(c["status"], c["status"])
            who = f"@{c.get('user')}" if c.get("user") else "—"
        else:
            st, who = STATUS_CN["open"], "—"
        scored = ", ".join(by_issue.get(n, [])) or "—"
        url = f"https://github.com/hongwei-2026/product-requirement-loop/issues/{n}"
        lines.append(
            f"| [#{n}]({url}) | {t['diff']} | {t['pts']} | {t['title']} | {st} | {who} | {scored} |"
        )

    lines += [
        "",
        "## 同步与放弃（命令）",
        "",
        "| 你想做什么 | 在任务 Issue 评论 | 仪表盘会怎样 |",
        "|------------|-------------------|--------------|",
        "| 接任务 | `/claim` | 出现在「进行中的认领」 |",
        "| 维护者正式锁定 | `/accept @用户` | 状态变为已锁定 |",
        "| **自己放弃**（已 claim 或已锁定） | `/release` 或 `/cancel` | **自动从进行中删除**，任务重回开放 |",
        "| 维护者清掉别人的认领 | `/reject-claim` | 同上，自动清除 |",
        "| 完成后记分 | `/score N` | 排行榜加分；认领标为已完成 |",
        "",
        "必审人：`hongwei-2026` · `hl019` · `Jerrybao99` · `likexin105`",
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
            f"<td><a href='https://github.com/hongwei-2026/product-requirement-loop/issues/{k}'>#{k}</a></td>"
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
        f"<td><a href='https://github.com/hongwei-2026/product-requirement-loop/issues/{t['num']}'>#{t['num']}</a></td>"
        f"<td>{t['diff']}</td><td>{t['pts']}</td><td>{t['title']}</td>"
        f"<td>{STATUS_CN.get((claims.get(str(t['num'])) or {}).get('status'), '开放可接')}</td>"
        f"<td>{('@'+(claims.get(str(t['num'])) or {}).get('user')) if (claims.get(str(t['num'])) or {}).get('user') else '—'}</td>"
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
    main {{ max-width:1000px; margin:0 auto; padding:32px 20px 64px; }}
    h1 {{ margin:0 0 8px; font-size:1.6rem; }}
    .sub {{ color:var(--muted); margin:0 0 22px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin:0 0 16px; }}
    table {{ width:100%; border-collapse:collapse; font-size:0.94rem; }}
    th,td {{ text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:var(--muted); font-size:0.78rem; }}
    a {{ color:var(--accent); text-decoration:none; }}
  </style>
</head>
<body>
<main>
  <h1>实训任务仪表盘</h1>
  <p class="sub">{now} · <a href="https://github.com/hongwei-2026/product-requirement-loop/issues/7">#7 总入口</a></p>
  <section class="card"><h2>积分排行榜</h2>
    <table><thead><tr><th>#</th><th>GitHub</th><th>总分</th></tr></thead><tbody>{rank_rows}</tbody></table>
  </section>
  <section class="card"><h2>进行中的认领</h2>
    <table><thead><tr><th>Issue</th><th>状态</th><th>人</th><th>更新</th></tr></thead><tbody>{claim_rows}</tbody></table>
    <p class="sub">放弃请在 Issue 评论 <code>/release</code> 或 <code>/cancel</code>，记录会自动删除。</p>
  </section>
  <section class="card"><h2>任务看板</h2>
    <table><thead><tr><th>Issue</th><th>难度</th><th>分</th><th>标题</th><th>状态</th><th>人</th></tr></thead><tbody>{task_rows}</tbody></table>
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
    HTML.parent.mkdir(parents=True, exist_ok=True)
    HTML.write_text(build_html(rows, claims), encoding="utf-8")
    print(f"[OK] {OUT.relative_to(ROOT)}")
    print(f"[OK] {HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
