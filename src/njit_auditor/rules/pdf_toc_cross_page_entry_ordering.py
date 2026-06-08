"""Conservative TOC cross-page section-number ordering check (P062).

Heuristic PDF coverage for Q056/Q057 (cross-page extension):
  - Q056: level-2/3 entries indented to show hierarchy implies sequential
    section numbering across all TOC pages
  - Q057: double spacing between consecutive section-title entries implies
    all entries are ordered across the full TOC section

Emits a WARNING when the TABLE OF CONTENTS spans multiple consecutive pages
and the combined section-number sequence across those pages is not in
non-decreasing order.

Companion to P060 (within-page TOC ordering) and P061 (cross-page LoT/LoF).
Conservative gates:
  - At least 2 consecutive TABLE OF CONTENTS pages with comparable entries
  - At least 3 total comparable entries across all pages of the section
  - At least 2 inversions in the combined sequence before flagging
  - Word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) skipped
  - Entries without page_number_token (wrapped continuation lines) skipped
  - LoT and LoF pages excluded; TABLE OF CONTENTS only

Findings contain only structural metadata — no entry text, chapter/section
titles, or dissertation content.
"""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import (
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    MIN_COMPARABLE_ENTRIES,
    MIN_ENTRY_TEXT_LEN,
    MIN_INVERSIONS_TO_FLAG,
    _parse_section_num,
)

_ISSUE_TYPE = "toc_cross_page_entry_numbers_not_nondecreasing"
_SOURCE_Q_RULE_ID = "Q056"


def _collect_comparable_entries(
    contexts: list[TocPageContext],
) -> list[tuple[int, ...]]:
    """Collect all parseable section numbers from a run of TOC pages in order."""
    comparable: list[tuple[int, ...]] = []
    for context in contexts:
        for entry in extract_toc_entry_lines(context):
            if entry.page_number_token is None:
                continue
            if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
                continue
            num = _parse_section_num(entry.cleaned_text)
            if num is None:
                continue
            comparable.append(num)
    return comparable


def _group_consecutive_toc_runs(
    contexts: list[TocPageContext],
) -> list[list[TocPageContext]]:
    """Group consecutive TABLE OF CONTENTS pages into runs."""
    toc_pages = sorted(
        (ctx for ctx in contexts if ctx.page_type == "table_of_contents"),
        key=lambda ctx: ctx.page.page_number,
    )
    runs: list[list[TocPageContext]] = []
    current: list[TocPageContext] = []
    for ctx in toc_pages:
        page_number = ctx.page.page_number
        if not current or page_number == current[-1].page.page_number + 1:
            current.append(ctx)
        else:
            if current:
                runs.append(current)
            current = [ctx]
    if current:
        runs.append(current)
    return runs


def _check_cross_page_toc_run(
    run: list[TocPageContext],
) -> list[AuditFinding]:
    """Check ordering across a multi-page TOC run; return findings."""
    if len(run) < 2:
        return []

    comparable = _collect_comparable_entries(run)

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

    first_page = run[0].page.page_number
    return [
        AuditFinding(
            rule_id="P062",
            severity=Severity.WARNING,
            page=first_page,
            message=(
                f"Table of Contents section numbers are not in non-decreasing order "
                f"across {len(run)} consecutive pages: {inversions} inversion(s) among "
                f"{len(comparable)} comparable entries. NJIT guidelines "
                f"({_SOURCE_Q_RULE_ID}) imply TOC entries should be in sequential order "
                f"across the full Table of Contents."
            ),
            details={
                "issue_type": _ISSUE_TYPE,
                "page": str(first_page),
                "section_type": "table_of_contents",
                "page_count": str(len(run)),
                "entry_count": str(len(comparable)),
                "comparable_entry_number_count": str(len(comparable)),
                "inversion_count": str(inversions),
                "first_inversion_index": str(first_inversion_index),
                "triage_tier": "medium",
                "source_q_rule_id": _SOURCE_Q_RULE_ID,
            },
        )
    ]


def check_pdf_toc_cross_page_entry_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P062 warnings for cross-page TOC section-number ordering violations."""
    findings: list[AuditFinding] = []
    contexts = detect_toc_like_pages(pdf_document)
    for run in _group_consecutive_toc_runs(contexts):
        findings.extend(_check_cross_page_toc_run(run))
    return findings
