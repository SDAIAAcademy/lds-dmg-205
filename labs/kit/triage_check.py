# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check a sharing decision log and a draft agreement (lab 1.1). From the labs/ folder:

    uv run kit/triage_check.py log out/decision_log.csv
    uv run kit/triage_check.py agreement out/agreement.md

The log check does not know the answers. It checks that every row is complete, that the codes
exist, and that the row is consistent with the procedure: a rejection has no route, an agreement
is for a non-government requester, the signatory follows the classification of the data. The
agreement check is the clause checklist: every clause is filled, the signatory is named, the
retention has a number of months, onward use and model training are addressed, and no field the
purpose does not need is shared.
"""
from __future__ import annotations

import re
import sys

from common import FILES, blank, finish, fix, info, ok, path, read_csv, sections

CODES = {
    "decision": {"approve", "approve_minimised", "reject", "redirect", "await_consent"},
    "route": {"gov_platforms", "secure_channel", "ndb", "open_data", "foi", "none"},
    "instrument": {"agreement", "controls_template", "log_only", "none"},
    "signatory": {"dmo_director", "head_of_entity", "none"},
}
CLAUSES = ["الطرفان", "الأساس النظامي والغرض", "البيانات المشاركة ومستوى تصنيفها", "المعالجة قبل المشاركة",
           "الأشخاص المخولون", "وسيلة المشاركة", "قيود الاستخدام والاستخدام اللاحق", "الطرف الثالث",
           "الاحتفاظ والإتلاف", "المدة والتكرار والإنهاء", "حقوق الهيئة في التدقيق والمراجعة",
           "الإبلاغ عن تسرب البيانات", "المسؤولية وحل النزاعات", "التوقيع"]
NOT_NEEDED = ["رقم الهوية", "رقم هوية", "تاريخ الميلاد", "تاريخ ميلاد"]


def check_log(p) -> int:
    rows = read_csv(p)
    ids = [r.get("request_id") for r in rows]
    expected = [f"R{i:02d}" for i in range(1, 11)]
    if sorted(ids) != expected:
        fix(f"السجل يجب أن يحوي R01 إلى R10 مرة واحدة لكل منها؛ وجدت: {', '.join(ids)}")
    for r in rows:
        rid = r.get("request_id", "?")
        bad = [f"{c}={r.get(c)!r}" for c in CODES if r.get(c) not in CODES[c]]
        if bad:
            fix(f"{rid}: رموز غير معروفة أو فارغة: {'; '.join(bad)} (انظر files/triage/codes.md)")
            continue
        if len(r.get("reason", "")) < 15:
            fix(f"{rid}: السبب قصير؛ اكتب المبدأ أو القاعدة التي حسمت القرار")
        if r["decision"] in ("reject", "await_consent") and (r["route"] != "none" or r["instrument"] != "none"):
            fix(f"{rid}: لا مسار ولا أداة لطلب مرفوض أو ينتظر موافقة الجهة المصدر")
        if r["decision"] in ("approve", "approve_minimised") and r["route"] == "none":
            fix(f"{rid}: الموافقة تحتاج مسارًا")
        if r["instrument"] == "none" and r["signatory"] != "none":
            fix(f"{rid}: موقّع بلا أداة يوقعها")
        if r["instrument"] in ("agreement", "controls_template") and r["signatory"] == "none":
            fix(f"{rid}: الاتفاقية أو نموذج الضوابط يحتاج موقّعًا بحسب مستوى التصنيف")
        if r["route"] == "open_data" and r["instrument"] != "none":
            fix(f"{rid}: البيانات العامة المنشورة لا تحتاج أداة")
    if not any(r.get("decision") == "approve_minimised" for r in rows):
        info("لا يوجد في سجلك أي طلب وافقت عليه بعد تقليصه: هل كل طلب وصل بالحد الأدنى فعلًا؟")
    return finish("اكتمال سجل القرارات واتساقه مع الإجراء")


def check_agreement(p) -> int:
    text = p.read_text(encoding="utf-8")
    secs = sections(text)
    for c in CLAUSES:
        if c not in secs:
            fix(f"البند «{c}» غائب: لا تحذف عناوين القالب")
        elif blank(secs[c]):
            fix(f"البند «{c}» لم يكتمل")
    s = secs.get("التوقيع", "")
    if s and not re.search(r"مدير مكتب إدارة البيانات|المسؤول الأول", s):
        fix("التوقيع: من يوقع عن الهيئة بحسب مستوى التصنيف؟")
    r = secs.get("الاحتفاظ والإتلاف", "")
    m = re.search(r"بالأشهر:\s*(\d+)", r)
    if not m:
        fix("الاحتفاظ: اكتب عدد الأشهر رقمًا")
    elif int(m.group(1)) > 24:
        info(f"الاحتفاظ {m.group(1)} شهرًا: هل يحتاج الغرض كل هذه المدة؟")
    u = secs.get("قيود الاستخدام والاستخدام اللاحق", "")
    if u and not re.search(r"تدريب", u):
        fix("الاستخدام اللاحق: لم تذكر تدريب نماذج الذكاء الاصطناعي، والطالب ذكره في طلبه")
    fields = secs.get("البيانات المشاركة ومستوى تصنيفها", "")
    for w in NOT_NEEDED:
        for line in fields.splitlines():
            if w in line and not re.search(r"لا يُشارك|لا تُشارك|دون|بلا|يُستبعد|يُحذف|لا يشارك", line):
                fix(f"الحقول: «{w}» لا يلزم لغرض الحملة")
                break
    if not re.search(r"مقيد|سري", fields):
        fix("اذكر مستوى تصنيف البيانات المشاركة")
    return finish("قائمة التحقق من بنود الاتفاقية")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("log", "agreement"):
        print(__doc__)
        return 2
    p = path(argv[1])
    if not p.exists():
        print(f"لا يوجد {argv[1]}. انسخ القالب من files/triage/ إلى out/ أولًا.")
        return 2
    return check_log(p) if argv[0] == "log" else check_agreement(p)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
