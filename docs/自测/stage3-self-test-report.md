# 阶段 3 提示词自测报告

**生成时间：** 2026-08-31 09:27 +0800
**结果：** 全部通过

> 提示词定稿 + 试跑产物（编造/句式）+ 执行器读 prompt；不要求句覆盖率 100%（阶段 5）。

| ID | 检查项 | 结果 | 说明 |
|----|--------|------|------|
| R05 | 阶段2 yaml 仍在 | ✓ | specification.yaml |
| R06 | llm_config 仍在 | ✓ | llm_config.py |
| P01 | Loop 级 step1-story.md | ✓ | project\product-requirement\prompts\step1-story.md |
| P02 | Loop 级 step2-json.md | ✓ | project\product-requirement\prompts\step2-json.md |
| P03 | step1 含 JOURNAL_RAW | ✓ | 占位符 |
| P04 | step1 含全局故事与原文摘录 | ✓ | 章节齐全 |
| P05 | step2 禁止编造与用户要 | ✓ | 约束齐全 |
| P06 | step2 level 三档 | ✓ | activity|task|story |
| P07 | step2 含 REQUIREMENT_STORY | ✓ | 占位符 |
| P08 | case-01 prompts 与 Loop 级同步 | ✓ | trials/case-01/prompts/ |
| P09 | implementation 加载 prompt 文件 | ✓ | build_prompt 读 md |
| P10 | resolve_prompt_path 可用 | ✓ | ok |
| P11 | 验收页读 step2-json.md | ✓ | stage0_server |
| P12 | 试跑脚本存在 | ✓ | run_stage3_trial.py |
| T01 | requirement-story.md 存在 | ✓ | output/ |
| T02 | 故事含全局故事/原文摘录 | ✓ | 1691 字 |
| T03 | stories.json 存在 | ✓ | output/ |
| T04 | stories.json 可解析 | ✓ | 5 条 |
| T05 | 编造条数=0 | ✓ | fab=0, n=5 |
| T06 | text 均以「用户要」开头 | ✓ | fmt=0 |
| T07 | 每条有 level | ✓ | activity|task|story |
| D01 | 阶段3实现报告 | ✓ | docs/阶段3/ |
| D02 | 阶段3快速验收清单 | ✓ | docs/阶段3/ |
| D03 | 阶段3自测工作流说明 | ✓ | docs/阶段3/ |

由 `python scripts/verify_stage3.py --write-report` 生成。