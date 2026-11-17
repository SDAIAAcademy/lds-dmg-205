"""Check a research decision: the field decisions and the memo (lab 1.2). From the labs/ folder:

    uv run kit/research_check.py out/fields_decision.csv out/research_memo.md

It does not know the decision. It checks that every requested field has a decision and a reason,
that no direct identifier stays as it is, that the memo's sections are filled, that the access
route is one of the authority's three, and that the duration is a number of months.
"""
from __future__ import annotations

import re
import sys

from common import FILES, blank, finish, fix, info, ok, path, read_csv, sections

SECTIONS = ["القرار", "الغرض والمتقدم والمصلحة العامة", "الحقول", "مسار الوصول", "شروط قبل الوصول",
            "ضمانات أثناء الوصول", "فحص المخرجات والنشر", "الاستخدام اللاحق والتمويل", "المدة والإتلاف",
            "لو تغيّر مقدم الطلب أو الغرض"]
DIRECT = {"worker_id", "worker_name", "worker_mobile", "establishment_cr", "establishment_name"}
ROUTES = ["جداول مجمّعة", "جداول مجمعة", "مستخرج منزوع الهوية", "بيئة البحث الآمنة"]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    fields_p, memo_p = path(argv[0]), path(argv[1])
    requested = [r["field"] for r in read_csv(FILES / "research" / "fields_requested.csv")]
    rows = {r["field"]: r for r in read_csv(fields_p)} if fields_p.exists() else {}
    if not rows:
        fix("لا يوجد ملف قرارات الحقول")
    for f in requested:
        r = rows.get(f)
        if not r or r.get("decision") not in ("keep", "transform", "drop"):
            fix(f"{f}: القرار keep أو transform أو drop")
            continue
        if len(r.get("reason", "")) < 8:
            fix(f"{f}: اكتب سبب القرار")
        if f in DIRECT and r["decision"] == "keep":
            fix(f"{f}: معرِّف مباشر يبقى كما هو؛ هل يلزم لسؤال الدراسة، أم يكفي مفتاح مستعار أو حذفه؟")
    if rows:
        counts = {d: sum(1 for r in rows.values() if r.get("decision") == d) for d in ("keep", "transform", "drop")}
        info(f"يبقى: {counts['keep']}، يُحوّل: {counts['transform']}، يُحذف: {counts['drop']}")
    if not memo_p.exists():
        fix("لا يوجد ملف المذكرة")
        return finish("قرارات الحقول والمذكرة")
    secs = sections(memo_p.read_text(encoding="utf-8"))
    for s in SECTIONS:
        if s not in secs:
            fix(f"القسم «{s}» غائب")
        elif blank(secs[s]):
            fix(f"القسم «{s}» لم يكتمل")
    route = secs.get("مسار الوصول", "")
    if route and not any(x in route for x in ROUTES):
        fix("مسار الوصول: سمِّ واحدًا من المسارات الثلاثة في files/research/access_routes.md")
    m = re.search(r"بالأشهر:\s*(\d+)", secs.get("المدة والإتلاف", ""))
    if not m:
        fix("المدة: اكتب عدد الأشهر رقمًا")
    elif int(m.group(1)) > 60:
        fix(f"المدة {m.group(1)} شهرًا: الطلب لدراسة محددة، لا لدراسات لم تتحدد")
    if not re.search(r"تمويل|ممول", secs.get("الاستخدام اللاحق والتمويل", "")):
        fix("الاستخدام اللاحق: قل ما موقف الهيئة من الممول")
    return finish("قرارات الحقول والمذكرة")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
