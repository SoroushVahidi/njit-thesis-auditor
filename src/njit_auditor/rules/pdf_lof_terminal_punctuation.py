"""Conservative List of Figures entry terminal punctuation checks (P040).

Partial heuristic PDF coverage for Q075:
  - Q075: Does every figure description end with a terminal punctuation mark?

List of Figures pages only. TOC and LoT are excluded.
Does not duplicate P024 (LoF sentence case, LoT capitalization), P018 (alignment),
P032 (wrap spacing), P036 (inter-entry spacing), or P039 (TOC indentation hierarchy).
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_ENTRY_TEXT_LEN = 10

_LEADER_STRIP_RE = re.compile(r"\s*(?:\.\s*){2,}$")
_LOF_PREFIX_RE = re.compile(
    r"^(?:fig(?:ure)?\.?)\s+[0-9]+(?:[.\-][0-9]+)?\s*[.):]?\s*",
    re.IGNORECASE,
)
_TERMINAL_PUNCT_RE = re.compile(r"[.?!]\s*$")


def _extract_description(entry: TocEntryLine) -> str | None:
    """Return figure description text stripped of page number, leaders, and prefix."""
    text = entry.cleaned_text
    if entry.page_number_token:
        stripped = text.rstrip()
        if stripped.endswith(entry.page_number_token):
            stripped = stripped[: -len(entry.page_number_token)].rstrip()
        text = stripped
    text = _LEADER_STRIP_RE.sub("", text).strip()
    match = _LOF_PREFIX_RE.match(text)
    if match:
        text = text[match.end() :].strip()
    return text if len(text) >= MIN_ENTRY_TEXT_LEN else None


def _check_lof_terminal_punctuation_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        description = _extract_description(entry)
        if description is None:
            continue
        if _TERMINAL_PUNCT_RE.search(description):
            continue
        details = {
            "page_number": str(context.page.page_number),
            "page_type": "list_of_figures",
            "issue_type": "lof_entry_missing_terminal_punctuation",
            # Document-global index (kept for existing internal dedup/
            # grouping consumers that expect a monotonic value across a
            # multi-page List of Figures).
            "entry_index": str(page_entry_offset + idx),
            # Page-relative index for display: "(entry #N)" must count
            # only what is visible on *this* page, or a List of
            # Figures continuation page can be labeled with an entry
            # number higher than the number of entries actually shown
            # on that page.
            "page_entry_index": str(idx),
            "line_y": f"{entry.line.bbox.y0:.1f}",
            "bbox": format_bbox_detail(entry.line.bbox),
            "terminal_punctuation_required": "., ?, or !",
            "triage_tier": "medium",
            "source_q_rule_id": "Q075",
        }
        findings.append(
            AuditFinding(
                rule_id="P040",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "List of Figures entry does not end with terminal punctuation "
                    "(period, question mark, or exclamation point) as required by "
                    "NJIT guidelines (Q075)."
                ),
                details=details,
            )
        )
    return findings


def check_pdf_lof_terminal_punctuation(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P040 warnings for LoF entries lacking terminal punctuation."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "list_of_figures":
            continue
        entries = extract_toc_entry_lines(context)
        if len(entries) < 2:
            continue
        page_findings = _check_lof_terminal_punctuation_page(context, entries, entry_offset)
        findings.extend(page_findings)
        entry_offset += len(entries)
    return findings
