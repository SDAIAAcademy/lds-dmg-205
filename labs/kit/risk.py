# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Re-identification risk before and after a treatment (lab 2.1). From the labs/ folder:

    uv run kit/risk.py files/open/treatment_start.json      # the treatment as it arrived
    uv run kit/risk.py out/treatment.json                   # your treatment

The measures are those ARX documents for its privacy models: records grouped into equivalence
classes by the quasi-identifiers; k is the size of the smallest class; the highest risk of a
record is 1 / (its class size), so the highest risk of the file is 1 / k; the average risk is
the number of classes divided by the number of records; a sample unique is a record alone in
its class. A class whose records all share one value of the sensitive column is homogeneous:
knowing that a person is in it reveals that value (the limit of k-anonymity that l-diversity
addresses).

Treatment keys: drop (columns removed), generalise (column: "hierarchy" | "bands:18,30,45,65"
| "band:10" | "month" | "quarter" | "year"), quasi_identifiers, sensitive, k, suppress_below_k
(remove the records of classes smaller than k). Writes out/release.csv and out/risk_report.json.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from common import FILES, OUT, fix, info, ok, path, read_csv, read_json, write_csv, finish

THRESHOLDS = {"k": 5, "highest": 0.2, "average": 0.05, "suppressed_share": 0.05}


def hierarchy() -> dict[str, dict[str, str]]:
    h: dict[str, dict[str, str]] = defaultdict(dict)
    for r in read_csv(FILES / "open" / "hierarchies.csv"):
        h[r["attribute"]][r["value"]] = r["parent"]
    return h


def generalise(value: str, rule: str, column: str, h) -> str:
    if value == "":
        return value
    if rule == "hierarchy":
        return h.get(column, {}).get(value, value)
    if rule.startswith("bands:"):
        cuts = [int(x) for x in rule[6:].split(",")]
        v = int(float(value))
        for lo, hi in zip(cuts, cuts[1:]):
            if lo <= v < hi:
                return f"{lo}-{hi - 1}"
        return f"{cuts[-1]}+" if v >= cuts[-1] else f"<{cuts[0]}"
    if rule.startswith("band:"):
        w = int(rule[5:])
        lo = int(float(value)) // w * w
        return f"{lo}-{lo + w - 1}"
    if rule == "month":
        return value[:7]
    if rule == "quarter":
        return f"{value[:4]}-Q{(int(value[5:7]) - 1) // 3 + 1}"
    if rule == "year":
        return value[:4]
    raise SystemExit(f"unknown rule {rule!r} for {column}")


def measure(rows: list[dict], qis: list[str], sensitive: str | None) -> dict:
    classes: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        classes[tuple(r[q] for q in qis)].append(r)
    sizes = [len(v) for v in classes.values()]
    n = len(rows)
    homogeneous = 0
    if sensitive:
        homogeneous = sum(1 for v in classes.values() if len(v) > 1 and len({r[sensitive] for r in v}) == 1)
    return {
        "records": n,
        "classes": len(classes),
        "k_min": min(sizes) if sizes else 0,
        "sample_uniques": sum(1 for s in sizes if s == 1),
        "records_in_classes_below_5": sum(s for s in sizes if s < 5),
        "highest_risk": round(1 / min(sizes), 4) if sizes else 0,
        "average_risk": round(len(classes) / n, 4) if n else 0,
        "homogeneous_classes": homogeneous,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    t = read_json(path(argv[0]))
    rows = read_csv(path(t["input"]))
    columns = list(rows[0].keys())
    print(f"الملف: {t['input']}، السجلات: {len(rows)}")

    # what a person could link on: columns whose values are near-unique or repeat across rows
    print("\nالأعمدة كما وصلت: عدد القيم المختلفة")
    for c in columns:
        distinct = len({r[c] for r in rows})
        tag = "  ← فريد تقريبًا لكل سجل" if distinct > 0.9 * len(rows) else ""
        print(f"  {c:<20} {distinct:>6}{tag}")

    before = measure(rows, [q for q in t["quasi_identifiers"] if q in columns], t.get("sensitive"))

    h = hierarchy()
    drop = set(t.get("drop", []))
    gen = t.get("generalise", {})
    treated = []
    for r in rows:
        nr = {c: v for c, v in r.items() if c not in drop}
        for c, rule in gen.items():
            if c in nr:
                nr[c] = generalise(nr[c], rule, c, h)
        treated.append(nr)
    qis = [q for q in t["quasi_identifiers"] if q not in drop]
    missing = [q for q in qis if q not in treated[0]]
    if missing:
        raise SystemExit(f"quasi-identifiers not in the file: {missing}")
    k = int(t.get("k", 5))
    suppressed = 0
    if t.get("suppress_below_k"):
        counts = Counter(tuple(r[q] for q in qis) for r in treated)
        kept = [r for r in treated if counts[tuple(r[q] for q in qis)] >= k]
        suppressed = len(treated) - len(kept)
        treated = kept
    after = measure(treated, qis, t.get("sensitive"))
    after["suppressed_records"] = suppressed
    after["suppressed_share"] = round(suppressed / len(rows), 4)

    print("\nالمقياس                      قبل        بعد")
    for key in ["records", "classes", "k_min", "sample_uniques", "records_in_classes_below_5", "highest_risk", "average_risk", "homogeneous_classes"]:
        print(f"  {key:<28} {before[key]:>8} {after[key]:>10}")
    print(f"  {'suppressed_records':<28} {'':>8} {suppressed:>10}  ({after['suppressed_share']:.1%})")

    print("\nمعايير الهيئة للنشر")
    leftover = [c for c in ("report_id", "worker_id", "establishment_cr") if c in treated[0]]
    if leftover:
        fix(f"معرّفات ما زالت في الملف: {', '.join(leftover)}")
    else:
        ok("لا معرِّف مباشر ولا معرّف إداري في الملف")
    if after["k_min"] >= THRESHOLDS["k"]:
        ok(f"k = {after['k_min']}")
    else:
        fix(f"k = {after['k_min']}، والمعيار {THRESHOLDS['k']} على الأقل")
    if after["highest_risk"] <= THRESHOLDS["highest"]:
        ok(f"أعلى خطر = {after['highest_risk']}")
    else:
        fix(f"أعلى خطر = {after['highest_risk']}، والمعيار {THRESHOLDS['highest']} على الأكثر")
    if after["average_risk"] <= THRESHOLDS["average"]:
        ok(f"متوسط الخطر = {after['average_risk']}")
    else:
        fix(f"متوسط الخطر = {after['average_risk']}، والمعيار {THRESHOLDS['average']} على الأكثر")
    if after["suppressed_share"] <= THRESHOLDS["suppressed_share"]:
        ok(f"المحذوف {after['suppressed_share']:.1%} من السجلات")
    else:
        fix(f"المحذوف {after['suppressed_share']:.1%} من السجلات، والمعيار 5% على الأكثر")
    if after["homogeneous_classes"]:
        info(f"تنبيه: مجموعات متجانسة في {t.get('sensitive')}: {after['homogeneous_classes']}. اذكرها في الخطر المتبقي")

    OUT.mkdir(exist_ok=True)
    write_csv(OUT / "release.csv", list(treated[0].keys()) if treated else [], treated)
    import json
    (OUT / "risk_report.json").write_text(json.dumps({"treatment": argv[0], "before": before, "after": after}, ensure_ascii=False, indent=2), encoding="utf-8")
    info("كُتب out/release.csv وout/risk_report.json")
    return finish("معايير النشر الأربعة")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
