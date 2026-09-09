#!/usr/bin/env python3
"""根据计分板与任务索引重建「任务仪表盘」Markdown。

Usage:
  python scripts/rebuild_task_dashboard.py
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORE = ROOT / "docs" / "交付" / "任务计分板.md"
OUT = ROOT / "docs" / "交付" / "任务仪表盘.md"
HTML = ROOT / "docs" / "dashboard" / "index.html"

# 种子学员/审阅人（无分也展示）
SEED = ["hongwei-2026", "hl019", "Jerrybao99", "likexin105"]

# 任务目录（可随 Issue 增删改）
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
        "why": "此前结项明确「本期不做」；现作为可选高难度增强",
    },
]


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


def build_md(rows: list[tuple[str, str, int, str]]) -> str:
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
        f"> 自动生成时间：{now}  ·  数据源：[任务计分板.md](./任务计分板.md)  ·  总入口：[Issue #7](https://github.com/hongwei-2026/product-requirement-loop/issues/7)",
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
        "## 任务看板",
        "",
        "| Issue | 难度 | 分值 | 标题 | 为何做 | 已计分记录 |",
        "|-------|------|------|------|--------|------------|",
    ]
    for t in TASKS:
        n = t["num"]
        scored = ", ".join(by_issue.get(n, [])) or "—"
        url = f"https://github.com/hongwei-2026/product-requirement-loop/issues/{n}"
        lines.append(
            f"| [#{n}]({url}) | {t['diff']} | {t['pts']} | {t['title']} | {t['why']} | {scored} |"
        )

    lines += [
        "",
        "## 怎么得分",
        "",
        "1. 在任务 Issue 评论 `/claim` → Design PR → 邮件 `feizi_050920@qq.com`",
        "2. 维护者 `/accept @你` 后实现，PR 需四位必审人全部 Approve",
        "3. 合并后维护者或必审人评论 `/score N`，本仪表盘自动刷新",
        "",
        "必审人：`hongwei-2026` · `hl019` · `Jerrybao99` · `likexin105`",
        "",
    ]
    return "\n".join(lines)


def build_html(md_table_rank: str, md_tasks: str) -> str:
    # simple static HTML dashboard for browsing / optional Pages
    score_text = SCORE.read_text(encoding="utf-8") if SCORE.exists() else ""
    rows = parse_scores(score_text)
    totals: dict[str, int] = {u: 0 for u in SEED}
    for _, user, _, pts, _ in rows:
        totals[user] = totals.get(user, 0) + pts
    ranked = sorted(totals.items(), key=lambda x: (-x[1], x[0].lower()))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rank_rows = "".join(
        f"<tr><td>{i}</td><td><a href='https://github.com/{u}'>@{u}</a></td><td><b>{p}</b></td></tr>"
        for i, (u, p) in enumerate(ranked, 1)
    )
    task_rows = "".join(
        "<tr>"
        f"<td><a href='https://github.com/hongwei-2026/product-requirement-loop/issues/{t['num']}'>#{t['num']}</a></td>"
        f"<td>{t['diff']}</td><td>{t['pts']}</td><td>{t['title']}</td><td>{t['why']}</td>"
        "</tr>"
        for t in TASKS
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>实训任务仪表盘 · product-requirement-loop</title>
  <style>
    :root {{ --bg:#0f1419; --card:#1a2332; --text:#e7ecf3; --muted:#9aa7b8; --accent:#3d8bfd; --line:#2a3545; }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, "Segoe UI", sans-serif; background:linear-gradient(160deg,#0f1419,#152033 50%,#101820); color:var(--text); }}
    main {{ max-width:980px; margin:0 auto; padding:32px 20px 64px; }}
    h1 {{ font-size:1.6rem; margin:0 0 8px; }}
    .sub {{ color:var(--muted); margin:0 0 24px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin:0 0 18px; }}
    table {{ width:100%; border-collapse:collapse; font-size:0.95rem; }}
    th, td {{ text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
    th {{ color:var(--muted); font-weight:600; font-size:0.8rem; letter-spacing:.04em; }}
    a {{ color:var(--accent); text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#243247; color:#c9d7ea; font-size:12px; }}
  </style>
</head>
<body>
<main>
  <h1>实训任务仪表盘</h1>
  <p class="sub">更新于 {now} · <a href="https://github.com/hongwei-2026/product-requirement-loop/issues/7">总入口 #7</a> · <a href="https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E4%BB%BB%E5%8A%A1%E8%AE%A1%E5%88%86%E6%9D%BF.md">计分板</a></p>
  <section class="card">
    <h2>积分排行榜 <span class="pill">/score 后自动刷新</span></h2>
    <table>
      <thead><tr><th>#</th><th>GitHub</th><th>总分</th></tr></thead>
      <tbody>{rank_rows}</tbody>
    </table>
  </section>
  <section class="card">
    <h2>任务看板</h2>
    <table>
      <thead><tr><th>Issue</th><th>难度</th><th>分</th><th>标题</th><th>为何做</th></tr></thead>
      <tbody>{task_rows}</tbody>
    </table>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    text = SCORE.read_text(encoding="utf-8") if SCORE.exists() else ""
    rows = parse_scores(text)
    OUT.write_text(build_md(rows), encoding="utf-8")
    HTML.parent.mkdir(parents=True, exist_ok=True)
    HTML.write_text(build_html("", ""), encoding="utf-8")
    print(f"[OK] wrote {OUT.relative_to(ROOT)}")
    print(f"[OK] wrote {HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
