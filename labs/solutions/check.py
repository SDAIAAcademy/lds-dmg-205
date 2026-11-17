"""Run every lab's reference solution and assert its numbers. From the labs/ folder:

    uv run solutions/check.py              # every lab, the follow-up task and the AI-use rule
    uv run solutions/check.py 1.1 2.1      # some of them

Each lab: the starting files still hold their planted problems (the kit reports them), and the
reference solution passes the kit and matches the key. No lab calls a model. Outputs go to out/,
which is deleted at the end.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
REF = LABS / "solutions" / "reference"
FILES = LABS / "files"
OUT = LABS / "out"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run(*args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, *args], cwd=LABS, capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def rows(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fresh() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()


def score_log(log: list[dict], key: dict) -> int:
    """A row matches when its decision, route, instrument and signatory are all in the key's accepted sets."""
    n = 0
    for r in log:
        k = key.get(r["request_id"])
        if k and all(r[c] in k[c] for c in ("decision", "route", "instrument", "signatory")):
            n += 1
    return n


def lab_1_1() -> None:
    key = json.loads((REF / "lab_1_1.json").read_text(encoding="utf-8"))
    fresh()
    shutil.copy(FILES / "triage" / "decision_log_template.csv", OUT / "decision_log.csv")
    code, text = run("kit/triage_check.py", "log", "out/decision_log.csv")
    assert code == 1, "the empty log should not pass"
    shutil.copy(REF / "decision_log_reference.csv", OUT / "decision_log.csv")
    code, text = run("kit/triage_check.py", "log", "out/decision_log.csv")
    print(text)
    assert code == 0, "reference log does not pass the kit"
    s = score_log(rows(OUT / "decision_log.csv"), key)
    assert s == 10, s
    print(f"lab 1.1 reference log matches the key on {s} of 10 (the bar is 8)")
    shutil.copy(FILES / "triage" / "agreement_template.md", OUT / "agreement.md")
    code, text = run("kit/triage_check.py", "agreement", "out/agreement.md")
    assert code == 1 and "لم يكتمل" in text, "the template should fail the clause checklist"
    shutil.copy(REF / "agreement_reference.md", OUT / "agreement.md")
    code, text = run("kit/triage_check.py", "agreement", "out/agreement.md")
    print(text)
    assert code == 0, "reference agreement fails the clause checklist"
    # a draft that keeps the identity number and says nothing about training must fail
    bad = (REF / "agreement_reference.md").read_text(encoding="utf-8")
    bad = bad.replace("لا يُشارك رقم الهوية ولا تاريخ الميلاد.", "ورقم الهوية.").replace("في تدريب نماذج الذكاء الاصطناعي أو تحسينها، ويُمنع", "في")
    (OUT / "agreement.md").write_text(bad, encoding="utf-8")
    code, text = run("kit/triage_check.py", "agreement", "out/agreement.md")
    assert code == 1 and "رقم الهوية" in text and "تدريب" in text, text


def lab_1_2() -> None:
    fresh()
    shutil.copy(FILES / "research" / "fields_decision_template.csv", OUT / "fields_decision.csv")
    shutil.copy(FILES / "research" / "memo_template.md", OUT / "research_memo.md")
    code, _ = run("kit/research_check.py", "out/fields_decision.csv", "out/research_memo.md")
    assert code == 1, "the templates should not pass"
    shutil.copy(REF / "fields_decision_reference.csv", OUT / "fields_decision.csv")
    shutil.copy(REF / "research_memo_reference.md", OUT / "research_memo.md")
    code, text = run("kit/research_check.py", "out/fields_decision.csv", "out/research_memo.md")
    print(text)
    assert code == 0, "reference research decision fails the kit"
    assert "يبقى: 9، يُحوّل: 5، يُحذف: 4" in text, text


