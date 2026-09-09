# -*- coding: utf-8 -*-
"""Create extreme extension task Issues (one-shot). Run: python scripts/create_extreme_tasks.py"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

TASKS = [
    {
        "pts": 75,
        "title": "[Task][Extreme] 定稿导出产品云可对齐的 requirement.json 包",
        "bg": "定稿终点目前是 accepted.json。量潮下游需要文件级 requirement 资产包，便于产品云/后续系统对齐，且不引入飞书 API、不做 JSON→SQL。",
        "goal": "从定稿档案一键导出（或校验）requirement.json 包：字段映射、校验脚本、手册说明、verify 门禁；失败时给出可读差异。",
        "accept": [
            "导出包可被离线校验脚本通过",
            "与现有 accepted.json / check 门禁兼容，不削弱 Step3",
            "文档写入 docs/交付；无真实 Key",
            "Design 落 docs/designs/#N-*.md；Impl 含视频+截图≥2",
        ],
    },
    {
        "pts": 80,
        "title": "[Task][Extreme] 第二大脑 Context 导出包（故事+引用+审核轨迹）",
        "bg": "对齐量潮 second-brain / public-second-brain 资产观：定稿结果应能打成可归档的 Context 包（非改章程文件名）。",
        "goal": "导出含用户要故事、source_quote、审核理由码、修订摘要、元数据格子的打包目录/压缩包；提供导入说明与校验。",
        "accept": [
            "包内结构稳定、有版本字段",
            "引用可回溯到源日志片段",
            "手册说明边界；不冒充组织章程改名",
            "Design + 视频 + 截图齐全",
        ],
    },
    {
        "pts": 70,
        "title": "[Task][Extreme] SemVer 发布门禁（标签 + CHANGELOG/release notes）",
        "bg": "量潮 release.md 要求 SemVer v.x.y.z（含 alpha/beta/rc）。本仓交付层缺少可自动检查的发布门禁。",
        "goal": "脚本+CI：校验标签格式、CHANGELOG/发布说明必填项；文档写清流程；不改业务文件名为 release.md。",
        "accept": [
            "错误标签/缺说明时 CI 红",
            "合法预发布标签可通过",
            "docs/交付 有操作说明",
            "Design + 视频（演示门禁红绿）+ 截图",
        ],
    },
    {
        "pts": 75,
        "title": "[Task][Extreme] 工作台覆盖率 / uncovered 面板 + 人确认 UX",
        "bg": "验收强调覆盖与 source_quote；check 已有能力，但工作台对未覆盖句暴露不足，人容易漏确认。",
        "goal": "在工作台展示未覆盖/弱覆盖句；定稿前强制路径（确认或退回）；与 check 结果一致；补 lessons。",
        "accept": [
            "未覆盖可见且可定位到原文",
            "未处理完不可静默定稿",
            "verify_lessons 增回归",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 70,
        "title": "[Task][Extreme] 故事/定稿修订时间线 UI（revisions）",
        "bg": "accepted 与会话已有 revisions 语义；量潮审核文化需要「谁改了什么/为何」可视。",
        "goal": "工作台或定稿详情展示修订时间线（作者、时间、理由码、前后摘要）；只读为主，可跳转。",
        "accept": [
            "有 revisions 的样本可完整展示",
            "无 revisions 有空态",
            "不泄露其它用户敏感字段",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 75,
        "title": "[Task][Extreme] 打叉理由分析看板（按产品/时间聚合）",
        "bg": "理由码（编造/分层/漏了…）已存在；缺少跨日志聚合，难以回流提示词与流程。",
        "goal": "审核历史 → 看板：按理由码/产品流/时间聚合；可下钻到条目；导出 CSV 可选。",
        "accept": [
            "至少 3 个聚合维度可用",
            "数据来自现有库/历史，不造假",
            "登录门禁保留",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 80,
        "title": "[Task][Extreme] 待审库指派 / 交接 / 超时回收（SLA）",
        "bg": "人多时队列需要所有权；已有 assignee 雏形，缺交接与僵死回收。",
        "goal": "指派、转交、超时标记/回收、审计日志；与 cancel 共存；禁止一键全过。",
        "accept": [
            "指派与转交可审计",
            "超时策略可配置且有默认",
            "cancel 与锁定语义不回退",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 80,
        "title": "[Task][Extreme] 官方日志 Inbox 强去重 + 冲突处理台",
        "bg": "量潮官方研发日志库是输入源；重复拉取/半条/冲突若静默，会破坏人审入口质量。",
        "goal": "去重指纹、冲突队列、人决合并/丢弃；保留同意入库门禁；有回归夹具。",
        "accept": [
            "重复与冲突可演示",
            "人决前不覆盖正式库",
            "无 Key；有 verify/夹具",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 85,
        "title": "[Task][Extreme] 批量：Step1 通过后可入队 Step2 草稿（仍必须人审）",
        "bg": "批量今日多停在 Step1 草稿；吞吐瓶颈，但不能破坏「AI 草稿、人拍板」。",
        "goal": "Step1 人审通过后可选入队生成 Step2 草稿；待审库状态清晰；禁止批量自动 Approve/定稿。",
        "accept": [
            "Step2 草稿入队可开关",
            "无人审不能进定稿",
            "状态机与 cancel 安全",
            "Design（含状态图）+ 视频 + 截图",
        ],
    },
    {
        "pts": 85,
        "title": "[Task][Extreme] Prompt 版本钉死 + 审计字段（prompt_sha）",
        "bg": "量潮 Agent Loop 要求可复现：同日志不同提示必须可追溯。",
        "goal": "运行时记录 prompt 路径/哈希写入会话与定稿元数据；手册说明如何钉版本；CI 断言字段存在。",
        "accept": [
            "产物含 prompt_sha（或等价）",
            "切换提示文件后哈希变化可测",
            "不把密钥写入审计",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 90,
        "title": "[Task][Extreme] 多 trial 矩阵（case-02+）+ CI 金标（无真实 Key）",
        "bg": "证据链几乎只有 case-01；组织 Loop 范式需要多样 trials 且 CI 无 Key。",
        "goal": "新增 ≥2 个 trial 夹具+金标；CI 矩阵跑静态/模拟门禁；文档说明与 case-01 关系。",
        "accept": [
            "CI 无 Key 全绿",
            "新 trial 有独立 golden/报告骨架",
            "不降低现有 case-01 门禁",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 90,
        "title": "[Task][Extreme] 运行时安全切换 LLM provider/model + 健康探测",
        "bg": "多厂商 llm_config 已有，但切换多靠改 .env 重启；运维需要管理员安全切换与探针。",
        "goal": "管理员 UI/API：切换 provider/model/timeout（不落盘明文 Key）；健康探测；审计；失败回滚。",
        "accept": [
            "非管理员不可改",
            "Key 永不进仓/进前端",
            "探测失败有明确错误分类",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 75,
        "title": "[Task][Extreme] 错误分类回流 verify_lessons（超时/代理/JSON/进程）",
        "bg": "结项反馈有超时、代理、JSON、进程中止等坑；需变成可回归门禁（量潮踩坑回流）。",
        "goal": "统一错误分类枚举；前端/后端对齐；verify_lessons 夹具覆盖主路径；文档 FAQ 同步。",
        "accept": [
            "至少 4 类错误有断言",
            "与「服务宕机 vs 超时」口径一致",
            "CI 无 Key 绿",
            "Design + 视频 + 截图",
        ],
    },
    {
        "pts": 85,
        "title": "[Task][Extreme] 待审库/定稿 JSON↔SQLite 单一数据源清理",
        "bg": "双写（json + db）是后续队列/定稿功能的可靠性地雷，人多扩展前必须收敛。",
        "goal": "选定单一真相源；迁移脚本；读写路径统一；兼容旧数据；强回归与回滚说明。",
        "accept": [
            "明确唯一写入路径",
            "迁移可重复执行/可回滚文档",
            "verify_lessons + 手动迁移演练记录（视频）",
            "Design（含数据流）+ 视频 + 截图",
        ],
    },
]


OPS = """
## 难度 / 积分
- 难度：**特难（Extreme）**
- 积分：{pts}

