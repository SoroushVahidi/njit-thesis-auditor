"""Conservative TOC section-number ordering check (P060).

Heuristic PDF coverage for Q056/Q057:
  - Q056: "Are level-2 and level-3 entries indented to show hierarchy?"
    (hierarchy implies sequential section numbering)
  - Q057: "Is there visible double spacing between consecutive section-title entries?"
    (sequential ordering is prerequisite for TOC validity)

Emits a WARNING when a TABLE OF CONTENTS page contains parseable numeric
section entries (entries starting with a bare number, e.g. "1 Introduction",
"1.1 Background", "2 Methods") whose section numbers are not in non-decreasing
order.

Conservative gates:
  - At least 3 entries with parseable section numbers
  - At least 2 inversions before flagging
  - Word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) skipped
  - Entries without page_number_token (wrapped continuation lines) skipped
  - LoT and LoF pages excluded; TABLE OF CONTENTS only

Findings contain only structural metadata — no entry text, chapter/section
titles, or dissertation content.
"""

from __future__ import annotations

import re

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

_SOURCE_Q_RULE_ID = "Q056"

_SECTION_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:\s|$)")


def _parse_section_num(cleaned_text: str) -> tuple[int, ...] | None:
    """Parse section number from TOC entry text.

    Returns:
        (N,) for top-level entries (e.g., "1 Introduction" → (1,))
        (N, M) for subsections (e.g., "1.1 Background" → (1, 1))
        (N, M, K) for deeper entries (e.g., "1.2.3 Detail" → (1, 2, 3))
        None for entries starting with a word (CHAPTER, ABSTRACT, APPENDIX, etc.)
        None for unparseable entries
    """
    text = cleaned_text.strip()
    m = _SECTION_NUM_RE.match(text)
    if not m:
        return None
    parts = m.group(1).split(".")
    return tuple(int(p) for p in parts)


def _check_toc_entry_ordering(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    comparable: list[tuple[int, ...]] = []

    for entry in entries:
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        num = _parse_section_num(entry.cleaned_text)
        if num is None:
            continue
        comparable.append(num)

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
            rule_id="P060",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                f"Table of Contents section numbers are not in non-decreasing order: "
                f"{inversions} inversion(s) among {len(comparable)} comparable entries. "
                f"NJIT guidelines ({_SOURCE_Q_RULE_ID}) imply TOC entries should be "
                f"in sequential order."
            ),
            details={
                "issue_type": "toc_entry_numbers_not_nondecreasing",
                "page": str(context.page.page_number),
                "section_type": "table_of_contents",
                "entry_count": str(len(comparable)),
                "comparable_entry_number_count": str(len(comparable)),
                "inversion_count": str(inversions),
                "first_inversion_index": str(first_inversion_index),
                "triage_tier": "medium",
                "source_q_rule_id": _SOURCE_Q_RULE_ID,
            },
        )
    ]


def check_pdf_toc_entry_number_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P060 warnings for TOC section-number ordering violations."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_entry_lines(context)
        findings.extend(_check_toc_entry_ordering(context, entries))
    return findings
