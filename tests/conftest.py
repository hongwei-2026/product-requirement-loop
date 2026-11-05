import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PROJECT = ROOT / "project"
for p in (SRC, PROJECT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
