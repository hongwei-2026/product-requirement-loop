---
tags: [待审]
date: 2026-10-01
---

# 唯一入口

同事只从这一页进入本仓库。过程材料还在，但不是入口。

## 目标

把官方产品日志整理成需求故事和定稿 JSON，并且让不同技术背景的人按写下来的步骤接手。

## 现在怎么协作

草创期先用直接分配，不用以前的初审和 `/claim`。

1. 任务写在 [实训基地任务清单](https://github.com/quanttide-academy/quanttide-academy/blob/main/roadmap.md)，写清目标、任务要求、评审标准和评审顺序。写法对齐该清单里的「日常任务：实训基地章程完善」。
2. 向该仓库提 PR。
3. 王敏华审阅并合并后，直接指定执行人。
4. 执行人在本仓库按任务要求改代码，再提实现 PR，由评审人按 PR 里的步骤验收。

## 三件要做的事

| 你要做的事 | 打开 |
| :-- | :-- |
| 跑起来 | [仓库首页「快速开始」](../../README.md#快速开始) |
| 验收这套产品 | [结项说明](../交付/结项说明-给审阅同事.md) |
| 看安全边界 | [安全说明](../交付/安全说明.md) |

## 文档放哪里

新文档只用这些目录，文件名用小写英文和连字符：

| 目录 | 放什么 |
| :-- | :-- |
| `docs/handbook/` | 给人看的操作入口（本页） |
| `docs/specification/` | 可检查的标准 |
| `docs/tutorial/` | 分步教程 |

`docs/交付/`、`docs/阶段*`、`docs/答辩总报告/` 是过程材料。不要从首页再链出整目录。命名依据是实训基地 [命名规范](https://github.com/quanttide-academy/quanttide-academy/blob/main/docs/specification/second-brain.md)。

## 当前在做的任务

- 文档入口归一：本页。执行人于鸿伟，评审人王敏华。
- [#1 顶栏展示模型摘要](https://github.com/hongwei-2026/product-requirement-loop/issues/1)：登录后顶栏显示 `provider`、`model`、`timeout`、`thinking_off`。验收看该 Issue 的「验收标准」。待本页合并进任务清单后，由王敏华直接分配执行人。
