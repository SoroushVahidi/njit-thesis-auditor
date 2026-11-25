"""Focused TOC leader-style consistency check (P075, Q052).

Q052: Is each entry connected to a page number by a consistent leader style?
Every TOC entry must connect to a right-aligned page number using one
consistent leader style (dots or hyphens) throughout the Table of Contents.

Complements the broader P018 diagnostic. Silent when all entries
consistently use dots, all use hyphens, or fewer than 3 paged entries exist.
Fires for: mixed dot+hyphen leaders (toc_mixed_leader_styles) or some entries
missing a leader while others have one (toc_missing_leader_style).

For dot grids, measured terminal cells and the folio column establish whether
a long title leaves room for a leader. The text fallback still handles rows
without sufficient geometry, including hyphen leaders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextSpan, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    detect_toc_like_pages,
    entry_has_visible_dot_leader,
    extract_toc_entry_lines,
    has_trailing_page_number_token,
    leader_evidence_entry,
    owned_detached_leader_lines,
)
from njit_auditor.toc_entry_geometry import LEADER_CHARS, row_glyphs

MIN_ENTRIES_FOR_LEADER_CHECK = 3

# Detect 4+ consecutive hyphens followed by optional whitespace and a page number.
_HYPHEN_PAGED_RE = re.compile(
    r"-{4,}\s*(?:[0-9]+|[ivxlcdm]+)\s*$",
    re.IGNORECASE,
)

# Detect a page number preceded by 2+ whitespace chars (uses raw, uncollapsed text).
_SPACE_PAGED_RE = re.compile(
    r"\s{2,}(?:[0-9]+|[ivxlcdm]+)\s*$",
    re.IGNORECASE,
)

# Scaled by the measured folio size to absorb extraction and grid rounding.
_GRID_JITTER_EM = 0.10


@dataclass(frozen=True)
class _LeaderRow:
    title_right: float
    folio_left: float
    folio_right: float
    font_size: float
    dots: tuple[tuple[float, float], ...]


def _extend_fragmented_title(
    title_right: float, stop_x: float, spans: list[PdfTextSpan], page: PdfPage, jitter: float,
) -> float:
    # The TOC parser can drop isolated spans in the right half of the page.
    # Only extend a title when its retained final row establishes a repeated
    # interword gap and the omitted fragments continue that same typography.
    title = [
        span for span in sorted(spans, key=lambda span: span.bbox.x0)
        if span.bbox.x1 <= title_right and span.text.strip()
    ]
    if len(title) < 3 or title[-1].bbox.x1 != title_right:
        return title_right
    first, middle, last = title[-3:]
    if not last.font or last.baseline_y is None:
        return title_right

    def same_text_style(span: PdfTextSpan) -> bool:
        return (
            span.font == last.font and span.size == last.size
            and span.baseline_y == last.baseline_y
        )

    before = middle.bbox.x0 - first.bbox.x1
    after = last.bbox.x0 - middle.bbox.x1
    if (
        not same_text_style(first) or not same_text_style(middle)
        or min(before, after) <= jitter or abs(before - after) > jitter
    ):
        return title_right
    gap = (before + after) / 2
    candidates = sorted(
        (
            span for block in page.text_blocks for line in block.lines for span in line.spans
            if title_right < span.bbox.x0 < span.bbox.x1 <= stop_x
            and same_text_style(span)
            and span.text == span.text.strip()
            and any(c.isalnum() for c in span.text)
        ),
        key=lambda span: span.bbox.x0,
    )
    for span in candidates:
        if abs(span.bbox.x0 - title_right - gap) > jitter:
            break
        title_right = span.bbox.x1
    return title_right


def _measure_leader_row(
    entry: TocEntryLine, page: PdfPage, peers: list[TocEntryLine],
) -> _LeaderRow | None:
    row, token = entry.page_number_line, entry.page_number_token
    if row is None or not token or not row.spans:
        return None
    folio_span = max(row.spans, key=lambda span: span.bbox.x1)
    if not folio_span.size or folio_span.baseline_y is None:
        return None
    jitter = _GRID_JITTER_EM * folio_span.size
    glyphs = [glyph for glyph in row_glyphs(row) if not glyph.char.isspace()]
    tail = glyphs[-len(token):]
    if (
        len(glyphs) <= len(token)
        or not re.search(rf"[\s.…·]{re.escape(token)}\s*$", row.text, re.IGNORECASE)
        or "".join(g.char for g in tail).casefold() != token.casefold()
    ):
        return None
    folio_left, folio_right = tail[0].x0, tail[-1].x1
    if (
        folio_left is None or folio_right is None or not folio_left < folio_right
        or entry.page_number_right_x is None
        or abs(folio_right - entry.page_number_right_x) > jitter
    ):
        return None

    end = len(glyphs) - len(token) - 1
    dots: set[tuple[float, float]] = set()
    while end > 0 and glyphs[end].char in LEADER_CHARS:
        dot, preceding = glyphs[end], glyphs[end - 1]
        if dot.x0 is None or dot.x1 is None or preceding.x1 is None:
            return None
        if (
            dot.char == "." and preceding.char not in LEADER_CHARS
            and dot.x0 - preceding.x1 <= jitter
        ):
            # An attached full stop consumes title space.
            break
        if not dot.x0 < dot.x1 <= folio_left:
            return None
        dots.add((dot.x0, dot.x1))
        end -= 1
    title_right = glyphs[end].x1
    if (
        title_right is None or title_right >= folio_left
        or not any(g.char.isalpha() for g in glyphs[:end + 1])
    ):
        return None
    extended_title_right = _extend_fragmented_title(
        title_right, min((left for left, _ in dots), default=folio_left),
        row.spans, page, jitter,
    )
    dots.update(
        (glyph.x0, glyph.x1)
        for line in owned_detached_leader_lines(entry, page, peers, title_right=title_right)
        if line.baseline_y is not None
        for glyph in row_glyphs(line)
        if glyph.char in LEADER_CHARS and glyph.x0 is not None and glyph.x1 is not None
        and extended_title_right + jitter < glyph.x0 < glyph.x1 <= folio_left
    )
    return _LeaderRow(
        extended_title_right, folio_left, folio_right, folio_span.size, tuple(sorted(dots))
    )


def _measured_grid_style(
    row: _LeaderRow, peers: list[_LeaderRow], column: float,
) -> str | None:
    jitter = _GRID_JITTER_EM * row.font_size
    if abs(row.folio_right - column) > jitter:
        return None
    terminal_cells = [
        peer.dots[-2:] for peer in peers
        if peer is not row and abs(peer.folio_right - column) <= jitter and len(peer.dots) >= 2
    ]
    if len(terminal_cells) < 2:
        return None
    previous_x = median(cells[0][0] for cells in terminal_cells)
    last_x = median(cells[1][0] for cells in terminal_cells)
    pitch = last_x - previous_x
    dot_width = median(cells[1][1] - cells[1][0] for cells in terminal_cells)
    agreement = sum(
        abs(previous[0] - previous_x) <= jitter and abs(last[0] - last_x) <= jitter
        and abs(previous[1] - previous[0] - dot_width) <= jitter
        and abs(last[1] - last[0] - dot_width) <= jitter
        for previous, last in terminal_cells
    )
    if agreement < 2 or agreement * 2 <= len(terminal_cells) or not 0 < dot_width <= pitch:
        return None

    # Matching uses jitter. Fit uses both edges of the centered cell itself,
    # including the space on each side of the rendered dot.
    padding = (pitch - dot_width) / 2
    last_cell_left = last_x - padding
    if last_cell_left + pitch > row.folio_left:
        return None
    if not row.dots:
        return "short" if row.title_right > last_cell_left else "none"
    if len(row.dots) >= 2:
        if abs(row.dots[-2][0] - previous_x) <= jitter and abs(row.dots[-1][0] - last_x) <= jitter:
            return "dot"
        return None
    ((left, right),) = row.dots
    return (
        "dot" if abs(left - last_x) <= jitter and abs(right - left - dot_width) <= jitter
        and row.title_right > previous_x - padding
        else "none"
    )


def _count_phrase(label: str, count: int) -> str:
    noun = "entry" if count == 1 else "entries"
    return f"{label}: {count} {noun}"


def _classify_entry(
    entry: TocEntryLine, page: PdfPage, peers: list[TocEntryLine] | None = None
) -> str | None:
    """Return leader style or None when no page number is detectable.

    'dot'    — entry uses dot leaders (... patterns)
    'hyphen' — entry uses hyphen leaders (---- patterns)
    'none'   — entry has a page number but no leader
    None     — no page number detected; skip this entry
    """
    # Dot leaders are set by the shared extractor.
    if entry.page_number_token is not None and entry_has_visible_dot_leader(
        entry, page, peers or []
    ):
        return "dot"
    # Fallback: use the raw (uncollapsed) line text for hyphen and space detection.
    raw = entry.line.text
    if _HYPHEN_PAGED_RE.search(raw):
        return "hyphen"
    # Shared extractor found a page number (via dots or double-spaces in raw text).
    if entry.page_number_token is not None and has_trailing_page_number_token(entry):
        return "none"
    if _SPACE_PAGED_RE.search(raw):
        return "none"
    return None


def _anchor_details(entry: TocEntryLine, page: PdfPage, index: int) -> dict[str, str]:
    """Describe one observed row without inventing a location for the whole TOC."""
    details = {
        "page_type": "table_of_contents",
        "section_type": "table_of_contents",
        "entry_index": str(index),
        "highlight_scope": "example_entry_only",
    }
    box = entry.line.bbox
    if (
        0 <= box.x0 < box.x1 <= page.width
        and 0 <= box.y0 < box.y1 <= page.height
    ):
        details["bbox"] = format_bbox_detail(box)
    else:
        details["highlight_unavailable_reason"] = "No reliable entry coordinates were extracted."
    return details


def check_pdf_toc_leader_consistency(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P075 warnings when TOC leader styles are inconsistent (Q052)."""
    paged: list[tuple[str, PdfPage, int, TocEntryLine]] = []
    overprinted_entries: set[TocEntryLine] = set()

    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        originals = extract_toc_entry_lines(context)
        entries = [leader_evidence_entry(entry) for entry in originals]
        overprinted_entries.update(
            entry
            for entry, original in zip(entries, originals, strict=True)
            if entry is not original
        )
        measured = [_measure_leader_row(entry, context.page, entries) for entry in entries]
        peers = [row for row in measured if row is not None]
        column = median(row.folio_right for row in peers) if len(peers) >= 3 else None
        for index, (entry, row) in enumerate(zip(entries, measured, strict=True)):
            style = _classify_entry(entry, context.page, entries)
            if (
                row is not None and column is not None and style != "hyphen"
                and (style != "dot" or len(row.dots) == 1)
            ):
                # Keep established multi-dot and hyphen detections. A lone
                # dot on the grid can still leave a missing earlier cell.
                style = _measured_grid_style(row, peers, column) or style
            if style is not None:
                paged.append((style, context.page, index, entry))

    if len(paged) < MIN_ENTRIES_FOR_LEADER_CHECK:
        return []

    dot_count = sum(1 for s, _, _, _ in paged if s == "dot")
    hyphen_count = sum(1 for s, _, _, _ in paged if s == "hyphen")
    none_count = sum(1 for s, _, _, _ in paged if s == "none")
    total = len(paged)

    if dot_count > 0 and hyphen_count > 0:
        example_style = "hyphen" if dot_count >= hyphen_count else "dot"
        _, example_page, example_index, example_entry = next(
            row for row in paged if row[0] == example_style
        )
        first_page = example_page.page_number
        style_summary = "; ".join(
            [
                _count_phrase("dot leaders", dot_count),
                _count_phrase("hyphen leaders", hyphen_count),
            ]
        )
        return [
            AuditFinding(
                rule_id="P075",
                severity=Severity.WARNING,
                page=first_page,
                message=(
                    f"Table of Contents entries are not connected to page numbers by one "
                    f"consistent leader style: {style_summary} "
                    f"(out of {total} paged entries). On page {first_page}, "
                    f"TOC entry {example_index + 1} is one {example_style}-leader example. "
                    "NJIT guidelines require one consistent leader style throughout the TOC."
                ),
                details={
                    "page_number": str(first_page),
                    "issue_type": "toc_mixed_leader_styles",
                    "dot_leader_count": str(dot_count),
                    "hyphen_leader_count": str(hyphen_count),
                    "total_paged_entries": str(total),
                    "confidence": "medium",
                    "triage_tier": "medium",
                    "suggested_fix": (
                        "Right-align page numbers and use one consistent leader style "
                        "(dots or hyphens)."
                    ),
                    "source_q_rule_id": "Q052",
                    **_anchor_details(example_entry, example_page, example_index),
                },
            )
        ]

    if (dot_count > 0 or hyphen_count > 0) and none_count > 0:
        dominant = "dot" if dot_count >= hyphen_count else "hyphen"
        dominant_count = dot_count if dominant == "dot" else hyphen_count
        missing = [row for row in paged if row[0] == "none"]
        previously_missing = [row for row in missing if row[3] not in overprinted_entries]
        _, missing_page, missing_index, missing_entry = (previously_missing or missing)[0]
        first_missing_page = missing_page.page_number
        style_summary = "; ".join(
            [
                _count_phrase(f"{dominant} leaders", dominant_count),
                _count_phrase("no leader", none_count),
            ]
        )
        return [
            AuditFinding(
                rule_id="P075",
                severity=Severity.WARNING,
                page=first_missing_page,
                message=(
                    f"Table of Contents entries are not all connected to page numbers by a "
                    f"consistent leader style: {style_summary} "
                    f"(out of {total} paged entries). On page {first_missing_page}, "
                    f"TOC entry {missing_index + 1} is one entry without a leader. "
                    "NJIT guidelines require every TOC entry to connect to its page "
                    "number with a consistent leader style."
                ),
                details={
                    "page_number": str(first_missing_page),
                    "issue_type": "toc_missing_leader_style",
                    "dominant_style": dominant,
                    "entries_with_leader": str(dominant_count),
                    "entries_without_leader": str(none_count),
                    "total_paged_entries": str(total),
                    "confidence": "medium",
                    "triage_tier": "medium",
                    "suggested_fix": (
                        "Right-align page numbers and use one consistent leader style "
                        "(dots or hyphens)."
                    ),
                    "source_q_rule_id": "Q052",
                    **_anchor_details(missing_entry, missing_page, missing_index),
                    **({} if previously_missing else {"_preserve_prior_finding_ids": "true"}),
                },
            )
        ]

    return []
