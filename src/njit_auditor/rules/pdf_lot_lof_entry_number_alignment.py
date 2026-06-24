"""Conservative LoT/LoF entry number left-column alignment checks (P046).

Partial heuristic PDF coverage for Q068 and Q078:
  - Q068: are all table numbers aligned vertically in one left column?
  - Q078: are all figure numbers aligned vertically in one left column?

List of Tables and List of Figures pages only. Does not read entry title text,
figure descriptions, table captions, or any private content. Complements P018
(page-number right-column alignment) and P031 (column-label presence).
"""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import detect_toc_like_pages, extract_toc_entry_lines
from njit_auditor.toc_list_student_preview import sanitize_toc_list_entry_preview

MIN_ENTRIES = 3
X0_RANGE_THRESHOLD_PT = 6.0

_SECTION_LABELS = {
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}
_ISSUE_TYPE = {
    "list_of_tables": "lot_entry_number_column_misaligned",
    "list_of_figures": "lof_entry_number_column_misaligned",
}
_SOURCE_Q_RULE = {
    "list_of_tables": "Q068",
    "list_of_figures": "Q078",
}


def check_pdf_lot_lof_entry_number_alignment(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P046 warnings when LoT/LoF entry number x0 positions vary beyond tolerance."""

    # Each tuple is (page_number, per_page_entry_index, x0, bbox, preview) so the worst
    # offender can be traced back safely without storing full entry text.
    entries_by_section: dict[str, list[tuple[int, int, float, BBox, str]]] = {
        "list_of_tables": [],
        "list_of_figures": [],
    }
    first_page_by_section: dict[str, int] = {}

    for context in detect_toc_like_pages(pdf_document):
        section = context.page_type
        if section not in entries_by_section:
            continue

        entries = extract_toc_entry_lines(context)
        # Prefer entries with a detected page number (complete entries, not label/header lines).
        complete = [e for e in entries if e.page_number_right_x is not None]
        if not complete:
            complete = entries

        for per_page_index, entry in enumerate(complete):
            preview = sanitize_toc_list_entry_preview(entry.cleaned_text)
            entries_by_section[section].append(
                (
                    context.page.page_number,
                    per_page_index,
                    entry.indent_x,
                    entry.line.bbox,
                    preview,
                )
            )

        if section not in first_page_by_section and complete:
            first_page_by_section[section] = context.page.page_number

    findings: list[AuditFinding] = []

    for section, located_entries in entries_by_section.items():
        if len(located_entries) < MIN_ENTRIES:
            continue

        x0s = [x0 for _, _, x0, _, _ in located_entries]
        x0_min = min(x0s)
        x0_max = max(x0s)
        x0_range = x0_max - x0_min

        if x0_range <= X0_RANGE_THRESHOLD_PT:
            continue

        page_num = first_page_by_section.get(section, 0)
        label = _SECTION_LABELS[section]

        affected = [
            (page_number, per_page_index, x0, bbox, preview)
            for page_number, per_page_index, x0, bbox, preview in located_entries
            if abs(x0 - x0_min) > X0_RANGE_THRESHOLD_PT
        ]
        details = {
            "page_number": str(page_num),
            "issue_type": _ISSUE_TYPE[section],
            "section_type": section,
            "entry_count": str(len(x0s)),
            "observed_x0_range_points": f"{x0_range:.1f}",
            "expected_x0": f"{x0_min:.1f}",
            "observed_x0_max": f"{x0_max:.1f}",
            "allowed_x0_range_points": f"{X0_RANGE_THRESHOLD_PT:.1f}",
            "triage_tier": "low",
            "source_q_rule_id": _SOURCE_Q_RULE[section],
        }
        if affected:
            details["affected_entry_count"] = str(len(affected))
            worst_page, worst_index, _, worst_bbox, worst_preview = max(
                affected, key=lambda item: abs(item[2] - x0_min)
            )
            # Only attribute an entry index when the worst offender is on the page this
            # finding is already reported on, so the location label never claims a page
            # the entry isn't actually on.
            if worst_page == page_num:
                details["entry_index"] = str(worst_index)
                details["bbox"] = format_bbox_detail(worst_bbox)
                if worst_preview:
                    details["affected_entry_preview"] = worst_preview

        findings.append(
            AuditFinding(
                rule_id="P046",
                severity=Severity.WARNING,
                page=page_num,
                message=(
                    f"{label} entry numbers do not appear to be aligned in a consistent "
                    f"left column, as required by NJIT guidelines ({_SOURCE_Q_RULE[section]})."
                ),
                details=details,
            )
        )

    return findings
