"""Conservative LoT/LoF entry-number ordering check (P059).

Heuristic PDF coverage for Q063/Q072:
  - Q063: "Is the word 'Table' … left-aligned in a separate column?"
    (correct column order implies sequential entry numbering)
  - Q072: "Is the word 'Figure' … left-aligned in a separate column?"
    (same)

Emits a WARNING when a List of Tables or List of Figures page contains
complete entries whose entry numbers (the numeric token following the
"Table"/"Figure" label) are not in non-decreasing order.

Conservative gates:
  - At least 3 entries with parseable entry numbers
  - At least 2 inversions before flagging
  - Mixed sequential + chapter-based format pages are skipped
  - Appendix/letter-prefixed entries skipped
  - TOC pages excluded

Findings contain only structural metadata — no entry text, titles, or captions.
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

_SECTION_CONFIG = {
    "list_of_tables": ("lot_entry_numbers_not_nondecreasing", "Q063"),
    "list_of_figures": ("lof_entry_numbers_not_nondecreasing", "Q072"),
}

_LETTER_PREFIX_RE = re.compile(r"^(?:table|figure)\s+[a-zA-Z]", re.IGNORECASE)
_CHAPTER_NUM_RE = re.compile(r"^(?:table|figure)\s+(\d+)\.(\d+)\b", re.IGNORECASE)
_SEQ_NUM_RE = re.compile(r"^(?:table|figure)\s+(\d+)(?:\s|$)", re.IGNORECASE)


def _parse_entry_num(cleaned_text: str) -> tuple[int, ...] | None:
    """Parse entry number from LoT/LoF entry text.

    Returns:
        (N,) for sequential entries (e.g., "Table 3 ..." → (3,))
        (C, N) for chapter-based entries (e.g., "Table 1.2 ..." → (1, 2))
        None for appendix/letter-prefixed entries or when unparseable
    """
    text = cleaned_text.strip()
    if _LETTER_PREFIX_RE.match(text):
        return None
    m = _CHAPTER_NUM_RE.match(text)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = _SEQ_NUM_RE.match(text)
    if m:
        return (int(m.group(1)),)
    return None


def _check_ordering(
    context: TocPageContext,
    entries: list[TocEntryLine],
    issue_type: str,
    section_type: str,
    source_q_rule_id: str,
) -> list[AuditFinding]:
    comparable: list[tuple[int, ...]] = []
    seq_count = 0
    chapter_count = 0

    for entry in entries:
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        num = _parse_entry_num(entry.cleaned_text)
        if num is None:
            continue
        if len(num) == 1:
            seq_count += 1
        else:
            chapter_count += 1
        comparable.append(num)

    # Skip mixed-format pages (P056 scope)
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

    return [
        AuditFinding(
            rule_id="P059",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                f"List entry numbers are not in non-decreasing order: "
                f"{inversions} inversion(s) among {len(comparable)} comparable entries. "
                "NJIT guidelines imply entries should be ordered."
            ),
            details={
                "issue_type": issue_type,
                "page": str(context.page.page_number),
                "section_type": section_type,
                "entry_count": str(len(comparable)),
                "comparable_entry_number_count": str(len(comparable)),
                "inversion_count": str(inversions),
                "first_inversion_index": str(first_inversion_index),
                "triage_tier": "medium",
                "source_q_rule_id": source_q_rule_id,
            },
        )
    ]


def check_pdf_lot_lof_entry_number_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P059 warnings for LoT/LoF entry-number ordering violations."""
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
