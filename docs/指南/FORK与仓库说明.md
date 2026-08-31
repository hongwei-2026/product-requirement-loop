# Fork 与仓库说明

> 阶段 0 用本仓库里的摘录就能验收。  
> 从阶段 1 起，你需要能打开官方仓库对照代码和日志。

---

## 你要 Fork 哪些仓库？

你已 Fork 到账号 **hongwei-2026**（2026-08-30 确认）：

| 优先级 | 你的 Fork 地址 |
|--------|----------------|
| **主输入·日志** | https://github.com/hongwei-2026/quanttide-journal-of-product-development |
| **Loop·执行器** | https://github.com/hongwei-2026/quanttide-profile-of-agent-engineering |
| **输出格式** | https://github.com/hongwei-2026/quanttide-profile-of-product-development |
| **参考·认知** | https://github.com/hongwei-2026/quanttide-journal-of-cognitive-engineering |

上游仍为 `quanttide/*`；你 Fork 后可在自己账号下改、对照，合适时再向上游 PR。

若尚未 Fork，按下面「官方原名」在 GitHub 点 Fork：

| 优先级 | 官方仓库 | 为什么要 Fork |
|--------|----------|----------------|
| **必 Fork** | [quanttide-journal-of-product-development](https://github.com/quanttide/quanttide-journal-of-product-development) | **主输入**：产品研发日志，导师指定来源 |
| **必 Fork** | [quanttide-profile-of-agent-engineering](https://github.com/quanttide/quanttide-profile-of-agent-engineering) | Loop 范式、`devops-code/implementation.py`、yaml 模板 |
| **建议 Fork** | [quanttide-profile-of-product-development](https://github.com/quanttide/quanttide-profile-of-product-development) | `requirement.json` / `requirement.md`，输出格式对齐 |
| **选 Fork** | [quanttide-journal-of-cognitive-engineering](https://github.com/quanttide/quanttide-journal-of-cognitive-engineering) | 认知工程日志，讲故事思路参考 |

**不用 Fork：** 本课题工作仓库（下面「你的工作仓库」）—— 这是你自己 push 作业的地方。

---

## 你的工作仓库（本课题）

Fork 官方仓库是为了**读和对照**；你写 Loop、跑 trials、交阶段报告，都在**自己的工作仓库**里：

- 建议名：`product-requirement-loop`（或导师指定的名字）
- 内容：本目录全部文件（课题申请、阶段报告、`project/` 骨架等）

克隆后目录结构应包含：

```
product-requirement-loop/
├── 阶段0验收操作手册.md    ← 你现在的验收步骤
├── 阶段0实现报告.md
├── project/
│   ├── product-requirement/specification.yaml
│   └── trials/case-01/review.html
└── screenshots/
```

---

## Fork 操作（GitHub 网页）

以 `quanttide-journal-of-product-development` 为例：

1. 打开 https://github.com/quanttide/quanttide-journal-of-product-development  
2. 右上角点 **Fork**  
3. 选你自己的账号，创建 Fork  
4. 对你账号下的 Fork 点 **Code** → 复制 HTTPS 地址  
5. 本地克隆（示例）：

```powershell
git clone https://github.com/你的用户名/quanttide-journal-of-product-development.git
```

对其余「必 Fork」仓库重复以上步骤。

---

## 本仓库怎么从 GitHub 拉下来？

导师或 AI 推送到你的 GitHub 后：

```powershell
git clone https://github.com/你的用户名/product-requirement-loop.git
cd product-requirement-loop
```

然后按 [阶段0验收操作手册.md](../阶段0/阶段0验收操作手册.md) 逐项验收。

---

## 阶段 1 要用官方仓库的哪些路径？

| 用途 | 官方路径 |
|------|----------|
| 复制执行器 | `quanttide-profile-of-agent-engineering/default/loops/devops-code/implementation.py` |
| yaml 模板 | 同目录 `specification.yaml` |
| 试点日志全文 | `quanttide-journal-of-product-development/qtcloud-product/2026-08-19.md` |
| 输出样例 | `quanttide-profile-of-product-development/qtcloud-product/requirement.json` |

---

## 代理（国内访问 GitHub）

若 `git clone` / `git push` 很慢或失败，在 PowerShell 里先设代理（端口按你本机改，常见 7890）：

```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

推送完成后可取消：

```powershell
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

## 和量潮上游的关系（答辩用一句话）

> 输入来自官方产品研发日志；Loop 定义对齐 Agent 工程档案；本期在 Fork 对照的基础上，于个人仓库补齐 `product-requirement` 可执行定义与 trials，合适时再向上游提 PR。
