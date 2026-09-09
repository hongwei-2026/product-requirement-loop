# 设计方案提交位（Design submissions）

> **这里就是 Design PR 要交文件的地方。**  
> 不要只在 PR 描述里写长文却不落库——审核员需要可版本管理、可检索的方案合同。

## 在整条接取流水中的位置

```text
/claim（意向，接取人栏仍空）
   → 本目录落库 + Design PR
   → 维护者 Merge Design PR
   → 维护者 /accept @你（接取人栏才写入）
   → Implementation PR
```

关联 PR 须至少每 **30 天** 有更新，否则任务自动释放。

## 怎么交 Design

1. 从 `main` 拉分支：`design/#<issue号>-简短英文`  
2. 复制 [`_TEMPLATE.md`](./_TEMPLATE.md) 为：

```text
docs/designs/#<issue号>-简短英文.md
```

例：Issue #1 → `docs/designs/#1-topbar-llm-summary.md`

3. 按模板填完后，在 GitHub 开 PR，**选择模板「Design」**  
4. 标题：`[Design] #<issue> 简要标题`；正文 `Related to #<issue>`（不要用 `Fixes`）  
5. 邮件 `feizi_050920@qq.com`：Issue 链接 + Design PR 链接 + 你的 GitHub ID  
6. 等 @hongwei-2026 **合并**本 Design PR 后，再等其在 Issue 上 `/accept @你`，然后才开 Implementation PR  

## 命名与约束

| 规则 | 说明 |
|------|------|
| 文件名 | 必须以 `#数字-` 开头，与 Issue 号一致 |
| 内容 | 方案、边界、验收、风险；**不要**贴完整业务实现 |
| 图片 | 可放 `docs/designs/assets/#N-…png` 并在 md 中引用 |
| 流水 | `Enterprise PR / design-gate` 会检查本目录是否有对应 `#N-` 文件 |
| 合并门禁 | 未合并 Design 时，维护者 `/accept` 会被机器人拒绝 |

## 已提交索引

| Issue | 文件 | 状态 |
|-------|------|------|
| （尚无） | 提交后请在本表追加一行 | — |

> 实现阶段请开 **Implementation** 模板 PR，不要把大段实现塞进本目录的 Design 文件。  
> 同学总说明：[任务贡献指南](../交付/任务贡献指南.md) · 汇报稿：[实训贡献机制-同学汇报稿](../交付/实训贡献机制-同学汇报稿.md)
