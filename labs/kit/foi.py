# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Information requests: deadlines, letters and redactions (lab 2.2). From the labs/ folder:

    uv run kit/foi.py deadlines                 # due date of each request under the case's rule
    uv run kit/foi.py check out                 # out/foi_log.csv, out/letters/F*.md, out/redacted/*.txt

The rule is the case's reading of the policy (files/foi/deadline_rule.md): a decision within 30
calendar days of receipt; an extension notified before that day, with a new date at most 30 days
later; an appeal within 10 working days, Sunday to Thursday. The check does not know your
decisions. It checks that each letter has a decision, grounds for any withholding, an appeal
statement, a signature and a date within the deadline, and that the redacted records show no
identity number or mobile number and mark every redaction with its category.
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta

from common import FILES, finish, fix, info, ok, path, read_csv, sections

TODAY = date(2026, 11, 23)
DECISIONS = ["موافقة جزئية", "موافقة", "رفض", "تمديد", "إشعار"]


def due(received: str) -> date:
    return date.fromisoformat(received) + timedelta(days=30)


def deadlines() -> int:
    print(f"اليوم في الحالة: {TODAY}")
    print("الطلب   الاستلام     آخر يوم للقرار   الأيام المتبقية")
    for r in read_csv(FILES / "foi" / "foi_log_template.csv"):
        d = due(r["received"])
        print(f"  {r['request_id']}    {r['received']}   {d}       {(d - TODAY).days}")
    return 0


def decision_of(text: str) -> str | None:
    m = re.search(r"^القرار:\s*(.+)$", text, re.M)
    if not m:
        return None
    v = m.group(1).strip()
    for d in DECISIONS:
        if v.startswith(d):
            return d
    return None


def check(folder: str) -> int:
    base = path(folder)
    received = {r["request_id"]: r["received"] for r in read_csv(FILES / "foi" / "foi_log_template.csv")}
    log_p = base / "foi_log.csv"
    log = {r["request_id"]: r for r in read_csv(log_p)} if log_p.exists() else {}
    if not log:
        fix("لا يوجد out/foi_log.csv: انسخ القالب من files/foi/ وأكمله")
    for rid, rec in received.items():
        last = due(rec)
        lp = base / "letters" / f"{rid}.md"
        if not lp.exists():
            fix(f"{rid}: لا يوجد خطاب out/letters/{rid}.md")
            continue
        text = lp.read_text(encoding="utf-8")
        secs = sections(text)
        d = decision_of(text)
        if not d:
            fix(f"{rid}: سطر «القرار:» بواحد من: {'، '.join(DECISIONS)}")
            continue
        m = re.search(r"التاريخ:\s*(\d{4}-\d{2}-\d{2})", text)
        if not m:
            fix(f"{rid}: تاريخ الخطاب بصيغة YYYY-MM-DD")
        elif date.fromisoformat(m.group(1)) > last:
            fix(f"{rid}: الخطاب بتاريخ {m.group(1)} بعد آخر يوم للقرار {last}")
        withheld = secs.get("ما حُجب وسببه", "")
        if d in ("موافقة جزئية", "رفض"):
            if not re.search(r"الفئة\s*\d", withheld):
                fix(f"{rid}: {d} دون رقم فئة لكل حجب")
        appeal = secs.get("حقك في التظلم", "")
        if not re.search(r"تظلم", appeal) or not re.search(r"10 أيام عمل|عشرة أيام عمل", appeal):
            fix(f"{rid}: حق التظلم ومهلته (10 أيام عمل)")
        if d == "تمديد":
            n = re.search(r"التاريخ الجديد:\s*(\d{4}-\d{2}-\d{2})", secs.get("التمديد", ""))
            if not n:
                fix(f"{rid}: التمديد يحتاج «التاريخ الجديد: YYYY-MM-DD» وسبب التأخير")
            elif date.fromisoformat(n.group(1)) > last + timedelta(days=30):
                fix(f"{rid}: التاريخ الجديد {n.group(1)} بعد {last + timedelta(days=30)}")
        sig = re.search(r"وقّعه:\s*(.+)", text)
        if not sig or "____" in sig.group(1) or len(sig.group(1).strip()) < 3:
            fix(f"{rid}: كل قرار إفصاح يوقعه المشارك")
        row = log.get(rid)
        if row and row.get("decision") and row["decision"] != d:
            fix(f"{rid}: القرار في السجل «{row['decision']}» وفي الخطاب «{d}»")
        if row and row.get("due") and row["due"] != last.isoformat():
            fix(f"{rid}: آخر يوم في السجل {row['due']} والصحيح وفق القاعدة {last}")
    red = base / "redacted"
    files = sorted(red.glob("*.txt")) if red.exists() else []
    if not files:
        info("لا توجد سجلات محجوبة في out/redacted/: إن أتحت سجلًا جزئيًا فضع نسخته المحجوبة هناك")
    for f in files:
        t = f.read_text(encoding="utf-8")
        if re.search(r"(?<!\d)[129]\d{9}(?!\d)", t):
            fix(f"{f.name}: رقم هوية ظاهر")
        if re.search(r"(?<!\d)05\d{8}(?!\d)", t):
            fix(f"{f.name}: رقم جوال ظاهر")
        marks = re.findall(r"\[محجوب: الفئة (\d)\]", t)
        loose = re.findall(r"\[محجوب[^\]]*\]", t)
        if len(loose) > len(marks):
            fix(f"{f.name}: علامة حجب دون رقم فئة")
        info(f"{f.name}: علامات حجب {len(marks)}")
    return finish("الخطابات الخمسة والسجلات المحجوبة")


def main(argv: list[str]) -> int:
    if argv[:1] == ["deadlines"]:
        return deadlines()
    if len(argv) == 2 and argv[0] == "check":
        return check(argv[1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
