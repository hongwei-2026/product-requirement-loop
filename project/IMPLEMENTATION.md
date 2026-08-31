# 官方 Loop 执行器（已本地化）

`implementation.py` 来自官方：

`quanttide-devops/loops/devops-code/implementation.py`

## 本地适配（相对官方原文件的改动）

| 改动 | 原因 |
|------|------|
| 读取 `product-requirement/specification.yaml` | 本课题 Loop 定义在此 |
| 使用 `llm_config.make_client()` | 默认 **Agnes**，可切 deepseek/openai |
| 无 task 时读 `input/journal-official-full.md` | case-01 试点 |
| `build_prompt` 读 `product-requirement/prompts/*.md` | 阶段 3：Step1/Step2 定稿提示词 |

## 用法

```bat
cd project
.venv\Scripts\activate
python implementation.py trials\case-01 --dry-run
python implementation.py trials\case-01
```

## LLM 配置

见 `llm_config.py` 与 `.env`：

- 本期：`LLM_PROVIDER=agnes`（免费）
- 商业：改为 `openai` 或其他，只改 `.env`

官方原仓库链接（对照用）：

https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/quanttide-devops/loops/devops-code/implementation.py
