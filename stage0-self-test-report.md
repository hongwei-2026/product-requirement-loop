# 阶段 0 工作流自测报告

**生成时间：** 2026-08-30 18:38 +0800
**结果：** 全部通过

| ID | 检查项 | 对应功能 | 结果 | 说明 |
|----|--------|----------|------|------|
| D01 | 阶段0实现报告 | 阅读记录与结论 | ✓ | 存在: 阶段0实现报告.md |
| D02 | 阶段0快速验收清单 | 10条勾表认可 | ✓ | 存在: 阶段0快速验收清单.md |
| D03 | 人机确认操作指南 | 人怎么验收AI笔记 | ✓ | 存在: 人机确认操作指南.md |
| D04 | 复核关键词卡 | 不熟文件时怎么找 | ✓ | 存在: 复核关键词卡-case01.md |
| D05 | 项目实现流程报告 | 全阶段路线图 | ✓ | 存在: 项目实现流程报告.md |
| D06 | 课题申请 | 正式申请文档 | ✓ | 存在: 课题申请.md |
| D07 | 资料清单 | 材料索引 | ✓ | 存在: 资料清单.md |
| D08 | 图文预览 | 浏览器看图 | ✓ | 存在: 图文预览.html |
| I01 | 官方日志摘录 | 输入不凭空编造 | ✓ | journal-raw.md |
| I02 | 摘录含核心句 | 与官方日志可对齐 | ✓ | 含「捕捉用户故事」「零碎话语」 |
| I03 | 来源证明 | 输入可追溯 | ✓ | SOURCE.md 含官方仓库链接 |
| U01 | 验收对照页 | 左原文右故事 | ✓ | project\trials\case-01\review.html |
| U02 | 关键词高亮 | 不熟文件也能复核 | ✓ | review.html 含关键词按钮 |
| U03 | 打叉须写原因 | revise 留痕 | ✓ | 含句式模板与 buildRevise |
| U04 | 锁定与重跑说明 | 不重复确认已通过项 | ✓ | 含锁定/unlock 文案 |
| L01 | specification.yaml | Loop 定义骨架 | ✓ | project\product-requirement\specification.yaml |
| L02 | yaml 字段完整 | 对齐 devops-code 模板 | ✓ | entry/exit/steps/feedback/loop/acceptance 齐全 |
| L03 | acceptance 数值门槛 | 课题验收标准声明 | ✓ | fabrication_count=0 |
| L04 | check.py | 自动验收脚本 | ✓ | project/check.py |
| L05 | accepted schema | 定稿 JSON 结构 | ✓ | schemas/accepted.schema.json |
| S01 | 官方资料截图 | 阅读笔记有据可查 | ✓ | screenshots/ 下 14 张 PNG（需≥7） |
| S02-13-pro | 图证据 13-product-cloud-capture.png | 文档插图 | ✓ | 13-product-cloud-capture.png |
| S02-03-pro | 图证据 03-product-requirement-index.png | 文档插图 | ✓ | 03-product-requirement-index.png |
| S02-12-req | 图证据 12-requirement-json.png | 文档插图 | ✓ | 12-requirement-json.png |
| M01 | 阶段0验收操作手册 | 逐步操作指导 | ✓ | 阶段0验收操作手册.md |
| M02 | 手册含截图引用 | 便于对照操作 | ✓ | 含 stage0 验收截图路径 |

由 `python scripts/verify_stage0.py --write-report` 自动生成。