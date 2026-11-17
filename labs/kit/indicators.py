"""Five access-performance indicators from a request log and download statistics. From labs/:

    uv run kit/indicators.py files/followup/indicators_start.json   # the configuration as it arrived
    uv run kit/indicators.py out/indicators.json                    # yours

Configuration keys: the five input files, period_end, exclude_duplicates (rows whose note says
they were entered twice), exclude_withdrawn, exclude_entry_errors (decided before received),
open_requests ("ignore" or "late_if_past_deadline"), sharing_days ("calendar" or "business":
the sharing deadline of 10 days counted in working days, Sunday to Thursday).

Indicators: 1 median days from receipt to decision, per channel; 2 share decided within the
deadline; 3 approval rate, full and partial, over decisions that grant or refuse; 4 reuse:
mean monthly downloads per published dataset and documented reuses; 5 publication plan
progress. Writes out/indicators.md: aggregated numbers only, no single request.
"""
from __future__ import annotations

import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

from common import OUT, path, read_csv, read_json


def business_days_between(a: date, b: date) -> int:
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() not in (4, 5):
            n += 1
    return n


def run(cfg: dict) -> dict:
    rows = read_csv(path(cfg["requests"]))
    notes = Counter()
    kept = []
    for r in rows:
        if cfg.get("exclude_duplicates") and r["note"] == "أُدخل مرتين":
            notes["duplicates"] += 1; continue
        if cfg.get("exclude_withdrawn") and r["decision"] == "سحب":
            notes["withdrawn"] += 1; continue
        if cfg.get("exclude_entry_errors") and r["decided"] and r["decided"] < r["received"]:
            notes["entry_errors"] += 1; continue
        kept.append(r)
    end = date.fromisoformat(cfg["period_end"])
    days = defaultdict(list)
    within = defaultdict(lambda: [0, 0])
    for r in kept:
        ch = r["channel"]
        rec = date.fromisoformat(r["received"])
        limit = int(r["limit_days"])
        business = ch != "حرية معلومات" and cfg.get("sharing_days") == "business"
        if r["decided"]:
            dec = date.fromisoformat(r["decided"])
            elapsed = business_days_between(rec, dec) if business else (dec - rec).days
            days[ch].append(elapsed)
            within[ch][1] += 1
            within[ch][0] += elapsed <= limit
        elif r["decision"] == "مفتوح" and cfg.get("open_requests") == "late_if_past_deadline":
            elapsed = business_days_between(rec, end) if business else (end - rec).days
            if elapsed > limit:
                within[ch][1] += 1
                notes["open_past_deadline"] += 1
    approvals = defaultdict(lambda: [0, 0])
    for r in kept:
        if r["decision"] in ("موافقة", "موافقة جزئية", "رفض"):
            approvals[r["channel"]][1] += 1
            approvals[r["channel"]][0] += r["decision"] != "رفض"
    dl = read_csv(path(cfg["downloads"]))
    per = defaultdict(list)
    for r in dl:
        per[r["dataset"]].append(int(r["downloads"]))
    reuse = read_csv(path(cfg["reuse"]))
    plan = read_csv(path(cfg["plan"]))
    fb = read_csv(path(cfg["feedback"]))
    return {
        "rows_in_log": len(rows), "rows_used": len(kept), "excluded": dict(notes),
        "median_days": {ch: float(f"{statistics.median(v):g}") for ch, v in sorted(days.items())},
        "within_deadline": {ch: round(a / b, 3) for ch, (a, b) in sorted(within.items()) if b},
        "approval_rate": {ch: round(a / b, 3) for ch, (a, b) in sorted(approvals.items()) if b},
        "monthly_downloads": {k: round(sum(v) / len(v)) for k, v in sorted(per.items())},
        "reuses": len(reuse),
        "plan": {"planned": len(plan), "published": sum(1 for r in plan if r["published"] == "نعم")},
        "feedback_mean": round(sum(int(r["rating"]) for r in fb) / len(fb), 2) if fb else None,
    }


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def markdown(res: dict) -> str:
    labels = {"duplicates": "مكرر", "withdrawn": "مسحوب", "entry_errors": "خطأ إدخال", "open_past_deadline": "مفتوح بعد مهلته (عُدّ متأخرًا)"}
    ex = "، ".join(f"{labels[k]}: {v}" for k, v in res["excluded"].items()) or "لا شيء"
    lines = ["# مؤشرات أداء الإتاحة", "", f"السجلات في الملف: {res['rows_in_log']}؛ المستخدمة: {res['rows_used']}", f"ما استُبعد أو عولج: {ex}", ""]
    lines += ["## 1. زمن الاستجابة (الوسيط بالأيام)"] + [f"- {k}: {v:g}" for k, v in res["median_days"].items()] + [""]
    lines += ["## 2. القرارات في المهلة"] + [f"- {k}: {pct(v)}" for k, v in res["within_deadline"].items()] + [""]
    lines += ["## 3. نسبة الموافقة الكلية والجزئية"] + [f"- {k}: {pct(v)}" for k, v in res["approval_rate"].items()] + [""]
    lines += ["## 4. إعادة الاستخدام", "متوسط التنزيلات الشهري لكل مجموعة منشورة:"] + [f"- {k}: {v}" for k, v in res["monthly_downloads"].items()]
    lines += [f"حالات إعادة الاستخدام الموثقة: {res['reuses']}", ""]
    p = res["plan"]
    lines += ["## 5. تقدم خطة النشر", f"المنشور: {p['published']} من {p['planned']} ({pct(p['published'] / p['planned'])})", ""]
    lines += [f"متوسط تقييم المستخدمين: {res['feedback_mean']} من 5"]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    res = run(read_json(path(argv[0])))
    md = markdown(res)
    OUT.mkdir(exist_ok=True)
    (OUT / "indicators.md").write_text(md, encoding="utf-8")
    print(md)
    print("كُتب out/indicators.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
