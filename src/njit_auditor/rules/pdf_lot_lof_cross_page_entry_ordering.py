"""Conservative LoT/LoF cross-page entry-number ordering check (P061).

Heuristic PDF coverage for Q063/Q072 (cross-page extension):
  - Q063: List of Tables entry numbering should be non-decreasing across pages
  - Q072: List of Figures entry numbering should be non-decreasing across pages

Emits a WARNING when consecutive same-type LoT or LoF pages span multiple pages
and the combined entry-number sequence across those pages is not non-decreasing.

Companion to P059 (within-page ordering). Conservative gates:
  - At least 2 consecutive pages in the same LoT or LoF run
  - At least 3 comparable entries across the combined run
  - At least 2 inversions in the combined sequence
  - Mixed sequential + chapter-based format runs skipped
  - Appendix/letter-prefixed entries skipped

Findings contain only structural metadata — no entry text, titles, or captions.
"""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_lot_lof_entry_number_ordering import (
    MIN_COMPARABLE_ENTRIES,
    MIN_ENTRY_TEXT_LEN,
    MIN_INVERSIONS_TO_FLAG,
    _parse_entry_num,
)
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

_SECTION_CONFIG = {
    "list_of_tables": (
        "lot_cross_page_entry_numbers_not_nondecreasing",
        "Q063",
    ),
    "list_of_figures": (
        "lof_cross_page_entry_numbers_not_nondecreasing",
        "Q072",
    ),
}


def _collect_comparable_entries(entries: list[TocEntryLine]) -> list[tuple[int, ...]]:
    comparable: list[tuple[int, ...]] = []
    for entry in entries:
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        num = _parse_entry_num(entry.cleaned_text)
        if num is None:
            continue
        comparable.append(num)
    return comparable


def _group_consecutive_runs(
    contexts: list[TocPageContext],
    section_type: str,
) -> list[list[TocPageContext]]:
    pages = sorted(
        (ctx for ctx in contexts if ctx.page_type == section_type),
        key=lambda ctx: ctx.page.page_number,
    )
    runs: list[list[TocPageContext]] = []
    current: list[TocPageContext] = []
    for ctx in pages:
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


def _check_cross_page_run(
    run: list[TocPageContext],
    issue_type: str,
    section_type: str,
    source_q_rule_id: str,
) -> list[AuditFinding]:
    if len(run) < 2:
        return []

    comparable: list[tuple[int, ...]] = []
    seq_count = 0
    chapter_count = 0
    for context in run:
        entries = extract_toc_entry_lines(context)
        for num in _collect_comparable_entries(entries):
            if len(num) == 1:
                seq_count += 1
            else:
                chapter_count += 1
            comparable.append(num)

    if seq_count > 0 and chapter_count > 0:
        return []

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
            rule_id="P061",
            severity=Severity.WARNING,
            page=first_page,
            message=(
                f"List entry numbers are not in non-decreasing order across "
                f"{len(run)} consecutive pages: {inversions} inversion(s) among "
                f"{len(comparable)} comparable entries. NJIT guidelines imply "
                "entries should be ordered across the full List section."
            ),
            details={
                "issue_type": issue_type,
                "page": str(first_page),
                "section_type": section_type,
                "page_count": str(len(run)),
                "entry_count": str(len(comparable)),
                "comparable_entry_number_count": str(len(comparable)),
                "inversion_count": str(inversions),
                "first_inversion_index": str(first_inversion_index),
                "triage_tier": "medium",
                "source_q_rule_id": source_q_rule_id,
            },
        )
    ]


def check_pdf_lot_lof_cross_page_entry_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P061 warnings for cross-page LoT/LoF entry-number ordering violations."""
    findings: list[AuditFinding] = []
    contexts = detect_toc_like_pages(pdf_document)
    for section_type, (issue_type, source_q_rule_id) in _SECTION_CONFIG.items():
        for run in _group_consecutive_runs(contexts, section_type):
            findings.extend(
                _check_cross_page_run(
                    run,
                    issue_type=issue_type,
                    section_type=section_type,
                    source_q_rule_id=source_q_rule_id,
                )
            )
    return findings
