"""Conservative List of Tables / List of Figures numbering format consistency checks (P056).

Heuristic PDF coverage for Q063/Q072:
  - Q063: LIST OF TABLES column header is "Table" — entries should follow consistent conventions.
  - Q072: LIST OF FIGURES column header is "Figure" — same.

Emits an advisory when a LoT or LoF section contains a mix of:
  - chapter-based numbering (e.g., Table 1.2, Figure 3.1)
  - plain sequential numbering (e.g., Table 1, Figure 3)

Requires ≥ 2 confident entries of each format type before flagging.
TOC pages are excluded. Findings contain only structural metadata — no title text.
"""

from __future__ import annotations

import re
from collections import Counter

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_ENTRY_TEXT_LEN = 10
MIN_FORMAT_COUNT_TO_FLAG = 2

_ENTRY_NUM_RE = re.compile(
    r"^(?:table|figure)\s+(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
_LETTER_PREFIX_RE = re.compile(
    r"^(?:table|figure)\s+[a-zA-Z]",
    re.IGNORECASE,
)


def _classify_entry_number_format(cleaned_text: str) -> str | None:
    """Return 'chapter_based', 'sequential', or None for ambiguous/skip."""
    text = cleaned_text.strip()
    if _LETTER_PREFIX_RE.match(text):
        return None
    m = _ENTRY_NUM_RE.match(text)
    if not m:
        return None
    return "chapter_based" if "." in m.group(1) else "sequential"


def _check_page_number_format(
    context: TocPageContext,
    entries: list[TocEntryLine],
    issue_type: str,
    section_type: str,
    source_q_rule_id: str,
) -> list[AuditFinding]:
    format_counts: Counter[str] = Counter()
    total_complete = 0
    for entry in entries:
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        fmt = _classify_entry_number_format(entry.cleaned_text.strip())
        if fmt is not None:
            format_counts[fmt] += 1
            total_complete += 1

    chapter_count = format_counts["chapter_based"]
    sequential_count = format_counts["sequential"]

    if (
        chapter_count < MIN_FORMAT_COUNT_TO_FLAG
        or sequential_count < MIN_FORMAT_COUNT_TO_FLAG
    ):
        return []

    dominant = "chapter_based" if chapter_count >= sequential_count else "sequential"
    counts_str = f"chapter_based:{chapter_count},sequential:{sequential_count}"

    return [
        AuditFinding(
            rule_id="P056",
            severity=Severity.WARNING,
            page=context.page.page_number,
            message=(
                f"List entry numbering format is inconsistent: "
                f"{chapter_count} chapter-based (X.Y) and "
                f"{sequential_count} sequential (N) entries detected. "
                "NJIT guidelines imply a single consistent format."
            ),
            details={
                "issue_type": issue_type,
                "page": str(context.page.page_number),
                "section_type": section_type,
                "entry_count": str(total_complete),
                "format_counts": counts_str,
                "observed_formats": "chapter_based,sequential",
                "dominant_format": dominant,
                "triage_tier": "low",
                "source_q_rule_id": source_q_rule_id,
            },
        )
    ]


def check_pdf_lot_lof_number_format(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P056 warnings for mixed LoT/LoF entry numbering formats."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type == "list_of_tables":
            entries = extract_toc_entry_lines(context)
            if len(entries) >= 2:
                findings.extend(
                    _check_page_number_format(
                        context,
                        entries,
                        issue_type="lot_mixed_numbering_format",
                        section_type="list_of_tables",
                        source_q_rule_id="Q063",
                    )
                )
        elif context.page_type == "list_of_figures":
            entries = extract_toc_entry_lines(context)
            if len(entries) >= 2:
                findings.extend(
                    _check_page_number_format(
                        context,
                        entries,
                        issue_type="lof_mixed_numbering_format",
                        section_type="list_of_figures",
                        source_q_rule_id="Q072",
                    )
                )
    return findings
