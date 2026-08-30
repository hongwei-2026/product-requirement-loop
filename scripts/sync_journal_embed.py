#!/usr/bin/env python3
"""把 journal-raw.md 同步进 review.html 的内嵌兜底块（改日志后运行一次）。"""

from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
journal = (root / "project/trials/case-01/input/journal-raw.md").read_text(encoding="utf-8").strip()
review = root / "project/trials/case-01/review.html"
text = review.read_text(encoding="utf-8")
new_text, n = re.subn(
    r'(<script type="text/plain" id="journal-embedded">)(.*?)(</script>)',
    lambda m: m.group(1) + journal + m.group(3),
    text,
    count=1,
    flags=re.DOTALL,
)
if n != 1:
    raise SystemExit("未找到 journal-embedded 块")
review.write_text(new_text, encoding="utf-8")
print("已同步 journal-raw.md → review.html#journal-embedded")
