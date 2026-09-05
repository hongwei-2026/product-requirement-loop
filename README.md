# product-requirement-loop

量潮 **产品需求梳理智能体**（product-requirement Loop）交付仓库。

[![CI](https://github.com/hongwei-2026/product-requirement-loop/actions/workflows/ci.yml/badge.svg)](https://github.com/hongwei-2026/product-requirement-loop/actions/workflows/ci.yml)

## 结项审阅（请先看）

审阅同事请先打开：

**[docs/交付/结项说明-给审阅同事.md](./docs/交付/结项说明-给审阅同事.md)** · **[docs/交付/安全说明.md](./docs/交付/安全说明.md)**

里面写清了三件事：

1. **验收实测在哪**：[`project/trials/case-01/trial-report.md`](./project/trials/case-01/trial-report.md)（立项 6 条门槛对照表）  
2. **为什么立项写「不做 UI」却交付了 Web**  
3. **`loop_runner.py` 与官方 LangGraph `implementation.py` 的关系**

一键复验门槛（任选一种）：

- **最省事：** 进入本仓库文件夹后，双击 **`验收门槛.bat`**
- 或先 `cd` 进本仓库再跑：

```bat
cd /d D:\量潮科技\课题申请-product-requirement-loop
project\.venv\Scripts\python.exe scripts\verify_acceptance.py
```

> 不要在上一级目录 `D:\量潮科技` 直接跑上面的命令，会报「找不到 project」。

---

## 交付快速开始

### Windows

1. 双击 `setup阶段1环境.bat`（首次）  
2. 复制 `project/.env.example` → `project/.env`，填写 `AGNES_API_KEY`  
3. （推荐）同步官方日志库：

```bat
project\.venv\Scripts\python.exe scripts\sync_journals.py
```

4. 双击 **`start-with-ai.bat`**（黑窗勿关）  
5. 浏览器打开 **http://127.0.0.1:8765/**

### Mac / Linux

```bash
chmod +x setup.sh start-with-ai.sh
./setup.sh
cp project/.env.example project/.env   # 填写 AGNES_API_KEY
project/.venv/bin/python scripts/sync_journals.py   # 推荐
./start-with-ai.sh                     # 终端勿关
```

浏览器打开 **http://127.0.0.1:8765/**

### 使用说明

**[docs/交付/产品操作手册.md](./docs/交付/产品操作手册.md)**  
**[docs/delivery-guide/项目功能全景说明.md](./docs/delivery-guide/项目功能全景说明.md)**（故事版 + 实机截图）

演示账号：`demo` / `demo1234`

---

## 登录与数据库

- 登录页：`http://127.0.0.1:8765/login.html`
- 数据库（SQLite）：`project/data/product_requirement.db`  
  （用户、会话、审核历史、定稿档案、待人审）

---

## 交付自检

```bash
# 服务已启动时
python scripts/verify_delivery.py
python scripts/verify_enterprise.py

# 立项 6 条门槛（不依赖 Web）
python scripts/verify_acceptance.py
```

全量课题自测（可选）：

```bash
python scripts/verify_all.py --write-reports
```

---

## 产品能力

| 能力 | 说明 |
|------|------|
| 日志库 | 官方多产品流 × 按日日志；可筛选/粘贴/上传 |
| 工作台 | Step1→人确认→锁定→Step2→人确认→定稿→check |
| 打叉重跑 | 只重跑当前步；五种原因码 |
| 可追溯 | `accepted.json` 含 revisions / journal_id |

---

## 关键入口

| 操作 | 说明 |
|------|------|
| **`start-with-ai.bat` / `start-with-ai.sh`** | 产品 Web（交付主入口） |
| **`setup阶段1环境.bat` / `setup.sh`** | 首次装环境 |
| `scripts/sync_journals.py` | 从官方 GitHub 拉全量日志 |
| `scripts/verify_acceptance.py` | 立项门槛一键复验 |
| `scripts/verify_delivery.py` | 交付冒烟自检 |
| `run-stage4-loop.bat` | CLI 闭环（无 Web 时备用） |

---

## 课题实训材料（存档）

阶段 0～7 报告、答辩总报告仍在 `docs/`；**对外交付以本 README + 操作手册 + 结项说明为准**。

## 目录

```
├── start-with-ai.bat / .sh     ← 交付启动（Win / Mac·Linux）
├── setup阶段1环境.bat / setup.sh
├── docs/交付/结项说明-给审阅同事.md
├── docs/交付/产品操作手册.md
├── project/                    ← 代码 / 日志库 / case-01（含 trial-report）
├── scripts/                    ← 服务 / 同步 / 自检
└── docs/                       ← 课题与答辩材料
```
