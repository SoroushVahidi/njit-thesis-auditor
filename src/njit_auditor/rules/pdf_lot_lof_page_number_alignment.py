"""Heuristic LoT/LoF page-number right-column alignment checks."""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_ENTRIES = 3
RIGHT_EDGE_TOLERANCE_PT = 10.0

_VALID_ROMAN_PAGE_NUMBER_RE = re.compile(
    r"^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$",
    re.IGNORECASE,
)

_SECTION_LABELS = {
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}
_ISSUE_TYPE = {
    "list_of_tables": "lot_page_number_column_misaligned",
    "list_of_figures": "lof_page_number_column_misaligned",
}
_SOURCE_Q_RULE = {
    "list_of_tables": "Q069",
    "list_of_figures": "Q079",
}


def _complete_entries(entries: list[TocEntryLine]) -> list[TocEntryLine]:
    """Return entries with confident trailing page-number geometry."""

    return [
        entry
        for entry in entries
        if entry.page_number_right_x is not None
        and (
            entry.page_number_token is None
            or entry.page_number_token.isdigit()
            or _VALID_ROMAN_PAGE_NUMBER_RE.fullmatch(entry.page_number_token)
        )
    ]


def check_pdf_lot_lof_page_number_alignment(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P048 warnings for strong LoT/LoF page-number column misalignment."""

    findings: list[AuditFinding] = []
    right_edges_by_section: dict[str, list[tuple[int, float]]] = {
        "list_of_tables": [],
        "list_of_figures": [],
    }
    first_page_by_section: dict[str, int] = {}

    for context in detect_toc_like_pages(pdf_document):
        section = context.page_type
        if section not in _SECTION_LABELS:
            continue

        complete_entries = _complete_entries(extract_toc_entry_lines(context))
        if len(complete_entries) < MIN_ENTRIES:
            continue

        first_page_by_section.setdefault(section, context.page.page_number)
        for entry_index, entry in enumerate(complete_entries, start=1):
            if entry.page_number_right_x is None:
                continue
            right_edges_by_section[section].append((entry_index, entry.page_number_right_x))

    for section, indexed_right_edges in right_edges_by_section.items():
        if len(indexed_right_edges) < MIN_ENTRIES:
            continue

        right_edges = [right_edge for _, right_edge in indexed_right_edges]
        expected_edge = median(right_edges)
        deltas = [abs(right_edge - expected_edge) for right_edge in right_edges]
        worst_delta = max(deltas)
        if worst_delta <= RIGHT_EDGE_TOLERANCE_PT:
            continue

        worst_idx = deltas.index(worst_delta)
        entry_index, observed_edge = indexed_right_edges[worst_idx]
        page_num = first_page_by_section.get(section, 0)
        label = _SECTION_LABELS[section]

        findings.append(
            AuditFinding(
                rule_id="P048",
                severity=Severity.WARNING,
                page=page_num,
                message=(
                    f"{label} page numbers do not appear to be aligned in a "
                    f"consistent right column, as required by NJIT guidelines "
                    f"({_SOURCE_Q_RULE[section]})."
                ),
                details={
                    "page_number": str(page_num),
                    "issue_type": _ISSUE_TYPE[section],
                    "section_type": section,
                    "entry_index": str(entry_index),
                    "observed_page_number_x": f"{observed_edge:.1f}",
                    "expected_page_number_x": f"{expected_edge:.1f}",
                    "x_delta_points": f"{worst_delta:.1f}",
                    "allowed_delta_points": f"{RIGHT_EDGE_TOLERANCE_PT:.1f}",
                    "entry_count": str(len(indexed_right_edges)),
                    "triage_tier": "low",
                    "source_q_rule_id": _SOURCE_Q_RULE[section],
                },
            )
        )

    return findings
