"""Conservative TOC page-number ordering check (P058).

Warns when TABLE OF CONTENTS body entries have page numbers that are not
in non-decreasing order.  Front-matter entries using Roman-numeral page
tokens are excluded (non-integer parse returns None); only entries with
positive-integer page numbers are compared.

Conservative gates:
  - At least 3 entries with comparable integer page numbers
  - At least 2 inversions before flagging
  - Entries with non-integer page tokens skipped
  - LoT and LoF pages excluded; TABLE OF CONTENTS only

Findings contain only structural metadata — no entry text, titles, or
chapter/section headings.
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

_SOURCE_Q_RULE_ID = "Q057"


def _parse_page_num(token: str) -> int | None:
    s = token.strip()
    if s.isdigit():
        n = int(s)
        return n if n > 0 else None
    return None


def _check_toc_ordering(
    context: TocPageContext,
    entries: list[TocEntryLine],
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
            rule_id="P058",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                f"Table of Contents entry page numbers are not in non-decreasing order: "
                f"{inversions} inversion(s) among {len(comparable)} comparable entries. "
                f"NJIT guidelines imply TOC entries should be ordered by page."
            ),
            details={
                "issue_type": "toc_page_numbers_not_nondecreasing",
                "page": str(context.page.page_number),
                "section_type": "table_of_contents",
                "entry_count": str(len(comparable)),
                "comparable_page_number_count": str(len(comparable)),
                "inversion_count": str(inversions),
                "first_inversion_index": str(first_inversion_index),
                "triage_tier": "medium",
                "source_q_rule_id": _SOURCE_Q_RULE_ID,
            },
        )
    ]


def check_pdf_toc_page_number_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P058 warnings for TOC page-number ordering violations."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_entry_lines(context)
        findings.extend(_check_toc_ordering(context, entries))
    return findings
