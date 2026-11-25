"""Identify an extra blank line before a verified opening level-three heading."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise

import pymupdf

from njit_auditor.digital_commons_wrapper import page_identity
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import join_content_span_texts
from njit_auditor.pdf_models import PdfDocument, PdfPage, format_bbox_detail
from njit_auditor.rules.pdf_body_heading_spacing import _bold, _Row, _rows
from njit_auditor.rules.pdf_captions import CAPTION_START_RE, normalize_caption_candidate_text
from njit_auditor.rules.pdf_headings import find_body_start_page
from njit_auditor.rules.pdf_indentation import (
    _AMBIGUOUS_PERIOD_ENDING_RE,
    _is_section_heading_line,
    _is_usable_paragraph_line,
)
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    LEFT_MARGIN_PT,
    OVERFLOW_TOLERANCE_PT,
    TOP_MARGIN_PT,
)
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE
from njit_auditor.rules.pdf_references_citations_structural import references_section_page_numbers

_LEVEL_THREE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\s+[A-Za-z]")
_SENTENCE_END = re.compile(r"""[.!?][\])"’”]*$""")
# Office of Graduate Studies' annotated Document Body example specifies 8 pt
# before a level-three heading and no empty line.
_LEVEL_THREE_SPACE_BEFORE_PT = 8
# Allows rounding differences between PDF text origins and exported layout.
_ORIGIN_TOLERANCE_PT = 1.0


@dataclass(frozen=True)
class _Opening:
    row: _Row
    title: str
    baseline: float
    pitch: float
    size: float
    prose_top_end: float


@dataclass(frozen=True)
class _Bookmark:
    index: int
    title: str
    number: tuple[str, str, int]
    point: pymupdf.Point


def _normalized_title(text: str) -> str:
    return "".join(text.split()).casefold()


def _row_title(row: _Row) -> str:
    return " ".join(join_content_span_texts(line.spans) for line in row.lines).strip()


def _outline_successors(source: pymupdf.Document) -> dict[int, list[tuple[_Bookmark, _Bookmark]]]:
    """Index consecutive sibling destinations and discard duplicate section numbers."""
    pairs: list[tuple[_Bookmark, _Bookmark]] = []
    occurrences: Counter[tuple[str, str, int]] = Counter()
    previous: _Bookmark | None = None
    for level, title, page, details in source.get_toc(simple=False):
        if level < 3:
            previous = None
        if level != 3:
            continue
        match = _LEVEL_THREE.match(title.strip())
        if not match:
            previous = None
            continue
        chapter, section, number = match.groups()
        try:
            sequence = int(number)
        except ValueError:
            previous = None
            continue
        identity = chapter, section, sequence
        occurrences[identity] += 1
        point = details.get("to")
        if (
            details.get("kind") != pymupdf.LINK_GOTO
            or details.get("page") != page - 1
            or not isinstance(point, pymupdf.Point)
        ):
            previous = None
            continue
        current = _Bookmark(page - 1, _normalized_title(title), identity, point)
        if (
            previous is not None and previous.number == (chapter, section, sequence - 1)
            and 0 <= previous.index < current.index
        ):
            pairs.append((current, previous))
        previous = current
    destinations: dict[int, list[tuple[_Bookmark, _Bookmark]]] = {}
    for current, preceding in pairs:
        if occurrences[current.number] == occurrences[preceding.number] == 1:
            destinations.setdefault(current.index, []).append((current, preceding))
    return destinations


def _owns_row(bookmark: _Bookmark, row: _Row, title: str, size: float) -> bool:
    return (
        bookmark.title == _normalized_title(title)
        and abs(bookmark.point.x - row.bbox.x0) <= size
        and abs(bookmark.point.y - row.bbox.y0) <= size
    )


def _previous_heading_visible(bookmark: _Bookmark, page: PdfPage | None) -> bool:
    if page is None or page.page_rotation or page.text_extraction_unavailable:
        return False
    matches = 0
    for row in _rows(page):
        if not all(_bold(line) for line in row.lines):
            continue
        span = next((span for line in row.lines for span in line.spans if span.text.strip()), None)
        if span is not None and span.size and _owns_row(bookmark, row, _row_title(row), span.size):
            matches += 1
    return matches == 1


def _prose_baseline(row: _Row, gutter: float) -> float | None:
    if len(row.lines) != 1 or abs(row.bbox.x0 - gutter) > _ORIGIN_TOLERANCE_PT:
        return None
    line = row.lines[0]
    if (
        not _is_usable_paragraph_line(line)
        or _is_section_heading_line(line)
        or CAPTION_START_RE.match(normalize_caption_candidate_text(line.text))
        or any(span.bold for span in line.spans)
        or line.line_dir != (1.0, 0.0)
        or line.wmode != 0
        or line.baseline_y is None
        or not row.bbox.y0 < line.baseline_y <= row.bbox.y1
    ):
        return None
    return line.baseline_y