def lab_2_1() -> None:
    fresh()
    code, text = run("kit/risk.py", "files/open/treatment_start.json")
    assert code == 1 and "report_id, establishment_cr" in text and "k = 1" in text, text
    code, text = run("kit/metadata_check.py", "files/open/dataset_start.json")
    assert code == 1, "the starting record should fail"
    for planted in ("cc-by-nc-4.0", "XLSX", "residual_risk", "maintainer_email", "Injuries 2025"):
        assert planted in text, planted
    code, text = run("kit/risk.py", "solutions/reference/treatment_reference.json")
    print(text)
    assert code == 0, "reference treatment does not meet the criteria"
    after = json.loads((OUT / "risk_report.json").read_text(encoding="utf-8"))["after"]
    rec = json.loads((REF / "dataset_reference.json").read_text(encoding="utf-8"))
    for e in rec["extras"]:
        if e["key"] == "k_anonymity":
            e["value"] = str(after["k_min"])
        if e["key"] == "suppressed_records":
            e["value"] = str(after["suppressed_records"])
    (OUT / "dataset.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    code, text = run("kit/metadata_check.py", "out/dataset.json")
    print(text)
    assert code == 0, "reference record fails the validator"
    print(f"lab 2.1 after treatment: k={after['k_min']}, average risk={after['average_risk']}, suppressed={after['suppressed_records']} ({after['suppressed_share']:.1%}), homogeneous classes={after['homogeneous_classes']}")


def lab_2_2() -> None:
    key = json.loads((REF / "lab_2_2.json").read_text(encoding="utf-8"))
    fresh()
    code, text = run("kit/foi.py", "deadlines")
    print(text)
    for rid, k in key["requests"].items():
        assert k["due"] in text, (rid, k["due"])
    (OUT / "letters").mkdir()
    (OUT / "redacted").mkdir()
    for rid in key["requests"]:
        shutil.copy(FILES / "foi" / "letter_template.md", OUT / "letters" / f"{rid}.md")
    code, _ = run("kit/foi.py", "check", "out")
    assert code == 1, "templates should not pass"
    for f in (REF / "letters").glob("*.md"):
        shutil.copy(f, OUT / "letters" / f.name)
    for f in (REF / "redacted").glob("*.txt"):
        shutil.copy(f, OUT / "redacted" / f.name)
    log = [["request_id", "received", "due", "decision", "grounds", "letter_date", "new_due", "signed_by"]]
    for rid, k in key["requests"].items():
        rec = next(r for r in rows(FILES / "foi" / "foi_log_template.csv") if r["request_id"] == rid)
        log.append([rid, rec["received"], k["due"], k["decision"], " ".join(map(str, k["grounds"])), key["today"],
                    "2027-01-10" if rid == "F5" else "", "مكتب الإتاحة"])
    with (OUT / "foi_log.csv").open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(log)
    code, text = run("kit/foi.py", "check", "out")
    print(text)
    assert code == 0, "reference letters fail the kit"
    for rid, k in key["requests"].items():
        letter = (OUT / "letters" / f"{rid}.md").read_text(encoding="utf-8")
        assert re.search(rf"^القرار: {k['decision']}$", letter, re.M), rid
        for g in k["grounds"]:
            assert f"الفئة {g}" in letter, (rid, g)
    for name, words in key["protected"].items():
        t = (OUT / "redacted" / name).read_text(encoding="utf-8")
        for w in words:
            assert w not in t, (name, w)
        for w in key["must_keep"][name]:
            assert w in t, (name, w)
    # an unredacted record must be caught
    shutil.copy(FILES / "foi" / "records" / "F2_visit_2024.txt", OUT / "redacted" / "F2_visit_2024.txt")
    code, text = run("kit/foi.py", "check", "out")
    assert code == 1 and "رقم هوية ظاهر" in text and "رقم جوال ظاهر" in text, text


def followup() -> None:
    fresh()
    code, start = run("kit/indicators.py", "files/followup/indicators_start.json")
    assert code == 0
    code, ref = run("kit/indicators.py", "solutions/reference/indicators_reference.json")
    print(ref)
    assert code == 0
    assert "السجلات في الملف: 266؛ المستخدمة: 266" in start
    assert "مكرر: 6، مسحوب: 3، خطأ إدخال: 1، مفتوح بعد مهلته (عُدّ متأخرًا): 3" in ref, ref
    assert start != ref
    code, ex = run("kit/indicators.py", "files/examples/indicators_example.json")
    assert code == 0
    print("session 4 example (slides):")
    print(ex)


def ai_rule() -> None:
    """Every file a lab page marks as one an assistant may receive is public in the authority's register."""
    reg = {r["file"]: r["classification"] for r in rows(FILES / "register.csv")}
    found = 0
    for page in sorted(LABS.glob("D*_*.html")):
        for href in re.findall(r'<a[^>]*class="[^"]*ai-ok[^"]*"[^>]*href="([^"]+)"', page.read_text(encoding="utf-8")) + \
                    re.findall(r'<a[^>]*href="([^"]+)"[^>]*class="[^"]*ai-ok[^"]*"', page.read_text(encoding="utf-8")):
            rel = href.replace("files/", "", 1)
            assert reg.get(rel) == "عام", f"{page.name}: {href} is marked for an assistant but is {reg.get(rel)!r} in the register"
            found += 1
    out_rel = "out/indicators.md"
    assert reg.get(out_rel) == "عام"
    for name, level in reg.items():
        if name.startswith(("triage/requests", "foi/requests", "foi/records", "open/injuries", "research/research_request", "followup/requests", "followup/feedback")):
            assert level != "عام", name
    print(f"AI-use rule: {found} files marked for an assistant, all public in files/register.csv")


LABS_RUN = {"1.1": lab_1_1, "1.2": lab_1_2, "2.1": lab_2_1, "2.2": lab_2_2, "followup": followup, "ai": ai_rule}


def main(argv: list[str]) -> int:
    chosen = argv or list(LABS_RUN)
    for name in chosen:
        print(f"===== {name}")
        LABS_RUN[name]()
        print(f"PASS {name}")
    shutil.rmtree(OUT, ignore_errors=True)
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
