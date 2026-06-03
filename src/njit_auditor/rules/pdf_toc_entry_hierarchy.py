"""Conservative TOC level indentation hierarchy checks (P039).

Partial heuristic PDF coverage for Q056:
  - Q056: Are level-2 and level-3 entries indented to show hierarchy?

TABLE OF CONTENTS pages only. LoT and LoF are excluded.
Does not duplicate P018 (alignment), P024 (capitalization), P032 (wrap spacing),
P036 (inter-entry spacing), or P030 (continued headings).
"""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_HIERARCHY_INDENT_PT = 6.0
MIN_CHILD_ENTRIES_TO_CHECK = 2
MIN_TOTAL_ENTRIES = 3

_CHAPTER_RE = re.compile(r"^(?:chapter|appendix)\b", re.IGNORECASE)
_LEVEL2_NUM_RE = re.compile(r"^[0-9]+\.[0-9]+(?:\s|$)")
_LEVEL3_NUM_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+")


def _classify_entry_level(text: str) -> int | None:
    """Return 1, 2, or 3 for confident level matches; None for ambiguous entries."""
    if _LEVEL3_NUM_RE.match(text):
        return 3
    if _LEVEL2_NUM_RE.match(text):
        return 2
    if _CHAPTER_RE.match(text):
        return 1
    return None


def _triage_tier(delta: float) -> str:
    if delta <= 0:
        return "high"
    if delta < MIN_HIERARCHY_INDENT_PT:
        return "medium"
    return "low"


def _check_toc_hierarchy_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    l1_indents: list[float] = []
    l2_indents: list[float] = []
    l3_indents: list[float] = []

    for entry in entries:
        level = _classify_entry_level(entry.cleaned_text)
        if level == 1:
            l1_indents.append(entry.indent_x)
        elif level == 2:
            l2_indents.append(entry.indent_x)
        elif level == 3:
            l3_indents.append(entry.indent_x)

    if l1_indents and len(l2_indents) >= MIN_CHILD_ENTRIES_TO_CHECK:
        l1_med = median(l1_indents)
        l2_med = median(l2_indents)
        delta = l2_med - l1_med
        if delta < MIN_HIERARCHY_INDENT_PT:
            findings.append(
                AuditFinding(
                    rule_id="P039",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "TOC level-2 entries do not appear to be indented relative to "
                        "level-1 entries, which is required for visual hierarchy (Q056)."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "issue_type": "toc_l2_not_indented_relative_to_l1",
                        "level": "2",
                        "parent_level": "1",
                        "observed_delta_points": f"{delta:.1f}",
                        "required_delta_points": f"{MIN_HIERARCHY_INDENT_PT:.1f}",
                        "l1_entry_count": str(len(l1_indents)),
                        "l2_entry_count": str(len(l2_indents)),
                        "triage_tier": _triage_tier(delta),
                        "source_q_rule_id": "Q056",
                    },
                )
            )

    if l2_indents and len(l3_indents) >= MIN_CHILD_ENTRIES_TO_CHECK:
        l2_med = median(l2_indents)
        l3_med = median(l3_indents)
        delta = l3_med - l2_med
        if delta < MIN_HIERARCHY_INDENT_PT:
            findings.append(
                AuditFinding(
                    rule_id="P039",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "TOC level-3 entries do not appear to be indented relative to "
                        "level-2 entries, which is required for visual hierarchy (Q056)."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "issue_type": "toc_l3_not_indented_relative_to_l2",
                        "level": "3",
                        "parent_level": "2",
                        "observed_delta_points": f"{delta:.1f}",
                        "required_delta_points": f"{MIN_HIERARCHY_INDENT_PT:.1f}",
                        "l2_entry_count": str(len(l2_indents)),
                        "l3_entry_count": str(len(l3_indents)),
                        "triage_tier": _triage_tier(delta),
                        "source_q_rule_id": "Q056",
                    },
                )
            )

    return findings


def check_pdf_toc_entry_hierarchy(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P039 warnings for TOC pages lacking visual level indentation hierarchy."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_entry_lines(context)
        if len(entries) < MIN_TOTAL_ENTRIES:
            continue
        findings.extend(_check_toc_hierarchy_page(context, entries))
    return findings
