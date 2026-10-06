"""Build one rule's reviewer workbook and highlighted evidence PDF.

Mirrors the R011 reference structure documented in
docs/evaluation/ester_feedback/README.md, but is fully generic: no
rule-specific visualization logic. Confidence, location, and excerpt text
all come from the current auditor's own output for that finding.
"""

from __future__ import annotations

import datetime as dt
import re
import tempfile
from pathlib import Path
from typing import Any

import fitz
import openpyxl
from lib import (
    DOCS,
    OUTPUT_DIR,
    build_evidence,
    doc_pdf_path,
    finding_confidence,
    load_or_build_doc_findings,
    measured_amount,
    printed_page_for,
    select_weakest_finding,
    visible_findings_for_rule,
)
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REVIEW_WORKBOOK_SCHEMA = "2026-10-05"


def review_workbook_filename(ester_id: str, review_date: dt.date) -> str:
    """Use a date-first, filesystem-safe name for each rule's review sheet."""
    if not re.fullmatch(r"R\d{3}[A-Z]*", ester_id):
        raise ValueError(f"invalid public rule ID for workbook filename: {ester_id!r}")
    return f"{review_date:%Y-%m-%d}_{ester_id}_NJIT_Thesis_Auditor_Review.xlsx"


def review_workbook_path_for_manifest(
    ester_id: str, manifest: dict[str, Any], output_dir: Path = OUTPUT_DIR
) -> Path:
    """Resolve both the current workbook name and archived batch names."""
    schema = manifest.get("review_workbook_schema")
    if schema is None:
        return output_dir / f"{ester_id}_Ester_Auditor_Feedback.xlsx"
    if schema != REVIEW_WORKBOOK_SCHEMA:
        raise ValueError(f"unsupported review workbook schema: {schema!r}")
    review_date = dt.date.fromisoformat(str(manifest["review_date"]))
    return output_dir / review_workbook_filename(ester_id, review_date)


def _structured_block(ester_id: str, row: dict[str, Any]) -> str:
    if row["no_finding"]:
        return f"No current auditor {ester_id} finding. No new review needed."
    if row["physical_page"] is not None:
        physical_page_text = str(row["physical_page"])
    elif row.get("physical_page_display"):
        physical_page_text = (
            f"{row['physical_page_display']} (document-level finding; "
            "see the two pages below where the numbering style changes)"
        )
    else:
        physical_page_text = "not applicable (document-level finding)"
    lines = [
        f"Physical PDF page: {physical_page_text}",
        f"Printed/document page: {row['printed_page']}",
        f"Location: {row['location'] or 'not reliably identifiable on page'}",
        "Affected content:",
    ]
    if row["affected_lines"]:
        for i, text in enumerate(row["affected_lines"], start=1):
            lines.append(f'  {i}. "{text}"')
    else:
        lines.append('  1. "(no drawable excerpt for this finding)"')
    lines.append(f"Possible violation: {row['message']}")
    lines.append(f"Measured amount: {row['measured_amount']}")
    lines.append(f"Auditor confidence: {row['confidence']}")
    return "\n".join(lines)


def build_rule_rows(internal_id: str) -> list[dict[str, Any]]:
    rows = []
    for short_name, filename in DOCS:
        doc_report = load_or_build_doc_findings(short_name, filename)
        candidates = visible_findings_for_rule(doc_report, internal_id)
        chosen = select_weakest_finding(candidates)

        if chosen is None:
            rows.append(
                {
                    "document": short_name,
                    "no_finding": True,
                    "physical_page": None,
                    "printed_page": "",
                    "location": "",
                    "affected_lines": [],
                    "message": "",
                    "measured_amount": "",
                    "confidence": "",
                }
            )
            continue

        details = chosen.get("details", {})
        physical_page = chosen.get("page")
        rows.append(
            {
                "document": short_name,
                "filename": filename,
                "no_finding": False,
                "physical_page": physical_page,
                "printed_page": printed_page_for(doc_report, physical_page),
                "message": chosen.get("message", ""),
                "measured_amount": measured_amount(details),
                "confidence": finding_confidence(chosen),
                "details": details,
                "issue_type": details.get("issue_type", ""),
            }
        )
    return rows


