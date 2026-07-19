"""Conservative LoT/LoF page-number ordering check (P057).

Heuristic PDF coverage for Q069/Q079:
  - Q069: "Are all table page numbers aligned vertically in one right column?"
  - Q079: "Are all figure page numbers aligned vertically in one right column?"

Emits a WARNING when a List of Tables or List of Figures page contains
complete entries whose listed page numbers are not in non-decreasing order.

Conservative gates:
  - At least 3 entries with comparable integer page numbers
  - At least 2 inversions before flagging
  - Entries with non-integer or non-positive page tokens skipped
  - TOC pages excluded

Findings contain only structural metadata — no entry text, titles, or captions.
"""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_ENTRY_TEXT_LEN = 10
MIN_COMPARABLE_ENTRIES = 3
MIN_INVERSIONS_TO_FLAG = 2

_SECTION_CONFIG = {
    "list_of_tables": ("lot_page_numbers_not_nondecreasing", "Q069"),
    "list_of_figures": ("lof_page_numbers_not_nondecreasing", "Q079"),
}


def _parse_page_num(token: str) -> int | None:
    s = token.strip()
    if s.isdigit():
        n = int(s)
        return n if n > 0 else None
    return None


def _check_ordering(
    context: TocPageContext,
    entries: list[TocEntryLine],
    issue_type: str,
    section_type: str,
    source_q_rule_id: str,
) -> list[AuditFinding]:
    comparable: list[int] = []
    for entry in entries:
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        n = _parse_page_num(entry.page_number_token)
        if n is not None:
            comparable.append(n)

    if len(comparable) < MIN_COMPARABLE_ENTRIES:
        return []

    inversions = 0
    first_inversion_index: int | None = None
    for i in range(len(comparable) - 1):
        if comparable[i] > comparable[i + 1]:
            if first_inversion_index is None:
                first_inversion_index = i
            inversions += 1

    if inversions < MIN_INVERSIONS_TO_FLAG:
        return []

    return [
        AuditFinding(
            rule_id="P057",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                f"List entry page numbers are not in non-decreasing order: "
                f"{inversions} inversion(s) among {len(comparable)} comparable entries. "
                "NJIT guidelines imply entries should be ordered by page."
            ),
            details={
                "issue_type": issue_type,
                "page": str(context.page.page_number),
                "section_type": section_type,
                "entry_count": str(len(comparable)),
                "comparable_page_number_count": str(len(comparable)),
                "inversion_count": str(inversions),
                "first_inversion_index": str(first_inversion_index),
                "triage_tier": "medium",
                "source_q_rule_id": source_q_rule_id,
            },
        )
    ]


def check_pdf_lot_lof_page_number_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P057 warnings for LoT/LoF page-number ordering violations."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        config = _SECTION_CONFIG.get(context.page_type)
        if config is None:
            continue
        issue_type, source_q_rule_id = config
        entries = extract_toc_entry_lines(context)
        findings.extend(
            _check_ordering(
                context,
                entries,
                issue_type=issue_type,
                section_type=context.page_type,
                source_q_rule_id=source_q_rule_id,
            )
        )
    return findings
