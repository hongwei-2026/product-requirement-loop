#!/usr/bin/env python3
"""Embed specification.yaml JSON into review.html for file:// fallback."""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "project/product-requirement/specification.yaml"
REVIEW = ROOT / "project/trials/case-01/review.html"


def main() -> None:
    data = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    blob = json.dumps(data, ensure_ascii=False)
    b64 = base64.b64encode(blob.encode("utf-8")).decode("ascii")
    # base64 单行，避免 HTML 格式化器在 JSON 字符串里插入换行
    block = f'<script type="application/json" id="spec-embedded" data-encoding="base64">{b64}</script>'
    pat = r'<script type="application/json" id="spec-embedded"[^>]*>.*?</script>'
    text = REVIEW.read_text(encoding="utf-8")
    if 'id="spec-embedded"' in text:
        text2, n = re.subn(pat, block, text, count=1, flags=re.DOTALL)
    else:
        text2 = text.replace(
            '<footer>验收用页面',
            block + "\n\n  <footer>验收用页面",
            1,
        )
        n = 1
    if n != 1:
        raise SystemExit("could not inject spec-embedded")
    REVIEW.write_text(text2, encoding="utf-8")
    json.loads(blob)
    print(f"synced spec into review.html ({len(blob)} chars json, base64 {len(b64)})")


if __name__ == "__main__":
    main()
