"""P049/P050: LoT/LoF column-header style checks.

P049: Page-column header right-alignment and bold-style (Q064/Q073).
P050: Left-column header bold-style — "Table"/"Figure" labels (Q063/Q072).
Complements P031 (presence/coarse alignment) with tighter geometry and style detection.
"""

from __future__ import annotations

from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine
from njit_auditor.rules.pdf_lot_lof_column_headers import (
    _collect_header_zone_lines,
    _matches_left_label,
    _matches_page_label,
)
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_COMPLETE_ENTRIES = 3
RIGHT_ALIGNMENT_TOLERANCE_PT = 25.0

_TARGET_SECTIONS = frozenset({"list_of_tables", "list_of_figures"})

_ISSUE_TYPE_ALIGNMENT = {
    "list_of_tables": "lot_page_header_not_right_aligned",
    "list_of_figures": "lof_page_header_not_right_aligned",
}
_ISSUE_TYPE_BOLD = {
    "list_of_tables": "lot_page_header_not_bold",
    "list_of_figures": "lof_page_header_not_bold",
}
_Q_RULE = {
    "list_of_tables": "Q064",
    "list_of_figures": "Q073",
}

# P050 — left-column header bold check
_ISSUE_TYPE_LEFT_BOLD = {
    "list_of_tables": "lot_table_header_not_bold",
    "list_of_figures": "lof_figure_header_not_bold",
}
_Q_RULE_LEFT = {
    "list_of_tables": "Q063",
    "list_of_figures": "Q072",
}
_SECTION_LABEL = {
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}


def _complete_entries(entries: list[TocEntryLine]) -> list[TocEntryLine]:
    return [e for e in entries if e.page_number_right_x is not None]


def _expected_right_x(complete: list[TocEntryLine]) -> float:
    values = [e.page_number_right_x for e in complete if e.page_number_right_x is not None]
    return float(median(values))


def _is_line_confidently_not_bold(line: PdfTextLine) -> bool:
    """Return True only when spans expose reliable non-bold font metadata."""
    if not line.spans:
        return False
    if not all(s.font is not None for s in line.spans):
        return False
    return not any(s.bold for s in line.spans)


def check_pdf_lot_lof_column_header_style_alignment(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P049 warnings for LoT/LoF Page-column header alignment and bold-style issues."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        if context.page_type not in _TARGET_SECTIONS:
            continue

        complete = _complete_entries(extract_toc_entry_lines(context))
        if len(complete) < MIN_COMPLETE_ENTRIES:
            continue

        expected_rx = _expected_right_x(complete)
        header_lines = _collect_header_zone_lines(context)
        page_header_matches = [ln for ln in header_lines if _matches_page_label(ln.text)]
        if not page_header_matches:
            continue  # P031 handles missing Page header

        page_line = max(page_header_matches, key=lambda ln: ln.bbox.x1)
        observed_rx = page_line.bbox.x1
        delta = abs(observed_rx - expected_rx)
        section = context.page_type
        page_num = context.page.page_number
        q_rule = _Q_RULE[section]

        if delta > RIGHT_ALIGNMENT_TOLERANCE_PT:
            findings.append(
                AuditFinding(
                    rule_id="P049",
                    severity=Severity.WARNING,
                    page=page_num,
                    message=(
                        f"{_SECTION_LABEL[section]} 'Page' column header does not appear "
                        f"to be right-aligned with the page-number column, as required by "
                        f"NJIT guidelines ({q_rule})."
                    ),
                    details={
                        "page_number": str(page_num),
                        "issue_type": _ISSUE_TYPE_ALIGNMENT[section],
                        "section_type": section,
                        "column_type": "page",
                        "observed_x": f"{observed_rx:.1f}",
                        "expected_x": f"{expected_rx:.1f}",
                        "x_delta_points": f"{delta:.1f}",
                        "allowed_delta_points": f"{RIGHT_ALIGNMENT_TOLERANCE_PT:.1f}",
                        "entry_count": str(len(complete)),
                        "triage_tier": "low",
                        "source_q_rule_id": q_rule,
                    },
                )
            )

        if _is_line_confidently_not_bold(page_line):
            findings.append(
                AuditFinding(
                    rule_id="P049",
                    severity=Severity.WARNING,
                    page=page_num,
                    message=(
                        f"{_SECTION_LABEL[section]} 'Page' column header does not appear "
                        f"to be bold, as required by NJIT guidelines ({q_rule})."
                    ),
                    details={
                        "page_number": str(page_num),
                        "issue_type": _ISSUE_TYPE_BOLD[section],
                        "section_type": section,
                        "column_type": "page",
                        "entry_count": str(len(complete)),
                        "triage_tier": "low",
                        "source_q_rule_id": q_rule,
                    },
                )
            )

    return findings


def check_pdf_lot_lof_left_column_header_bold(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P050 warnings for LoT/LoF left-column header bold-style issues."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        if context.page_type not in _TARGET_SECTIONS:
            continue

        complete = _complete_entries(extract_toc_entry_lines(context))
        if len(complete) < MIN_COMPLETE_ENTRIES:
            continue

        header_lines = _collect_header_zone_lines(context)
        left_matches = [
            ln for ln in header_lines if _matches_left_label(ln.text, context.page_type)
        ]
        if not left_matches:
            continue  # P031 handles missing left header

        left_line = min(left_matches, key=lambda ln: ln.bbox.x0)
        section = context.page_type
        page_num = context.page.page_number
        q_rule = _Q_RULE_LEFT[section]

        if _is_line_confidently_not_bold(left_line):
            findings.append(
                AuditFinding(
                    rule_id="P050",
                    severity=Severity.WARNING,
                    page=page_num,
                    message=(
                        f"{_SECTION_LABEL[section]} left column header does not appear "
                        f"to be bold, as required by NJIT guidelines ({q_rule})."
                    ),
                    details={
                        "page_number": str(page_num),
                        "issue_type": _ISSUE_TYPE_LEFT_BOLD[section],
                        "section_type": section,
                        "column_type": "left",
                        "style_signal": "font_metadata",
                        "font_metadata_available": "true",
                        "entry_count": str(len(complete)),
                        "triage_tier": "low",
                        "source_q_rule_id": q_rule,
                    },
                )
            )

    return findings
