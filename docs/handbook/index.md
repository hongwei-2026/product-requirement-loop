---
tags: [待审]
date: 2026-10-01
---

# 唯一入口

同事只从这一页进入本仓库。过程材料还在，但不是入口。

## 目标

把官方产品日志整理成需求故事和定稿 JSON。接任务和审 PR 不用等人同时在线。

## 从选题到结项

任务在 [Issue #7](https://github.com/hongwei-2026/product-requirement-loop/issues/7)。审核通知邮箱：`feizi_050920@qq.com`。管理员：@hongwei-2026。审核员：@hongwei-2026、@hl019、@Jerrybao99、@likexin105。

1. **选题。** 打开任务 Issue，读完目标、要求和验收。
2. **登记。** 在该 Issue 评论，单独一行：`/claim`
3. **设计文档 PR。** 复制 `docs/designs/_TEMPLATE.md` 为 `docs/designs/#编号-简短英文.md`。开 PR，标题 `[Design] #编号 标题`，正文 `Related to #编号`。不要写 `Fixes`。
4. **发邮件。** 发到 `feizi_050920@qq.com`。主题 `[Design] #编号 你的GitHubID`。正文放 Issue 链接、Design PR 链接、GitHub ID。
5. **批准。** 管理员合并 Design PR 后，在 Issue 评论：`/accept @你的GitHubID`。这时接取人才写成你。
6. **实现 PR。** 标题 `[Impl] #编号 标题`，正文 `Fixes #编号`，再加可打开的演示视频链接和至少 2 张截图。
7. **审核。** 审核员在 PR 评论 `/通过` 或 `/驳回`。作者不能给自己 `/通过`。缺材料就先 `/驳回`，补完后作者评论 `/recheck`。
8. **合并。** 审核通过且 CI 为绿，管理员合并实现 PR。
9. **结项。** 管理员在 Issue 评论 `/score 分数`，然后关闭 Issue。

放弃：在 Issue 评论 `/cancel`。管理员可评论 `/reject-claim` 清掉别人的接取。

### 命令

| 命令 | 写在哪里 | 谁可以发 | 作用 |
| :-- | :-- | :-- | :-- |
| `/claim` | 任务 Issue | 想接的人 | 登记意向，接取人仍为空 |
| `/accept @用户名` | 任务 Issue | 仅管理员 | Design PR 已合并后，把接取人写成该用户 |
| `/cancel` | 任务 Issue | 接取人或管理员 | 放弃，接取人清空。同等命令：`/release` |
| `/reject-claim` | 任务 Issue | 仅管理员 | 清掉别人的接取 |
| `/通过` | PR | 审核员，不能是作者 | 同意当前提交。同等命令：`/approve` |
| `/驳回` | PR | 审核员 | 要求修改。同等命令：`/reject` |
| `/recheck` | PR | 作者或审核员 | 补材料后重跑交付检查 |
| `/score 分数` | 任务 Issue | 管理员或审核员 | 合并后记分，任务结项 |

## 三件要做的事

| 你要做的事 | 打开 |
| :-- | :-- |
| 跑起来 | [仓库首页「快速开始」](../../README.md#快速开始) |
| 验收这套产品 | [结项说明](../交付/结项说明-给审阅同事.md) |
| 看安全边界 | [安全说明](../交付/安全说明.md) |

## 文档放哪里

| 目录 | 放什么 |
| :-- | :-- |
| `docs/handbook/` | 本页 |
| `docs/specification/` | 可检查的标准 |
| `docs/bylaw/` | 本仓库工作边界 |

`docs/交付/`、`docs/阶段*` 是过程材料，不是入口。成熟、大家用顺了的做法，再收成可复用工具。现在先把上面这五步跑通。
