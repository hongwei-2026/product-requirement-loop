# product-requirement Loop — 运行说明

文档入口：[docs/README.md](../docs/README.md)

## 一键环境

仓库根目录双击 `setup阶段1环境.bat`，或：

```bat
cd project
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

配置 `project/.env`（见 `.env.example`），默认 `LLM_PROVIDER=agnes`。

## 复跑 case-01（答辩演示）

```bat
cd project
.venv\Scripts\activate

:: 预览三步
python implementation.py trials\case-01 --dry-run

:: 非交互闭环（含 1 次 revise + 锁定 + accepted.json）
python implementation.py trials\case-01 --demo --reuse-artifacts

:: 自动验收
python check.py trials\case-01\output\stories.json --source trials\case-01\input\journal-official-full.md --write-uncovered trials\case-01\output\uncovered.md --allow-documented-uncovered
python check.py trials\case-01\output\accepted.json --source trials\case-01\input\journal-official-full.md --strict --allow-documented-uncovered
```

根目录也可双击 **`启动阶段4闭环.bat`**。

交互模式（真人输入 ok / revise）：

```bat
python implementation.py trials\case-01
```

## 目录

```
project/
├── product-requirement/
│   ├── specification.yaml
│   └── prompts/                 # Step1 / Step2 定稿
├── loop_runner.py               # 阶段4 闭环编排
├── implementation.py            # 入口（默认调 loop_runner）
├── check.py
├── llm_config.py
├── schemas/accepted.schema.json
└── trials/case-01/
    ├── input/
    ├── prompts/                 # 试点副本
    ├── output/                  # 运行产物
    └── trial-report.md          # 阶段6 实测
```

## 验收门槛（申请声明）

| 项 | 标准 |
|----|------|
| 编造条数 | 0 |
| source_quote 通过率 | 100% |
| 句覆盖率 | 100% 或 uncovered + review.comments 人工确认 |
| 人工确认 | accepted 每条 approved + revisions |
| 反馈点 | ≥ 1 次 |

实测见 `trials/case-01/trial-report.md`（勿与门槛混写）。
