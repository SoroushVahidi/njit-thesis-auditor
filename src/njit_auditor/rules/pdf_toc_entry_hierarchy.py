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
from njit_auditor.pdf_models import BBox, PdfDocument, format_bbox_detail
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


def _offending_geometry(children: list[TocEntryLine], parent_median: float) -> dict[str, str]:
    """Highlight the child entries that are not indented past the parent level.

    Returns the union ``bbox`` plus one ``highlight_bboxes`` box per offending
    entry line, so the student sees which entries need more indentation
    instead of an unhighlighted page-level note.
    """
    offending = [
        entry.line.bbox
        for entry in children
        if entry.indent_x - parent_median < MIN_HIERARCHY_INDENT_PT
    ]
    if not offending:
        return {}
    union = BBox(
        x0=min(b.x0 for b in offending),
        y0=min(b.y0 for b in offending),
        x1=max(b.x1 for b in offending),
        y1=max(b.y1 for b in offending),
    )
    return {
        "bbox": format_bbox_detail(union),
        "highlight_bboxes": " | ".join(format_bbox_detail(b) for b in offending),
        "offending_entry_count": str(len(offending)),
    }


def _check_toc_hierarchy_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    by_level: dict[int, list[TocEntryLine]] = {1: [], 2: [], 3: []}
    for entry in entries:
        level = _classify_entry_level(entry.cleaned_text)
        if level is not None:
            by_level[level].append(entry)
    l1_indents = [entry.indent_x for entry in by_level[1]]
    l2_indents = [entry.indent_x for entry in by_level[2]]
    l3_indents = [entry.indent_x for entry in by_level[3]]

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
                        "level-1 entries, which is required for visual hierarchy."
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
                        "confidence": "medium",
                        "confidence_reason": "numbered_levels_with_measured_indentation_heuristic",
                        "source_q_rule_id": "Q056",
                        **_offending_geometry(by_level[2], l1_med),
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
                        "level-2 entries, which is required for visual hierarchy."
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
                        "confidence": "medium",
                        "confidence_reason": "numbered_levels_with_measured_indentation_heuristic",
                        "source_q_rule_id": "Q056",
                        **_offending_geometry(by_level[3], l2_med),
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
