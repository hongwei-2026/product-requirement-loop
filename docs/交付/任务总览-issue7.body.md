# 实训任务总览（跳转入口）

维护者：@hongwei-2026  
必审人（PR 须 **四人全部 Approve**）：@hongwei-2026 @hl019 @Jerrybao99 @likexin105  

- 同学：[任务贡献指南](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E4%BB%BB%E5%8A%A1%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97.md)
- **审核员**：[审核员指南](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E5%AE%A1%E6%A0%B8%E5%91%98%E6%8C%87%E5%8D%97.md)
- 汇报稿：[实训贡献机制-同学汇报稿](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E5%AE%9E%E8%AE%AD%E8%B4%A1%E7%8C%AE%E6%9C%BA%E5%88%B6-%E5%90%8C%E5%AD%A6%E6%B1%87%E6%8A%A5%E7%A8%BF.md)
- 任务列表：[任务列表](https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E4%BB%BB%E5%8A%A1%E5%88%97%E8%A1%A8.md)
- Design 提交位：[docs/designs](https://github.com/hongwei-2026/product-requirement-loop/tree/main/docs/designs)

## 硬性规则

1. **同一 GitHub 账号同时只能接 1 个进行中任务**（`/claim` 或已 `/accept` 锁定期间）。换题先 `/cancel`。
2. 实现 PR 必须：**代码 + 演示视频链接 + 截图≥2**。
3. Design 方案落库：`docs/designs/#N-….md`。
4. **接取人**列：仅在维护者 **合并 Design PR 之后** 评论 `/accept @ID` 才写入（单独 `/claim` 不会写）。
5. **30 天无关联 PR 更新 → 自动释放**（接取人清空，任务重开）。

_接取人表上次同步：2026-09-09 10:35 UTC_

## 子任务列表

### 基础 / 进阶

| 难度 | 积分 | Issue | 标题 | 接取人 |
|------|------|-------|------|--------|
| 简单 | 10 | [#1](https://github.com/hongwei-2026/product-requirement-loop/issues/1) | [顶栏 LLM 摘要](https://github.com/hongwei-2026/product-requirement-loop/issues/1) | — |
| 简单 | 15 | [#2](https://github.com/hongwei-2026/product-requirement-loop/issues/2) | [服务宕机 vs AI 超时](https://github.com/hongwei-2026/product-requirement-loop/issues/2) | — |
| 中等 | 30 | [#3](https://github.com/hongwei-2026/product-requirement-loop/issues/3) | [心跳与重试](https://github.com/hongwei-2026/product-requirement-loop/issues/3) | — |
| 中等 | 35 | [#4](https://github.com/hongwei-2026/product-requirement-loop/issues/4) | [待审库轻量搜索](https://github.com/hongwei-2026/product-requirement-loop/issues/4) | — |
| 难 | 60 | [#5](https://github.com/hongwei-2026/product-requirement-loop/issues/5) | [异步 Step1/2](https://github.com/hongwei-2026/product-requirement-loop/issues/5) | — |
| 难 | 50 | [#6](https://github.com/hongwei-2026/product-requirement-loop/issues/6) | [长日志压测 CI](https://github.com/hongwei-2026/product-requirement-loop/issues/6) | — |
| 难 | 55 | [#8](https://github.com/hongwei-2026/product-requirement-loop/issues/8) | [待审库工作台级分组](https://github.com/hongwei-2026/product-requirement-loop/issues/8) | — |

### 特难扩展（量潮对齐）

| 难度 | 积分 | Issue | 标题 | 接取人 |
|------|------|-------|------|--------|
| 特难 | 75 | [#9](https://github.com/hongwei-2026/product-requirement-loop/issues/9) | [requirement.json 导出包](https://github.com/hongwei-2026/product-requirement-loop/issues/9) | — |
| 特难 | 80 | [#10](https://github.com/hongwei-2026/product-requirement-loop/issues/10) | [第二大脑 Context 导出包](https://github.com/hongwei-2026/product-requirement-loop/issues/10) | — |
| 特难 | 70 | [#11](https://github.com/hongwei-2026/product-requirement-loop/issues/11) | [SemVer 发布门禁](https://github.com/hongwei-2026/product-requirement-loop/issues/11) | — |
| 特难 | 75 | [#12](https://github.com/hongwei-2026/product-requirement-loop/issues/12) | [覆盖率 uncovered 面板](https://github.com/hongwei-2026/product-requirement-loop/issues/12) | — |
| 特难 | 70 | [#13](https://github.com/hongwei-2026/product-requirement-loop/issues/13) | [修订时间线 UI](https://github.com/hongwei-2026/product-requirement-loop/issues/13) | — |
| 特难 | 75 | [#14](https://github.com/hongwei-2026/product-requirement-loop/issues/14) | [打叉理由分析看板](https://github.com/hongwei-2026/product-requirement-loop/issues/14) | — |
| 特难 | 80 | [#15](https://github.com/hongwei-2026/product-requirement-loop/issues/15) | [待审库指派/SLA](https://github.com/hongwei-2026/product-requirement-loop/issues/15) | — |
| 特难 | 80 | [#16](https://github.com/hongwei-2026/product-requirement-loop/issues/16) | [Inbox 去重+冲突台](https://github.com/hongwei-2026/product-requirement-loop/issues/16) | — |
| 特难 | 85 | [#17](https://github.com/hongwei-2026/product-requirement-loop/issues/17) | [Step1 后入队 Step2 草稿](https://github.com/hongwei-2026/product-requirement-loop/issues/17) | — |
| 特难 | 85 | [#18](https://github.com/hongwei-2026/product-requirement-loop/issues/18) | [Prompt 版本 / prompt_sha](https://github.com/hongwei-2026/product-requirement-loop/issues/18) | — |
| 特难 | 90 | [#19](https://github.com/hongwei-2026/product-requirement-loop/issues/19) | [多 trial 矩阵](https://github.com/hongwei-2026/product-requirement-loop/issues/19) | — |
| 特难 | 90 | [#20](https://github.com/hongwei-2026/product-requirement-loop/issues/20) | [运行时切换 LLM](https://github.com/hongwei-2026/product-requirement-loop/issues/20) | — |
| 特难 | 75 | [#21](https://github.com/hongwei-2026/product-requirement-loop/issues/21) | [错误分类回流 lessons](https://github.com/hongwei-2026/product-requirement-loop/issues/21) | — |
| 特难 | 85 | [#22](https://github.com/hongwei-2026/product-requirement-loop/issues/22) | [JSON↔SQLite 单一数据源](https://github.com/hongwei-2026/product-requirement-loop/issues/22) | — |

接取：目标 Issue 评论 `/claim` → Design PR → 维护者 **Merge** → 维护者 `/accept @你` → **接取人栏才出现你的 ID**。
