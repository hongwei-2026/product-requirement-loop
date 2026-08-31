#!/usr/bin/env python3
"""阶段 0 自动验收脚本（工作流自测）。

用法：
  python scripts/verify_stage0.py
  python scripts/verify_stage0.py --write-report stage0-self-test-report.md
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent

# 每项：id, 检查什么, 对应阶段0功能, 路径或检查函数
CHECKS: list[dict] = []


def check_exists(rel: str, feature: str, desc: str) -> tuple[bool, str]:
    p = ROOT / rel
    if p.exists():
        return True, f"存在: {rel}"
    return False, f"缺失: {rel}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", type=Path, help="写入自测报告 markdown")
    args = parser.parse_args()

    results: list[dict] = []
    failed = 0

    def run(cid: str, name: str, feature: str, ok: bool, detail: str):
        nonlocal failed
        if not ok:
            failed += 1
        results.append(
            {"id": cid, "name": name, "feature": feature, "ok": ok, "detail": detail}
        )
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {cid} {name} — {detail}")

    # --- 文档产出 ---
    docs = [
        ("D01", "阶段0实现报告", "阅读记录与结论", "docs/阶段0/阶段0实现报告.md"),
        ("D02", "阶段0快速验收清单", "10条勾表认可", "docs/阶段0/阶段0快速验收清单.md"),
        ("D03", "人机确认操作指南", "人怎么验收AI笔记", "docs/阶段0/人机确认操作指南.md"),
        ("D04", "复核关键词卡", "不熟文件时怎么找", "docs/阶段0/复核关键词卡-case01.md"),
        ("D05", "项目实现流程报告", "全阶段路线图", "docs/申请/项目实现流程报告.md"),
        ("D06", "课题申请", "正式申请文档", "docs/申请/课题申请.md"),
        ("D07", "资料清单", "材料索引", "docs/申请/资料清单.md"),
        ("D08", "图文预览", "浏览器看图", "docs/阶段0/图文预览.html"),
    ]
    for cid, name, feat, rel in docs:
        ok, detail = check_exists(rel, feat, name)
        run(cid, name, feat, ok, detail)

    # --- 试点输入 ---
    full_path = ROOT / "project/trials/case-01/input/journal-official-full.md"
    excerpt_path = ROOT / "project/trials/case-01/input/journal-excerpt.md"
    run(
        "I01",
        "官方原文（完整）",
        "左侧展示原封不动",
        full_path.exists(),
        "journal-official-full.md",
    )
    full = full_path.read_text(encoding="utf-8") if full_path.exists() else ""
    run(
        "I02",
        "完整原文够长且含核心句",
        "不是摘要冒充原文",
        len(full) > 1500 and "捕捉用户故事" in full and "事件风暴" in full,
        f"{len(full)} 字，含捕捉用户故事/事件风暴",
    )
    run(
        "I03",
        "摘录单独存放",
        "关键词卡用短摘录",
        excerpt_path.exists() and len(excerpt_path.read_text(encoding="utf-8")) < len(full),
        "journal-excerpt.md 短于 full",
    )
    run(
        "I04",
        "来源证明与正确路径",
        "输入可追溯",
        (ROOT / "project/trials/case-01/input/SOURCE.md").exists()
        and "quanttide-devops/loops/devops-code" in (ROOT / "project/trials/case-01/input/SOURCE.md").read_text(encoding="utf-8"),
        "SOURCE.md 含 quanttide-devops/loops/devops-code",
    )

    # --- 验收 UI ---
    review = ROOT / "project/trials/case-01/review.html"
    review_text = review.read_text(encoding="utf-8") if review.exists() else ""
    run("U01", "验收对照页", "左原文右故事", review.exists(), str(review.relative_to(ROOT)))
    run(
        "U02",
        "关键词高亮",
        "不熟文件也能复核",
        'data-kw="捕捉用户故事"' in review_text,
        "review.html 含关键词按钮",
    )
    run(
        "U03",
        "打叉须写原因",
        "revise 留痕",
        "buildRevise" in review_text and "TEMPLATES" in review_text,
        "含句式模板与 buildRevise",
    )
    run(
        "U04",
        "锁定与重跑说明",
        "不重复确认已通过项",
        "锁定" in review_text and "unlock" in review_text,
        "含锁定/unlock 文案",
    )
    run(
        "U05",
        "左侧标题为完整原文",
        "不标原始却给摘要",
        "官方原文（完整" in review_text and "原始日志" not in review_text,
        "标题含「官方原文（完整）」",
    )
    run(
        "U06",
        "AI 试抓按钮",
        "右侧可跑 Agnes",
        "runAiDraft" in review_text and "btn-ai" in review_text,
        "含 AI 试抓与 runAiDraft",
    )
    run(
        "U07",
        "通过/打叉互斥",
        "点叉后 ok 清空",
        "setVerdict" in review_text and "verdict-pending" in review_text,
        "含 setVerdict 与 pending 状态",
    )

    # --- Loop 骨架 ---
    spec = ROOT / "project/product-requirement/specification.yaml"
    run("L01", "specification.yaml", "Loop 定义骨架", spec.exists(), str(spec.relative_to(ROOT)))
    if spec.exists() and yaml:
        data = yaml.safe_load(spec.read_text(encoding="utf-8"))
        keys = {"entry", "exit", "steps", "feedback", "loop", "acceptance"}
        missing = keys - set(data.keys())
        run(
            "L02",
            "yaml 字段完整",
            "对齐 devops-code 模板",
            not missing,
            f"缺少: {missing}" if missing else "entry/exit/steps/feedback/loop/acceptance 齐全",
        )
        run(
            "L03",
            "acceptance 数值门槛",
            "课题验收标准声明",
            data.get("acceptance", {}).get("fabrication_count") == 0,
            "fabrication_count=0",
        )
    elif spec.exists():
        run("L02", "yaml 字段完整", "对齐 devops-code 模板", False, "未安装 pyyaml，跳过解析")
        run("L03", "acceptance 数值门槛", "课题验收标准声明", False, "未安装 pyyaml")

    run(
        "L04",
        "check.py",
        "自动验收脚本",
        (ROOT / "project/check.py").exists(),
        "project/check.py",
    )
    run(
        "L05",
        "accepted schema",
        "定稿 JSON 结构",
        (ROOT / "project/schemas/accepted.schema.json").exists(),
        "schemas/accepted.schema.json",
    )

    # --- 截图证据 ---
    pngs = list((ROOT / "screenshots").glob("*.png"))
    run(
        "S01",
        "官方资料截图",
        "阅读笔记有据可查",
        len(pngs) >= 7,
        f"screenshots/ 下 {len(pngs)} 张 PNG（需≥7）",
    )
    required_png = [
        "13-product-cloud-capture.png",
        "03-product-requirement-index.png",
        "12-requirement-json.png",
    ]
    for fn in required_png:
        ok = (ROOT / "screenshots" / fn).exists()
        run("S02-" + fn[:6], f"图证据 {fn}", "文档插图", ok, fn)

    # --- 阶段0验收手册 ---
    manual = ROOT / "docs/阶段0/阶段0验收操作手册.md"
    run(
        "M01",
        "阶段0验收操作手册",
        "逐步操作指导",
        manual.exists(),
        "docs/阶段0/阶段0验收操作手册.md",
    )
    if manual.exists():
        mtext = manual.read_text(encoding="utf-8")
        run(
            "M02",
            "手册含截图引用",
            "便于对照操作",
            bool(re.search(r"screenshots/stage0/", mtext)),
            "含 stage0 验收截图路径",
        )

    # --- 启动器 ---
    bat = ROOT / "启动阶段0验收.bat"
    run("P01", "启动 bat 存在", "双击启动入口", bat.exists(), "启动阶段0验收.bat")
    open_review = ROOT / "open-review.bat"
    run("P01b", "open-review.bat", "纯英文兜底启动", open_review.exists(), "open-review.bat")
    if open_review.exists():
        text = open_review.read_text(encoding="utf-8")
        non_ascii = [c for c in text if ord(c) > 127]
        run(
            "P01c",
            "open-review 纯 ASCII",
            "避免 cmd 乱码",
            len(non_ascii) == 0,
            f"非 ASCII 字符数={len(non_ascii)}（应为 0）",
        )
    fallback = ROOT / "打开验收页.bat"
    run("P02", "备用打开 bat", "主启动失败时兜底", fallback.exists(), "打开验收页.bat")
    ps1 = ROOT / "scripts" / "start_stage0.ps1"
    run("P03", "启动 ps1 存在", "bat 调用的脚本", ps1.exists(), "scripts/start_stage0.ps1")
    syntax_ok = False
    syntax_detail = "未检测"
    test_ps1 = ROOT / "scripts" / "test_launcher_syntax.ps1"
    if test_ps1.exists():
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-File", str(test_ps1)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(ROOT),
            )
            syntax_ok = r.returncode == 0
            syntax_detail = (r.stdout or r.stderr or "").strip().split("\n")[-1][:80]
        except Exception as e:
            syntax_detail = str(e)
    run("P04", "ps1 语法合法", "避免双击闪退", syntax_ok, syntax_detail)
    manifest = ROOT / "launcher-files.json"
    run("P05", "launcher-files.json", "中文路径清单", manifest.exists(), "launcher-files.json")
    run(
        "P07",
        "start-with-ai.bat",
        "带 AI 的本地服务入口",
        (ROOT / "start-with-ai.bat").exists(),
        "start-with-ai.bat",
    )
    run(
        "P08",
        "stage0_server.py",
        "Agnes API 代理",
        (ROOT / "scripts/stage0_server.py").exists(),
        "scripts/stage0_server.py",
    )
    if manifest.exists():
        mf = json.loads(manifest.read_text(encoding="utf-8"))
        for key in ("review_html", "preview_html", "acceptance_manual_md"):
            p = ROOT / mf.get(key, "").replace("/", "\\")
            run(f"P06-{key[:6]}", f"清单路径存在 {key}", "启动器能打开文件", p.exists(), str(p.name))

    # --- 自测报告 ---
    print(f"\n合计: {len(results)} 项, 通过 {len(results) - failed}, 失败 {failed}")

    if args.write_report:
        lines = [
            "# 阶段 0 工作流自测报告",
            "",
            f"**生成时间：** {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %z')}",
            f"**结果：** {'全部通过' if failed == 0 else f'{failed} 项未通过'}",
            "",
            "| ID | 检查项 | 对应功能 | 结果 | 说明 |",
            "|----|--------|----------|------|------|",
        ]
        for r in results:
            lines.append(
                f"| {r['id']} | {r['name']} | {r['feature']} | {'✓' if r['ok'] else '✗'} | {r['detail']} |"
            )
        lines.append("")
        lines.append("由 `python scripts/verify_stage0.py --write-report` 自动生成。")
        args.write_report.write_text("\n".join(lines), encoding="utf-8")
        print(f"已写入: {args.write_report}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