## 背景
{bg}

## 目标
{goal}

## 非目标（禁止踩线）
- 不做飞书 API / JSON→SQL / 产品云画布 / 局域网放开
- 不削弱 Step3 check 门禁、待审库 cancel、登录与本机绑定
- 不提交 API Key

## 如何接取 / 放弃 / 同步仪表盘
命令写在**本 Issue 评论区**，单独一行。

| 你要做的事 | 评论命令 | 仪表盘会怎样 |
|------------|----------|--------------|
| 接任务 | `/claim` | 「进行中的认领」出现你与本 Issue |
| 维护者正式锁定 | （仅 @hongwei-2026）`/accept @你的ID` | 状态 → 已锁定实现中 |
| **自己放弃** | `/cancel` 或 `/release` | 认领记录**自动删除** |
| 维护者清掉别人的认领 | `/reject-claim` | 同上 |
| 合并后计分 | （维护者/必审人）`/score {pts}` | 排行榜刷新 |

**硬性规则：同一 GitHub 账号同时只能有 1 个进行中任务**（`claim-pending` 或 `locked`）。想换题必须先 `/cancel`。

接取后：Design 落 `docs/designs/#N-….md` → Design PR → 邮件 `feizi_050920@qq.com` → `/accept` → Impl PR。  
仪表盘：https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E4%BB%BB%E5%8A%A1%E4%BB%AA%E8%A1%A8%E7%9B%98.md

