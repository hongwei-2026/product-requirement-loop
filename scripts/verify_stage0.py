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
        ("D01", "阶段0实现报告", "阅读记录与结论", "阶段0实现报告.md"),
        ("D02", "阶段0快速验收清单", "10条勾表认可", "阶段0快速验收清单.md"),
        ("D03", "人机确认操作指南", "人怎么验收AI笔记", "人机确认操作指南.md"),
        ("D04", "复核关键词卡", "不熟文件时怎么找", "复核关键词卡-case01.md"),
        ("D05", "项目实现流程报告", "全阶段路线图", "项目实现流程报告.md"),
        ("D06", "课题申请", "正式申请文档", "课题申请.md"),
        ("D07", "资料清单", "材料索引", "资料清单.md"),
        ("D08", "图文预览", "浏览器看图", "图文预览.html"),
    ]
    for cid, name, feat, rel in docs:
        ok, detail = check_exists(rel, feat, name)
        run(cid, name, feat, ok, detail)

    # --- 试点输入 ---
    run(
        "I01",
        "官方日志摘录",
        "输入不凭空编造",
        (ROOT / "project/trials/case-01/input/journal-raw.md").exists(),
        "journal-raw.md",
    )
    raw = (ROOT / "project/trials/case-01/input/journal-raw.md").read_text(encoding="utf-8")
    run(
        "I02",
        "摘录含核心句",
        "与官方日志可对齐",
        "捕捉用户故事" in raw and "零碎话语" in raw,
        "含「捕捉用户故事」「零碎话语」",
    )
    run(
        "I03",
        "来源证明",
        "输入可追溯",
        (ROOT / "project/trials/case-01/input/SOURCE.md").exists()
        and "quanttide-journal-of-product-development" in (ROOT / "project/trials/case-01/input/SOURCE.md").read_text(encoding="utf-8"),
        "SOURCE.md 含官方仓库链接",
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
    manual = ROOT / "阶段0验收操作手册.md"
    run(
        "M01",
        "阶段0验收操作手册",
        "逐步操作指导",
        manual.exists(),
        "阶段0验收操作手册.md",
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
