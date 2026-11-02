---
tags: [handbook]
date: 2026-11-02
---

# 开发者协作指南

> **读者：** 第一次 clone 本仓库的同学、实训基地接任务的同学、外部协作者  
> **任务认领与评审命令：** 仍以 [唯一入口](./index.md) 为准（`/claim` → Design → `/accept` → Impl PR）  
> **维护者：** @hongwei-2026 · 审核通知：`feizi_050920@qq.com`

本文说明**怎么在本机跑起来、改哪里、测什么、怎么提 PR**。不接任务也可以按「本地开发」一节贡献修复；接任务请同时遵守入口页的 Design / Implementation 流程。

---

## 1. 五分钟上手

| 步骤 | 做什么 |
| :-- | :-- |
| 1 | Fork 或 clone：`https://github.com/hongwei-2026/product-requirement-loop` |
| 2 | 复制 **根目录** [`.env.example`](../../.env.example) → `project/.env`，填写 `LLM_*` 与对应 API Key（**勿提交**） |
| 3 | Windows：双击 `setup阶段1环境.bat`；Mac/Linux：`./setup.sh` |
| 4 | （推荐）`project/.venv/Scripts/python scripts/sync_journals.py`（Linux 用 `bin/python`） |
| 5 | 启动：`start-with-ai.bat` / `./start-with-ai.sh`，浏览器打开 **http://127.0.0.1:8765/**（演示账号 `demo` / `demo1234`） |

环境变量只读 `project/.env`。根目录 `.env.example` 与 `project/.env.example` 内容一致，任选其一复制即可。

---

## 2. 仓库结构（对齐实训基地工具包）

| 路径 | 用途 |
| :-- | :-- |
| `src/product_requirement_loop/` | **Python 包**：闭环 `loop_runner.py`、Web 子包 `web/`（含 `review_queue`、`security_guard` 等） |
| `tests/` | **pytest** 单元测试（与 CI 同源） |
| `pyproject.toml` | 包名、依赖、pytest 配置 |
| `AGENTS.md` | 给 Cursor / Copilot 等 Agent 的约束 |
| `CHANGELOG.md` | 面向协作者的版本变更摘要 |
| `project/` | **运行时**：`data/`、`journals/`、`trials/`、`.env`、现有启动脚本仍从这里找路径 |
| `docs/handbook/` | 同事入口与本文 |
| `docs/specification/` | 可检查的标准（如目录对照） |
| `docs/bylaw/` | 本仓库工作边界 |
| `scripts/` | 验收门禁、`verify_*`、同步日志 |

改业务逻辑优先改 **`src/product_requirement_loop/`**，并补 **`tests/`**。`project/*.py` 若仍存在，是为兼容旧启动方式；新代码以 `src` 为准。

---

## 3. 本地开发循环

### 3.1 依赖与测试

```bash
# 已在 setup 脚本里建过 .venv 时可跳过
python -m venv project/.venv
project/.venv/Scripts/pip install -e ".[dev]"   # Linux: project/.venv/bin/pip

# 全量测试（CI 会跑）
project/.venv/Scripts/python -m pytest tests/ -q

# 与 README 同源的一键门槛（Windows）
验收门槛.bat
```

### 3.2 改代码时注意

1. **不要**把 `project/.env`、真实 API Key、录屏里的密钥提交进 Git。  
2. 安全相关逻辑在 `src/product_requirement_loop/web/security_guard.py`、`auth_passwords.py`；改完请跑对应测试。  
3. 评审队列在 `web/review_queue.py`；闭环编排在 `loop_runner.py`。  
4. 文档新增：说明类写入 `docs/handbook/`、`docs/specification/`、`docs/bylaw/`，文件名用小写英文与连字符；不要把 `docs/交付/`、`docs/阶段*` 当新同事入口。

### 3.3 分支命名（接任务时）

| 类型 | 分支示例 |
| :-- | :-- |
| 设计 | `design/#12-short-title` |
| 实现 | `feat/#12-short-title` |
| 杂项 / 结构 | `chore/align-package-layout` |

---

## 4. 提 PR 前自检

与 [企业级 PR 流水](../交付/企业级PR流水.md) 及 CI 一致，至少确认：

| 检查 | 命令 / 说明 |
| :-- | :-- |
| 测试 | `pytest tests/` 全绿 |
| 文档布局 | `python scripts/verify_docs_layout.py` |
| 安全 | `python scripts/verify_security.py` |
| 密钥 | diff 中无 `.env` 实文件、无 Key 明文 |

**Implementation PR** 还必须：正文 `Fixes #<Issue>`、**可公网打开的演示视频链接**、**≥2 张截图**（贴在正文）、审核员在 PR 评论 `/approve`（仅点 GitHub Approve 按钮不算）。

**Design PR** 用 `Related to #<Issue>`，不要用 `Fixes`。

---

## 5. 角色速查

| 角色 | 做什么 |
| :-- | :-- |
| 接任务的同学 | 读任务 Issue → `/claim` → Design PR → 等 `/accept` → Impl PR → `/submitted` |
| 审核员 @hongwei-2026 @hl019 @Jerrybao99 @likexin105 | 看 Checks、视频、截图；PR 评论 `/approve` 或 `/reject` |
| 管理员 @hongwei-2026 | 合并 Design、`/accept`、合并 Impl、`/score` |

命令表与逐步说明见 [唯一入口](./index.md#命令)。

---

## 6. 常见问题

**Q：clone 后不知道填什么环境变量？**  
A：看根目录 `.env.example`，复制到 `project/.env` 后改 `AGNES_API_KEY`（或切换 `LLM_PROVIDER` 与对应 Key）。

**Q：我只修一个小 bug，要不要 Design PR？**  
A：正式任务 Issue 仍走 Design → accept；若维护者另开「纯文档 / 结构」Issue，按 Issue 正文要求来。

**Q：测试 import 失败？**  
A：`pyproject.toml` 已配置 `pythonpath = ["src", "project"]`；用 `pytest tests/`，不要裸跑单个文件且漏 `PYTHONPATH`。

**Q：和实训基地第二大脑什么关系？**  
A：任务选题与 roadmap 在 [quanttide-academy](https://github.com/quanttide-academy/quanttide-academy)；本仓库是 **Platform 产品代码**，目录约定对齐基地 `packages/` 下工具包（`src` + `tests` + `pyproject.toml`）。

---

## 7. 延伸阅读

| 文档 | 用途 |
| :-- | :-- |
| [唯一入口](./index.md) | 认领、审核命令、结项 |
| [目录对照](../specification/layout.md) | 与基地规范的对照 |
| [工作边界](../bylaw/index.md) | 密钥、入口、组织归属 |
| [安全说明](../交付/安全说明.md) | 绑定地址、注册开关 |
| [README 快速开始](../../README.md#快速开始) | 启动脚本与端口 |
