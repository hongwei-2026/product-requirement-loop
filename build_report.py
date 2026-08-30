# -*- coding: utf-8 -*-
from pathlib import Path
import base64

base = Path(__file__).resolve().parent
shot = base / "screenshots"
imgs = [
    ("01-agent-engineering-repo.png", "图1 量潮智能体工程档案仓库（quanttide-profile-of-agent-engineering）"),
    ("02-loops-readme.png", "图2 Loop 范式：从人出发、回到人；关键是反馈点；用 YAML 定义 steps"),
    ("03-product-requirement-index.png", "图3 product-requirement 目录：只有目标/三步循环/约束，没有 specification.yaml"),
    ("04-devops-code-spec.png", "图4 对照：devops-code 已有完整 specification.yaml（entry/exit/steps/artifact/check）"),
    ("05-product-cloud-requirement.png", "图5 产品云需求：从研发日志捕捉用户故事，AI 辅助划分层级后人工调整"),
    ("06-docs-center.png", "图6 量潮文档中心：第二大脑文档统一入口"),
    ("07-docs-intention.png", "图7 量潮科技工作意图：记录「我们要什么、为什么」"),
]


def img_tag(filename: str, caption: str) -> str:
    data = base64.b64encode((shot / filename).read_bytes()).decode("ascii")
    return (
        "<figure>\n"
        f'  <img src="data:image/png;base64,{data}" alt="{caption}" />\n'
        f"  <figcaption>{caption}</figcaption>\n"
        "</figure>\n"
    )


