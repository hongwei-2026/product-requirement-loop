# -*- coding: utf-8 -*-
from pathlib import Path
import base64

base = Path(__file__).resolve().parent
shot = base / "screenshots"

imgs = [
    ("06-docs-center.png", "图1 量潮文档中心：第二大脑文档统一入口"),
    ("07-docs-intention.png", "图2 量潮科技工作意图：记录「我们要什么、为什么」"),
    ("01-agent-engineering-repo.png", "图3 量潮智能体工程档案仓库（quanttide-profile-of-agent-engineering）"),
    ("02-loops-readme.png", "图4 Loop 范式：从人出发回到人；关键是反馈点；用 YAML 定义 steps"),
    ("04-devops-code-spec.png", "图5 对照：devops-code 已有完整 specification.yaml"),
    ("03-product-requirement-index.png", "图6 product-requirement 仅有 index.md，无可执行定义"),
    ("05-product-cloud-requirement.png", "图7 产品云需求：从研发日志捕捉用户故事"),
]


def embed(filename: str, caption: str) -> str:
    data = base64.b64encode((shot / filename).read_bytes()).decode("ascii")
    return f"![{caption}](data:image/png;base64,{data})\n\n*{caption}*\n"


md = """# 实训基地课题申请

**课题名称：** 补全产品需求梳理循环（product-requirement）第 1 步——模糊原文 → 清晰 Markdown  
**方向：** Agent 工程  
**申请人：** （填写姓名）  
**提交日期：** 2026-08-26  

**课题一句话：** 把仓库里已写明但未落地的 product-requirement 循环，先做成「模糊原文 → 清晰 Markdown + 人类反馈点」这一件可运行的任务。

---

## 目录

1. [基本信息与依据材料](#1-基本信息与依据材料)
2. [观察到什么（带截图证据）](#2-观察到什么带截图证据)
3. [盲区判断](#3-盲区判断)
4. [课题范围：只做一个任务](#4-课题范围只做一个任务)
5. [方案设计](#5-方案设计)
6. [最小可运行设计](#6-最小可运行设计)
7. [样例走查（答辩演示）](#7-样例走查答辩演示)
8. [时间安排、支持与风险](#8-时间安排支持与风险)

---

## 1. 基本信息与依据材料

| 项 | 内容 |
|----|------|
| 课题名称 | 补全产品需求梳理循环（product-requirement）第 1 步——模糊原文 → 清晰 Markdown |
| 方向 | Agent 工程 |
| 申请人 | （填写姓名） |
| 提交日期 | 2026-08-26 |

### 依据材料（公开）

1. Agent 工程档案：https://github.com/quanttide/quanttide-profile-of-agent-engineering  
2. Loop 说明：https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/README.md  
3. product-requirement 意图：https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/product-requirement/index.md  
4. devops-code 对照：https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/devops-code/specification.yaml  
5. 产品云需求：https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.md  
6. 文档中心：https://docs.quanttide.com/  

---

## 2. 观察到什么（带截图证据）

以下截图均来自量潮公开仓库与文档中心，日期 2026-08-25。图片已内嵌在本 Markdown 中，用任意 Markdown 预览器打开即可查看。

### 2.1 文档中心在收敛知识入口

群公告将 https://docs.quanttide.com 定位为「第二大脑文档统一入口」。页面上已挂载第二大脑、工作手册、工作意图等多类文档应用，说明公司正在把分散文档收成可稳定访问的生产资产。

"""

md += embed(*imgs[0])
md += embed(*imgs[1])

md += """
### 2.2 Agent 工程把 Loop 当作核心形态

仓库 `quanttide-profile-of-agent-engineering` 定位为**跨 Agent 系统配置层**，集中管理 Zed / OpenCode / Hermes / dsh 等配置；同时在 `default/loops/` 沉淀从实践日志提取的循环范式。

"""

md += embed(*imgs[2])

md += """
`loops/README.md` 明确三点，构成本课题的工程约束：

1. **Loop 范式**：先从人类视角出发，中间交给机器，再回到人类视角。  
2. **Loop ≠ Workflow**：关键是 **反馈点**——一轮后必须与人交互；连续无人交互即退化为 workflow，loop 定义失效。  
3. **承载方式**：用 YAML 定义 steps（比 Markdown 更适合程序读取）；可用 SH / Python 承载执行。

"""

md += embed(*imgs[3])

