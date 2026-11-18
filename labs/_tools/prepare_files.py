# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate every file of the LDS-DMG-205 labs, with a fixed seed. From the labs/ folder:

    uv run --no-project _tools/prepare_files.py

Writes labs/files/ (what participants get) and labs/solutions/reference/ (the trainer's keys).
The case: Siyan Occupational Safety and Health Authority, a fictional regulator. Every name,
number, identity number and phone number is synthetic: worker identity numbers start with 9,
establishment registration numbers with CR-9, phones with 0599, mail uses example.org.
Python standard library only; the same bytes on every run.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
FILES = LABS / "files"
REF = LABS / "solutions" / "reference"
SEED = 205

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import content as C  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- the register (classification of every file)

def register() -> None:
    rows = [[f, level, note] for f, level, note in C.REGISTER]
    write_csv(FILES / "register.csv", ["file", "classification", "note"], rows)


# ---------------------------------------------------------------- lab 1.1: ten sharing requests

def triage() -> None:
    d = FILES / "triage"
    for r in C.REQUESTS:
        write(d / "requests" / f"{r['id']}.txt", r["text"])
    write_csv(d / "data_inventory.csv", ["dataset", "description", "classification", "source_entity", "published_open"], C.INVENTORY)
    header = ["request_id", "decision", "route", "instrument", "signatory", "reason"]
    write_csv(d / "decision_log_template.csv", header, [[r["id"], "", "", "", "", ""] for r in C.REQUESTS])
    write(d / "codes.md", C.TRIAGE_CODES)
    write(d / "sharing_procedure.md", C.SHARING_PROCEDURE)
    write(d / "agreement_template.md", C.AGREEMENT_TEMPLATE)
    key = {r["id"]: r["key"] for r in C.REQUESTS}
    write_json(REF / "lab_1_1.json", key)
    write_csv(REF / "decision_log_reference.csv", header,
              [[r["id"], r["key"]["decision"][0], r["key"]["route"][0], r["key"]["instrument"][0], r["key"]["signatory"][0], r["key"]["reason"]] for r in C.REQUESTS])
    write(REF / "agreement_reference.md", C.AGREEMENT_REFERENCE)


# ---------------------------------------------------------------- lab 1.2: a research request for linked records

def research() -> None:
    d = FILES / "research"
    write(d / "research_request.txt", C.RESEARCH_REQUEST)
    write(d / "funding_note.txt", C.FUNDING_NOTE)
    write_csv(d / "fields_requested.csv", ["field", "source_table", "description"], [[f, t, desc] for f, t, desc, _k, _r in C.RESEARCH_FIELDS])
    write_csv(d / "fields_decision_template.csv", ["field", "decision", "reason"], [[f, "", ""] for f, *_ in C.RESEARCH_FIELDS])
    write(d / "memo_template.md", C.MEMO_TEMPLATE)
    write(d / "access_routes.md", C.ACCESS_ROUTES)
    write_csv(REF / "fields_decision_reference.csv", ["field", "decision", "reason"], [[f, k, r] for f, _t, _d, k, r in C.RESEARCH_FIELDS])
    write(REF / "research_memo_reference.md", C.MEMO_REFERENCE)


# ---------------------------------------------------------------- lab 2.1: injury reports for open publication

def injuries(rng: random.Random, year: int, n: int) -> list[dict]:
    rows = []
    start = date(year, 1, 1)
    for i in range(n):
        region = rng.choices(list(C.REGIONS), weights=[34, 22, 20, 14, 10])[0]
        city = rng.choices(C.REGIONS[region], weights=[60, 25, 15])[0]
        sector = rng.choices([s for s, _w in C.SECTORS], weights=[w for _s, w in C.SECTORS])[0]
        group = rng.choices(list(C.OCCUPATIONS), weights=C.OCC_WEIGHTS[sector])[0]
        occ = rng.choice([o for o in C.OCCUPATIONS[group] if o != C.RARE_OCCUPATION])
        size = rng.choices(C.SIZES, weights=[18, 30, 30, 22])[0]
        age = max(18, min(64, int(rng.gauss(36, 10))))
        gender = "أنثى" if rng.random() < (0.30 if sector in ("الرعاية الصحية", "التجزئة") else 0.04) else "ذكر"
        nat = "سعودي" if rng.random() < 0.38 else "غير سعودي"
        day = start + timedelta(days=rng.randrange(365))
        itype = rng.choices([t for t, _w in C.INJURY_TYPES], weights=[w for _t, w in C.INJURY_TYPES])[0]
        days_lost = max(0, int(rng.expovariate(1 / 9)))
        rows.append({
            "report_id": f"INJ-{year}-{i + 1:05d}",
            "worker_id": "9" + "".join(str(rng.randrange(10)) for _ in range(9)),
            "establishment_cr": "CR-9" + "".join(str(rng.randrange(10)) for _ in range(8)),
            "region": region, "city": city, "sector": sector, "establishment_size": size,
            "occupation": occ, "age": age, "gender": gender, "nationality": nat,
            "injury_date": day.isoformat(), "injury_type": itype, "days_lost": days_lost,
        })
    return rows


def plant_open(rows: list[dict]) -> None:
    """Planted problems the risk test must find (lab 2.1)."""
    # 1. a rare occupation in one small city: three commercial divers, all in one quarter
    for k, r in enumerate(rows[100:103]):
        r.update(region="الساحل", city="العوسج", sector="التشييد", occupation="غواص تجاري", gender="ذكر",
                 establishment_size="صغيرة (أقل من 10)", injury_date=f"2025-08-{10 + k:02d}")
    # 2. a homogeneous group: female workers in health care in the mountain region, all needle-stick injuries
    for r in rows:
        if r["sector"] == "الرعاية الصحية" and r["gender"] == "أنثى" and r["region"] == "الجبل":
            r["injury_type"] = "وخز إبرة"
    # 3. one establishment reports many injuries: its registration number links rows across the year
    for r in rows[200:260]:
        r["establishment_cr"] = "CR-900000417"


def open_data(rng: random.Random) -> None:
    d = FILES / "open"
    rows = injuries(rng, 2025, 6000)
    plant_open(rows)
    header = list(rows[0].keys())
    write_csv(d / "injuries_2025.csv", header, [[r[h] for h in header] for r in rows])
    write_csv(d / "dictionary.csv", ["column", "meaning", "kind"], C.OPEN_DICTIONARY)
    hier = []
    for region, cities in C.REGIONS.items():
        for c in cities:
            hier.append(["city", c, region])
    for group, occs in C.OCCUPATIONS.items():
        for o in occs:
            hier.append(["occupation", o, group])
    write_csv(d / "hierarchies.csv", ["attribute", "value", "parent"], hier)
    write_json(d / "treatment_start.json", C.TREATMENT_START)
    write_json(d / "dataset_start.json", C.DATASET_START)
    write_json(d / "portal_profile.json", C.PORTAL_PROFILE)
    write(d / "publication_request.txt", C.PUBLICATION_REQUEST)
    write_json(REF / "treatment_reference.json", C.TREATMENT_REFERENCE)
    write_json(REF / "dataset_reference.json", C.DATASET_REFERENCE)


# ---------------------------------------------------------------- lab 2.2: five information requests

def foi() -> None:
    d = FILES / "foi"
    for r in C.FOI_REQUESTS:
        write(d / "requests" / f"{r['id']}.txt", r["text"])
    for name, text in C.FOI_RECORDS.items():
        write(d / "records" / name, text)
    write(d / "exemptions.md", C.EXEMPTIONS)
    write(d / "letter_template.md", C.LETTER_TEMPLATE)
    write(d / "deadline_rule.md", C.DEADLINE_RULE)
    write_csv(d / "foi_log_template.csv", ["request_id", "received", "due", "decision", "grounds", "letter_date", "new_due", "signed_by"],
              [[r["id"], r["received"], "", "", "", "", "", ""] for r in C.FOI_REQUESTS])
    write(d / "summaries_for_assistant.md", C.FOI_PUBLIC_SUMMARIES)
    write_json(REF / "lab_2_2.json", {"today": C.FOI_TODAY, "requests": {r["id"]: r["key"] for r in C.FOI_REQUESTS},
                                       "protected": C.FOI_PROTECTED, "must_keep": C.FOI_MUST_KEEP})
    for name, text in C.FOI_REFERENCE_LETTERS.items():
        write(REF / "letters" / name, text)
    for name, text in C.FOI_REFERENCE_REDACTED.items():
        write(REF / "redacted" / name, text)


# ---------------------------------------------------------------- the follow-up task and the session 4 example: request logs

def business_days(start: date, n: int) -> date:
    d = start
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() not in (4, 5):  # Friday, Saturday
            n -= 1
    return d


def request_log(rng: random.Random, first: date, months: int, n: int, prefix: str, plant: bool) -> list[list]:
    rows = []
    span = (date(first.year + (first.month + months - 1) // 12, (first.month + months - 1) % 12 + 1, 1) - first).days
    for i in range(n):
        channel = rng.choices(["مشاركة", "حرية معلومات", "استخدام ثانوي"], weights=[46, 44, 10])[0]
        rtype = {"مشاركة": rng.choices(["حكومية", "خاصة"], weights=[70, 30])[0],
                 "حرية معلومات": "فرد",
                 "استخدام ثانوي": rng.choices(["جامعة", "خاصة"], weights=[75, 25])[0]}[channel]
        received = first + timedelta(days=rng.randrange(span))
        limit = 10 if channel != "حرية معلومات" else 30  # business days for sharing, calendar days for information requests
        decision = rng.choices(["موافقة", "موافقة جزئية", "رفض", "إشعار", "تمديد"], weights=[52, 14, 16, 10, 8])[0]
        if channel != "حرية معلومات" and decision in ("إشعار", "تمديد"):
            decision = "موافقة"
        if channel == "حرية معلومات":
            days = int(rng.gauss(22, 9))
            decided = received + timedelta(days=max(2, days))
        else:
            bd = max(2, int(rng.gauss(9, 4)))
            decided = business_days(received, bd)
        appealed = "نعم" if decision in ("رفض", "موافقة جزئية") and rng.random() < 0.3 else "لا"
        overturned = ("نعم" if rng.random() < 0.35 else "لا") if appealed == "نعم" else ""
        rows.append([f"{prefix}-{i + 1:04d}", channel, rtype, received.isoformat(), decided.isoformat(), decision, limit, appealed, overturned, ""])
    rows.sort(key=lambda r: (r[3], r[0]))
    if plant:
        # duplicates: the same request entered twice by two staff members
        for src in (5, 40, 77, 150, 201, 233):
            dup = list(rows[src]); dup[0] = dup[0] + "B"; dup[9] = "أُدخل مرتين"
            rows.append(dup)
        # withdrawn by the requester: no decision
        for k in (12, 99, 180):
            rows[k][4] = ""; rows[k][5] = "سحب"; rows[k][7] = "لا"; rows[k][8] = ""
        # still open at the end of the period, three of them already past their deadline
        for k in (n - 3, n - 2, n - 1, 60, 61, 62):
            rows[k][4] = ""; rows[k][5] = "مفتوح"; rows[k][7] = "لا"; rows[k][8] = ""
        # a data entry error: decided before it was received
        rows[120][4] = (date.fromisoformat(rows[120][3]) - timedelta(days=3)).isoformat()
        rows[120][9] = "خطأ إدخال"
    rows.sort(key=lambda r: (r[3], r[0]))
    return rows


def downloads(rng: random.Random, first: date, months: int, datasets: list[tuple]) -> list[list]:
    rows = []
    for name, published, base in datasets:
        for m in range(months):
            y, mo = first.year + (first.month - 1 + m) // 12, (first.month - 1 + m) % 12 + 1
            month = f"{y}-{mo:02d}"
            if published and month < published:
                continue
            dl = max(0, int(rng.gauss(base, base * 0.25)))
            api = max(0, int(rng.gauss(base * 0.6, base * 0.2)))
            rows.append([name, month, dl, api])
    return rows


def logs(rng: random.Random) -> None:
    header = ["request_id", "channel", "requester_type", "received", "decided", "decision", "limit_days", "appealed", "overturned", "note"]
    # session 4 example: the second half of 2025 (slides only)
    ex = request_log(rng, date(2025, 7, 1), 6, 210, "H2", plant=False)
    write_csv(FILES / "examples" / "requests_2025H2.csv", header, ex)
    write_csv(FILES / "examples" / "downloads_2025H2.csv", ["dataset", "month", "downloads", "api_calls"], downloads(rng, date(2025, 7, 1), 6, C.DATASETS_2025))
    write_csv(FILES / "examples" / "reuse_2025H2.csv", ["dataset", "reuser", "kind"], C.REUSE_2025)
    write_csv(FILES / "examples" / "plan_2025H2.csv", ["dataset", "planned", "published"], C.PLAN_2025)
    # the follow-up task: the first half of 2026
    fu = request_log(rng, date(2026, 1, 1), 6, 260, "H1", plant=True)
    d = FILES / "followup"
    write_csv(d / "requests_2026H1.csv", header, fu)
    write_csv(d / "downloads_2026H1.csv", ["dataset", "month", "downloads", "api_calls"], downloads(rng, date(2026, 1, 1), 6, C.DATASETS_2026))
    write_csv(d / "reuse_2026H1.csv", ["dataset", "reuser", "kind"], C.REUSE_2026)
    write_csv(d / "plan_2026H1.csv", ["dataset", "planned", "published"], C.PLAN_2026)
    write_csv(d / "feedback_2026H1.csv", ["dataset", "rating", "comment"], C.FEEDBACK_2026)
    write_json(d / "indicators_start.json", C.INDICATORS_START)
    write(d / "brief.md", C.FOLLOWUP_BRIEF)
    write(d / "report_template.md", C.REPORT_TEMPLATE)
    write_json(REF / "indicators_reference.json", C.INDICATORS_REFERENCE)
    write_csv(FILES / "examples" / "feedback_2025H2.csv", ["dataset", "rating", "comment"], C.FEEDBACK_2026[:4])
    example = {"_note": "مثال الشرائح: النصف الثاني من 2025، بلا مشكلات مزروعة",
               "requests": "files/examples/requests_2025H2.csv", "downloads": "files/examples/downloads_2025H2.csv",
               "reuse": "files/examples/reuse_2025H2.csv", "plan": "files/examples/plan_2025H2.csv",
               "feedback": "files/examples/feedback_2025H2.csv", "period_end": "2025-12-31",
               "exclude_duplicates": True, "exclude_withdrawn": True, "exclude_entry_errors": True,
               "open_requests": "late_if_past_deadline", "sharing_days": "business"}
    write_json(FILES / "examples" / "indicators_example.json", example)


def examples(rng: random.Random) -> None:
    """Slide examples from other domains of the authority: heat-stress complaints (session 3)."""
    rows = []
    for i in range(1200):
        region = rng.choices(list(C.REGIONS), weights=[30, 25, 20, 15, 10])[0]
        city = rng.choice(C.REGIONS[region])
        sector = rng.choice(["التشييد", "الزراعة", "النقل والمستودعات", "الخدمات البلدية"])
        age = max(18, min(64, int(rng.gauss(35, 9))))
        gender = "أنثى" if rng.random() < 0.05 else "ذكر"
        nat = "سعودي" if rng.random() < 0.3 else "غير سعودي"
        month = rng.choice(["2025-06", "2025-07", "2025-08", "2025-09"])
        outcome = rng.choices(["تفتيش وإنذار", "تفتيش ومخالفة", "لم تثبت"], weights=[40, 25, 35])[0]
        rows.append([f"HS-{i + 1:04d}", region, city, sector, age, gender, nat, month, outcome])
    write_csv(FILES / "examples" / "heat_complaints_2025.csv",
              ["complaint_id", "region", "city", "sector", "age", "gender", "nationality", "month", "outcome"], rows)
    write_json(FILES / "examples" / "heat_treatment.json", C.HEAT_TREATMENT)


def main() -> None:
    rng = random.Random(SEED)
    register()
    triage()
    research()
    open_data(rng)
    foi()
    logs(rng)
    examples(rng)
    print("files written under", FILES.relative_to(LABS.parent), "and", REF.relative_to(LABS.parent))


if __name__ == "__main__":
    main()
