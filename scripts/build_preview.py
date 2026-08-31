from pathlib import Path

base = Path(__file__).resolve().parent.parent
imgs = [
    ("图1 产品云", "13-product-cloud-capture.png"),
    ("图2 product-requirement", "03-product-requirement-index.png"),
    ("图3 journal", "11-journal-asset.png"),
    ("图5 requirement.json", "12-requirement-json.png"),
    ("图6 loops", "02-loops-readme.png"),
    ("图8 implementation", "08-implementation-py.png"),
    ("图10 划分层级", "10-product-cloud-stories.png"),
]
parts = [
    '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>图文预览</title>',
    '<style>body{font-family:"PingFang SC",sans-serif;max-width:960px;margin:0 auto;padding:20px;line-height:1.7}',
    'img{max-width:100%;border:1px solid #ddd;border-radius:8px;margin:12px 0}',
    'h2{margin-top:2em}</style></head><body>',
    "<h1>阶段0 图文预览（浏览器打开，不依赖 VS Code）</h1>",
    "<p>若 VS Code 预览看不到图，用浏览器打开本文件：<code>图文预览.html</code></p>",
]
for title, fn in imgs:
    parts.append(
        f'<h2>{title}</h2><p><code>../../screenshots/{fn}</code></p>'
        f'<img src="../../screenshots/{fn}" alt="{title}" />'
    )
parts.append(
    '<hr><p>更多文档：'
    '<a href="阶段0实现报告.md">阶段0实现报告.md</a> · '
    '<a href="人机确认操作指南.md">人机确认操作指南.md</a></p></body></html>'
)
out = base / "docs" / "阶段0" / "图文预览.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("".join(parts), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
