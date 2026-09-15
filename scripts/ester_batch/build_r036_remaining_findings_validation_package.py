"""Build the R036 "remaining findings after the 2026-09-14 policy fix"
reviewer-validation package.

Context: Ester reviewed all 12 R036 findings on Praneeth's TOC page 11
(``R036_Praneeth_Page11_All_Examples.*``) and confirmed all 12 false
positive, stating the governing rule: "The TOC must be double spaced
except for titles that run longer than one line in which case these
titles must be single spaced." That policy was implemented on
``fix/r036-toc-wrapped-title-spacing-policy-20260914`` -- see
``docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md`` for the
full measurement/grouping-fix writeup.

After that fix, R036 still reports findings on four other dissertations
(Youra, Muyeed, Philip, Patrick -- Anthony/Praneeth/Sebastian are now at
zero). None of those were part of the September 14 review. This script
selects a small, representative, manually-verified subset of them (not
all ~193) and renders a self-contained package so Ester can tell us
whether the corrected detector is now identifying genuine under-spacing,
without recreating the old interpretation-A-vs-B ambiguity (already
resolved).

This is evidence preparation only: it calls the same real audit pipeline
and evidence-rendering building blocks the existing single-example and
Praneeth-page-11 packages use (``lib.build_full_audit_json``,
``lib.visible_findings_for_rule``, ``lib.build_evidence``), and a small
amount of read-only introspection into the detector's own already-computed
entry-grouping (to report which side of each pair wraps) -- it does not
change any detector file, threshold, or test.

Outputs (new files; does not touch any existing R036 package):
  - docs/evaluation/ester_feedback/R036_Remaining_Findings_Validation_20260914.xlsx
  - docs/evaluation/ester_feedback/R036_Remaining_Findings_Validation_20260914.pdf
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

import fitz
import openpyxl
from lib import (
    DOCS,
    OUTPUT_DIR,
    build_evidence,
    build_full_audit_json,
    doc_pdf_path,
    printed_page_for,
    visible_findings_for_rule,
)
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from njit_auditor.pdf_layout import load_pdf_layout  # noqa: E402
from njit_auditor.rules.pdf_toc_alignment import detect_toc_like_pages  # noqa: E402
from njit_auditor.rules.pdf_toc_list_entry_spacing import (  # noqa: E402
    _group_lines_into_entries,
)
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import (
    _collect_entry_region_lines,  # noqa: E402
)

RULE_ID = "P036"
ESTER_ID = "R036"

XLSX_PATH = OUTPUT_DIR / f"{ESTER_ID}_Remaining_Findings_Validation_20260914.xlsx"
PDF_PATH = OUTPUT_DIR / f"{ESTER_ID}_Remaining_Findings_Validation_20260914.pdf"

# Full remaining-count expectations, re-verified fresh against the real
# PDFs each run (never assumed) -- see build_package()'s check below.
EXPECTED_TOTAL_COUNTS = {
    "Youra": 20,
    "Anthony": 0,
    "Muyeed": 114,
    "Philip": 20,
    "Praneeth": 0,
    "Sebastian": 0,
    "Patrick": 39,
}

# The 3 findings that only became visible after the entry-grouping bug
# fixes landed alongside the pitch-measurement change (see the status doc,
# "Logical entry grouping (three real bugs fixed)"). Identified once by
# diffing this branch's output against a pre-fix baseline; recorded here
# as a fixed fact for labeling, not recomputed on every run.
NEWLY_SURFACED = {
    ("Muyeed", 20, 8),
    ("Muyeed", 21, 5),
    ("Patrick", 8, 10),
}

# (dissertation, physical_page, entry_pair_index, note). `note` is a short,
# internal-only selection rationale (not shown to Ester) recorded here so
# the selection is auditable later without re-deriving it. Picked from a
# full inventory of all ~193 remaining findings, clustered by dissertation,
# spacing-ratio band, and structural/transition shape -- see
# docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md and the
# session record for the clustering analysis.
SELECTED_EXAMPLES: list[tuple[str, int, int, str]] = [
    # -- Mandatory: the 3 newly-surfaced findings --
    ("Muyeed", 20, 8, "newly surfaced by REFERENCES/keyword-style grouping context; ratio ~1.24"),
    ("Muyeed", 21, 5, "newly surfaced; ratio ~1.46, nearest this doc gets to the 1.6 boundary"),
    ("Patrick", 8, 10, "newly surfaced; APPENDIX->REFERENCES, the structural-heading grouping fix"),
    # -- Muyeed: 3 more, different ratio bands / structural shapes --
    ("Muyeed", 16, 0, "clearly tight (ratio ~1.0), same-level ordinary List of Tables entries"),
    ("Muyeed", 13, 16, "clearly tight (ratio ~1.0), wrapped previous entry, Table of Contents"),
    ("Muyeed", 20, 0, "moderately tight (ratio ~1.11), wrapped previous entry, List of Figures"),
    # -- Patrick: 3 more --
    ("Patrick", 7, 8, "clearly tight (ratio ~1.0), ordinary Table of Contents entries"),
    ("Patrick", 7, 11, "clearly tight (ratio ~1.0), ordinary Table of Contents entries"),
    ("Patrick", 11, 2, "borderline (ratio ~1.51, nearest the 1.6 boundary), List of Figures"),
    # -- Philip: 2 --
    ("Philip", 11, 5, "clearly tight (ratio ~1.01), ordinary Table of Contents entries"),
    ("Philip", 15, 2, "borderline (ratio ~1.56, nearest the 1.6 boundary), List of Figures"),
    # -- Youra: 2 --
    ("Youra", 12, 4, "clearly tight (ratio ~1.01), ordinary Table of Contents entries"),
    ("Youra", 12, 0, "clearly tight (ratio ~1.01), wrapped previous entry, Table of Contents"),
]

COVER_NOTE = (
    "Ester's September 14, 2026 policy clarification has already been incorporated into "
    f"the {ESTER_ID} detector: 'The TOC must be double spaced except for titles that run "
    "longer than one line in which case these titles must be single spaced.' The 12 "
    "previously-reviewed Praneeth examples (all marked false positive) are no longer "
    "flagged. This package contains a small, representative sample of the remaining "
    f"{ESTER_ID} findings on four other dissertations, so we can confirm whether these "
    "should be treated as genuine spacing issues or whether the detector needs further "
    "adjustment. A few of the sampled findings come from List of Figures/Tables captions "
    "where the source PDF's text extraction drops spaces between some words (e.g. "
    "'ThreeNewtoniterations') -- this affects only how the entry text is displayed here, "
    "not the measured spacing, which is based on line position, not on the text."
)

REVIEW_QUESTION = (
    "Under the rule that separate TOC entries should be double-spaced while wrapped "
    "lines within the same title are single-spaced, should each of these highlighted "
    "gaps be reported by the auditor?"
)

XLSX_HEADERS = [
    "Example #",
    "Dissertation",
    "Physical PDF Page",
    "Printed Page",
    "Previous Entry",
    "Next Entry",
    "Transition Type",
    "Previous Entry Wraps?",
    "Next Entry Wraps?",
    "Measured Pitch",
    "Local Single-Line Pitch",
    "Normalized Ratio",
    "Newly Surfaced by Grouping Fix?",
    "Similar Findings Represented",
    "Reviewer Decision",
    "Reviewer Comment",
]
XLSX_COLUMN_WIDTHS = [10, 14, 12, 12, 34, 34, 26, 12, 12, 12, 16, 12, 16, 16, 18, 34]
XLSX_HEADER_ROW_HEIGHT = 30


def _normalize_display_whitespace(text: str) -> str:
    return " ".join(text.split())


def _transition_type_label(
    prev_text: str, next_text: str, prev_wraps: bool | None, next_wraps: bool | None
) -> str:
    """Presentation-only label. The numbering-shape half mirrors the
    existing R036_Praneeth_Page11 package's ``_classify_transition_label``
    (derived only from already-sanitized preview text); the wrap-shape half
    additionally reports which side of the pair spans multiple physical
    lines (from the read-only entry-grouping lookup in
    ``_wrap_flags_for_pair`` -- not re-derived here)."""
    import re

    def _level(text: str) -> str:
        stripped = text.strip()
        upper = stripped.upper()
        structural_words = (
            "CHAPTER", "APPENDIX", "REFERENCES", "BIBLIOGRAPHY", "VITA", "GLOSSARY", "INDEX"
        )
        if upper.startswith(structural_words):
            return "structural heading"
        if re.match(r"^\d+\.\d+\.\d+", stripped):
            return "level-3 (X.X.X)"
        if re.match(r"^\d+\.\d+", stripped):
            return "level-2 (X.X)"
        if not stripped:
            return "(blank preview)"
        return "unnumbered entry"

    prev_level, next_level = _level(prev_text), _level(next_text)
    if prev_level == "structural heading" or next_level == "structural heading":
        base = f"structural-heading transition ({prev_level} -> {next_level})"
    elif prev_level == next_level:
        base = f"same-level entries ({prev_level})"
    else:
        base = f"{prev_level} -> {next_level}"
    wrap_bits = []
    if prev_wraps:
        wrap_bits.append("previous entry wraps")
    if next_wraps:
        wrap_bits.append("next entry wraps")
    if wrap_bits:
        base += " [" + ", ".join(wrap_bits) + "]"
    return base


def _entries_by_page(pdf_path: Path) -> dict[int, list[list]]:
    """Read-only introspection: re-run the detector's own entry-grouping
    (unchanged) to look up, per physical page, the logical entries in
    order -- used only to report whether the previous/next entry in a
    selected pair spans multiple physical lines. Does not change any
    detector file; calls the same functions the rule itself calls."""
    doc = load_pdf_layout(str(pdf_path))
    by_page: dict[int, list[list]] = {}
    for context in detect_toc_like_pages(doc):
        lines = _collect_entry_region_lines(context)
        entries = _group_lines_into_entries(lines, context.page_type)
        by_page[context.page.page_number] = entries
    return by_page


def _wrap_flags_for_pair(
    entries_by_page: dict[int, list[list]], page: int, pair_index: int
) -> tuple[bool | None, bool | None]:
    entries = entries_by_page.get(page)
    if entries is None or pair_index + 1 >= len(entries):
        return None, None
    previous_entry, next_entry = entries[pair_index], entries[pair_index + 1]
    return len(previous_entry) > 1, len(next_entry) > 1


def _similar_findings_count(
    all_page_findings: list[dict[str, Any]], target: dict[str, Any]
) -> int:
    """Count of OTHER findings in the same document whose ratio falls in the
    same 0.1-wide band as *target* -- a simple, reproducible, non-arbitrary
    proxy for "how many similar findings does this example stand in for"."""
    target_ratio = round(float(target["details"].get("gap_ratio", "0")), 1)
    count = 0
    for f in all_page_findings:
        try:
            ratio = round(float(f["details"].get("gap_ratio", "0")), 1)
        except ValueError:
            continue
        if ratio == target_ratio:
            count += 1
    return count


def _find_finding(
    findings: list[dict[str, Any]], page: int, pair_index: int
) -> dict[str, Any] | None:
    for f in findings:
        details = f.get("details", {})
        if f.get("page") == page and str(details.get("entry_pair_index", "")) == str(pair_index):
            return f
    return None


def build_example_rows() -> list[dict[str, Any]]:
    docs_by_name = dict(DOCS)
    findings_by_doc: dict[str, list[dict[str, Any]]] = {}
    reports_by_doc: dict[str, dict[str, Any]] = {}
    entries_by_doc: dict[str, dict[int, list[list]]] = {}

    needed_docs = sorted({name for name, *_ in SELECTED_EXAMPLES})
    for name in needed_docs:
        pdf_path = doc_pdf_path(docs_by_name[name])
        report = build_full_audit_json(pdf_path)
        reports_by_doc[name] = report
        findings_by_doc[name] = visible_findings_for_rule(report, RULE_ID)
        entries_by_doc[name] = _entries_by_page(pdf_path)

    rows: list[dict[str, Any]] = []
    for example_number, (name, page, pair_index, note) in enumerate(SELECTED_EXAMPLES, start=1):
        finding = _find_finding(findings_by_doc[name], page, pair_index)
        if finding is None:
            raise SystemExit(
                f"Refusing to build package: selected example #{example_number} "
                f"({name}, physical page {page}, pair {pair_index}) is not present in "
                "the current live R036 findings. The detector output has changed since "
                "selection -- stop and re-select before generating a package."
            )
        details = finding["details"]
        prev_text = _normalize_display_whitespace(str(details.get("previous_entry_preview", "")))
        next_text = _normalize_display_whitespace(str(details.get("next_entry_preview", "")))
        prev_wraps, next_wraps = _wrap_flags_for_pair(entries_by_doc[name], page, pair_index)
        rows.append(
            {
                "example_number": example_number,
                "dissertation": name,
                "physical_page": page,
                "printed_page": printed_page_for(reports_by_doc[name], page),
                "previous_entry": prev_text,
                "next_entry": next_text,
                "transition_label": _transition_type_label(
                    prev_text, next_text, prev_wraps, next_wraps
                ),
                "prev_wraps": prev_wraps,
                "next_wraps": next_wraps,
                "gap_points": str(details.get("gap_points", "")),
                "local_pitch": str(details.get("local_single_line_pitch_points", "")),
                "gap_ratio": str(details.get("gap_ratio", "")),
                "newly_surfaced": (name, page, pair_index) in NEWLY_SURFACED,
                "similar_findings": _similar_findings_count(findings_by_doc[name], finding),
                "message": finding.get("message", ""),
                "details": details,
                "selection_note": note,
                "pdf_path": doc_pdf_path(docs_by_name[name]),
            }
        )
    return rows


def _fill_evidence(rows: list[dict[str, Any]], evidence_dir: Path) -> None:
    for row in rows:
        out_path = evidence_dir / f"example_{row['example_number']:02d}.pdf"
        evidence = build_evidence(
            row["pdf_path"],
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
    cover_ws.row_dimensions[1].height = 110
    question_cell = cover_ws.cell(row=3, column=1, value=REVIEW_QUESTION)
    question_cell.alignment = Alignment(wrap_text=True, vertical="top")
    question_cell.font = Font(name="Calibri", size=11, bold=True)
    cover_ws.row_dimensions[3].height = 40

    ws = wb.create_sheet(title=f"{ESTER_ID}_Remaining_Findings")
    header_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11, bold=False)

    for col, header in enumerate(XLSX_HEADERS, start=1):
        header_cell = ws.cell(row=1, column=col, value=header)
        header_cell.font = header_font
        header_cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = XLSX_HEADER_ROW_HEIGHT
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{chr(64 + len(XLSX_HEADERS))}1"

    for col, width in enumerate(XLSX_COLUMN_WIDTHS, start=1):
        ws.column_dimensions[chr(64 + col)].width = width

    def _wrap_label(value: bool | None) -> str:
        if value is None:
            return "unknown"
        return "YES" if value else "NO"

    for r, row in enumerate(rows, start=2):
        values = [
            row["example_number"],
            row["dissertation"],
            row["physical_page"],
            row["printed_page"],
            row["previous_entry"],
            row["next_entry"],
            row["transition_label"],
            _wrap_label(row["prev_wraps"]),
            _wrap_label(row["next_wraps"]),
            row["gap_points"],
            row["local_pitch"],
            row["gap_ratio"],
            "YES" if row["newly_surfaced"] else "NO",
            row["similar_findings"],
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
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=15)
    note_style = ParagraphStyle("note", parent=styles["BodyText"], fontSize=10, leading=13)
    question_style = ParagraphStyle(
        "question", parent=styles["BodyText"], fontSize=11, leading=14, fontName="Helvetica-Bold"
    )
    header_cell_style = ParagraphStyle(
        "header_cell",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=landscape(letter),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    elements = [
        Paragraph(f"{ESTER_ID} — Remaining Findings Validation (2026-09-14)", title_style),
        Spacer(1, 0.1 * inch),
        Paragraph(COVER_NOTE, note_style),
        Spacer(1, 0.15 * inch),
        Paragraph(REVIEW_QUESTION, question_style),
        Spacer(1, 0.2 * inch),
    ]

    header = [
        Paragraph(h, header_cell_style)
        for h in (
            "Ex#",
            "Dissertation",
            "Page",
            "Transition",
            "Ratio",
            "New?",
            "Similar",
        )
    ]
    data = [header]
    for row in rows:
        data.append(
            [
                str(row["example_number"]),
                row["dissertation"],
                str(row["physical_page"]),
                Paragraph(row["transition_label"], cell_style),
                row["gap_ratio"],
                "YES" if row["newly_surfaced"] else "NO",
                str(row["similar_findings"]),
            ]
        )

    col_widths = [
        0.5 * inch, 1.1 * inch, 0.6 * inch, 2.6 * inch, 0.6 * inch, 0.55 * inch, 0.65 * inch,
    ]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)


def _yes_no_unknown(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "YES" if value else "NO"


def _write_evidence_header_pdf(row: dict[str, Any], out_path: Path) -> None:
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=13)
    title_style = ParagraphStyle("title2", parent=styles["Heading1"], fontSize=14)
    reviewer_style = ParagraphStyle(
        "reviewer", parent=styles["BodyText"], fontSize=11, leading=15, fontName="Helvetica-Bold"
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    elements = [
        Paragraph(
            f"Example {row['example_number']} of {len(SELECTED_EXAMPLES)} — "
            f"{ESTER_ID} ({row['dissertation']}, physical page {row['physical_page']})",
            title_style,
        ),
        Spacer(1, 0.05 * inch),
        Paragraph(f"Printed/document page: {row['printed_page']}", body_style),
        Paragraph(
            f"Location: {row['location'] or 'not reliably identifiable on page'}",
            body_style,
        ),
        Spacer(1, 0.08 * inch),
        Paragraph(f'Previous entry: "{row["previous_entry"]}"', body_style),
        Paragraph(f'Next entry: "{row["next_entry"]}"', body_style),
        Paragraph(f"Transition type: {row['transition_label']}", body_style),
        Paragraph(
            f"Previous entry wraps onto more than one line? {_yes_no_unknown(row['prev_wraps'])}",
            body_style,
        ),
        Paragraph(
            f"Next entry wraps onto more than one line? {_yes_no_unknown(row['next_wraps'])}",
            body_style,
        ),
        Spacer(1, 0.05 * inch),
        Paragraph(f"Observed: {row['message']}", body_style),
        Paragraph(f"Measured pitch: {row['gap_points']}pt", body_style),
        Paragraph(f"Local single-line pitch (this page): {row['local_pitch']}pt", body_style),
        Paragraph(f"Normalized ratio: {row['gap_ratio']} (required >= 1.60)", body_style),
        Spacer(1, 0.15 * inch),
        Paragraph("Reviewer decision: True positive / False positive / Unsure", reviewer_style),
        Paragraph("Comment: ________________________________________________", body_style),
    ]
    doc.build(elements)


def _assemble_combined_pdf(
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
        header_pdf = evidence_dir / f"example_{row['example_number']:02d}_header.pdf"
        _write_evidence_header_pdf(row, header_pdf)

        page_start = combined.page_count + 1
        combined.insert_pdf(fitz.open(str(header_pdf)))
        evidence_pdf = row.get("evidence_pdf")
        if evidence_pdf and evidence_pdf.exists():
            combined.insert_pdf(fitz.open(str(evidence_pdf)))
        marker = " (newly surfaced)" if row["newly_surfaced"] else ""
        toc_label = f"Example {row['example_number']} — {row['dissertation']}{marker}"
        toc.append([1, toc_label, page_start])

    combined.set_toc(toc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(str(out_path))
    page_count = combined.page_count
    combined.close()
    return page_count


def validate_package(rows: list[dict[str, Any]], xlsx_path: Path, pdf_path: Path) -> list[str]:
    problems: list[str] = []

    if not (10 <= len(rows) <= 18):
        problems.append(f"expected 10-18 example rows, got {len(rows)}")

    seen = {(row["dissertation"], row["physical_page"], row["example_number"]) for row in rows}
    if len(seen) != len(rows):
        problems.append("duplicate example rows detected")

    newly_surfaced_count = sum(1 for row in rows if row["newly_surfaced"])
    if newly_surfaced_count != 3:
        problems.append(
            f"expected exactly 3 newly-surfaced examples included, got {newly_surfaced_count}"
        )

    docs_present = {row["dissertation"] for row in rows}
    for required_doc in ("Youra", "Muyeed", "Philip", "Patrick"):
        if required_doc not in docs_present:
            problems.append(f"required dissertation {required_doc} not represented")

    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = f"{ESTER_ID}_Remaining_Findings"
    if sheet_name not in wb.sheetnames:
        problems.append(f"xlsx missing sheet {sheet_name}")
    else:
        ws = wb[sheet_name]
        if ws.cell(row=1, column=1).value != "Example #":
            problems.append("xlsx header A1 wrong")
        decision_col = XLSX_HEADERS.index("Reviewer Decision") + 1
        comment_col = XLSX_HEADERS.index("Reviewer Comment") + 1
        for r in range(2, 2 + len(rows)):
            if ws.cell(row=r, column=decision_col).value not in (None, ""):
                problems.append(f"xlsx row {r}: Reviewer Decision column not blank")
            if ws.cell(row=r, column=comment_col).value not in (None, ""):
                problems.append(f"xlsx row {r}: Reviewer Comment column not blank")

    for name in ("P036", "Q057", "Q067", "Q077"):
        wb2 = openpyxl.load_workbook(xlsx_path)
        for sheet in wb2.worksheets:
            for row_cells in sheet.iter_rows():
                for cell in row_cells:
                    if cell.value is not None and name in str(cell.value):
                        problems.append(
                            f"internal identifier {name!r} leaked into xlsx cell {cell.coordinate}"
                        )

    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count < 1:
            problems.append("combined pdf has zero pages")
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if "P036" in text or "Q057" in text or "Q067" in text or "Q077" in text:
                problems.append(f"internal identifier leaked into combined pdf page {i + 1}")
            if not text.strip() and not page.get_images():
                problems.append(f"combined pdf page {i + 1} appears blank")

    for row in rows:
        if not row.get("evidence_pdf"):
            problems.append(f"example {row['example_number']}: no rendered evidence page")
        if not row.get("has_highlight"):
            problems.append(f"example {row['example_number']}: highlight missing on evidence page")

    return problems


def build_package() -> dict[str, Any]:
    # Re-verify the full remaining-count picture fresh against the real
    # PDFs (never cached JSON) before selecting anything, per the task's
    # own instruction to confirm current counts before proceeding.
    actual_counts: dict[str, int] = {}
    for name, filename in DOCS:
        report = build_full_audit_json(doc_pdf_path(filename))
        actual_counts[name] = len(visible_findings_for_rule(report, RULE_ID))
    mismatches = {
        name: (EXPECTED_TOTAL_COUNTS[name], actual_counts[name])
        for name in EXPECTED_TOTAL_COUNTS
        if EXPECTED_TOTAL_COUNTS[name] != actual_counts[name]
    }
    if mismatches:
        raise SystemExit(
            "Refusing to build package: current R036 counts differ from the "
            f"expected implementation-report state: {mismatches}. Investigate "
            "before generating a reviewer package."
        )

    rows = build_example_rows()

    with tempfile.TemporaryDirectory(prefix="r036_remaining_findings_") as tmpdir:
        evidence_dir = Path(tmpdir)
        _fill_evidence(rows, evidence_dir)

        overview_pdf = evidence_dir / "overview.pdf"
        _write_overview_pdf(rows, overview_pdf)

        _write_xlsx(rows, XLSX_PATH)
        page_count = _assemble_combined_pdf(rows, overview_pdf, evidence_dir, PDF_PATH)

    problems = validate_package(rows, XLSX_PATH, PDF_PATH)

    return {
        "xlsx_path": str(XLSX_PATH),
        "pdf_path": str(PDF_PATH),
        "pdf_page_count": page_count,
        "example_count": len(rows),
        "actual_counts": actual_counts,
        "validation_problems": problems,
    }


if __name__ == "__main__":
    result = build_package()
    print(result)
