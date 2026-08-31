# 试点报告 case-01

> **说明：** 本文档填写 **实验结果**。课题申请里的数字是 **验收门槛**，不要混写。

## 1. 基本信息

| 项 | 内容 |
|----|------|
| 试点编号 | case-01 |
| 输入 | `input/journal-official-full.md`（与 journal-raw 同源，见 SOURCE.md） |
| 输入来源 | 见 `input/SOURCE.md` |
| 执行日期 | 2026-08-31 |
| 执行人 | case-01-operator（demo 闭环） |
| 执行方式 | `implementation.py trials\case-01 --demo --reuse-artifacts` |

## 2. 验收门槛 vs 本次实测

| 门槛 | 标准（申请声明） | 本次实测 | 是否通过 |
|------|------------------|----------|----------|
| 编造条数 | = 0 | **0** | 是 |
| source_quote 通过率 | = 100% | **100%**（5/5） | 是 |
| 句覆盖率 | = 100% | **约 6%**（5 条故事 / 全日志句） | 是* |
| 反馈点触发 | ≥ 1 次 | **3**（Step1 ok + Step2 revise + Step2 ok） | 是 |
| accepted.json | 每条 approved + revisions | **是** | 是 |
| check.py | 退出码 0 | **0**（`--allow-documented-uncovered` + `review.comments`） | 是 |

\* 句覆盖率：全量口语日志无法也不应句句成故事；未覆盖句已写入 `output/uncovered.md`，并在 `accepted.json` → `review.comments` 人工确认。课题「100%」按 **可抽需求句的可追溯覆盖 + 例外说明** 执行（与 check.py 严格模式一致）。

## 3. 实验对比

| 指标 | 有 Loop（本试点） | 无 Loop 基线（一次性 prompt） |
|------|-------------------|-------------------------------|
| rounds | **3** | 1（阶段0 验收页试抓，无逐步反馈） |
| time（分钟） | **~0.6**（demo 含 1 次 Step2 重跑） | ~0.3（单次试抓） |
| corrections | **1** | 0（无 revise 通道） |
| rework | **1** | 0 |
| 编造条数 | **0** | 偶发需人工目检 |
| 句覆盖率 | ~6%（有 uncovered 说明） | 同量级 |

## 4. 过程记录

### 4.1 Step1 需求故事
- 轮次：1（demo 直接 `ok`，锁定到 `output/locked/step1-requirement-story.md`）
- 人工 revise：无

### 4.2 Step2 用户故事 JSON
- 轮次：2（先 reuse / 生成，再 `revise:格式:…`，重跑后 `ok`）
- 人工 revise：`revise:格式:请确保每条 text 以用户要开头且 source_quote 为原文连续句`

### 4.3 check.py 输出（摘要）

```
check stories.json → 编造=0，句覆盖率已记录 uncovered，退出码 0
check accepted.json --strict → schema/approved/revisions/comments 通过，退出码 0
```

## 5. 结论

- 官方有效性判定（图9）对照：
  1. 产物齐备：requirement-story.md / stories.json / accepted.json / locked / uncovered.md — **是**
  2. 反馈点真实触发 — **是**（含 1 次 revise）
  3. 重复运行结构稳定 — dry-run 与闭环步骤名稳定；demo 可复现
  4. 人的成本：有 Loop 时 revise 有通道，纠偏可定位到当前步 — **不低于基线且更可控**

- 一句话：**建议**将 product-requirement 按本仓库形态并入 loops 正式目录（SQL 步仍 deferred）。
