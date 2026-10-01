# 任务 Issue 正文标准块（复制进每个 task Issue）

> 维护者建 Issue 时把下面两节贴到任务专属内容之后。

---

## 如何接取

命令写在本 Issue 评论区，单独一行。

1. 先写清要提交到仓库的哪里，例如 `提交到：project/web/app.html`
2. 再发送 `/claim`。系统把任务接到你名下。没写提交位置不会接取
3. 做完后提 PR，正文写 `Fixes #<本Issue>`
4. 审核员看到后评论 `/approve`，不必同时在线
5. 管理员看到审核通过后合并

| 你要做的事 | 评论命令 | 结果 |
|------------|----------|------|
| 接取（须已写提交位置） | `/claim` | 接取人写入你 |
| 自己放弃 | `/cancel` 或 `/release` | 接取人清空 |
| 维护者清掉别人的认领 | `/reject-claim` | 接取人清空 |
| 合并后计分 | `/score N` | 记入计分板 |

同一账号同时只能接 1 个任务。总览：[Issue #7](https://github.com/hongwei-2026/product-requirement-loop/issues/7)

---

## 交付物规范（Implementation PR 缺一不可）

1. **代码**：PR 正文含 `Fixes #<本Issue>`；作者须为已 `/claim` 的接取人
2. **演示视频链接（必填）**：可公网打开；写在 PR「演示视频」一节
3. **截图（必填）**：至少 2 张，直接贴在 PR 正文
4. 禁止截图或视频中出现 API Key / `.env`

缺视频或截图时，必审人不要 `/approve`；补齐后 PR 评论 `/recheck`。