def _fallback_affected_lines(details: dict[str, Any]) -> list[str]:
    """Expose identifiable adjacent entries when a finding has no line bbox text.

    P036 stores the comparison context as previews plus a gap bbox.  Keeping
    that context in the Ester-facing summary makes the highlighted gap
    understandable without changing detector output or selection.
    """
    issue_type = str(details.get("issue_type", ""))
    if issue_type != "toc_inter_entry_spacing_too_tight":
        return []
    lines = []
    previous = str(details.get("previous_entry_preview", "")).strip()
    following = str(details.get("next_entry_preview", "")).strip()
    if previous:
        lines.append(f"Previous entry: {previous}")
    if following:
        lines.append(f"Next entry: {following}")
    return lines


def _fill_evidence(internal_id: str, rows: list[dict[str, Any]], evidence_dir: Path) -> None:
    for row in rows:
        if row["no_finding"]:
            continue
        pdf_path = doc_pdf_path(row["filename"])
        out_path = evidence_dir / f"{row['document'].lower()}.pdf"
        evidence = build_evidence(
            pdf_path,
            row["physical_page"],
            row["details"],
            internal_id,
            out_path,
        )
        row["location"] = evidence.location
        row["affected_lines"] = evidence.affected_lines
        if not row["affected_lines"]:
            row["affected_lines"] = _fallback_affected_lines(row["details"])
        row["evidence_pdf"] = out_path if out_path.exists() else None
        row["has_highlight"] = evidence.has_highlight
        # Document-level finding (row["physical_page"] is None) that names
        # two real pages via the evidence's transition pairing: show both
        # physical pages and both printed-page labels explicitly instead of
        # the generic "not applicable (document-level finding)" text, since
        # this is now real, displayable evidence rather than nothing.
        if evidence.transition_pages and evidence.transition_labels:
            row["physical_page_display"] = " and ".join(
                str(p) for p in evidence.transition_pages
            )
            row["printed_page"] = " / ".join(
                f'"{label}" (physical p.{page})'
                for page, label in zip(evidence.transition_pages, evidence.transition_labels)
            )


def _write_xlsx(ester_id: str, rows: list[dict[str, Any]], xlsx_path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = ester_id

    header_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11, bold=False)

    pdf_name = f"{ester_id}_Ester_Auditor_Feedback.pdf"
    ws.cell(row=1, column=1, value="DOCUMENT")
    evidence_header = ws.cell(
        row=1,
        column=2,
        value=f"Possible {ester_id} violation — page, location, reason, confidence\n"
        "Open highlighted evidence PDF",
    )
    evidence_header.hyperlink = pdf_name
    evidence_header.hyperlink.tooltip = "Open the highlighted evidence PDF"
    ws.cell(row=1, column=3, value="Question 1")
    ws.cell(row=1, column=4, value="Comment")
    for cell in ws[1]:
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    evidence_header.font = Font(
        name="Calibri", size=11, bold=True, color="0563C1", underline="single"
    )

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 76
    ws.column_dimensions["C"].width = 48
    ws.column_dimensions["D"].width = 44
    ws.freeze_panes = "A2"

    for r, row in enumerate(rows, start=2):
        question = None
        if not row["no_finding"]:
            question = str(row.get("question") or "").strip() or (
                f"Should the auditor report this as an {ester_id} violation?"
            )
        for column, value in enumerate(
            (row["document"], _structured_block(ester_id, row), question, None), start=1
        ):
            cell = ws.cell(row=r, column=column, value=value)
            cell.font = regular_font
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(xlsx_path)