md += """
### 2.3 成熟循环已落地，可作为模板

`devops-code` 目录同时具备 `requirement.md`、`specification.yaml`、`implementation.py`。YAML 中包含 `entry` / `exit` / `steps`（actor、artifact、check）/ `feedback` / `loop` / `metrics` 等字段，是本课题直接对齐的模板。

"""

md += embed(*imgs[4])

md += """
### 2.4 盲区：product-requirement 只有意图，没有可执行物

`product-requirement/index.md` 已写清：

- **目标**：从蕴含模糊产品需求的原始文本出发，经一次或多次循环，得到对人类、AI、规则引擎都清晰的需求。  
- **三步循环**：① 模糊上下文 → 清晰 Markdown；② Markdown → 半结构化 JSON；③ JSON → 结构化 SQL。  
- **约束**：Markdown 转 JSON 时，AI 必须严格遵循语义，**禁止编造**。

但该目录 **只有 index.md**，没有 `specification.yaml`，也没有实现脚本。

"""

md += embed(*imgs[5])

md += """
**仓库现状对比：**

| 循环 | 说明文档 | specification.yaml | implementation |
|------|----------|:------------------:|:--------------:|
| devops-code | 有 | 有 | 有（LangGraph） |
| devops-plan | 有 | 有 | 有 |
| **product-requirement** | **仅有 index.md** | **无** | **无** |

### 2.5 产品云需求与之同向（上游）

`qtcloud-product/requirement.md` 描述产研负责人从研发日志捕捉用户故事：AI 辅助把零碎话语划分成活动 / 任务 / 故事细节，人工调整后评审定稿。这与 product-requirement 的「模糊原文结构化」是同一条产研链路。

本期 **不做客故事地图 UI**，只做上游最薄、且档案里明确缺失的一步。

"""

md += embed(*imgs[6])

