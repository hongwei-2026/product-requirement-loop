# product-requirement-loop

量潮实训课题：**产品需求梳理智能体（product-requirement Loop）** 工作仓库。

## 当前进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| **0 读资料** | ✅ 已完成 | 见下方验收文档 |
| 1 搭环境 | 待做 | |
| 2～7 | 待做 | 见 [项目实现流程报告.md](./项目实现流程报告.md) |

## 阶段 0：你怎么验收？

**第一步：双击 `open-review.bat`**（打开验收页，不会乱码）

1. **详细步骤：** [阶段0验收操作手册.md](./阶段0验收操作手册.md) — 从「第 0 步」跟着做  
2. **完整启动（可选）：** `start-stage0.bat` — 多开预览页 + 自动检查  
3. **快速勾表：** [阶段0快速验收清单.md](./阶段0快速验收清单.md)

## 要 Fork 的官方仓库

见 [FORK与仓库说明.md](./FORK与仓库说明.md)。

## 目录

```
├── open-review.bat           # 【先点这个】打开验收页，纯英文不乱码
├── start-stage0.bat          # 完整启动（可选）
├── 启动阶段0验收.bat         # 转调 start-stage0.bat
├── 打开验收页.bat            # 转调 open-review.bat
├── 阶段0验收操作手册.md      # 跟着做，从第 0 步开始
├── 阶段0实现报告.md
├── project/                  # Loop 骨架与 case-01 试点
│   └── trials/case-01/review.html
├── screenshots/              # 官方资料截图 + stage0 验收截图
└── scripts/verify_stage0.py # 阶段 0 自动检查
```

## 推送到你自己的 GitHub

本机需先登录 GitHub CLI：`gh auth login`  
然后见 [GITHUB推送说明.md](./GITHUB推送说明.md)。
