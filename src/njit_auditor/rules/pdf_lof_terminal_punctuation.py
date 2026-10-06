"""Conservative List of Figures entry terminal punctuation checks (P040).

Partial heuristic PDF coverage for Q075:
  - Q075: Does every figure description end with a terminal punctuation mark?

List of Figures pages only. TOC and LoT are excluded.
Does not duplicate P024 (LoT and LoF title case), P018 (alignment),
P032 (wrap spacing), P036 (inter-entry spacing), or P039 (TOC indentation hierarchy).
"""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_lot_lof_page_number_alignment import RIGHT_EDGE_TOLERANCE_PT
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
    has_trailing_page_number_token,
)

MIN_ENTRY_TEXT_LEN = 10

_DOT_LEADER_CHARS = ".…·"
_LOF_PREFIX_RE = re.compile(
    r"^(?:fig(?:ure)?\.?)\s+[0-9]+(?:[.\-][0-9]+)?\s*[.):]?\s*",
    re.IGNORECASE,
)
_TERMINAL_PUNCT_RE = re.compile(r"[.?!]\s*$")


def _dot_leader_weight(text: str) -> int:
    """Return visible dot weight for a candidate dot-leader fragment."""

    return sum(3 if char == "…" else 1 for char in text if char in _DOT_LEADER_CHARS)


def _strip_trailing_lof_dot_leaders(text: str) -> str:
    """Strip visual LoF dot leaders while preserving terminal punctuation.

    R040 is the List of Figures counterpart to P053/P054, but its semantics
    are reversed: a terminal dot immediately before a visual leader run is the
    required punctuation, not a violation. PDF extraction often attaches that
    dot to Unicode/ASCII leader fragments, so this helper removes the leader
    suffix while preserving one leading period from the suffix when that
    period touches the title or is set apart from a different leader glyph.
    The first dot of a gap-separated, uniform ASCII leader run is not
    punctuation.
    """

    stripped = text.rstrip()
    suffix_start = len(stripped)
    while suffix_start > 0 and stripped[suffix_start - 1] in _DOT_LEADER_CHARS + " ":
        suffix_start -= 1

    suffix = stripped[suffix_start:]
    if _dot_leader_weight(suffix) < 2:
        return stripped.strip()

    prefix = stripped[:suffix_start].rstrip()
    if _TERMINAL_PUNCT_RE.search(prefix):
        return prefix

    leader = suffix.lstrip()
    # A period touching the title text is the title's terminal punctuation,
    # whatever leader run follows it ("title. . . ." or "title.……").
    if suffix.startswith(".") and _dot_leader_weight(leader[1:]) >= 1:
        return f"{prefix}.".strip()
    # After a gap, the first dot of a uniform ASCII leader run is only a
    # leader ("title (2.6) . . . . 30"); Ester confirmed that pattern lacks
    # terminal punctuation (2026-10-05). A lone ASCII period followed by a
    # different leader glyph ("title .……") is still the title's own period,
    # set off by a stray space; that gap is leader placement (P018S), not R040.
    following = leader[1:].lstrip()
    if (
        leader.startswith(".")
        and following[:1] in ("…", "·")
        and _dot_leader_weight(following) >= 2
    ):
        return f"{prefix}.".strip()

    return prefix.strip()


def _extract_description(entry: TocEntryLine) -> str | None:
    """Return figure description text stripped of page number, leaders, and prefix."""
    text = entry.cleaned_text
    if entry.page_number_token:
        stripped = text.rstrip()
        if stripped.endswith(entry.page_number_token):
            stripped = stripped[: -len(entry.page_number_token)].rstrip()
        text = stripped
    text = _strip_trailing_lof_dot_leaders(text)
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
    page_edges = [
        entry.page_number_right_x
        for entry in entries
        if entry.page_number_token is not None and entry.page_number_right_x is not None
    ]
    # A wrapped title can have a real page number in the right column even
    # when the row reconstructor omits it from cleaned_text. The page-wide
    # median remains a useful column anchor in that case; an embedded number
    # inside a description is an outlier and cannot establish the anchor.
    expected_page_edge = median(page_edges) if len(page_edges) >= 3 else None
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        if not has_trailing_page_number_token(entry):
            # PDF row reconstruction can omit a real, visually aligned page
            # number from cleaned_text. Keep that case, but reject a digit
            # mistaken for a page number inside a wrapped description.
            if (
                expected_page_edge is None
                or entry.page_number_right_x is None
                or abs(entry.page_number_right_x - expected_page_edge)
                > RIGHT_EDGE_TOLERANCE_PT
            ):
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
                    "NJIT guidelines."
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
        entries = extract_toc_logical_entry_lines(context)
        if not entries:
            continue
        page_findings = _check_lof_terminal_punctuation_page(context, entries, entry_offset)
        findings.extend(page_findings)
        entry_offset += len(entries)
    return findings