md += """
### 2.6 观察结论

公司已经：

- 定义了 product-requirement 的目标、步骤与「禁止编造」约束；  
- 在 devops-* 上示范了如何用 YAML + 反馈点把 loop 做实；  
- 在产品云需求里表达了「从日志捕捉故事」的产品意图。

**缺口：** `product-requirement` 还停在说明层。本课题选择补 **第 1 步**，做成一件能跑完、能答辩的任务。

---

## 3. 盲区判断

1. **公司已定义、尚未落地**——不是凭空选题，而是补齐档案里公开缺口。  
2. **与现有范式同构**——可直接复用 devops-code 的 YAML 字段与「反馈点」验证方式。  
3. **可切小**——三步里只做第 1 步，三周内能跑通、能演示。  
4. **有下游价值但不绑架本期**——第 1 步跑通后自然可接 JSON；本期明确不把后续步骤算进交付。

---

## 4. 课题范围：只做一个任务

### 4.1 任务定义

> 输入一段模糊的产品 / 业务原始文本 → AI 整理为清晰 Markdown → **停在反馈点等人确认** → 输入 `ok` 则归档；输入 `revise:…` 则带意见再跑一轮。

### 4.2 交付物

| 产出 | 说明 |
|------|------|
| `specification.yaml` | 只描述第 1 步 + feedback + loop + metrics，字段对齐 devops-code |
| `run.py` | 本地 CLI：读原文、生成 Markdown、人工 interrupt、写回产物与 metrics |
| `examples/` | 1 个脱敏样例输入 + 至少 1 次完整跑通结果（含一次 revise 更佳） |
| `README.md` | 安装、运行、反馈点操作、验收清单、非目标 |

### 4.3 明确不做

- 不做第 2、3 步（Markdown → JSON、JSON → SQL）  
- 不做用户故事地图画布 / 拖拽 UI  
- 不接入真实 journal 仓库、飞书、邮箱  
- 不做多 Agent 编排；一条「整理 + 人类确认」循环即可  

### 4.4 为什么只做第 1 步

1. index.md 的三步里，第 1 步是后续一切的输入质量闸门。  
2. 「禁止编造」在第 1 步就可以用「来源摘录 + 人工反馈」落地。  
3. 体量匹配实训周期：三周内可交付、可演示。

---

## 5. 方案设计

### 5.1 输入

- 主输入：`input/raw.md`（口语化、不完整、背景与诉求混杂的原文）  
- 反馈输入：终端中的 `ok` 或 `revise: <意见>`  

### 5.2 输出结构（默认模板）

```markdown
# 需求说明（整理稿）

## 背景
## 目标用户
## 要做什么
## 明确不做
## 待确认问题
## 来源摘录（原文关键句，便于核对无编造）
```

### 5.3 禁止编造（怎么落地）

1. **提示词约束**：只重组、不发明；原文没写清的内容写入「待确认问题」。  
2. **来源摘录**：输出末尾保留原文关键句，答辩时可人工对照。  
3. **验收抽查**：整理稿中每条「要做什么」都必须能在原文找到依据。  

### 5.4 反馈点（Loop 的灵魂）

1. AI 写出 `output/clear.md` 后必须暂停。  
2. 终端打印全文，等待人类指令。  
3. `ok` → 复制为 `output/accepted.md`，写入 `metrics.json`，结束。  
4. `revise: …` → 把意见并入上下文，重跑整理步骤。  
5. 无人确认直接结束 → 记为失败用例（对齐 loops README：人未参与的轮次视为失效）。

### 5.5 模型策略

- 有 API Key（环境变量）：调用真实 LLM。  
- 无 API Key：进入 **mock 模式**（按模板规则拼 Markdown），保证反馈点机制仍可演示。

### 5.6 验收标准

1. 产物齐备：yaml、脚本、样例、README。  
2. 反馈点真实触发；建议保留一次 revise 记录。  
3. 同一输入连续跑两次，标题结构稳定。  
4. 人工核对：无原文之外的新功能点。  
5. （加分）metrics 记录 rounds / corrections / time。

---

## 6. 最小可运行设计

### 6.1 `specification.yaml` 草案

```yaml
name: product-requirement-step1
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
```

### 6.2 运行流程

```text
python run.py --input examples/sample-raw.md
  → 生成 output/clear.md
  → [反馈点] 显示内容，等待 ok / revise
  → revise 则重跑；ok 则写入 output/accepted.md + metrics.json
```

### 6.3 建议目录结构

```text
product-requirement-step1/
├── specification.yaml
├── run.py
├── README.md
├── examples/
│   └── sample-raw.md
└── output/
    ├── clear.md
    ├── accepted.md
    └── metrics.json
```

---

## 7. 样例走查（答辩演示）

### 7.1 样例输入（公开材料改写，非真实客户）

```text
我们想做个东西，产研的人平时日志很乱，希望 AI 能帮着从话里抓出用户要什么，
先不用图画布，能整理成看得懂的需求说明就行，别自己编功能。
人要能改，改完再出一版。
```

### 7.2 期望整理方向

| 区块 | 应出现的要点 |
|------|----------------|
| 背景 | 日志零碎，需求难沉淀 |
| 要做什么 | 模糊话 → 清晰需求说明；支持人工修订后再生成 |
| 明确不做 | 故事地图画布；禁止编造功能 |
| 待确认 | 日志来源格式、输出标题是否固定 |

### 7.3 现场 5 分钟流程

1. 运行脚本，展示第一版 Markdown。  
2. 输入一句 revise，例如：「把『明确不做』写得更清楚」。  
3. 展示第二版。  
4. 输入 ok，展示 `accepted.md` 与 `metrics.json`。  
5. 口头说明：为何这符合 Loop（有反馈点），以及为何范围只停在第 1 步。

---

## 8. 时间安排、支持与风险

### 8.1 时间安排

| 时间 | 动作 |
|------|------|
| 08-26 中午前 | 提交本课题申请 |
| 08-27 ~ 08-31 | 定稿 yaml；mock 跑通反馈点 |
| 09-01 ~ 09-07 | 接真实 LLM；补禁止编造抽查；固化样例 |
| 09-08 ~ 09-16 | 打磨 README 与答辩；最多提交三次 |

### 8.2 需要的支持

1. 允许基于公开仓库规范做外部实验；成果可先放个人仓，合适再提 PR。  
2. 不强制指定模型；提供 API Key + mock 双轨即可。  
3. （可选）若内部已有 Markdown 标题规范，请告知；否则用第 5.2 节默认模板。

### 8.3 风险与应对

| 风险 | 应对 |
|------|------|
| 模型编造 | 提示词约束 + 来源摘录 + 人类反馈点 |
| 无 API Key | mock 模式仍演示 loop 机制 |
| 范围膨胀 | 书面锁定「只做第 1 步」 |

---

## 9. 提交说明

**提交文件：** 本 `课题申请.md`（已含全部截图，可直接提交）

**邮件正文：** 见同目录 `提交邮件正文.txt`

**一句话总结：** 把 `product-requirement` 循环里已经写明、但尚未落地的 **第 1 步**，做成带人类反馈点的最小可运行 Agent 任务。
"""

out = base / "课题申请.md"
out.write_text(md, encoding="utf-8")
print("wrote", out, "bytes", out.stat().st_size)
