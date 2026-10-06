"""Independent re-derivation of the weakest-surviving-finding selection.

Deliberately does NOT import build_rule_package.select_weakest_finding (the
function under audit) or lib.select_weakest_finding. It re-reads the raw
cached per-document audit JSON, re-applies the evaluation policy from
scratch (pure confidence rank, no page preference), and cross-checks the
result against what actually ended up in the generated XLSX for that
rule+document.

Policy under audit (as specified by the task owner):
  1. Only student_visible_problem findings count.
  2. Select strictly by lowest confidence: LOW < MEDIUM < HIGH.
  3. Ties broken by a deterministic internal criterion only -- never by
     "does it have a page" / "is it easy to visualize".
  4. No visible finding -> "No current auditor finding".
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_rule_package import review_workbook_path_for_manifest  # noqa: E402
from lib import CACHE_DIR, DOCS, OUTPUT_DIR  # noqa: E402

MANIFEST_PATH = OUTPUT_DIR / "all_rules_batch_manifest.json"
QA_OUT_PATH = OUTPUT_DIR / "all_rules_selection_qa.json"
CONFIDENCE_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def load_doc_report(short_name: str) -> dict:
    path = CACHE_DIR / f"{short_name.lower()}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def visible_findings(doc_report: dict, internal_id: str) -> list[dict]:
    out = []
    for f in doc_report.get("findings", []):
        if f.get("rule_id") != internal_id:
            continue
        if f.get("severity") == "PASS":
            continue
        if not f.get("student_visible_problem"):
            continue
        out.append(f)
    return out


def confidence_of(f: dict) -> str:
    raw = str(f.get("details", {}).get("confidence", "")).strip().upper()
    return raw if raw in CONFIDENCE_RANK else "HIGH"


def independent_select(findings: list[dict]) -> dict | None:
    """Pure policy: lowest confidence wins, page is NEVER a selection criterion."""
    if not findings:
        return None

    def key(f: dict) -> tuple:
        conf = confidence_of(f)
        page = f.get("page")
        page_key = page if page is not None else -1
        return (CONFIDENCE_RANK[conf], page_key, f.get("message", ""))

    return sorted(findings, key=key)[0]


_PAGE_RE = re.compile(r"Physical PDF page:\s*(.+)")
_CONF_RE = re.compile(r"Auditor confidence:\s*(LOW|MEDIUM|HIGH)")
_MSG_RE = re.compile(r"Possible violation:\s*(.+)")
_NO_FINDING_RE = re.compile(r"^No current auditor")


def parse_generated_cell(text: str) -> dict:
    if _NO_FINDING_RE.match(text.strip()):
        return {"no_finding": True}
    page_m = _PAGE_RE.search(text)
    conf_m = _CONF_RE.search(text)
    msg_m = _MSG_RE.search(text)
    page_raw = page_m.group(1).strip() if page_m else None
    page = None
    if page_raw and page_raw.isdigit():
        page = int(page_raw)
    return {
        "no_finding": False,
        "page_raw": page_raw,
        "page": page,
        "confidence": conf_m.group(1) if conf_m else None,
        "message": msg_m.group(1).strip() if msg_m else None,
    }


def main() -> None:
    import openpyxl

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    applicable = [r for r in manifest["rules"] if r["applicable_to_batch"]]

    doc_reports = {short: load_doc_report(short) for short, _ in DOCS}

    rows = []
    mismatches = []
    page_less_rows = []

    for entry in applicable:
        internal_id = entry["internal_id"]
        ester_id = entry["ester_id"]
        xlsx_path = review_workbook_path_for_manifest(ester_id, manifest)
        if not xlsx_path.exists():
            rows.append(
                {
                    "rule": ester_id,
                    "document": None,
                    "match": False,
                    "notes": "xlsx missing entirely",
                }
            )
            mismatches.append(ester_id)
            continue

        wb = openpyxl.load_workbook(xlsx_path, read_only=True)
        ws = wb[ester_id] if ester_id in wb.sheetnames else None

        for row_idx, (short_name, filename) in enumerate(DOCS, start=2):
            doc_report = doc_reports[short_name]
            candidates = visible_findings(doc_report, internal_id)
            expected = independent_select(candidates)

            generated_cell = ""
            if ws is not None:
                generated_cell = ws.cell(row=row_idx, column=2).value or ""
            parsed = parse_generated_cell(generated_cell)

            visible_count = len(candidates)
            weakest_conf = confidence_of(expected) if expected else None

            row = {
                "rule": ester_id,
                "internal_id": internal_id,
                "document": short_name,
                "visible_finding_count": visible_count,
                "weakest_confidence": weakest_conf,
                "expected_selected_page": expected.get("page") if expected else None,
                "expected_selected_confidence": weakest_conf,
                "expected_selected_message": (expected.get("message") if expected else None),
                "generated_no_finding": parsed.get("no_finding"),
                "generated_page": parsed.get("page"),
                "generated_page_raw": parsed.get("page_raw"),
                "generated_confidence": parsed.get("confidence"),
                "generated_message": parsed.get("message"),
                "match": None,
                "notes": "",
            }

            if expected is None:
                row["match"] = bool(parsed.get("no_finding"))
                if not row["match"]:
                    row["notes"] = "expected no finding but xlsx shows one"
            else:
                if parsed.get("no_finding"):
                    row["match"] = False
                    row["notes"] = "xlsx says no finding but a visible finding exists"
                else:
                    conf_match = parsed.get("confidence") == weakest_conf
                    msg_match = (parsed.get("message") or "").strip() == (
                        expected.get("message") or ""
                    ).strip()
                    exp_page = expected.get("page")
                    if exp_page is None:
                        page_match = parsed.get("page") is None
                    else:
                        page_match = parsed.get("page") == exp_page
                    row["match"] = conf_match and msg_match and page_match
                    if not row["match"]:
                        parts = []
                        if not conf_match:
                            parts.append(
                                f"confidence expected={weakest_conf} "
                                f"generated={parsed.get('confidence')}"
                            )
                        if not page_match:
                            parts.append(
                                f"page expected={exp_page} generated={parsed.get('page_raw')}"
                            )
                        if not msg_match:
                            parts.append("message text differs")
                        row["notes"] = "; ".join(parts)

            if expected is not None and expected.get("page") is None:
                page_less_rows.append(
                    {
                        "rule": ester_id,
                        "document": short_name,
                        "expected_confidence": weakest_conf,
                        "expected_message": expected.get("message"),
                        "match": row["match"],
                        "other_paged_candidates_exist": any(
                            c.get("page") is not None for c in candidates
                        ),
                    }
                )

            rows.append(row)
            if not row["match"]:
                mismatches.append(f"{ester_id}/{short_name}")

    payload = {
        "generated_at": None,
        "rows_checked": len(rows),
        "mismatch_count": len(mismatches),
        "mismatched_rule_documents": mismatches,
        "rows": rows,
    }
    import datetime

    payload["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    QA_OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    page_less_path = OUTPUT_DIR / "_page_less_raw.json"
    page_less_path.write_text(json.dumps(page_less_rows, indent=2), encoding="utf-8")

    print(f"Rows checked: {len(rows)}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Page-less expected-selection rows: {len(page_less_rows)}")
    wrongly_replaced = [r for r in page_less_rows if not r["match"]]
    print(f"Page-less rows where generated output does NOT match expected: {len(wrongly_replaced)}")
    affected_rules = sorted({r["rule"] for r in wrongly_replaced})
    print(f"Rules affected by page-less mis-selection: {affected_rules}")


if __name__ == "__main__":
    main()
