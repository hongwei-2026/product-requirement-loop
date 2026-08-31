# 阶段 0 工作流自测报告

**生成时间：** 2026-08-31 09:26 +0800
**结果：** 全部通过

| ID | 检查项 | 对应功能 | 结果 | 说明 |
|----|--------|----------|------|------|
| D01 | 阶段0实现报告 | 阅读记录与结论 | ✓ | 存在: docs/阶段0/阶段0实现报告.md |
| D02 | 阶段0快速验收清单 | 10条勾表认可 | ✓ | 存在: docs/阶段0/阶段0快速验收清单.md |
| D03 | 人机确认操作指南 | 人怎么验收AI笔记 | ✓ | 存在: docs/阶段0/人机确认操作指南.md |
| D04 | 复核关键词卡 | 不熟文件时怎么找 | ✓ | 存在: docs/阶段0/复核关键词卡-case01.md |
| D05 | 项目实现流程报告 | 全阶段路线图 | ✓ | 存在: docs/申请/项目实现流程报告.md |
| D06 | 课题申请 | 正式申请文档 | ✓ | 存在: docs/申请/课题申请.md |
| D07 | 资料清单 | 材料索引 | ✓ | 存在: docs/申请/资料清单.md |
| D08 | 图文预览 | 浏览器看图 | ✓ | 存在: docs/阶段0/图文预览.html |
| I01 | 官方原文（完整） | 左侧展示原封不动 | ✓ | journal-official-full.md |
| I02 | 完整原文够长且含核心句 | 不是摘要冒充原文 | ✓ | 3298 字，含捕捉用户故事/事件风暴 |
| I03 | 摘录单独存放 | 关键词卡用短摘录 | ✓ | journal-excerpt.md 短于 full |
| I04 | 来源证明与正确路径 | 输入可追溯 | ✓ | SOURCE.md 含 quanttide-devops/loops/devops-code |
| U01 | 验收对照页 | 左原文右故事 | ✓ | project\trials\case-01\review.html |
| U02 | 关键词高亮 | 不熟文件也能复核 | ✓ | review.html 含关键词按钮 |
| U03 | 打叉须写原因 | revise 留痕 | ✓ | 含句式模板与 buildRevise |
| U04 | 锁定与重跑说明 | 不重复确认已通过项 | ✓ | 含锁定/unlock 文案 |
| U05 | 左侧标题为完整原文 | 不标原始却给摘要 | ✓ | 标题含「官方原文（完整）」 |
| U06 | AI 试抓按钮 | 右侧可跑 Agnes | ✓ | 含 AI 试抓与 runAiDraft |
| U07 | 通过/打叉互斥 | 点叉后 ok 清空 | ✓ | 含 setVerdict 与 pending 状态 |
| L01 | specification.yaml | Loop 定义骨架 | ✓ | project\product-requirement\specification.yaml |
| L02 | yaml 字段完整 | 对齐 devops-code 模板 | ✓ | entry/exit/steps/feedback/loop/acceptance 齐全 |
| L03 | acceptance 数值门槛 | 课题验收标准声明 | ✓ | fabrication_count=0 |
| L04 | check.py | 自动验收脚本 | ✓ | project/check.py |
| L05 | accepted schema | 定稿 JSON 结构 | ✓ | schemas/accepted.schema.json |
| S01 | 官方资料截图 | 阅读笔记有据可查 | ✓ | screenshots/ 下 14 张 PNG（需≥7） |
| S02-13-pro | 图证据 13-product-cloud-capture.png | 文档插图 | ✓ | 13-product-cloud-capture.png |
| S02-03-pro | 图证据 03-product-requirement-index.png | 文档插图 | ✓ | 03-product-requirement-index.png |
| S02-12-req | 图证据 12-requirement-json.png | 文档插图 | ✓ | 12-requirement-json.png |
| M01 | 阶段0验收操作手册 | 逐步操作指导 | ✓ | docs/阶段0/阶段0验收操作手册.md |
| M02 | 手册含截图引用 | 便于对照操作 | ✓ | 含 stage0 验收截图路径 |
| P01 | 启动 bat 存在 | 双击启动入口 | ✓ | 启动阶段0验收.bat |
| P01b | open-review.bat | 纯英文兜底启动 | ✓ | open-review.bat |
| P01c | open-review 纯 ASCII | 避免 cmd 乱码 | ✓ | 非 ASCII 字符数=0（应为 0） |
| P02 | 备用打开 bat | 主启动失败时兜底 | ✓ | 打开验收页.bat |
| P03 | 启动 ps1 存在 | bat 调用的脚本 | ✓ | scripts/start_stage0.ps1 |
| P04 | ps1 语法合法 | 避免双击闪退 | ✓ | start_stage0.ps1 syntax OK |
| P05 | launcher-files.json | 中文路径清单 | ✓ | launcher-files.json |
| P07 | start-with-ai.bat | 带 AI 的本地服务入口 | ✓ | start-with-ai.bat |
| P08 | stage0_server.py | Agnes API 代理 | ✓ | scripts/stage0_server.py |
| P06-review | 清单路径存在 review_html | 启动器能打开文件 | ✓ | review.html |
| P06-previe | 清单路径存在 preview_html | 启动器能打开文件 | ✓ | 图文预览.html |
| P06-accept | 清单路径存在 acceptance_manual_md | 启动器能打开文件 | ✓ | 阶段0验收操作手册.md |

由 `python scripts/verify_stage0.py --write-report` 自动生成。