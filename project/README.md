# product-requirement Loop — 运行说明

## 环境

```bash
cd project
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install pyyaml openai langgraph langgraph-checkpoint
```

复用官方执行器（从 agent-engineering 仓库复制或 clone）：

```bash
# 将 quanttide-profile-of-agent-engineering 中
# default/loops/devops-code/implementation.py 复制到本目录，或指定路径运行
```

环境变量（与官方一致）：

- `DEEPSEEK_API_KEY` 或 `~/.hermes/.env`

## 目录结构

```
project/
├── product-requirement/specification.yaml
├── check.py
├── schemas/accepted.schema.json
└── trials/case-01/
    ├── input/journal-raw.md
    ├── prompts/
    └── output/          # 运行后生成
```

## 运行 Loop（官方执行器）

```bash
cd trials/case-01
python ../../path/to/implementation.py . --task "$(cat input/journal-raw.md)"
```

或手动按 prompts 分步调用 LLM，产出写入 `output/`。

## 验收

```bash
python check.py output/stories.json --source input/journal-raw.md --write-uncovered output/uncovered.md
python check.py output/accepted.json --source input/journal-raw.md --strict
```

## 验收门槛（必须全部满足）

| 项 | 标准 |
|----|------|
| 编造条数 | 0 |
| source_quote 通过率 | 100% |
| 句覆盖率 | 100%（例外须人工确认并写入 review.comments） |
| 人工确认 | accepted.json 每条 approved=true + revisions |
| 反馈点 | 至少触发 1 次 |
