"""Validate a dataset record against the case's portal profile (lab 2.1). From the labs/ folder:

    uv run kit/metadata_check.py files/open/dataset_start.json   # the record as it arrived
    uv run kit/metadata_check.py out/dataset.json                # your record

The record uses the dataset fields of the CKAN API (package_create: name, title, notes,
license_id, owner_org, maintainer, maintainer_email, tags, resources, extras). The profile in
files/open/portal_profile.json is the case's portal: which fields it requires and which values it
accepts. The record's k_anonymity and suppressed_records must equal out/risk_report.json.
"""
from __future__ import annotations

import re
import sys

from common import FILES, OUT, finish, fix, info, ok, path, read_json


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    rec = read_json(path(argv[0]))
    prof = read_json(FILES / "open" / "portal_profile.json")
    for f in prof["required"]:
        if not rec.get(f):
            fix(f"الحقل {f} مطلوب وهو فارغ أو غائب")
    if rec.get("name") and not re.match(prof["name_pattern"], rec["name"]):
        fix(f"name «{rec['name']}» لا يطابق {prof['name_pattern']}: حروف لاتينية صغيرة وأرقام و- و_ فقط")
    if len(rec.get("notes", "")) < prof["notes_min_chars"]:
        fix(f"notes أقصر من {prof['notes_min_chars']} حرفًا: صف ما في الملف، ولمن يصلح، وما عولج فيه")
    lic = rec.get("license_id", "")
    if lic not in prof["licenses"]:
        fix(f"license_id «{lic}» ليس من التراخيص المقبولة: {', '.join(prof['licenses'])}")
    else:
        ok(f"الترخيص: {prof['licenses'][lic]}")
    if rec.get("maintainer_email") and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", rec["maintainer_email"]):
        fix("maintainer_email ليس عنوان بريد")
    if len(rec.get("tags", [])) < prof["tags_min"]:
        fix(f"الوسوم أقل من {prof['tags_min']}")
    for res in rec.get("resources", []):
        fmt = res.get("format", "")
        if fmt not in prof["resource_formats"]:
            fix(f"صيغة المورد «{fmt}» ليست من {prof['resource_formats']}: صيغة مفتوحة يقرؤها الحاسوب")
        elif not res.get("url", "").lower().endswith("." + fmt.lower()):
            fix(f"المورد يقول {fmt} والملف {res.get('url')}")
    extras = {e.get("key"): str(e.get("value", "")) for e in rec.get("extras", [])}
    for key in prof["required_extras"]:
        if not extras.get(key):
            fix(f"extras: {key} مطلوب")
    if extras.get("classification") and extras["classification"] != prof["classification_value"]:
        fix(f"التصنيف «{extras['classification']}»: لا يُنشر إلا «{prof['classification_value']}»")
    if extras.get("temporal_coverage") and not re.match(r"^\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}$", extras["temporal_coverage"]):
        fix("temporal_coverage بصيغة YYYY-MM-DD/YYYY-MM-DD")
    if extras.get("residual_risk") is not None and 0 < len(extras["residual_risk"]) < prof["residual_risk_min_chars"]:
        fix("residual_risk قصير: اذكر ما يبقى من خطر بعد المعالجة، ولماذا تقبله الهيئة")
    report = OUT / "risk_report.json"
    if report.exists():
        after = read_json(report)["after"]
        if extras.get("k_anonymity") and extras["k_anonymity"] != str(after["k_min"]):
            fix(f"k_anonymity = {extras['k_anonymity']} ونتيجة الاختبار {after['k_min']}")
        if extras.get("k_anonymity", "").isdigit() and int(extras["k_anonymity"]) < prof["k_min"]:
            fix(f"k_anonymity أقل من {prof['k_min']}")
        if extras.get("suppressed_records") and extras["suppressed_records"] != str(after["suppressed_records"]):
            fix(f"suppressed_records = {extras['suppressed_records']} ونتيجة الاختبار {after['suppressed_records']}")
    else:
        info("لم يُعثر على out/risk_report.json: شغّل kit/risk.py أولًا لتتحقق قيم k والمحذوف")
    return finish("سجل البيانات الوصفية")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
