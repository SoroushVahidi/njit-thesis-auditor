"""Conservative TOC entry terminal-period absence check (P054).

Partial heuristic PDF coverage for Q049/Q050/Q051:
  - Q049: TOC L1 entries (chapter headings) are all-caps with no terminal period.
  - Q050: TOC L2 entries use title case with no terminal period.
  - Q051: TOC L3 entries use sentence case with no terminal period.

Table of Contents pages only. LoT and LoF are excluded (handled by P053 and P040).
Does not duplicate P024 (TOC case/punctuation), P039 (hierarchy), P042 (appendix format),
P053 (LoT no terminal period), or P040 (LoF must have terminal punctuation).

P040 checks that LoF entries DO have terminal punctuation.
P053 checks that LoT entries do NOT have a terminal period.
P054 checks that TOC entries do NOT have a terminal period (symmetric to P053 for TOC pages).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    LEADER_GAP_JITTER_EM,
    LEADER_GRID_MAX_SPREAD_PT,
    LEADER_GRID_MIN_ROWS,
    SAME_BASELINE_Y_TOLERANCE_PT,
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
    is_isolated_terminal_grid_leader_dot,
)
from njit_auditor.toc_entry_geometry import MIN_LEADER_DOT_WEIGHT, Glyph, row_glyphs

MIN_ENTRY_TEXT_LEN = 10

_LEADER_STRIP_RE = re.compile(r"\s*(?:(?:\.\s*){2,}|[-–—_]{2,})$")
_DOT_LEADER_CHARS = ".…·"
_SEPARATED_DOT_LEADER_RE = re.compile(r"\s+[.…·][.…·\s]*$")
_ATTACHED_DOT_LEADER_RE = re.compile(r"[.…·]+$")
_MIXED_DOT_SUFFIX_RE = re.compile(r"(?<=[^\s.…·])\.(?=\s*[.…·][.…·\s]*$)")
_TERMINAL_PERIOD_RE = re.compile(r"\.\s*$")


def _dot_leader_weight(text: str) -> int:
    """Return visible dot weight for a candidate dot-leader fragment."""

    return sum(3 if char == "…" else 1 for char in text if char in _DOT_LEADER_CHARS)


def _strip_trailing_leaders(text: str) -> str:
    """Strip visual leaders while preserving isolated title punctuation."""

    stripped = text.rstrip()
    while True:
        legacy_stripped = _LEADER_STRIP_RE.sub("", stripped).strip()
        if legacy_stripped != stripped:
            stripped = legacy_stripped
            continue

        separated = _SEPARATED_DOT_LEADER_RE.search(stripped)
        if separated is not None and _dot_leader_weight(separated.group()) >= 2:
            stripped = stripped[: separated.start()].rstrip()
            continue

        attached = _ATTACHED_DOT_LEADER_RE.search(stripped)
        if attached is not None and _dot_leader_weight(attached.group()) >= 2:
            stripped = stripped[: attached.start()].rstrip()
            continue

        break

    return stripped.strip()


def _without_folio(text: str, folio: str | None) -> str:
    text = text.rstrip()
    if folio and text.endswith(folio):
        return text[:-len(folio)].rstrip()
    return text


def _extract_toc_entry_text(entry: TocEntryLine) -> str | None:
    """Return entry text stripped of page number and leaders."""
    text = _strip_trailing_leaders(_without_folio(entry.cleaned_text, entry.page_number_token))
    return text if len(text) >= MIN_ENTRY_TEXT_LEN else None


@dataclass(frozen=True)
class _PeriodBeforeLeader:
    bbox: BBox
    period_x: float | None
    leader_x: float


def _final_title_row(entry: TocEntryLine) -> PdfTextLine:
    # The folio row normally holds the last visual title line. An auxiliary
    # folio fragment can hold only dots and a number, so use the title line
    # in that case.
    row = entry.page_number_line
    if row is not None and any(
        c.isalpha() for c in _without_folio(row.text, entry.page_number_token)
    ):
        return row
    return entry.line


def _title_glyphs(row: PdfTextLine, folio: str | None) -> tuple[list[Glyph], list[int]]:
    glyphs = row_glyphs(row)
    visible = [i for i, glyph in enumerate(glyphs) if not glyph.char.isspace()]
    if folio and "".join(glyphs[i].char for i in visible[-len(folio):]) == folio:
        visible = visible[:-len(folio)]
    return glyphs, visible


def _mixed_dot_period(entry: TocEntryLine) -> _PeriodBeforeLeader | None:
    """Locate a candidate attached period before separate leaders."""
    folio = entry.page_number_token
    title = _without_folio(entry.cleaned_text, folio)
    match = _MIXED_DOT_SUFFIX_RE.search(title)
    if match is None or match.end() < MIN_ENTRY_TEXT_LEN:
        return None

    row = _final_title_row(entry)
    glyphs, visible = _title_glyphs(row, folio)
    suffix = "".join(title[match.start() - 1:].split())
    tail = visible[-len(suffix):]
    if "".join(glyphs[i].char for i in tail) != suffix:
        return None

    preceding, period, leader = (glyphs[i] for i in tail[:3])
    if period.x1 is None or leader.x0 is None or not period.size:
        return None
    jitter = LEADER_GAP_JITTER_EM * period.size
    if leader.x0 - period.x1 <= jitter:
        return None

    offset = tail[1]
    for span in sorted(row.spans, key=lambda item: item.bbox.x0):
        if offset >= len(span.text):
            offset -= len(span.text)
            continue
        if preceding.x1 is not None and period.x0 is not None:
            if abs(period.x0 - preceding.x1) > jitter:
                return None
        elif offset == 0 or span.text[offset - 1] != preceding.char:
            return None
        # A span ending at an unmeasured period still gives a title-only
        # highlight. Never extend the box through the first leader.
        return _PeriodBeforeLeader(
            bbox=BBox(
                x0=period.x0 if period.x0 is not None else span.bbox.x0,
                y0=span.bbox.y0,
                x1=period.x1,
                y1=span.bbox.y1,
            ),
            period_x=period.x0,
            leader_x=leader.x0,
        )
    return None


def _row_baseline(row: PdfTextLine) -> float:
    if row.baseline_y is not None:
        return row.baseline_y
    # Reconstructed TOC rows retain their span origins.
    return next(
        (span.baseline_y for span in row.spans if span.baseline_y is not None),
        (row.bbox.y0 + row.bbox.y1) / 2,
    )


def _leader_grid_rows(
    context: TocPageContext, entries: list[TocEntryLine]
) -> dict[TocEntryLine, list[float]]:
    # Detached dots past the entry-region cutoff can be absent from reconstructed
    # rows. Recover their positions only between a peer title and its folio.
    fragments = [
        (_row_baseline(line), row_glyphs(line))
        for block in context.page.text_blocks
        for line in block.lines
        if re.fullmatch(r"[.…·\s]+", line.text)
    ]
    grids: dict[TocEntryLine, list[float]] = {}
    for entry in entries:
        if entry.page_number_token is None or entry.page_number_right_x is None:
            continue
        row = _final_title_row(entry)
        glyphs, visible = _title_glyphs(row, entry.page_number_token)
        trailing_dots: list[Glyph] = []
        title_end = None
        for index in reversed(visible):
            glyph = glyphs[index]
            if glyph.char not in _DOT_LEADER_CHARS:
                title_end = glyph.x1
                break
            trailing_dots.append(glyph)
        positions = {dot.x0 for dot in trailing_dots if dot.x0 is not None}
        if title_end is not None:
            baseline = _row_baseline(row)
            positions.update(
                dot.x0
                for y, dots in fragments
                if abs(y - baseline) <= SAME_BASELINE_Y_TOLERANCE_PT
                for dot in dots
                if dot.x0 is not None
                and dot.char in _DOT_LEADER_CHARS
                and title_end <= dot.x0 < entry.page_number_right_x
            )
        if len(positions) >= MIN_LEADER_DOT_WEIGHT:
            grids[entry] = sorted(positions)
    return grids


def _period_is_on_leader_grid(
    entry: TocEntryLine, candidate: _PeriodBeforeLeader, grids: dict[TocEntryLine, list[float]]
) -> bool:
    period_x = candidate.period_x
    if period_x is None:
        return False
    # Require the candidate and the following leader to match consecutive cells
    # on several peer runs. A period near a grid column alone is insufficient.
    matching_rows = sum(
        any(
            abs(left - period_x) <= LEADER_GRID_MAX_SPREAD_PT
            and abs(right - candidate.leader_x) <= LEADER_GRID_MAX_SPREAD_PT
            for left, right in zip(dots, dots[1:])
        )
        for peer, dots in grids.items()
        if peer is not entry
    )
    return matching_rows >= LEADER_GRID_MIN_ROWS


def _single_spaced_dot_is_ambiguous(entry_text: str) -> bool:
    """Avoid treating an isolated, space-separated leader as title punctuation.

    A lone dot can be the last cell of a leader grid. Without a repeated dot
    pattern or a page-wide aligned grid, extracted whitespace alone cannot
    establish whether the dot belongs to the title.
    """
    return re.search(r"\s+\.$", entry_text) is not None


def _check_toc_terminal_period_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    grids = None
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        candidate = _mixed_dot_period(entry)
        if candidate is not None and candidate.period_x is not None:
            if grids is None:
                grids = _leader_grid_rows(context, entries)
            if _period_is_on_leader_grid(entry, candidate, grids):
                continue
        if candidate is None:
            entry_text = _extract_toc_entry_text(entry)
            if entry_text is None or not _TERMINAL_PERIOD_RE.search(entry_text):
                continue
            if is_isolated_terminal_grid_leader_dot(entry, entries):
                continue
            if _single_spaced_dot_is_ambiguous(entry_text):
                continue
        details = {
            "issue_type": "toc_entry_has_terminal_period",
            "page": str(context.page.page_number),
            "section_type": "table_of_contents",
            "entry_index": str(page_entry_offset + idx),
            "terminal_punctuation": ".",
            "page_number_token_present": "true",
            "bbox": format_bbox_detail(candidate.bbox if candidate else entry.line.bbox),
            "triage_tier": "medium",
            "source_q_rule_id": "Q050",
        }
        if candidate is not None:
            details["highlight_right_limit"] = str(candidate.leader_x)
        findings.append(
            AuditFinding(
                rule_id="P054",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "Table of Contents entry ends with a terminal period. "
                    "NJIT guidelines require that TOC entries "
                    "at all levels do not end with a terminal period."
                ),
                details=details,
            )
        )
    return findings


def check_pdf_toc_terminal_period(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P054 warnings for TOC entries with a terminal period."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_entry_lines(context)
        if len(entries) < 2:
            continue
        page_findings = _check_toc_terminal_period_page(context, entries, entry_offset)
        findings.extend(page_findings)
        entry_offset += len(entries)
    return findings
