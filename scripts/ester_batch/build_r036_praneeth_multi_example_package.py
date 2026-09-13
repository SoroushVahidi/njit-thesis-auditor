"""Build the R036/Praneeth "all page-11 examples" review package.

Context: the standard per-rule package built by ``build_rule_package.py``
shows exactly one selected finding per document
(``lib.select_weakest_finding``). For R036/Praneeth, Ester reviewed that one
selected pair and marked it a false positive, referring back to her earlier
R036 comment about chapter/appendix headings. Investigation
(``docs/status/p036_praneeth_forensic_investigation_20260908.md``) found
that Praneeth's physical PDF page 11 currently produces 12 P036 findings
that all share the same ~1.19 gap ratio, none of which involve a
chapter/appendix/top-level heading transition -- the reviewed pair is only
one of those 12, chosen by an arbitrary geometric tie-break, not because it
was judged more likely to be a false positive. Ester has since said she
cannot decide between "the spacing pattern itself is fine" and "only
structural-heading transitions are fine" without seeing the other examples.

This script renders all 12 as a single, self-contained review package. It
deliberately does not select a "weakest" finding, does not classify any
example as a true/false positive, and does not change any detector file --
it only calls the same evidence-rendering building blocks
``build_rule_package.py`` already uses (``lib.build_evidence`` and friends).

Outputs (new files, does not touch the existing single-example package):
  - docs/evaluation/ester_feedback/R036_Praneeth_Page11_All_Examples.xlsx
  - docs/evaluation/ester_feedback/R036_Praneeth_Page11_All_Examples.pdf
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import fitz
import openpyxl
from lib import (
    OUTPUT_DIR,
    build_evidence,
    doc_pdf_path,
    finding_confidence,
    measured_amount,
    printed_page_for,
    visible_findings_for_rule,
)
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

RULE_ID = "P036"
ESTER_ID = "R036"
DOCUMENT_SHORT_NAME = "Praneeth"
DOCUMENT_FILENAME = "Praneeth Ivan Joel. FNU_3rd review draft.pdf"
TARGET_PAGE = 11
EXPECTED_EXAMPLE_COUNT = 12

XLSX_PATH = OUTPUT_DIR / f"{ESTER_ID}_Praneeth_Page11_All_Examples.xlsx"
PDF_PATH = OUTPUT_DIR / f"{ESTER_ID}_Praneeth_Page11_All_Examples.pdf"

# The exact pair Ester already reviewed, recovered by verbatim text match in
# docs/status/p036_praneeth_forensic_investigation_20260908.md. Used only to
# label which example was previously reviewed -- never to change selection,
# scoring, or which findings are included.
REVIEWED_PREVIOUS_PREVIEW = (
    "Characterization ………………………. "
    "…………………………………………"
)
REVIEWED_NEXT_PREVIEW = (
    "1.2 Protein Quantification Using Mass Spectrometry"
    "……………………………"
)

COVER_NOTE = (
    "R036 checks spacing between consecutive Table of Contents/List entries. "
    "The auditor currently reports the 12 examples below on Praneeth's "
    "physical PDF page 11. One of these examples was previously reviewed; "
    "the remaining examples are included so the formatting pattern can be "
    "reviewed consistently. No rule change has been made based on these "
    "examples."
)


def is_previously_reviewed(details: dict[str, Any]) -> bool:
    """Return True only for the exact pair Ester already reviewed."""
    return (
        str(details.get("previous_entry_preview", "")) == REVIEWED_PREVIOUS_PREVIEW
        and str(details.get("next_entry_preview", "")) == REVIEWED_NEXT_PREVIEW
    )


def select_all_findings_for_page(
    findings: list[dict[str, Any]], page: int
) -> list[dict[str, Any]]:
    """Return every visible finding on *page*, in deterministic top-to-bottom
    (entry_pair_index) order.

    Unlike ``lib.select_weakest_finding``, this never narrows the set down
    to one -- that narrowing is exactly the behavior this package exists to
    avoid repeating.
    """
    page_findings = [f for f in findings if f.get("page") == page]
    return sorted(page_findings, key=lambda f: int(f["details"]["entry_pair_index"]))


def _classify_transition_label(details: dict[str, Any]) -> str:
    """Human-readable transition description derived only from already-computed
    finding details (entry text) -- does not re-run or duplicate detector
    classification logic."""
    import re

    prev_text = str(details.get("previous_entry_preview", ""))
    next_text = str(details.get("next_entry_preview", ""))

    def _level(text: str) -> str:
        stripped = text.strip()
        if stripped.upper().startswith("CHAPTER") or stripped.upper().startswith("APPENDIX"):
            return "level-1 (chapter/appendix heading)"
        if re.match(r"^\d+\.\d+\.\d+", stripped):
            return "level-3 (X.X.X)"
        if re.match(r"^\d+\.\d+", stripped):
            return "level-2 (X.X)"
        return "wrapped continuation text (no leading section number)"

    return f"{_level(prev_text)} -> {_level(next_text)}"


def build_example_rows(
    page_findings: list[dict[str, Any]], doc_report: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example_number, finding in enumerate(page_findings, start=1):
        details = finding.get("details", {})
        physical_page = finding.get("page")
        reviewed = is_previously_reviewed(details)
        rows.append(
            {
                "example_number": example_number,
                "previously_reviewed": reviewed,
                "physical_page": physical_page,
                "printed_page": printed_page_for(doc_report, physical_page),
                "previous_entry": str(details.get("previous_entry_preview", "")),
                "next_entry": str(details.get("next_entry_preview", "")),
                "transition_label": _classify_transition_label(details),
                "gap_ratio": str(details.get("gap_ratio", "")),
                "required_gap_points": str(details.get("required_gap_points", "")),
                "gap_points": str(details.get("gap_points", "")),
                "message": finding.get("message", ""),
                "measured_amount": measured_amount(details),
                "confidence": finding_confidence(finding),
                "details": details,
                "entry_pair_index": details.get("entry_pair_index", ""),
            }
        )
    return rows


def _fill_evidence(rows: list[dict[str, Any]], evidence_dir: Path) -> None:
    pdf_path = doc_pdf_path(DOCUMENT_FILENAME)
    for row in rows:
        out_path = evidence_dir / f"example_{row['example_number']:02d}.pdf"
        evidence = build_evidence(
            pdf_path,
            row["physical_page"],
            row["details"],
            RULE_ID,
            out_path,
        )
        row["location"] = evidence.location
        row["evidence_pdf"] = out_path if out_path.exists() else None
        row["has_highlight"] = evidence.has_highlight


def _write_xlsx(rows: list[dict[str, Any]], xlsx_path: Path) -> None:
    wb = openpyxl.Workbook()

    cover_ws = wb.active
    cover_ws.title = "Cover Note"
    cover_ws.column_dimensions["A"].width = 110
    cover_cell = cover_ws.cell(row=1, column=1, value=COVER_NOTE)
    cover_cell.alignment = Alignment(wrap_text=True, vertical="top")
    cover_cell.font = Font(name="Calibri", size=11)
    cover_ws.row_dimensions[1].height = 70

    ws = wb.create_sheet(title=f"{ESTER_ID}_Praneeth_p11")
    header_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11, bold=False)

    headers = [
        "Example #",
        "Previously reviewed by Ester?",
        "Physical PDF page",
        "Previous entry",
        "Next entry",
        "Transition type / levels",
        "Gap ratio",
        "Required threshold (gap ratio)",
        "Brief neutral description",
        "Ester decision",
        "Ester notes",
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=header).font = header_font

    widths = [10, 14, 12, 42, 42, 24, 10, 14, 46, 14, 30]
    for col, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + col)].width = width

    for r, row in enumerate(rows, start=2):
        description = (
            f"TOC entry-to-entry transition ({row['transition_label']}); "
            f"measured gap ratio {row['gap_ratio']} against required ratio 1.40."
        )
        values = [
            row["example_number"],
            "YES" if row["previously_reviewed"] else "NO",
            row["physical_page"],
            row["previous_entry"],
            row["next_entry"],
            row["transition_label"],
            row["gap_ratio"],
            "1.40",
            description,
            None,
            None,
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = regular_font
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(xlsx_path)


def _write_overview_pdf(rows: list[dict[str, Any]], out_path: Path) -> None:
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8, leading=10)
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16)
    note_style = ParagraphStyle("note", parent=styles["BodyText"], fontSize=10, leading=13)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    elements = [
        Paragraph(
            f"{ESTER_ID} — Praneeth, physical page {TARGET_PAGE}: all current examples",
            title_style,
        ),
        Spacer(1, 0.1 * inch),
        Paragraph(COVER_NOTE, note_style),
        Spacer(1, 0.2 * inch),
    ]

    header = [
        "Example #",
        "Reviewed?",
        "Previous entry",
        "Next entry",
        "Transition",
        "Gap ratio",
    ]
    data = [header]
    for row in rows:
        data.append(
            [
                str(row["example_number"]),
                "YES" if row["previously_reviewed"] else "NO",
                Paragraph(row["previous_entry"], cell_style),
                Paragraph(row["next_entry"], cell_style),
                Paragraph(row["transition_label"], cell_style),
                row["gap_ratio"],
            ]
        )

    table = Table(
        data,
        colWidths=[0.6 * inch, 0.7 * inch, 2.6 * inch, 2.6 * inch, 1.6 * inch, 0.7 * inch],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)


def _draw_page11_map(rows: list[dict[str, Any]], out_path: Path) -> None:
    """One compact page: the full physical page, all 12 gaps boxed and numbered.

    Purely presentational -- draws rectangles/labels from geometry each
    finding's own ``details['bbox']`` already carries; computes no new
    geometry and does not touch any detector file.
    """
    pdf_path = doc_pdf_path(DOCUMENT_FILENAME)
    with fitz.open(pdf_path) as src:
        page_index = TARGET_PAGE - 1
        with fitz.open() as out:
            out.insert_pdf(src, from_page=page_index, to_page=page_index)
            page = out[0]
            for row in rows:
                bbox_raw = str(row["details"].get("bbox", ""))
                parts = [p.strip() for p in bbox_raw.split(",")]
                if len(parts) != 4:
                    continue
                x0, y0, x1, y1 = (float(p) for p in parts)
                color = (0.85, 0.1, 0.1) if row["previously_reviewed"] else (0.1, 0.35, 0.85)
                rect = fitz.Rect(x0, y0, x1, y1)
                page.draw_rect(rect, color=color, width=1.2)
                label = f"{row['example_number']}"
                if row["previously_reviewed"]:
                    label += "*"
                page.insert_text((x1 + 3, y1), label, fontsize=8, color=color)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out.save(str(out_path))


def _write_evidence_header_pdf(row: dict[str, Any], out_path: Path) -> None:
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=13)
    title_style = ParagraphStyle("title2", parent=styles["Heading1"], fontSize=14)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    reviewed_text = "YES — this is the example previously reviewed" if row[
        "previously_reviewed"
    ] else "NO — additional example, not previously reviewed individually"
    elements = [
        Paragraph(
            f"Example {row['example_number']} of {EXPECTED_EXAMPLE_COUNT} — {ESTER_ID} "
            f"(Praneeth, physical page {row['physical_page']})",
            title_style,
        ),
        Spacer(1, 0.05 * inch),
        Paragraph(f"Previously reviewed by Ester? {reviewed_text}", body_style),
        Paragraph(f"Printed/document page: {row['printed_page']}", body_style),
        Paragraph(
            f"Location: {row['location'] or 'not reliably identifiable on page'}",
            body_style,
        ),
        Spacer(1, 0.08 * inch),
        Paragraph(f'Previous entry: "{row["previous_entry"]}"', body_style),
        Paragraph(f'Next entry: "{row["next_entry"]}"', body_style),
        Paragraph(f"Transition type / levels: {row['transition_label']}", body_style),
        Spacer(1, 0.05 * inch),
        Paragraph(f"Possible violation: {row['message']}", body_style),
        Paragraph(f"Measured amount: {row['measured_amount']}", body_style),
        Paragraph("Required threshold: gap ratio >= 1.40", body_style),
        Paragraph(f"Auditor confidence: {row['confidence']}", body_style),
    ]
    doc.build(elements)


def _assemble_combined_pdf(
    rows: list[dict[str, Any]],
    overview_pdf: Path,
    map_pdf: Path,
    evidence_dir: Path,
    out_path: Path,
) -> int:
    combined = fitz.open()
    combined.insert_pdf(fitz.open(str(overview_pdf)))
    combined.insert_pdf(fitz.open(str(map_pdf)))
    combined.set_toc([[1, "Overview", 1], [1, "Page 11 map (all examples)", 2]])
    toc = combined.get_toc(simple=True)

    for row in rows:
        header_pdf = evidence_dir / f"example_{row['example_number']:02d}_header.pdf"
        _write_evidence_header_pdf(row, header_pdf)

        page_start = combined.page_count + 1
        combined.insert_pdf(fitz.open(str(header_pdf)))
        evidence_pdf = row.get("evidence_pdf")
        if evidence_pdf and evidence_pdf.exists():
            combined.insert_pdf(fitz.open(str(evidence_pdf)))
        marker = " (previously reviewed)" if row["previously_reviewed"] else ""
        toc.append([1, f"Example {row['example_number']}{marker}", page_start])

    combined.set_toc(toc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(str(out_path))
    page_count = combined.page_count
    combined.close()
    return page_count


def validate_package(rows: list[dict[str, Any]], xlsx_path: Path, pdf_path: Path) -> list[str]:
    problems: list[str] = []

    if len(rows) != EXPECTED_EXAMPLE_COUNT:
        problems.append(f"expected {EXPECTED_EXAMPLE_COUNT} example rows, got {len(rows)}")

    seen_pair_indices = {row["entry_pair_index"] for row in rows}
    if len(seen_pair_indices) != len(rows):
        problems.append("duplicate entry_pair_index detected across example rows")

    reviewed_count = sum(1 for row in rows if row["previously_reviewed"])
    if reviewed_count != 1:
        problems.append(
            f"expected exactly 1 example flagged as previously reviewed, got {reviewed_count}"
        )

    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = f"{ESTER_ID}_Praneeth_p11"
    if sheet_name not in wb.sheetnames:
        problems.append(f"xlsx missing sheet {sheet_name}")
    else:
        ws = wb[sheet_name]
        if ws.cell(row=1, column=1).value != "Example #":
            problems.append("xlsx header A1 wrong")
        for r in range(2, 2 + EXPECTED_EXAMPLE_COUNT):
            if ws.cell(row=r, column=10).value not in (None, ""):
                problems.append(f"xlsx row {r}: Ester decision column not blank")
            if ws.cell(row=r, column=11).value not in (None, ""):
                problems.append(f"xlsx row {r}: Ester notes column not blank")

    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count < 1:
            problems.append("combined pdf has zero pages")
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if not text and not page.get_images():
                problems.append(f"combined pdf page {i + 1} appears blank")

    for row in rows:
        if not row.get("evidence_pdf"):
            problems.append(f"example {row['example_number']}: no rendered evidence page")

    return problems


def build_package() -> dict[str, Any]:
    from lib import build_full_audit_json

    pdf_path = doc_pdf_path(DOCUMENT_FILENAME)
    # Always a fresh run against the real, current detector -- never the
    # shared, potentially-stale ester_all_rules_batch_20260819 cache.
    doc_report = build_full_audit_json(pdf_path)

    candidates = visible_findings_for_rule(doc_report, RULE_ID)
    page_findings = select_all_findings_for_page(candidates, TARGET_PAGE)

    if len(page_findings) != EXPECTED_EXAMPLE_COUNT:
        raise SystemExit(
            f"Refusing to build package: expected exactly {EXPECTED_EXAMPLE_COUNT} "
            f"{RULE_ID} findings on {DOCUMENT_SHORT_NAME} physical page {TARGET_PAGE}, "
            f"but the current detector produced {len(page_findings)}. This means "
            "current detector output no longer matches the audited state "
            "(docs/status/p036_praneeth_forensic_investigation_20260908.md) -- "
            "stop and investigate before generating a package."
        )

    reviewed_matches = [f for f in page_findings if is_previously_reviewed(f["details"])]
    if len(reviewed_matches) != 1:
        raise SystemExit(
            f"Refusing to build package: expected exactly 1 finding matching the "
            f"previously-reviewed pair, found {len(reviewed_matches)}."
        )

    rows = build_example_rows(page_findings, doc_report)

    with tempfile.TemporaryDirectory(prefix="r036_praneeth_all_examples_") as tmpdir:
        evidence_dir = Path(tmpdir)
        _fill_evidence(rows, evidence_dir)

        overview_pdf = evidence_dir / "overview.pdf"
        map_pdf = evidence_dir / "page11_map.pdf"
        _write_overview_pdf(rows, overview_pdf)
        _draw_page11_map(rows, map_pdf)

        _write_xlsx(rows, XLSX_PATH)
        page_count = _assemble_combined_pdf(rows, overview_pdf, map_pdf, evidence_dir, PDF_PATH)

    problems = validate_package(rows, XLSX_PATH, PDF_PATH)

    return {
        "xlsx_path": str(XLSX_PATH),
        "pdf_path": str(PDF_PATH),
        "pdf_page_count": page_count,
        "example_count": len(rows),
        "reviewed_example_number": reviewed_matches[0]["details"]["entry_pair_index"],
        "validation_problems": problems,
    }


if __name__ == "__main__":
    result = build_package()
    print(result)
