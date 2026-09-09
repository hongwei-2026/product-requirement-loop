# 企业级 PR 流水（架构说明）

> 给维护者 / 审核员看的流水设计说明。同学日常只需知道：开对模板、交齐材料、红了就 `/recheck`。

## 流水地图

```text
                    ┌─ pull_request (open/sync) ─┐
                    │                            │
 PR 评论 /recheck ──┼──►  Enterprise PR 套件  ◄──┤── workflow_dispatch(pr#)
                    │         │                  │
                    │         ├─ classify（自动打 type:design|implementation）
                    │         ├─ delivery-artifacts（视频 URL + 截图 / 设计文档章节）
                    │         ├─ design-gate（Design 必须改 docs/designs/#N-*.md）
                    │         ├─ scope-guard（超大 PR / 乱碰 workflows 拦截）
                    │         ├─ task-lock（Impl 必须已 /accept 且作者=Assignee）
                    │         └─ suite-summary（粘性评论仪表盘）
                    │
                    ├─ CI（仓库级 verify_* / 密钥 / bandit）
                    ├─ Task PR gate（verify + 自动审核清单评论）
                    ├─ Required reviewers（四人全 Approve）
                    └─ Task stale auto-release（每天：关联 PR >30 天无更新 → 自动释放）
```

## 设计 PR 提交位

| 路径 | 用途 |
|------|------|
| `docs/designs/_TEMPLATE.md` | 模板 |
| `docs/designs/#N-slug.md` | 每个任务的方案合同 |
| `.github/PULL_REQUEST_TEMPLATE/design.md` | 开 PR 时选 **Design** |
| `.github/PULL_REQUEST_TEMPLATE/implementation.md` | 开 PR 时选 **Implementation** |

## 命令

| 命令 | 位置 | 作用 |
|------|------|------|
| `/recheck` `/rerun` `/rerun-checks` | **PR 评论**单独一行 | 重跑 Enterprise PR 套件 |
| `/claim` `/accept` `/cancel` `/score` | **Issue 评论** | 任务板（见 task-board.yml） |

## 停滞自动释放（30 天）

| 项 | 说明 |
|----|------|
| Workflow | `Task stale auto-release`（`task-stale-release.yml`） |
| 触发 | 每天定时；也可 Actions 页手动 `workflow_dispatch` |
| 判定 | 进行中（claim-pending / locked）任务：关联 Design/Impl PR 的 `updated_at`（若无 PR 则用认领时间）距今 **> 30 天** |
| 动作 | 清 Assignee / 状态标签 / 认领 JSON；Issue 评论通知；刷新 #7 接取人栏 |
| dry_run | 手动运行时输入 `dry_run=true` 只报告不释放 |

## 建议纳入分支保护的 Checks

1. `CI / Strict delivery + security gates`  
2. `Enterprise PR / delivery-artifacts`  
3. `Enterprise PR / design-gate`  
4. `Enterprise PR / task-lock`  
5. `Enterprise PR / scope-guard`  
6. `Required reviewers (all must approve) / all-reviewers`  

（`classify` / `suite-summary` 可选；`suite-summary` 失败表示套件内已有红灯。）

## 标签逃生舱（企业例外）

| 标签 | 作用 |
|------|------|
| `large-pr` | 允许超过体量上限 |
| `maintainer-ok` | 允许改 `.github/workflows` 等敏感路径 |

仅维护者应打这些标签。
