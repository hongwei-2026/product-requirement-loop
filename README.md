# product-requirement-loop

量潮 **产品需求梳理智能体**（product-requirement Loop）交付仓库。

## 交付快速开始

1. 运行 `setup阶段1环境.bat`（首次）  
2. 配置 `project/.env`（`AGNES_API_KEY`）  
3. （推荐）同步官方日志库：

```bat
project\.venv\Scripts\python.exe scripts\sync_journals.py
```

4. 双击 **`start-with-ai.bat`**  
5. 浏览器打开 **http://127.0.0.1:8765/**  
6. 按操作手册使用：

**[docs/交付/产品操作手册.md](./docs/交付/产品操作手册.md)**

## 登录与数据库

- 打开产品会先到 **登录页**：`http://127.0.0.1:8765/login.html`
- 演示账号：`demo` / `demo1234`；也可自行注册
- 数据库（SQLite）：`project/data/product_requirement.db`
  - 用户、登录会话
  - 审核历史（谁、何时、哪条日志、通过/打叉理由）
  - 定稿档案台账
  - 待人审队列

人和数据的关系：用户审日志 → 写出审核事件；定稿后写入定稿档案，以后可检索、默认不必重审。

## 交付自检

```bat
project\.venv\Scripts\python.exe scripts\verify_delivery.py
project\.venv\Scripts\python.exe scripts\verify_enterprise.py
```

（需先启动 `start-with-ai.bat`）

- `verify_delivery.py`：入口 / 登录 / 日志库 / 阶段机冒烟  
- `verify_enterprise.py`：鉴权 / 数据库 / 通过理由 / 审核历史 / 入库 / 待人审  

全量课题自测（可选）：

```bat
python scripts\verify_all.py --write-reports
```

## 产品能力

| 能力 | 说明 |
|------|------|
| 日志库 | 官方多产品流 × 按日日志；可筛选/粘贴/上传 |
| 工作台 | Step1→人确认→锁定→Step2→人确认→定稿→check |
| 打叉重跑 | 只重跑当前步；五种原因码 |
| 可追溯 | `accepted.json` 含 revisions / journal_id |

## 关键入口

| 操作 | 说明 |
|------|------|
| **`start-with-ai.bat`** | 产品 Web（交付主入口） |
| `scripts/sync_journals.py` | 从官方 GitHub 拉全量日志 |
| `scripts/verify_delivery.py` | 交付冒烟自检 |
| `run-stage4-loop.bat` | CLI 闭环（无 Web 时备用） |

## 课题实训材料（存档）

阶段 0～7 报告、答辩总报告仍在 `docs/`，供答辩与过程追溯；**对外交付以本 README + 操作手册为准**。

## 目录

```
├── start-with-ai.bat          ← 交付启动
├── docs/交付/产品操作手册.md   ← 交付手册
├── project/                   ← 代码 / 日志库 / case
├── scripts/                   ← 服务 / 同步 / 自检
└── docs/                      ← 课题与答辩材料
```
