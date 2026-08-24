"""Phase 5+6 structural QA: every generated xlsx/pdf, all 60 applicable rules.

Checks things automatable without a human eyeball: correct sheet name,
exactly 7 rows, correct document names in order, blank reviewer columns,
no formula/error cells, no stray R011-specific or margin-specific wording
leaking into unrelated rules, no stale tie-break language, PDF opens with a
sensible page count, no blank pages, TOC entries agree with row count.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import DOCS, OUTPUT_DIR  # noqa: E402

MANIFEST_PATH = OUTPUT_DIR / "all_rules_batch_manifest.json"
DOC_NAMES = [short for short, _ in DOCS]

_FORBIDDEN_PHRASES = [
    "tie-broken",
    "tie broken",
    "closest to threshold",
    "closest to the",
    "smallest overflow",
    "borderline overflow",
]
_MARGIN_SPECIFIC_PHRASES = [
    "1-inch bottom margin",
    "1-inch right margin",
    "1-inch left margin",
    "1-inch top margin",
    "required margin",
]


def audit_xlsx(ester_id: str, path: Path) -> tuple[list[str], list[str]]:
    import openpyxl

    problems: list[str] = []
    finding_docs: list[str] = []
    try:
        wb = openpyxl.load_workbook(path)
    except Exception as exc:  # noqa: BLE001
        return [f"failed to open: {exc}"], finding_docs

    if ester_id not in wb.sheetnames:
        problems.append(f"missing sheet named {ester_id}")
        return problems, finding_docs
    if len(wb.sheetnames) != 1:
        problems.append(f"unexpected extra sheets: {wb.sheetnames}")

    ws = wb[ester_id]
    header = [ws.cell(row=1, column=c).value for c in range(1, 5)]
    if header[0] != "DOCUMENT":
        problems.append(f"A1 header wrong: {header[0]!r}")
    if not header[1] or ester_id not in str(header[1]):
        problems.append(f"B1 header missing rule id: {header[1]!r}")
    if header[2] != "Correct? (Y/N)":
        problems.append(f"C1 header wrong: {header[2]!r}")
    if header[3] != "Notes":
        problems.append(f"D1 header wrong: {header[3]!r}")

    if ws.max_row != len(DOC_NAMES) + 1:
        problems.append(f"expected {len(DOC_NAMES) + 1} rows, sheet has {ws.max_row}")

    row_names = [ws.cell(row=i, column=1).value for i in range(2, ws.max_row + 1)]
    if set(row_names) != set(DOC_NAMES):
        problems.append(f"document set mismatch: {row_names} vs expected {DOC_NAMES}")
    if row_names != DOC_NAMES and ester_id != "R011":
        problems.append(
            f"document row order differs from canonical batch order: {row_names} "
            f"(expected {DOC_NAMES}); every other rule package should use the same order"
        )

    for i in range(2, ws.max_row + 1):
        doc_name = ws.cell(row=i, column=1).value
        cell_b = ws.cell(row=i, column=2).value or ""
        if not re.match(r"^No current auditor", cell_b.strip()):
            if doc_name:
                finding_docs.append(doc_name)
        if isinstance(cell_b, str) and cell_b.startswith("="):
            problems.append(f"row {i}: column B looks like a formula: {cell_b[:40]!r}")
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in cell_b.lower():
                problems.append(f"row {i}: internal tie-break language leaked: {phrase!r}")
        if ester_id != "R011":
            for phrase in _MARGIN_SPECIFIC_PHRASES:
                if phrase in cell_b.lower():
                    problems.append(
                        f"row {i}: margin-specific wording on non-margin rule: {phrase!r}"
                    )

        c_val = ws.cell(row=i, column=3).value
        d_val = ws.cell(row=i, column=4).value
        if c_val not in (None, ""):
            problems.append(f"row {i}: reviewer column C not blank: {c_val!r}")
        if d_val not in (None, ""):
            problems.append(f"row {i}: reviewer column D not blank: {d_val!r}")

    return problems, finding_docs


def audit_pdf(ester_id: str, path: Path, expected_finding_docs: list[str]) -> list[str]:
    """expected_finding_docs: document names, in xlsx row order, that have a
    real finding (i.e. NOT "No current auditor ... finding") -- only these
    get a TOC entry/evidence section in the combined PDF."""
    import fitz

    problems = []
    try:
        doc = fitz.open(str(path))
    except Exception as exc:  # noqa: BLE001
        return [f"failed to open: {exc}"]

    if doc.page_count < 1:
        problems.append("zero pages")
        return problems

    page0_text = doc[0].get_text("text")
    if ester_id not in page0_text:
        problems.append(f"overview page does not mention {ester_id}")

    toc = doc.get_toc(simple=True)
    if not toc or toc[0][1] != "Overview":
        problems.append("missing/incorrect Overview TOC entry")
    doc_entries = [t for t in toc if t[0] == 1][1:]
    if len(doc_entries) != len(expected_finding_docs):
        problems.append(
            f"expected {len(expected_finding_docs)} per-document TOC entries "
            f"(docs with a finding), found {len(doc_entries)}"
        )
    else:
        for (_level, title, _pg), expected_name in zip(
            doc_entries, expected_finding_docs, strict=False
        ):
            if not title.startswith(expected_name):
                problems.append(f"TOC entry order/name mismatch: {title!r} vs {expected_name!r}")

    for i in range(doc.page_count):
        page = doc[i]
        text = page.get_text("text").strip()
        if not text and not page.get_images():
            problems.append(f"page {i + 1} appears blank")

    doc.close()
    return problems


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    applicable = [r for r in manifest["rules"] if r["applicable_to_batch"]]

    results = {}
    xlsx_failures = 0
    pdf_failures = 0
    for entry in applicable:
        ester_id = entry["ester_id"]
        xlsx_path = OUTPUT_DIR / f"{ester_id}_Ester_Auditor_Feedback.xlsx"
        pdf_path = OUTPUT_DIR / f"{ester_id}_Ester_Auditor_Feedback.pdf"

        if xlsx_path.exists():
            xlsx_problems, finding_docs = audit_xlsx(ester_id, xlsx_path)
        else:
            xlsx_problems, finding_docs = ["file missing"], []

        pdf_problems = (
            audit_pdf(ester_id, pdf_path, finding_docs) if pdf_path.exists() else ["file missing"]
        )

        if xlsx_problems:
            xlsx_failures += 1
        if pdf_problems:
            pdf_failures += 1

        results[ester_id] = {"xlsx_problems": xlsx_problems, "pdf_problems": pdf_problems}

    out_path = OUTPUT_DIR / "_structural_qa_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"Rules checked: {len(applicable)}")
    print(f"xlsx with problems: {xlsx_failures}")
    print(f"pdf with problems: {pdf_failures}")
    for rid, r in results.items():
        if r["xlsx_problems"] or r["pdf_problems"]:
            print(f"  {rid}: xlsx={r['xlsx_problems']} pdf={r['pdf_problems']}")


if __name__ == "__main__":
    main()