## 交付物规范（Implementation PR 缺一不可）
1. **代码**：`[Impl] #N …` + `Fixes #N`；作者须为已 `/accept` 的 Assignee
2. **演示视频链接（必填）**
3. **截图 ≥2（必填，贴正文）**
4. 缺材料必审人可拒 Approve；补齐后 `/recheck`

## 验收标准
{accept}

## AI / 自动审核关注点
- 特难扩展：Design 必须含状态/数据流与非目标
- 安全与门禁零回退
- Enterprise PR 套件全绿

总入口：https://github.com/hongwei-2026/product-requirement-loop/issues/7
指南：https://github.com/hongwei-2026/product-requirement-loop/blob/main/docs/%E4%BA%A4%E4%BB%98/%E4%BB%BB%E5%8A%A1%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97.md
"""


def main() -> None:
    # ensure labels
    labels = [
        ("difficulty:extreme", "B60205", "extreme / 特难"),
        ("status:open", "EDEDED", "open for claim"),
    ]
    for name, color, desc in labels:
        subprocess.run(
            ["gh", "label", "create", name, "--color", color, "--description", desc, "--force"],
            check=False,
        )

    created = []
    for t in TASKS:
        pts = t["pts"]
        accept = "\n".join(f"- [ ] {x}" for x in t["accept"])
        body = OPS.format(pts=pts, bg=t["bg"], goal=t["goal"], accept=accept)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as f:
            f.write(body)
            path = f.name
        # points label
        pl = f"points:{pts}"
        subprocess.run(
            ["gh", "label", "create", pl, "--color", "5319E7", "--description", f"{pts} pts", "--force"],
            check=False,
        )
        r = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--title",
                t["title"],
                "--body-file",
                path,
                "--label",
                "task",
                "--label",
                "difficulty:extreme",
                "--label",
                pl,
                "--label",
                "status:open",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        url = (r.stdout or "").strip()
        print(url)
        created.append({"title": t["title"], "pts": pts, "url": url})
        Path(path).unlink(missing_ok=True)

    out = Path("docs/交付/_extreme_tasks_created.json")
    out.write_text(json.dumps(created, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
