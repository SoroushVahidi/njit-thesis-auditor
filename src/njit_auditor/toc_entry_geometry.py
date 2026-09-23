"""Sub-span horizontal geometry for TOC / List of Tables / List of Figures rows.

PDF text extraction frequently delivers a whole TOC row -- section number,
title, leader dots -- as one span, so span boxes alone cannot say where the
title text starts (after the section number) or where the title ends and its
leader dots begin. ``load_pdf_layout`` records per-character x-extents
(``PdfTextSpan.char_x_bounds``) on leader-bearing pages; the helpers here turn
a visual row into a flat glyph sequence and measure those positions.

Every measurement returns ``None`` when the needed position falls inside a
span without character geometry, so callers stay silent rather than guess.
The one deliberate exception is ``title_text_start_x``, which falls back to a
documented *lower-bound* estimate (see ``_NUMBER_LABEL_MIN_ADVANCE_EM``).
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from njit_auditor.pdf_models import PdfTextLine

LEADER_CHARS = frozenset({".", "\u2026", "\u00b7"})
_ROMAN_CHARS = frozenset("ivxlcdm")
# Minimum visible leader weight (an ellipsis counts as three dots) before a
# trailing dot run is treated as a leader rather than punctuation.
MIN_LEADER_DOT_WEIGHT = 3
# Lower-bound glyph advances, in em, used only when a section-number label and
# its title share a span that has no character geometry. Real text fonts set
# digits at >= 0.5 em and periods/spaces at >= 0.25 em (Times, Arial, Computer
# Modern, Latin Modern); these smaller values keep the estimate at or left of
# the true title start, so an estimate can only hide a misalignment, never
# invent one.
_NUMBER_LABEL_MIN_ADVANCE_EM = {"digit": 0.40, "other": 0.20, "space": 0.20}
_FALLBACK_FONT_SIZE_PT = 12.0
_FALLBACK_SPACE_EM = 0.25


@dataclass(frozen=True)
class Glyph:
    """One character of a visual row; x-extents are ``None`` when unmeasured."""

    char: str
    x0: float | None
    x1: float | None
    size: float | None


def row_glyphs(line: PdfTextLine) -> list[Glyph]:
    """Flatten a (possibly multi-span) visual row into left-to-right glyphs.

    Spans without character geometry contribute glyphs whose extents are only
    known at the span's own visible edges (first/last non-space character).
    """

    glyphs: list[Glyph] = []
    for span in sorted(line.spans, key=lambda span: span.bbox.x0):
        text = span.text
        if not text:
            continue
        bounds = span.char_x_bounds
        if bounds is not None and len(bounds) == len(text):
            glyphs.extend(
                Glyph(ch, x0, x1, span.size) for ch, (x0, x1) in zip(text, bounds)
            )
            continue
        first = next((i for i, ch in enumerate(text) if not ch.isspace()), None)
        last = next(
            (i for i in range(len(text) - 1, -1, -1) if not text[i].isspace()), None
        )
        for i, ch in enumerate(text):
            x0 = span.bbox.x0 if i == first and first == 0 else None
            x1 = span.bbox.x1 if i == last and last == len(text) - 1 else None
            glyphs.append(Glyph(ch, x0, x1, span.size))
    return glyphs


def row_font_size(glyphs: list[Glyph]) -> float:
    sizes = [g.size for g in glyphs if g.size and not g.char.isspace()]
    return float(median(sizes)) if sizes else _FALLBACK_FONT_SIZE_PT


def visible_start_x(line: PdfTextLine) -> float | None:
    """x0 of the row's first non-space glyph, or ``None`` when unmeasured."""

    for glyph in row_glyphs(line):
        if not glyph.char.isspace():
            return glyph.x0
    return None


def title_text_start_x(
    line: PdfTextLine, label_nonspace_len: int
) -> tuple[float | None, bool]:
    """Return ``(x, exact)`` for where title text starts after a numeric label.

    *label_nonspace_len* is the number of non-space characters in the leading
    section-number label (``"1.3.3"`` -> 5, ``"2.1."`` -> 4). ``exact`` is
    False when the position was estimated from lower-bound glyph advances.
    """

    glyphs = row_glyphs(line)
    size = row_font_size(glyphs)
    consumed = 0
    label_start: float | None = None
    label_advance = 0.0
    for glyph in glyphs:
        if glyph.char.isspace():
            continue
        if consumed < label_nonspace_len:
            if consumed == 0:
                label_start = glyph.x0
            kind = "digit" if glyph.char.isdigit() else "other"
            label_advance += _NUMBER_LABEL_MIN_ADVANCE_EM[kind] * (glyph.size or size)
            consumed += 1
            continue
        if glyph.x0 is not None:
            return glyph.x0, True
        if label_start is None:
            return None, False
        # One separating space always sits between a label and its title.
        label_advance += _NUMBER_LABEL_MIN_ADVANCE_EM["space"] * size
        return label_start + label_advance, False
    return None, False


@dataclass(frozen=True)
class LeaderGap:
    """Measured gap between a row's title text and its trailing leader dots."""

    gap_pt: float
    space_width_pt: float
    leader_pitch_pt: float
    dot_advance_pt: float
    font_size_pt: float
    title_end_x: float
    leader_start_x: float
    has_page_number: bool


