# product-requirement-loop

量潮 **产品需求梳理智能体**（product-requirement Loop）交付仓库。

[![CI](https://github.com/hongwei-2026/product-requirement-loop/actions/workflows/ci.yml/badge.svg)](https://github.com/hongwei-2026/product-requirement-loop/actions/workflows/ci.yml)

## 5 个入口（结项 / 公司端先看这些）

| # | 你要做什么 | 打开 |
|---|------------|------|
| 1 | **怎么跑起来** | 下方「快速开始」；或 `start-with-ai.bat` / `start-with-ai.sh` |
| 2 | **怎么验收** | [`docs/交付/结项说明-给审阅同事.md`](./docs/交付/结项说明-给审阅同事.md) · [`trial-report.md`](./project/trials/case-01/trial-report.md) · 双击 `验收门槛.bat` |
| 3 | **结项说明** | [`docs/交付/结项说明-给审阅同事.md`](./docs/交付/结项说明-给审阅同事.md)（证据位置、CLI→Web、执行器） |
| 4 | **操作手册** | [`docs/交付/产品操作手册.md`](./docs/交付/产品操作手册.md)（与产品内 UI 手册一致） |
| 5 | **问题与处理** | [`docs/交付/问题反馈整理-2026-09-08.md`](./docs/交付/问题反馈整理-2026-09-08.md) |

交付目录总表：[`docs/交付/README.md`](./docs/交付/README.md)  
安全：[`docs/交付/安全说明.md`](./docs/交付/安全说明.md)

> `docs/阶段*`、`docs/自测/`、`docs/答辩总报告/` 是**过程材料**，不是结项必读。

---

## 快速开始

### Windows

1. 双击 `setup阶段1环境.bat`（首次）  
2. 复制 `project/.env.example` → `project/.env`，填写 Key（见示例里的 `LLM_*`）  
3. （推荐）`project\.venv\Scripts\python.exe scripts\sync_journals.py`  
4. 双击 **`start-with-ai.bat`**（黑窗勿关）  
5. 打开 **http://127.0.0.1:8765/** · 演示账号 `demo` / `demo1234`

### Mac / Linux

```bash
chmod +x setup.sh start-with-ai.sh
./setup.sh
cp project/.env.example project/.env   # 填写 Key
project/.venv/bin/python scripts/sync_journals.py
./start-with-ai.sh
```

---

## 一键自检（CI 同源）

```bat
cd /d D:\量潮科技\课题申请-product-requirement-loop
验收门槛.bat
project\.venv\Scripts\python.exe scripts\verify_docs_layout.py
project\.venv\Scripts\python.exe scripts\verify_lessons.py
project\.venv\Scripts\python.exe scripts\verify_security.py
```

立项 6 条门槛：`scripts\verify_acceptance.py`  
多模型冒烟（需本地 Key，**勿提交**）：`scripts\smoke_llm_providers.py`

> 不要在上一级目录 `D:\量潮科技` 直接跑命令。

---

## 结项审阅要点（摘要）

1. **验收实测**：[`project/trials/case-01/trial-report.md`](./project/trials/case-01/trial-report.md)  
2. **为何有 Web**：立项「不做 UI」是控范围；Web 为「同事能用起来」加餐，见结项说明  
3. **执行器**：`implementation.py` 仍为官方入口；`loop_runner.py` 做闭环编排  

---

## 产品能力

| 能力 | 说明 |
|------|------|
| 日志库 | 官方多产品流 × 按日日志；可筛选/粘贴/上传 |
| 工作台 | Step1→人确认→锁定→Step2→人确认→check→定稿 |
| 打叉重跑 | 只重跑当前步；五种原因码 |
| 可追溯 | `accepted.json` 含 revisions / journal_id |

---

## 脚本入口

| 操作 | 说明 |
|------|------|
| `start-with-ai.bat` / `.sh` | 产品 Web |
| `setup阶段1环境.bat` / `setup.sh` | 首次环境 |
| `scripts/sync_journals.py` | 同步官方日志 |
| `scripts/verify_acceptance.py` | 立项门槛 |
| `scripts/verify_docs_layout.py` | 交付门面 / 文档布局门禁 |
| `scripts/verify_lessons.py` | 踩坑回流 |
| `scripts/verify_security.py` | 安全门禁 |
| `run-stage4-loop.bat` | CLI 闭环备用 |

---

## 目录（社区态 · 轻量）

```
├── README.md                 ← 本页（5 入口）
├── start-with-ai.bat / .sh
├── docs/交付/                ← 对外唯一门面
├── docs/阶段* · 自测 · 答辩  ← 过程材料（非必读）
├── project/                  ← 代码 / case-01 / trial-report
└── scripts/                  ← 服务 / 同步 / 自检
```
