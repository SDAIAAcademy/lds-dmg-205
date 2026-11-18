"""Shared helpers of the LDS-DMG-205 lab kit. Run every kit command from the labs/ folder.

Python standard library only: `uv run kit/<tool>.py` on a laptop, `python kit/<tool>.py` in Colab.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
FILES = LABS / "files"
OUT = LABS / "out"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROBLEMS: list[str] = []


def ok(text: str) -> None:
    print(f"[OK]  {text}")


def fix(text: str) -> None:
    PROBLEMS.append(text)
    print(f"[FIX] {text}")


def info(text: str) -> None:
    print(f"      {text}")


def finish(evidence: str) -> int:
    print()
    if PROBLEMS:
        print(f"RESULT: {len(PROBLEMS)} to fix. النتيجة: بنود تحتاج إصلاحًا ({len(PROBLEMS)})، ولم يتحقق بعد: {evidence}")
        return 1
    print(f"RESULT: PASS. النتيجة: تحقق {evidence}")
    return 0


def path(arg: str) -> Path:
    p = Path(arg)
    return p if p.is_absolute() else LABS / p


def read_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(p: Path, header: list[str], rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sections(markdown: str) -> dict[str, str]:
    """Split a Markdown file by its '## ' headings: {heading without its number: body}."""
    out: dict[str, str] = {}
    current = None
    for line in markdown.splitlines():
        m = re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)
        if m:
            current = m.group(1)
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def blank(text: str) -> bool:
    return "____" in text or not re.sub(r"[\s\-:()]", "", text)
