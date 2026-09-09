# 任务 Issue 正文标准块（复制进每个 task Issue）

> 维护者建 Issue 时把下面两节贴到任务专属内容之后；勿只写在评论里。

---

## 如何接取 / 放弃 / 同步仪表盘

**标准顺序（必须）：**

1. 同学评论 `/claim`（仅登记意向，**接取人栏仍为空**）  
2. 同学开 Design PR（`docs/designs/#N-….md`）并邮件 `feizi_050920@qq.com`  
3. 维护者审查并 **Merge** Design PR  
4. 维护者在同学 `/claim` 语境下评论 `/accept @同学ID` → **接取人栏才写入该 ID**  
5. 同学再开 Implementation PR（代码 + 视频链接 + 截图≥2）

命令写在**本 Issue 评论区**，单独一行。

| 你要做的事 | 评论命令 | 接取人栏 |
|------------|----------|----------|
| 登记意向 | `/claim` | 仍为 — |
| 维护者批准（Design 已合并后） | （仅 @hongwei-2026）`/accept @你的ID` | **写入 @你的ID** |
| **自己放弃** | `/cancel` 或 `/release` | 清空为 — |
| 维护者清掉别人的认领 | `/reject-claim` | 清空为 — |
| 合并后计分 | `/score N` | 标已完成 |
| （自动）关联 PR 超 30 天无更新 | — | **自动释放**，清空接取人 |

**硬性规则：**

- 同一 GitHub 账号同时只能有 1 个进行中任务（意向或已锁定）。想换题必须先 `/cancel`。  
- **进度新鲜度：** 关联 Design/Impl PR 须至少每 **30 天** 有更新；超时系统自动释放。  
- 总览接取人表：[Issue #7](https://github.com/hongwei-2026/product-requirement-loop/issues/7) · [任务列表.md](./任务列表.md) · [任务仪表盘.md](./任务仪表盘.md)

---

## 交付物规范（Implementation PR 缺一不可）

1. **代码**：PR 标题 `[Impl] #<本Issue> …`，正文含 `Fixes #<本Issue>`；作者须为已 `/accept` 的 Assignee  
2. **演示视频链接（必填）**：可公网打开（B 站 / 飞书云文档·妙记 / 录屏分享等）；写在 PR「演示视频」一节  
3. **截图（必填）**：至少 2 张，**直接贴在 PR 正文**  
4. 禁止截图或视频中出现 API Key / `.env`  

缺视频或截图时，必审人可要求补齐后再 Approve；补齐后 PR 评论 `/recheck`。