def _write_overview_pdf(ester_id: str, rows: list[dict[str, Any]], out_path: Path) -> None:
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8, leading=10)
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    elements = [
        Paragraph(f"{ester_id} — Ester Auditor Feedback: Overview", title_style),
        Spacer(1, 0.15 * inch),
        Paragraph(
            "One evidence page follows per dissertation with a current-auditor finding. "
            "Confidence reflects the actual auditor classification for the selected finding "
            "(the lowest-confidence surviving finding per document).",
            styles["BodyText"],
        ),
        Spacer(1, 0.2 * inch),
    ]

    header = [
        "Document",
        "PDF page",
        "Printed page",
        "Location",
        "Possible violation",
        "Confidence",
    ]
    data = [header]
    for row in rows:
        if row["no_finding"]:
            data.append(
                [
                    row["document"],
                    "-",
                    "-",
                    "-",
                    Paragraph("No current auditor finding", cell_style),
                    "-",
                ]
            )
        else:
            if row["physical_page"] is not None:
                pdf_page_text = str(row["physical_page"])
            elif row.get("physical_page_display"):
                pdf_page_text = row["physical_page_display"]
            else:
                pdf_page_text = "n/a"
            data.append(
                [
                    row["document"],
                    Paragraph(pdf_page_text, cell_style),
                    Paragraph(row["printed_page"] or "n/a", cell_style),
                    Paragraph(row["location"] or "n/a", cell_style),
                    Paragraph(row["message"], cell_style),
                    row["confidence"],
                ]
            )

    table = Table(
        data,
        colWidths=[0.9 * inch, 0.8 * inch, 1.1 * inch, 1.3 * inch, 4.2 * inch, 0.8 * inch],
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


def _write_evidence_header_pdf(ester_id: str, row: dict[str, Any], out_path: Path) -> None:
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
    if row["physical_page"] is not None:
        physical_page_short: str | int = row["physical_page"]
    elif row.get("physical_page_display"):
        physical_page_short = f"{row['physical_page_display']} (document-level finding)"
    else:
        physical_page_short = "n/a"
    lines = [
        f"<b>{row['document']}</b> — {ester_id} evidence",
        f"Physical PDF page: {physical_page_short} &nbsp;&nbsp; "
        f"Printed/document page: {row['printed_page']} &nbsp;&nbsp; "
        f"Auditor confidence: {row['confidence']}",
    ]
    elements = [
        Paragraph(lines[0], title_style),
        Spacer(1, 0.05 * inch),
        Paragraph(lines[1], body_style),
    ]
    elements.append(Spacer(1, 0.08 * inch))
    elements.append(
        Paragraph(f"Location: {row['location'] or 'not reliably identifiable on page'}", body_style)
    )
    for i, text in enumerate(row["affected_lines"], start=1):
        elements.append(Paragraph(f'{i}. "{text}"', body_style))
    elements.append(Spacer(1, 0.05 * inch))
    elements.append(Paragraph(f"Possible violation: {row['message']}", body_style))
    elements.append(Paragraph(f"Measured amount: {row['measured_amount']}", body_style))
    doc.build(elements)


def _assemble_combined_pdf(
    ester_id: str,
    rows: list[dict[str, Any]],
    overview_pdf: Path,
    evidence_dir: Path,
    out_path: Path,
) -> int:
    combined = fitz.open()
    combined.insert_pdf(fitz.open(str(overview_pdf)))
    combined.set_toc([[1, "Overview", 1]])
    toc = combined.get_toc(simple=True)

    for row in rows:
        if row["no_finding"]:
            continue
        header_pdf = evidence_dir / f"{row['document'].lower()}_header.pdf"
        _write_evidence_header_pdf(ester_id, row, header_pdf)

        page_start = combined.page_count + 1
        combined.insert_pdf(fitz.open(str(header_pdf)))
        evidence_pdf = row.get("evidence_pdf")
        if evidence_pdf and evidence_pdf.exists():
            combined.insert_pdf(fitz.open(str(evidence_pdf)))
        toc.append([1, f"{row['document']} ({ester_id})", page_start])

    combined.set_toc(toc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(str(out_path))
    page_count = combined.page_count
    combined.close()
    return page_count


def validate_package(
    ester_id: str, rows: list[dict[str, Any]], xlsx_path: Path, pdf_path: Path
) -> list[str]:
    problems = []
    if len(rows) != len(DOCS):
        problems.append(f"expected {len(DOCS)} document rows, got {len(rows)}")

    wb = openpyxl.load_workbook(xlsx_path)
    if ester_id not in wb.sheetnames:
        problems.append(f"xlsx missing sheet {ester_id}")
    else:
        ws = wb[ester_id]
        if ws.cell(row=1, column=1).value != "DOCUMENT":
            problems.append("xlsx header A1 wrong")
        if ws.cell(row=1, column=3).value != "Question 1":
            problems.append("xlsx header C1 wrong")
        if ws.cell(row=1, column=4).value != "Comment":
            problems.append("xlsx header D1 wrong")
        if ws.freeze_panes != "A2":
            problems.append("xlsx header row is not frozen")
        if ws.cell(row=1, column=2).hyperlink is None:
            problems.append("xlsx evidence PDF link missing")
        for r in range(2, 2 + len(DOCS)):
            no_finding = rows[r - 2]["no_finding"]
            question = ws.cell(row=r, column=3).value
            if no_finding and question not in (None, ""):
                problems.append(f"xlsx row {r} no-action question is not blank")
            if not no_finding and not question:
                problems.append(f"xlsx row {r} current-case question is blank")
            if ws.cell(row=r, column=4).value not in (None, ""):
                problems.append(f"xlsx row {r} column D (comment field) not blank")

    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count < 1:
            problems.append("combined pdf has zero pages")
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if not text and not page.get_images():
                problems.append(f"combined pdf page {i + 1} appears blank")

    for row in rows:
        if row["no_finding"]:
            continue
        if row["physical_page"] is not None and not row.get("evidence_pdf"):
            problems.append(
                f"{row['document']}: page-anchored finding (page {row['physical_page']}) "
                "has no rendered evidence page"
            )

    return problems


def build_rule(
    internal_id: str, ester_id: str | None = None, *, review_date: dt.date | None = None
) -> dict[str, Any]:
    if ester_id is None:
        ester_id = f"R{internal_id[1:]}"
    if review_date is None:
        review_date = dt.date.today()
    rows = build_rule_rows(internal_id)
    with tempfile.TemporaryDirectory(prefix=f"{ester_id.lower()}_evidence_") as tmpdir:
        evidence_dir = Path(tmpdir)
        _fill_evidence(internal_id, rows, evidence_dir)

        xlsx_path = OUTPUT_DIR / review_workbook_filename(ester_id, review_date)
        pdf_path = OUTPUT_DIR / f"{ester_id}_Ester_Auditor_Feedback.pdf"
        overview_pdf = evidence_dir / "overview.pdf"

        _write_xlsx(ester_id, rows, xlsx_path)
        _write_overview_pdf(ester_id, rows, overview_pdf)
        page_count = _assemble_combined_pdf(ester_id, rows, overview_pdf, evidence_dir, pdf_path)

    problems = validate_package(ester_id, rows, xlsx_path, pdf_path)
    findings_present = sum(1 for r in rows if not r["no_finding"])
    return {
        "internal_id": internal_id,
        "ester_id": ester_id,
        "xlsx_path": str(xlsx_path),
        "pdf_path": str(pdf_path),
        "pdf_page_count": page_count,
        "documents_with_findings": findings_present,
        "documents_with_no_finding": len(rows) - findings_present,
        "validation_problems": problems,
    }


if __name__ == "__main__":
    import sys

    rid = sys.argv[1]
    result = build_rule(rid)
    print(result)
