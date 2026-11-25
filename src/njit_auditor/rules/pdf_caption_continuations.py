"""Bounded, opt-in reconstruction of figure and table captions.

P017 and P088 use logical captions. Geometry/layout consumers keep the legacy
page-local parser: no coordinate is moved to a different source page.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from statistics import median

from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, text_space_size
from njit_auditor.rules.pdf_captions import (
    CAPTION_NUMBER_PREFIX_RE,
    CAPTION_START_RE,
    CaptionLine,
    _has_mixed_number_segment,
    _is_caption_continuation_line,
    _is_page_number_line,
    _page_context,
    _reads_as_prose_after_float_reference,
    _reads_as_prose_sentence,
    _starts_caption_note,
    _starts_new_caption,
    _starts_with_lowercase_word,
    _terminal_punctuation,
    detect_caption_lines,
    normalize_caption_candidate_text,
    normalize_caption_text,
)

# New association gates, not changes to the existing page-local tolerances.
_BOTTOM_TEXT_RATIO = 0.87
_TOP_TEXT_RATIO = 0.17
_MAX_LINES = 24
_PANEL = re.compile(
    r"(?:^|[.;,]\s+)(?:top|bottom|upper|lower|left|right|middle|center)"
    r"(?:\s+(?:left|right|center))?\s*[,:]", re.IGNORECASE,
)
_CONNECTOR = re.compile(r"\b(?:using|with|of|and|or|to|for|in|by|from|across|between)\s*$", re.I)
_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\s+[A-Za-z]|chapter\b|appendix\b|references\b)", re.I)
_CONTINUED = re.compile(
    r"^(?:figure|fig\.)\s+(?P<number>\d+(?:\.\d+)*)\s*"
    r"\(continued\)[.:]?(?:\s+(?P<body>.*))?$", re.I,
)
_DEPENDENT_LEAD = re.compile(
    r"^(?:and|or|under|with|without|using|including|"
    r"as (?:compared|shown|measured|observed))\b"
)
_FOOTNOTE = re.compile(r"^(?:[Ff]ootnotes?\b|[†‡*]|\[\d+\]\s+[A-Z])")
# Loose ownership is never inferred from pitch alone. Use this bound only
# after the geometry, source sequence, style and textual checks below.
_MAX_LOOSE_PITCH_IN_FONT_SIZES = 2.5


@dataclass(frozen=True)
class CaptionFragment:
    """Source lines on exactly one physical page; never a cross-page bbox."""

    page_number: int
    lines: tuple[PdfTextLine, ...]
    document_page_label: str = ""

    @property
    def bbox(self) -> BBox:
        return BBox(
            x0=min(line.bbox.x0 for line in self.lines),
            y0=min(line.bbox.y0 for line in self.lines),
            x1=max(line.bbox.x1 for line in self.lines),
            y1=max(line.bbox.y1 for line in self.lines),
        )


@dataclass(frozen=True)
class PageCaptionEnd:
    """Lines owned by a P017 body caption and whether its endpoint is known."""

    lines: tuple[PdfTextLine, ...]
    resolved: bool


class LogicalCaption(CaptionLine):
    """One figure identity, anchored on its original page, with source fragments."""

    def __init__(self, start: CaptionLine, fragments: tuple[CaptionFragment, ...]) -> None:
        self.fragments = fragments
        continuation = " ".join(line.text.strip() for line in fragments[1].lines)
        # A repeated continued label is provenance, not another figure identity.
        continued = _CONTINUED.match(continuation)
        if continued:
            continuation = continued.group("body") or ""
        super().__init__(
            page_number=start.page_number,
            raw_text=normalize_caption_text(start.raw_text + " " + continuation),
            caption_type="figure",
            caption_body=normalize_caption_text(start.caption_body + " " + continuation),
            context="body", bbox=start.bbox,
        )


def _lines(page: PdfPage) -> list[PdfTextLine]:
    return sorted(
        (line for block in page.text_blocks for line in block.lines
         if line.text.strip()
         and not (_is_page_number_line(line.text.strip())
                  and line.bbox.y0 > page.height * 0.90)
         and page.height * 0.06 <= line.bbox.y0 < page.height * 0.94),
        key=lambda line: (line.bbox.y0, line.bbox.x0),
    )


def _font_family(font: str) -> str:
    font = re.sub(r"^[A-Z]{6}\+", "", font)
    return re.sub(r"bold|italic|oblique|regular|psmt|ps|mt|[-_, ]", "", font.lower())


def _style(line: PdfTextLine) -> tuple[str, float] | None:
    spans = [s for s in line.spans if s.text.strip() and s.font and s.size]
    if not spans:
        return None
    size = median(s.size for s in spans if s.size is not None)
    fonts: Counter[str] = Counter()
    for span in spans:
        if span.size is not None and span.size >= size * 0.85:
            fonts[_font_family(span.font or "")] += len(span.text.strip())
    return (fonts.most_common(1)[0][0], size) if fonts else None


def _same_style(first: PdfTextLine, second: PdfTextLine) -> bool:
    a, b = _style(first), _style(second)
    return bool(a and b and a[0] == b[0] and abs(a[1] - b[1]) <= 0.5)


def _heading(line: PdfTextLine) -> bool:
    text = line.text.strip()
    spans = [s for s in line.spans if any(c.isalpha() for c in s.text)]
    return bool(_HEADING.match(text) or (spans and all(s.bold for s in spans)))


def _horizontal(line: PdfTextLine) -> bool:
    return line.wmode in (None, 0) and (
        line.line_dir is None
        or (abs(line.line_dir[0] - 1) <= 0.01 and abs(line.line_dir[1]) <= 0.01)
    )


def _continues_phrase(previous: str, following: str) -> bool:
    return (
        previous.count("(") > previous.count(")") and ")" in following
    ) or bool(_CONNECTOR.search(previous) and following[0].isalpha())


def _caption_boundary(line: PdfTextLine) -> bool:
    text = normalize_caption_text(line.text)
    return (
        _is_page_number_line(text)
        or _starts_new_caption(text)
        or bool(CAPTION_NUMBER_PREFIX_RE.fullmatch(text))
        or _starts_caption_note(text)
        or bool(_FOOTNOTE.match(text))
        or not _horizontal(line)
    )


def _loose_pitch(first: PdfTextLine, left: PdfTextLine, right: PdfTextLine) -> float | None:
    style = _style(left)
    if style is None or not _same_style(left, right):
        return None
    if left.baseline_y is None or right.baseline_y is None:
        return None
    if (
        abs(first.bbox.x0 - right.bbox.x0) > 2
        or right.bbox.x1 > first.bbox.x1 + style[1]
    ):
        return None
    pitch = right.baseline_y - left.baseline_y
    return pitch if 0 < pitch <= style[1] * _MAX_LOOSE_PITCH_IN_FONT_SIZES else None


def _parallel_rows(first: PdfTextLine, second: PdfTextLine) -> bool:
    return (
        first.baseline_y is not None
        and second.baseline_y is not None
        and abs(first.baseline_y - second.baseline_y) <= 1
        and (first.bbox.x1 <= second.bbox.x0 or second.bbox.x1 <= first.bbox.x0)
    )


def locate_page_caption_end(page: PdfPage, start: CaptionLine) -> PageCaptionEnd | None:
    """Resolve a body-caption endpoint without changing the legacy layout parser.

    A split extraction block has weaker provenance than a tight wrap. To join
    it, require a measured adjacent row plus an unfinished phrase or two
    matching-pitch dependent lines. Plausible but unowned lines never supply
    punctuation.
    """
    rows = sorted(
        ((index, line) for index, block in enumerate(page.text_blocks)
         for line in block.lines if line.text.strip()),
        key=lambda row: (row[1].bbox.y0, row[1].bbox.x0),
    )
    locations = [i for i, (_, line) in enumerate(rows) if line.bbox == start.bbox]
    if not locations:
        return None
    index = locations[0]
    first = rows[index][1]
    if len(locations) != 1 or not _horizontal(first):
        return PageCaptionEnd((first,), False)

    owned = [first]
    last_loose_pitch: float | None = None
    width, _ = text_space_size(page)
    while index + 1 < len(rows):
        block, previous = rows[index]
        next_block, following = rows[index + 1]
        if _caption_boundary(following):
            break
        next_row = rows[index + 2][1] if index + 2 < len(rows) else None
        if (
            next_row is not None
            and next_block != block == rows[index + 2][0]
            and following.bbox.y0 < previous.bbox.y1
            and following.bbox.x0 > first.bbox.x0 + 2
            and _is_caption_continuation_line(previous, next_row)
        ):
            # An interleaved glyph run can split a visual row across blocks.
            # Leave its endpoint to the existing grouping instead of moving
            # a punctuation highlight to the preceding line.
            return None
        competing_row = next_row is not None and _parallel_rows(following, next_row)
        text = normalize_caption_text(following.text)
        previous_text = normalize_caption_text(previous.text)
        phrase = _continues_phrase(previous_text, text)

        if block == next_block and _is_caption_continuation_line(previous, following):
            # A short line, with ample room before the opposite margin, does
            # not mechanically wrap to a new capitalized sentence. Elsewhere
            # retain the original block grouping, including proper nouns,
            # mathematical symbols and short runs in another font.
            width_at_margin = width - 2 * previous.bbox.x0
            if (
                not phrase
                and text[0].isupper()
                and len(text.split()) >= 3
                and previous.bbox.width < 0.65 * width_at_margin
            ):
                break
            if competing_row:
                return PageCaptionEnd(tuple(owned), False)
            last_loose_pitch = None
        else:
            if _heading(following) or (
                not phrase and (
                    not _starts_with_lowercase_word(text) or _terminal_punctuation(previous_text)
                )
            ):
                break
            pitch = _loose_pitch(first, previous, following)
            if pitch is None:
                break
            if (
                competing_row
                or next_block not in (block, block + 1)
                or following.bbox.y0 < previous.bbox.y1
            ):
                return PageCaptionEnd(tuple(owned), False)

            # A single dependent-looking line can also be an unrelated block.
            # Require corroboration before borrowing its punctuation.
            rhythm = last_loose_pitch is not None and abs(last_loose_pitch - pitch) <= 1
            tail_can_supply_punctuation = False
            if not rhythm and next_row is not None:
                tail_block = rows[index + 2][0]
                tail_pitch = _loose_pitch(first, following, next_row)
                if (
                    tail_block in (next_block, next_block + 1)
                    and next_row.bbox.y0 >= following.bbox.y1
                    and tail_pitch is not None
                    and not _caption_boundary(next_row)
                    and not _heading(next_row)
                ):
                    tail_text = normalize_caption_text(next_row.text)
                    rhythm = abs(tail_pitch - pitch) <= 1 and bool(
                        _DEPENDENT_LEAD.match(tail_text)
                    )
                    tail_can_supply_punctuation = (
                        _starts_with_lowercase_word(tail_text) and _terminal_punctuation(tail_text)
                    )
            if not phrase and not (_DEPENDENT_LEAD.match(text) and rhythm):
                if _terminal_punctuation(text) or tail_can_supply_punctuation:
                    return PageCaptionEnd(tuple(owned), False)
                break
            last_loose_pitch = pitch
        owned.append(following)
        index += 1
    return PageCaptionEnd(tuple(owned), True)


def _block_run(page: PdfPage, first: PdfTextLine) -> tuple[PdfTextLine, ...]:
    for block in page.text_blocks:
        rows = sorted(block.lines, key=lambda line: (line.bbox.y0, line.bbox.x0))
        for index, line in enumerate(rows):
            if line is not first:
                continue
            result = [line]
            for following in rows[index + 1:]:
                if _heading(following) or not _is_caption_continuation_line(result[-1], following):
                    break
                if not _same_style(result[-1], following):
                    break
                result.append(following)
                if len(result) > _MAX_LINES:
                    return ()
            return tuple(result)
    return ()


def _uncontested(page: PdfPage, rows: tuple[PdfTextLine, ...]) -> bool:
    """Parallel/overlapping columns are not a supported reading order."""
    identities = {id(line) for line in rows}
    return not any(
        id(line) not in identities
        and rows[0].bbox.y0 < (line.bbox.y0 + line.bbox.y1) / 2 < rows[-1].bbox.y1
        for line in _lines(page)
    )


def _owns_graphic(page: PdfPage, first: PdfTextLine) -> bool:
    style = _style(first)
    if style is None:
        return False
    return any(
        graphic.bbox.height >= 24 and graphic.bbox.width >= first.bbox.width * 0.35
        and 0 <= first.bbox.y0 - graphic.bbox.y1 <= 5 * style[1]
        and min(graphic.bbox.x1, first.bbox.x1) - max(graphic.bbox.x0, first.bbox.x0)
        >= first.bbox.width * 0.35
        for graphic in page.graphic_blocks
    )


def _label(page: PdfPage) -> str:
    # Do not infer a printed folio from the physical PDF page index. Only a
    # unique numeric footer at the page center supplies a document reference.
    labels = {
        line.text.strip() for block in page.text_blocks for line in block.lines
        if line.bbox.y0 > page.height * 0.92
        and abs((line.bbox.x0 + line.bbox.x1) / 2 - page.width / 2) < page.width * 0.08
        and re.fullmatch(r"\d{1,4}|[ivxlcdm]+", line.text.strip(), re.I)
    }
    return next(iter(labels)) if len(labels) == 1 else ""


def _associate(
    start: CaptionLine, page: PdfPage, next_page: PdfPage,
) -> LogicalCaption | None:
    if (
        start.caption_type != "figure" or start.context != "body" or start.bbox is None
        or next_page.page_number != page.page_number + 1
        or (next_page.original_page_number or next_page.page_number)
        != (page.original_page_number or page.page_number) + 1
        or page.page_rotation or next_page.page_rotation
        or page.is_visually_landscape or next_page.is_visually_landscape
        or abs(page.width - next_page.width) > 1 or abs(page.height - next_page.height) > 1
        or _page_context(next_page) != "body"
    ):
        return None
    rows, next_rows = _lines(page), _lines(next_page)
    first = next((line for line in rows if line.bbox == start.bbox), None)
    if first is None or not next_rows or not _owns_graphic(page, first):
        return None
    run = _block_run(page, first)
    if not run or run[-1] is not rows[-1] or run[-1].bbox.y1 < page.height * _BOTTOM_TEXT_RATIO:
        return None
    following = next_rows[0]
    explicit = _CONTINUED.match(following.text.strip())
    number = CAPTION_START_RE.match(normalize_caption_candidate_text(start.raw_text))
    if explicit and (number is None or explicit.group("number") != number.group("number")):
        return None
    if (
        following.bbox.y0 > next_page.height * _TOP_TEXT_RATIO
        or abs(following.bbox.x0 - run[-1].bbox.x0) > 3
        or not _same_style(run[-1], following)
        or (not explicit and (_heading(following) or _starts_new_caption(following.text)))
        or _starts_caption_note(following.text)
    ):
        return None
    tail = _block_run(next_page, following)
    if any(
        line.wmode not in (None, 0)
        or (line.line_dir is not None
            and (abs(line.line_dir[0] - 1) > 0.01 or abs(line.line_dir[1]) > 0.01))
        for line in (*run, *tail)
    ):
        return None
    if not tail or not _uncontested(page, run) or not _uncontested(next_page, tail):
        return None
    if explicit:
        # The marker must introduce actual description text, not a source
        # note, heading or an otherwise empty repeated figure label.
        marked_tail = _CONTINUED.match(" ".join(line.text.strip() for line in tail))
        body = (marked_tail.group("body") or "").strip() if marked_tail else ""
        if (not body or _starts_caption_note(body) or _starts_new_caption(body)
                or _HEADING.match(body)):
            return None
    # A second boundary is outside this bounded association. Never pretend
    # that the middle of a three-page caption is its logical end.
    if tail[-1].bbox.y1 >= next_page.height * _BOTTOM_TEXT_RATIO:
        return None
    # Without an explicit continued label, a same-margin, same-font next
    # paragraph makes the endpoint ambiguous. Do not borrow its punctuation.
    after = next((line for line in next_rows if line.bbox.y0 > tail[-1].bbox.y0), None)
    style = _style(tail[-1])
    if (not explicit and after is not None and style is not None
            and abs(after.bbox.x0 - tail[-1].bbox.x0) <= 3
            and _same_style(tail[-1], after)
            and 0 < after.bbox.y0 - tail[-1].bbox.y0 <= 3 * style[1]
            and not _heading(after) and not _starts_new_caption(after.text)
            and not _starts_caption_note(after.text)):
        return None
    initial = normalize_caption_text(start.caption_body)
    lead = following.text.strip()
    panel = bool(_PANEL.search(initial) and _PANEL.match(lead))
    incomplete = (
        initial.count("(") > initial.count(")") and ")" in lead
    ) or bool(_CONNECTOR.search(initial) and _starts_with_lowercase_word(lead))
    if not (explicit or panel or incomplete):
        return None
    return LogicalCaption(start, (
        CaptionFragment(page.page_number, run, _label(page)),
        CaptionFragment(next_page.page_number, tail, _label(next_page)),
    ))


def detect_logical_caption_lines(
    pdf_document: PdfDocument, *, page_captions: list[CaptionLine] | None = None,
) -> list[CaptionLine]:
    """Use legacy captions unless corroborated figure continuity is established."""
    captions = detect_caption_lines(pdf_document) if page_captions is None else page_captions
    pages = {p.page_number: p for p in pdf_document.pages}
    recovered: list[CaptionLine] = []
    # Only recover the first-line multi-sentence rejection when there is both
    # a graphic owner and a supported cross-page panel-description relationship.
    known = {(c.page_number, str(c.bbox)) for c in captions}
    for page in pdf_document.pages:
        following = pages.get(page.page_number + 1)
        if following is None or _page_context(page) != "body":
            continue
        for line in _lines(page):
            if (page.page_number, str(line.bbox)) in known:
                continue
            match = CAPTION_START_RE.match(normalize_caption_candidate_text(line.text))
            if (not match or match.group("label").lower() == "table"
                    or _has_mixed_number_segment(match.group("number"))):
                continue
            body = match.group("body")
            if (not _reads_as_prose_sentence(body) or not _PANEL.search(body)
                    or _starts_with_lowercase_word(body)
                    or _reads_as_prose_after_float_reference(body)):
                continue
            run = _block_run(page, line)
            candidate = CaptionLine(
                page.page_number, normalize_caption_text(" ".join(r.text for r in run)),
                "figure", normalize_caption_text(body + " " + " ".join(r.text for r in run[1:])),
                "body", line.bbox,
            )
            resolved = _associate(candidate, page, following)
            if resolved:
                recovered.append(resolved)
    result: list[CaptionLine] = []
    consumed: set[tuple[int, str]] = set()
    ordered = sorted(
        captions + recovered, key=lambda c: (c.page_number, c.bbox.y0 if c.bbox else 0),
    )
    for caption in ordered:
        key = (caption.page_number, str(caption.bbox))
        if key in consumed:
            continue
        source_page = pages.get(caption.page_number)
        following = pages.get(caption.page_number + 1)
        resolved = caption if isinstance(caption, LogicalCaption) else (
            _associate(caption, source_page, following) if source_page and following else None
        )
        if resolved:
            result.append(resolved)
            if isinstance(resolved, LogicalCaption):
                tail = resolved.fragments[1]
                consumed.add((tail.page_number, str(tail.lines[0].bbox)))
        else:
            result.append(caption)
    return result
