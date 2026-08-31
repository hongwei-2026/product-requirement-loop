#!/usr/bin/env python3
"""Sync journal-official-full.md into review.html embedded block."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
full = (root / "project/trials/case-01/input/journal-official-full.md").read_text(encoding="utf-8")
review = root / "project/trials/case-01/review.html"
text = review.read_text(encoding="utf-8")
text2, n = re.subn(
    r'(<script type="text/plain" id="journal-embedded">)(.*?)(</script>)',
    lambda m: m.group(1) + full + m.group(3),
    text,
    count=1,
    flags=re.DOTALL,
)
if n != 1:
    raise SystemExit("journal-embedded block not found")
review.write_text(text2, encoding="utf-8")
print(f"synced {len(full)} chars into review.html")