def _dot_weight(ch: str) -> int:
    if ch == "\u2026":
        return 3
    return 1 if ch in LEADER_CHARS else 0


def _trailing_leader_bounds(chars: str) -> tuple[int, int, bool] | None:
    """Return ``(title_end_index, leader_start_index, has_page_number)``.

    Scans from the right: optional page-number token, the leader run (dots and
    interior spaces), then the title's last visible character. A single period
    attached to the title and separated from the rest of the run by space is
    kept as title punctuation, not counted as the first leader dot.
    """

    end = len(chars)
    while end > 0 and chars[end - 1].isspace():
        end -= 1
    token_start = end
    while token_start > 0 and (
        chars[token_start - 1].isdigit() or chars[token_start - 1].lower() in _ROMAN_CHARS
    ):
        token_start -= 1
    has_page_number = False
    if token_start < end and (
        token_start == 0
        or chars[token_start - 1].isspace()
        or chars[token_start - 1] in LEADER_CHARS
    ):
        end = token_start
        has_page_number = True
    while end > 0 and chars[end - 1].isspace():
        end -= 1
    run_start = end
    while run_start > 0 and (
        chars[run_start - 1] in LEADER_CHARS or chars[run_start - 1].isspace()
    ):
        run_start -= 1
    if sum(_dot_weight(ch) for ch in chars[run_start:end]) < MIN_LEADER_DOT_WEIGHT:
        return None
    leader_start = run_start
    while leader_start < end and chars[leader_start].isspace():
        leader_start += 1
    title_end = run_start - 1
    while title_end >= 0 and chars[title_end].isspace():
        title_end -= 1
    if title_end < 0:
        return None
    if (
        chars[leader_start] == "."
        and leader_start == title_end + 1
        and leader_start + 1 < end
        and chars[leader_start + 1].isspace()
    ):
        rest = leader_start + 1
        while rest < end and chars[rest].isspace():
            rest += 1
        if sum(_dot_weight(ch) for ch in chars[rest:end]) >= MIN_LEADER_DOT_WEIGHT:
            title_end = leader_start
            leader_start = rest
    return title_end, leader_start, has_page_number


def _leader_pitch(glyphs: list[Glyph], start: int, stop: int) -> float | None:
    """Median horizontal repeat distance of the leader's visible dots."""

    positions: list[float] = []
    for glyph in glyphs[start:stop]:
        if glyph.char not in LEADER_CHARS or glyph.x0 is None:
            continue
        if glyph.char == "\u2026" and glyph.x1 is not None:
            third = (glyph.x1 - glyph.x0) / 3.0
            positions.extend(glyph.x0 + third * k for k in range(3))
        else:
            positions.append(glyph.x0)
        if len(positions) >= 12:
            break
    diffs = [b - a for a, b in zip(positions, positions[1:]) if b > a]
    return float(median(diffs)) if diffs else None


def _dot_advance(glyphs: list[Glyph], start: int, fallback: float) -> float:
    """Median advance width of one visible leader dot."""

    widths: list[float] = []
    for glyph in glyphs[start:]:
        if glyph.x0 is None or glyph.x1 is None or glyph.x1 <= glyph.x0:
            continue
        if glyph.char == "\u2026":
            widths.append((glyph.x1 - glyph.x0) / 3.0)
        elif glyph.char in LEADER_CHARS:
            widths.append(glyph.x1 - glyph.x0)
        if len(widths) >= 12:
            break
    return float(median(widths)) if widths else fallback


def _space_width(glyphs: list[Glyph], title_end: int, size: float) -> float:
    widths = [
        g.x1 - g.x0
        for g in glyphs[: title_end + 1]
        if g.char == " " and g.x0 is not None and g.x1 is not None and g.x1 > g.x0
    ]
    if widths:
        return float(median(widths))
    return _FALLBACK_SPACE_EM * size


def measure_title_leader_gap(line: PdfTextLine) -> LeaderGap | None:
    """Measure the gap between the last title glyph and the first leader dot."""

    glyphs = row_glyphs(line)
    chars = "".join(g.char for g in glyphs)
    bounds = _trailing_leader_bounds(chars)
    if bounds is None:
        return None
    title_end, leader_start, has_page_number = bounds
    if sum(1 for ch in chars[: title_end + 1] if ch.isalnum()) < 2:
        return None
    title_glyph = glyphs[title_end]
    leader_glyph = glyphs[leader_start]
    if title_glyph.x1 is None or leader_glyph.x0 is None:
        return None
    size = row_font_size(glyphs)
    pitch = _leader_pitch(glyphs, leader_start, len(glyphs))
    if pitch is None:
        return None
    return LeaderGap(
        gap_pt=max(0.0, leader_glyph.x0 - title_glyph.x1),
        space_width_pt=_space_width(glyphs, title_end, size),
        leader_pitch_pt=pitch,
        dot_advance_pt=_dot_advance(glyphs, leader_start, pitch),
        font_size_pt=size,
        title_end_x=title_glyph.x1,
        leader_start_x=leader_glyph.x0,
        has_page_number=has_page_number,
    )