def _opening(page: PdfPage) -> _Opening | None:
    rows = _rows(page)
    if len(rows) < 4:
        return None
    heading, *prose = rows[:4]
    title = _row_title(heading)
    if (
        not _LEVEL_THREE.match(title)
        or abs(heading.bbox.x0 - LEFT_MARGIN_PT) > OVERFLOW_TOLERANCE_PT
        or not all(_bold(line) and line.line_dir == (1.0, 0.0) and line.wmode == 0
                   for line in heading.lines)
    ):
        return None
    spans = [span for line in heading.lines for span in line.spans if span.text.strip()]
    first_span = spans[0]
    size = first_span.size
    baseline = first_span.baseline_y
    if (
        baseline is None or size is None or not 0 < size < page.height
        or not (0 <= heading.bbox.x0 < heading.bbox.x1 <= page.width
                and TOP_MARGIN_PT < heading.bbox.y0 < baseline < heading.bbox.y1)
        or any(span.size != size or span.baseline_y is None
               or abs(span.baseline_y - baseline) > _ORIGIN_TOLERANCE_PT for span in spans)
        or any(left.bbox.y1 >= right.bbox.y0 for left, right in pairwise(rows[:4]))
    ):
        return None
    first, second, third = (_prose_baseline(row, heading.bbox.x0) for row in prose)
    if first is None or second is None or third is None:
        return None
    pitch = second - first
    if (
        pitch <= max(row.bbox.height for row in prose)
        or abs(pitch - (third - second)) > _ORIGIN_TOLERANCE_PT
        or not 0 < first - baseline <= pitch + _ORIGIN_TOLERANCE_PT
    ):
        return None
    return _Opening(heading, title, baseline, pitch, size, prose[0].bbox.y1)


def _previous_section_closed(previous: PdfPage, opening: _Opening) -> bool:
    rows = [
        row for row in _rows(previous)
        if not (row.bbox.y0 > previous.height - BOTTOM_MARGIN_PT
                and PAGE_NUM_RE.fullmatch(row.text))
    ]
    if len(rows) < 2:
        return False
    upper, lower = rows[-2:]
    gutter = opening.row.bbox.x0
    start = _prose_baseline(upper, gutter)
    end = _prose_baseline(lower, gutter)
    terminal_text = lower.text.rstrip().rstrip("\"’”')]")
    return (
        start is not None and end is not None
        and abs(end - start - opening.pitch) <= _ORIGIN_TOLERANCE_PT
        and previous.height - BOTTOM_MARGIN_PT <= lower.bbox.y1 + opening.pitch
        and lower.bbox.y1 <= previous.height
        and bool(_SENTENCE_END.search(lower.text))
        and not _AMBIGUOUS_PERIOD_ENDING_RE.search(terminal_text)
    )


def _blank_baseline(source: pymupdf.Page, page: PdfPage, opening: _Opening) -> float | None:
    if source.rotation or source.rect.width != page.width or source.rect.height != page.height:
        return None
    box = opening.row.bbox
    expected = opening.baseline - opening.pitch - _LEVEL_THREE_SPACE_BEFORE_PT
    blanks = [
        chars[0][2][1] for span in source.get_texttrace()
        if span["dir"] == (1.0, 0.0) and span["wmode"] == 0 and span["type"] == 0
        and span["opacity"] == 1 and span["size"] == opening.size
        and (chars := span["chars"])
        and abs(chars[0][2][0] - box.x0) <= _ORIGIN_TOLERANCE_PT
        and abs(span["bbox"][1] - TOP_MARGIN_PT) <= OVERFLOW_TOLERANCE_PT
        and all(abs(char[2][1] - expected) <= _ORIGIN_TOLERANCE_PT and chr(char[0]).isspace()
                for char in chars)
    ]
    if len(blanks) != 1:
        return None
    if any(
        not kind.endswith("-text") and bounds[1] < opening.prose_top_end and bounds[3] > 0
        for kind, bounds in source.get_bboxlog()
    ):
        return None
    pixels = source.get_pixmap(
        matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csGRAY,
        clip=pymupdf.Rect(0, 0, page.width, box.y0 - 1), annots=False,
    )
    return blanks[0] if pixels.width and pixels.height and min(pixels.samples) >= 250 else None


def check_pdf_section_page_top_spacing(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Warn about the explicit extra line on corroborated level-three section starts."""
    body_start = find_body_start_page(pdf_doc)
    if body_start is None:
        return []
    try:
        pdf = pymupdf.open(pdf_doc.path)
    except (OSError, RuntimeError, ValueError):
        return []
    findings: list[AuditFinding] = []
    with pdf:
        try:
            destinations = _outline_successors(pdf)
        except (RuntimeError, ValueError):
            return []
        if not destinations:
            return []
        reference_pages = references_section_page_numbers(pdf_doc)
        pages = {page_identity(page).original_page_index: page for page in pdf_doc.pages}
        for previous, page in pairwise(pdf_doc.pages):
            index = page_identity(page).original_page_index
            if (
                index not in destinations
                or not 0 <= index < len(pdf)
                or page_identity(previous).original_page_index + 1 != index
                or previous.page_number < body_start
                or any(p.page_number in reference_pages or p.text_extraction_unavailable
                       or p.page_rotation or p.is_visually_landscape for p in (previous, page))
                or page.width >= page.height
                or (previous.width, previous.height) != (page.width, page.height)
            ):
                continue
            opening = _opening(page)
            if opening is None or not _previous_section_closed(previous, opening):
                continue
            owners = [
                (current, preceding) for current, preceding in destinations[index]
                if _owns_row(current, opening.row, opening.title, opening.size)
            ]
            if len(owners) != 1:
                continue
            (current, preceding), = owners
            if not _previous_heading_visible(preceding, pages.get(preceding.index)):
                continue
            try:
                blank = _blank_baseline(pdf[index], page, opening)
            except (OSError, RuntimeError, ValueError, IndexError):
                continue
            if blank is None:
                continue
            findings.append(AuditFinding(
                rule_id="P023",
                severity=Severity.WARNING,
                page=page.page_number,
                message="An extra blank line appears above the opening level-three heading.",
                details={
                    "issue_type": "blank_line_before_opening_level_three_heading",
                    "bbox": format_bbox_detail(opening.row.bbox),
                    "heading_number": ".".join(map(str, current.number)),
                    "blank_baseline_pt": f"{blank:.1f}",
                    "heading_baseline_pt": f"{opening.baseline:.1f}",
                    "body_pitch_pt": f"{opening.pitch:.1f}",
                    "confidence": "high",
                },
            ))
    return findings
