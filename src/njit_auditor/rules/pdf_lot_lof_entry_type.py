"""Conservative List of Tables / List of Figures cross-type entry checks (P055).

Heuristic PDF coverage for Q063/Q072:
  - Q063: LIST OF TABLES column header is "Table" — entries should be table entries.
  - Q072: LIST OF FIGURES column header is "Figure" — entries should be figure entries.

Emits an advisory when:
  - A complete List of Tables entry starts with "Figure" (lot_entry_is_figure).
  - A complete List of Figures entry starts with "Table" (lof_entry_is_table).

TOC pages are excluded. Findings contain only structural metadata — no title text.
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

_FIGURE_PREFIX_RE = re.compile(r"^figure\s+\d", re.IGNORECASE)
_TABLE_PREFIX_RE = re.compile(r"^table\s+\d", re.IGNORECASE)


def _get_entry_type_prefix(cleaned_text: str) -> str | None:
    """Return 'table', 'figure', or None for a clear type prefix at the start of an entry."""
    if _FIGURE_PREFIX_RE.match(cleaned_text):
        return "figure"
    if _TABLE_PREFIX_RE.match(cleaned_text):
        return "table"
    return None


def _check_lot_entry_type_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        prefix = _get_entry_type_prefix(entry.cleaned_text.strip())
        if prefix != "figure":
            continue
        findings.append(
            AuditFinding(
                rule_id="P055",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "List of Tables entry starts with 'Figure'. "
                    "NJIT guidelines require that the List of Tables "
                    "contain only table entries."
                ),
                details={
                    "issue_type": "lot_entry_is_figure",
                    "page": str(context.page.page_number),
                    "section_type": "list_of_tables",
                    "entry_index": str(page_entry_offset + idx),
                    "observed_entry_type": "figure",
                    "expected_entry_type": "table",
                    "page_number_token_present": "true",
                    "triage_tier": "medium",
                    "source_q_rule_id": "Q063",
                },
            )
        )
    return findings


def _check_lof_entry_type_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
            continue
        prefix = _get_entry_type_prefix(entry.cleaned_text.strip())
        if prefix != "table":
            continue
        findings.append(
            AuditFinding(
                rule_id="P055",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "List of Figures entry starts with 'Table'. "
                    "NJIT guidelines require that the List of Figures "
                    "contain only figure entries."
                ),
                details={
                    "issue_type": "lof_entry_is_table",
                    "page": str(context.page.page_number),
                    "section_type": "list_of_figures",
                    "entry_index": str(page_entry_offset + idx),
                    "observed_entry_type": "table",
                    "expected_entry_type": "figure",
                    "page_number_token_present": "true",
                    "triage_tier": "medium",
                    "source_q_rule_id": "Q072",
                },
            )
        )
    return findings


def check_pdf_lot_lof_entry_type(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P055 warnings for cross-type LoT/LoF entries."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type == "list_of_tables":
            entries = extract_toc_entry_lines(context)
            if len(entries) >= 2:
                findings.extend(
                    _check_lot_entry_type_page(context, entries, entry_offset)
                )
            entry_offset += len(entries)
        elif context.page_type == "list_of_figures":
            entries = extract_toc_entry_lines(context)
            if len(entries) >= 2:
                findings.extend(
                    _check_lof_entry_type_page(context, entries, entry_offset)
                )
            entry_offset += len(entries)
    return findings