figures = {f"FIG{i+1}": img_tag(fn, cap) for i, (fn, cap) in enumerate(imgs)}

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>实训基地课题申请｜product-requirement 第1步</title>
<style>
  :root {{ --fg:#1a1a1a; --muted:#555; --line:#ddd; --bg:#f7f8fa; --card:#fff; --accent:#0b57d0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; color:var(--fg); background:var(--bg); line-height:1.75; }}
  .wrap {{ max-width: 920px; margin: 0 auto; padding: 32px 20px 80px; }}
  header {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:28px; margin-bottom:24px; }}
  h1 {{ margin:0 0 12px; font-size:1.55rem; line-height:1.35; }}
  .meta p {{ margin:4px 0; color:var(--muted); }}
  h2 {{ margin-top:2.2em; border-bottom:1px solid var(--line); padding-bottom:6px; font-size:1.3rem; }}
  h3 {{ margin-top:1.35em; font-size:1.08rem; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); margin:12px 0 20px; }}
  th, td {{ border:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; font-size:0.95rem; }}
  th {{ background:#f3f5f8; }}
  pre {{ background:#0f172a; color:#e2e8f0; padding:16px; border-radius:10px; overflow:auto; font-size:0.88rem; }}
  code {{ font-family: ui-monospace, Consolas, monospace; }}
  ul, ol {{ padding-left: 1.3em; }}
  .callout {{ background:#eef5ff; border-left:4px solid var(--accent); padding:12px 16px; border-radius:0 8px 8px 0; margin:16px 0; }}
  .warn {{ background:#fff7e8; border-left-color:#d97706; }}
  figure {{ margin:16px 0 28px; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  figure img {{ display:block; width:100%; height:auto; }}
  figcaption {{ padding:10px 14px; color:var(--muted); font-size:0.9rem; border-top:1px solid var(--line); }}
  a {{ color:var(--accent); }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>实训基地课题申请<br/>补全产品需求梳理循环（product-requirement）第 1 步</h1>
  <div class="meta">
    <p><strong>方向：</strong>Agent 工程</p>
    <p><strong>申请人：</strong>（填写姓名）</p>
    <p><strong>提交日期：</strong>2026-08-26</p>
    <p><strong>课题一句话：</strong>把仓库里已写明但未落地的 product-requirement 循环，先做成「模糊原文 → 清晰 Markdown + 人类反馈点」这一件可运行的任务。</p>
  </div>
</header>

<nav>
  <h2>目录</h2>
  <ol>
    <li><a href="#s1">观察依据与截图证据</a></li>
    <li><a href="#s2">盲区判断</a></li>
    <li><a href="#s3">课题范围：只做一个任务</a></li>
    <li><a href="#s4">方案设计</a></li>
    <li><a href="#s5">最小可运行设计</a></li>
    <li><a href="#s6">样例走查</a></li>
    <li><a href="#s7">计划、支持与风险</a></li>
  </ol>
</nav>

<section id="s1">
<h2>1. 观察依据与截图证据</h2>
<p>以下材料来自量潮公开仓库与文档中心，截图日期 2026-08-25。本页图片已内嵌，用浏览器打开即可直接看到。</p>

<h3>1.1 文档中心已上线</h3>
<p>群公告将文档中心定位为「第二大脑文档统一入口」。页面已挂载第二大脑、工作手册、工作意图等应用，说明知识入口正在收敛为可对外访问的生产资产。</p>
{figures['FIG6']}
{figures['FIG7']}

<h3>1.2 Agent 工程档案与 Loop 范式</h3>
<p>仓库 <code>quanttide-profile-of-agent-engineering</code> 是跨 Agent 配置层，并在 <code>default/loops/</code> 沉淀循环范式。</p>
{figures['FIG1']}
<p><code>loops/README.md</code> 明确：Loop 从人出发再回到人；关键是<strong>反馈点</strong>；用 YAML 定义 steps。</p>
{figures['FIG2']}
<p>成熟对照：<code>devops-code</code> 已有完整 <code>specification.yaml</code>（entry/exit/steps/artifact/check）。</p>
{figures['FIG4']}

<h3>1.3 盲区：product-requirement 只有说明</h3>
<p><code>product-requirement/index.md</code> 已写目标与三步（模糊→Markdown→JSON→SQL），并强调禁止编造；但目录内没有 yaml、没有实现脚本。</p>
{figures['FIG3']}
<div class="callout">
<table>
  <tr><th>循环</th><th>说明文档</th><th>specification.yaml</th><th>implementation</th></tr>
  <tr><td>devops-code</td><td>有</td><td>有</td><td>有</td></tr>
  <tr><td>devops-plan</td><td>有</td><td>有</td><td>有</td></tr>
  <tr><td><strong>product-requirement</strong></td><td><strong>仅 index.md</strong></td><td><strong>无</strong></td><td><strong>无</strong></td></tr>
</table>
</div>

<h3>1.4 产品云需求同向</h3>
<p>产品云要求从研发日志捕捉用户故事，AI 划分后人工调整。本期只做上游最薄一步：模糊原文→清晰 Markdown。</p>
{figures['FIG5']}
</section>

<section id="s2">
<h2>2. 盲区判断</h2>
<ol>
  <li>公司已定义、尚未落地——不是空想题目。</li>
  <li>与 devops-code 的 YAML/反馈点范式同构，答辩好对齐。</li>
  <li>三步只做第 1 步，三周可完成。</li>
  <li>后续可接 JSON，但不纳入本期交付。</li>
</ol>
</section>

<section id="s3">
<h2>3. 课题范围：只做一个任务</h2>
<div class="callout">
<strong>任务：</strong>模糊原文 → AI 整理为清晰 Markdown → 停在反馈点等人确认 → ok 归档 / revise 再跑一轮。
</div>
<h3>交付</h3>
<table>
  <tr><th>产出</th><th>说明</th></tr>
  <tr><td>specification.yaml</td><td>第 1 步 + feedback + loop + metrics</td></tr>
  <tr><td>run.py</td><td>本地可跑，含人工 interrupt</td></tr>
  <tr><td>examples/</td><td>1 个脱敏样例 + 跑通结果</td></tr>
  <tr><td>README.md</td><td>运行、验收、非目标</td></tr>
</table>
<h3>不做</h3>
<ul>
  <li>第 2/3 步（JSON、SQL）</li>
  <li>故事地图 UI</li>
  <li>接 journal / 飞书 / 邮箱</li>
  <li>多 Agent 编排</li>
</ul>
</section>

<section id="s4">
<h2>4. 方案设计</h2>
<h3>4.1 输入 / 输出</h3>
<p>输入：<code>input/raw.md</code>。输出默认结构：</p>
<pre># 需求说明（整理稿）

## 背景
## 目标用户
## 要做什么
## 明确不做
## 待确认问题
## 来源摘录（原文关键句，便于核对无编造）
</pre>
<h3>4.2 禁止编造</h3>
<ol>
  <li>提示词：只重组、不发明；不确定写入「待确认问题」。</li>
  <li>保留「来源摘录」便于对照。</li>
  <li>验收：每条「要做什么」都能在原文找到依据。</li>
</ol>
<h3>4.3 反馈点</h3>
<ul>
  <li>写出 clear.md 后必须暂停，等待 <code>ok</code> 或 <code>revise:…</code>。</li>
  <li>无人确认直接结束 = 失败（符合 loops README）。</li>
</ul>
<h3>4.4 验收</h3>
<ol>
  <li>产物齐备</li>
  <li>反馈点真实触发</li>
  <li>同一输入跑两次结构稳定</li>
  <li>人工核对无编造</li>
</ol>
</section>

<section id="s5">
<h2>5. 最小可运行设计</h2>
<pre>name: product-requirement-step1
description: 模糊原文 → 清晰 Markdown（仅第 1 步）
entry: 人类提供模糊原始文本
exit: 人类确认 Markdown 无编造、本期结束

steps:
  - name: 整理为清晰 Markdown
    actor: ai
    artifact: output/clear.md
    check: 结构完整；不出现原文没有的需求点

feedback:
  - after: 整理为清晰 Markdown
    actor: human
    ask: 是否接受？若否请给出 revise 意见

loop:
  condition: 人类 revise → 带意见重跑整理步骤
  exit: 人类输入 ok

metrics:
  - rounds
  - corrections
  - time
</pre>
<pre>python run.py --input examples/sample-raw.md
  → 生成 output/clear.md
  → [反馈点] 等待 ok / revise
  → ok → output/accepted.md + metrics.json
</pre>
<p>无 API Key 时走 mock 模式，仍可演示反馈点机制。</p>
</section>

<section id="s6">
<h2>6. 样例走查（答辩 5 分钟）</h2>
<pre>我们想做个东西，产研的人平时日志很乱，希望 AI 能帮着从话里抓出用户要什么，
先不用图画布，能整理成看得懂的需求说明就行，别自己编功能。
人要能改，改完再出一版。
</pre>
<p>现场：跑脚本 → 读输出 → 输入一句 revise → 再出一版 → ok → 展示 metrics。</p>
</section>

<section id="s7">
<h2>7. 计划、支持与风险</h2>
<table>
  <tr><th>时间</th><th>动作</th></tr>
  <tr><td>08-26 中午前</td><td>提交本申请</td></tr>
  <tr><td>08-27 ~ 08-31</td><td>yaml + mock 反馈点</td></tr>
  <tr><td>09-01 ~ 09-07</td><td>接 LLM + 样例</td></tr>
  <tr><td>09-08 ~ 09-16</td><td>打磨与答辩</td></tr>
</table>
<ol>
  <li>允许基于公开规范做外部实验，合适再 PR。</li>
  <li>模型：API Key + mock 双轨。</li>
  <li>可选：内部 Markdown 标题规范。</li>
</ol>
<div class="callout warn">
<strong>怎么看截图：</strong>请用浏览器打开本 HTML（双击即可）。同目录 <code>screenshots/</code> 也有原始 PNG；Markdown 预览不一定显示相对路径图片。
</div>
</section>
</div>
</body>
</html>
"""

out = base / "课题申请-详细版.html"
out.write_text(html, encoding="utf-8")
print("wrote", out, "bytes", out.stat().st_size)
