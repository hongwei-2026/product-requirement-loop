# product-requirement-loop

量潮实训课题：**产品需求梳理智能体（product-requirement Loop）** 工作仓库。

## 当前进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| **0 读资料** | ✅ 已完成 | 见下方验收文档 |
| 1 搭环境 | 待做 | |
| 2～7 | 待做 | 见 [项目实现流程报告.md](./项目实现流程报告.md) |

## 阶段 0：你怎么验收？

1. **推荐（逐步）：** [阶段0验收操作手册.md](./阶段0验收操作手册.md) — 30～40 分钟，含截图与功能对照  
2. **快速勾表：** [阶段0快速验收清单.md](./阶段0快速验收清单.md) — 5～10 分钟  
3. **自测脚本：** `python scripts/verify_stage0.py`（应全部 PASS）

## 要 Fork 的官方仓库

见 [FORK与仓库说明.md](./FORK与仓库说明.md)。

## 目录

```
├── 阶段0验收操作手册.md      # 你的验收步骤（从这里开始）
├── 阶段0实现报告.md
├── project/                  # Loop 骨架与 case-01 试点
│   └── trials/case-01/review.html
├── screenshots/              # 官方资料截图 + stage0 验收截图
└── scripts/verify_stage0.py # 阶段 0 自动检查
```

## 推送到你自己的 GitHub

本机需先登录 GitHub CLI：`gh auth login`  
然后见 [GITHUB推送说明.md](./GITHUB推送说明.md)。
