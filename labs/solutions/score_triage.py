"""Score a participant's decision log against the key (lab 1.1, for the trainer). From labs/:

    uv run solutions/score_triage.py <the participant's decision_log.csv>

A row matches when its decision, route, instrument and signatory are all accepted by the key.
The outcome's evidence asks for at least eight of ten.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    key = json.loads((LABS / "solutions" / "reference" / "lab_1_1.json").read_text(encoding="utf-8"))
    with open(argv[0], encoding="utf-8-sig", newline="") as f:
        log = {r["request_id"]: r for r in csv.DictReader(f)}
    n = 0
    for rid, k in key.items():
        r = log.get(rid, {})
        miss = [c for c in ("decision", "route", "instrument", "signatory") if r.get(c) not in k[c]]
        n += not miss
        print(f"{rid}: {'match' if not miss else 'differs on ' + ', '.join(miss)}")
    print(f"\n{n} of 10 match; the bar is 8: {'PASS' if n >= 8 else 'NOT YET'}")
    return 0 if n >= 8 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
