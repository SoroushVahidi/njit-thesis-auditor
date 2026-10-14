"""Conservative List of Tables / List of Figures cross-type entry checks (P055).

Heuristic PDF coverage for Q063/Q072:
  - Q063: LIST OF TABLES column header is "Table" — entries should be table entries.
  - Q072: LIST OF FIGURES column header is "Figure" — entries should be figure entries.

Emits an advisory when:
  - A List of Tables entry starts with "Figure" (lot_entry_is_figure) or
    is numeric-only (lot_entry_missing_table_prefix).
  - A List of Figures entry starts with "Table" (lof_entry_is_table) or
    is numeric-only (lof_entry_missing_figure_prefix).

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
    extract_toc_logical_entry_lines,
)

MIN_ENTRY_TEXT_LEN = 10

_FIGURE_PREFIX_RE = re.compile(
    r"^figure\s+([0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)", re.IGNORECASE
)
_TABLE_PREFIX_RE = re.compile(
    r"^table\s+([0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)", re.IGNORECASE
)
_NUMERIC_PREFIX_RE = re.compile(
    r"^(?:\d+(?:[.\-]\d+)*(?=\s|[.):]|(?-i:[A-Z])|$)|[ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*(?=\s|[.):]|$))",
    re.IGNORECASE,
)


def _check_lot_entry_type_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        text = entry.cleaned_text.strip()
        if len(text) < MIN_ENTRY_TEXT_LEN:
            continue

        if _FIGURE_PREFIX_RE.match(text):
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
        elif _NUMERIC_PREFIX_RE.match(text):
            findings.append(
                AuditFinding(
                    rule_id="P055",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Tables entry is missing the required 'Table' prefix. "
                        "NJIT guidelines require that each entry in the List of Tables "
                        "begin with the word 'Table'."
                    ),
                    details={
                        "issue_type": "lot_entry_missing_table_prefix",
                        "page": str(context.page.page_number),
                        "section_type": "list_of_tables",
                        "entry_index": str(page_entry_offset + idx),
                        "observed_entry_type": "numeric_only",
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
        text = entry.cleaned_text.strip()
        if len(text) < MIN_ENTRY_TEXT_LEN:
            continue

        if _TABLE_PREFIX_RE.match(text):
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
        elif _NUMERIC_PREFIX_RE.match(text):
            findings.append(
                AuditFinding(
                    rule_id="P055",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Figures entry is missing the required 'Figure' prefix. "
                        "NJIT guidelines require that each entry in the List of Figures "
                        "begin with the word 'Figure'."
                    ),
                    details={
                        "issue_type": "lof_entry_missing_figure_prefix",
                        "page": str(context.page.page_number),
                        "section_type": "list_of_figures",
                        "entry_index": str(page_entry_offset + idx),
                        "observed_entry_type": "numeric_only",
                        "expected_entry_type": "figure",
                        "page_number_token_present": "true",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q072",
                    },
                )
            )
    return findings


def check_pdf_lot_lof_entry_type(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P055 warnings for cross-type or missing prefix LoT/LoF entries."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type == "list_of_tables":
            entries = extract_toc_logical_entry_lines(context, require_right_edge=True)
            if len(entries) >= 2:
                findings.extend(
                    _check_lot_entry_type_page(context, entries, entry_offset)
                )
            entry_offset += len(entries)
        elif context.page_type == "list_of_figures":
            entries = extract_toc_logical_entry_lines(context, require_right_edge=True)
            if len(entries) >= 2:
                findings.extend(
                    _check_lof_entry_type_page(context, entries, entry_offset)
                )
            entry_offset += len(entries)
    return findings
