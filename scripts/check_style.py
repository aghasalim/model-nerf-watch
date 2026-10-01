"""Fail if any prose or source file contains an em dash or en dash."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
bad = []
for p in ROOT.rglob("*"):
    if p.suffix in {".md", ".py", ".yml", ".txt", ".jsonl"} and ".venv" not in p.parts:
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if chr(0x2014) in line or chr(0x2013) in line:
                bad.append(f"{p.relative_to(ROOT)}:{i}")
print("\n".join(bad) or "no dashes found")
sys.exit(1 if bad else 0)
