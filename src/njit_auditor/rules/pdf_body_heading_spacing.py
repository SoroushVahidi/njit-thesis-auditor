"""Detect supported spacing defects at numbered body headings (P023).

Ester's reviewed body heading and the P023 multi-line-title exception establish
the spacing requirement.  A wide first title line, matching bold continuation,
and the page's own double-spaced prose pitch are all required.  Ambiguous pairs
are left for manual review.

F05 separately establishes that level-three headings have no blank line above
them. Evaluate the preceding gap only where the surrounding prose establishes
a consistent double-spaced baseline rhythm on the same page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median

import pymupdf

from njit_auditor.digital_commons_wrapper import page_identity
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import join_content_span_texts
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_body_spacing import (
    BULLET_PREFIX_RE,
    CAPTION_PREFIX_RE,
    _is_body_text_line,
)
from njit_auditor.rules.pdf_heading_levels import _is_qualified_heading
from njit_auditor.rules.pdf_headings import find_body_start_page
from njit_auditor.rules.pdf_references_citations_structural import references_section_page_numbers

# Level 2 and 3 are stand-alone bold headings.  Level 4 is run-in and Level 5
# is italic, so their wrapped prose cannot safely be grouped as heading text.
_NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+){1,2}(?:\.)?(?:\s+|$)")
_NUMBER_ONLY = re.compile(r"^\d+(?:\.\d+){1,2}\.?$")
_LEVEL_THREE_HEADING = re.compile(r"^(\d+\.\d+\.\d+)\.?\s+(.+)$")
_ROW_ALIGNMENT_PT = 1.5
_PRECEDING_PROSE_LINES = 4
_CAPTION_START = re.compile(r"^(?:Figure|Fig\.|Table)\s*\d", re.IGNORECASE)
_EXCLUDED_PAGE_HEADINGS = frozenset({
    "TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES",
    "ABSTRACT", "BIOGRAPHICAL SKETCH", "ACKNOWLEDGEMENTS",
    "REFERENCES", "BIBLIOGRAPHY", "WORKS CITED",
})


@dataclass(frozen=True)
class _Row:
    lines: tuple[PdfTextLine, ...]
    bbox: BBox

    @property
    def text(self) -> str:
        return " ".join(line.text.strip() for line in self.lines).strip()


def _union(boxes: list[BBox]) -> BBox:
    return BBox(
        x0=min(box.x0 for box in boxes), y0=min(box.y0 for box in boxes),
        x1=max(box.x1 for box in boxes), y1=max(box.y1 for box in boxes),
    )


def _rows(page: PdfPage) -> list[_Row]:
    """Reconstruct visual rows independently of PDF text-block boundaries."""
    lines = sorted(
        (line for block in page.text_blocks for line in block.lines if line.text.strip()),
        key=lambda line: (line.bbox.y0, line.bbox.x0),
    )
    groups: list[list[PdfTextLine]] = []
    for line in lines:
        if groups and abs(line.bbox.y0 - groups[-1][0].bbox.y0) <= _ROW_ALIGNMENT_PT:
            groups[-1].append(line)
        else:
            groups.append([line])
    return [
        _Row(tuple(sorted(group, key=lambda line: line.bbox.x0)),
             _union([line.bbox for line in group]))
        for group in groups
    ]


def _font(line: PdfTextLine) -> tuple[str, float] | None:
    spans = [span for span in line.spans if span.text.strip() and span.size]
    if not spans:
        return None
    sizes = [span.size for span in spans if span.size is not None]
    if not sizes or max(sizes) - min(sizes) > 0.5:
        return None
    fonts = {span.font for span in spans}
    if len(fonts) != 1 or None in fonts:
        return None
    return spans[0].font or "", median(sizes)


def _bold(line: PdfTextLine) -> bool:
    spans = [span for span in line.spans if span.text.strip()]
    return bool(spans) and all(span.bold for span in spans)


def _body_metrics(rows: list[_Row]) -> tuple[float, float, float] | None:
    """Return prose pitch, font size, and right edge from regular lines."""
    prose = [
        (row, font)
        for row in rows
        if len(row.lines) == 1
        and len(row.text) >= 30
        and not _bold(row.lines[0])
        and (font := _font(row.lines[0])) is not None
    ]
    if len(prose) < 5:
        return None
    pitches: list[float] = []
    sizes: list[float] = []
    right_edges: list[float] = []
    for (first, first_font), (second, second_font) in zip(prose, prose[1:]):
        if first_font != second_font:
            continue
        pitch = second.bbox.y0 - first.bbox.y0
        size = first_font[1]
        if 1.7 * size <= pitch <= 2.5 * size:
            pitches.append(pitch)
            sizes.append(size)
            right_edges.append(first.bbox.x1)
    if len(pitches) < 3:
        return None
    return median(pitches), median(sizes), median(right_edges)


def _title_line(row: _Row) -> PdfTextLine | None:
    """Find title text on a numbered heading row, including split number/title."""
    if len(row.lines) == 2 and _NUMBER_ONLY.fullmatch(row.lines[0].text.strip()):
        number, title = row.lines
        if not (_bold(number) and _bold(title)):
            return None
        if title.bbox.x0 - number.bbox.x1 > 6 * (_font(title) or ("", 12))[1]:
            return None
        return title
    if len(row.lines) == 1 and _NUMBERED_HEADING.match(row.text):
        return row.lines[0] if _bold(row.lines[0]) else None
    return None


def _continuation_matches(anchor: _Row, title: PdfTextLine, next_row: _Row) -> bool:
    if (len(next_row.lines) != 1 or _NUMBERED_HEADING.match(next_row.text)
            or _CAPTION_START.match(next_row.text)):
        return False
    following = next_row.lines[0]
    if not _bold(following) or len(next_row.text) < 5:
        return False
    title_font = _font(title)
    if title_font is None or title_font != _font(following):
        return False
    size = title_font[1]
    # Split number/title rows give the exact continuation indent.  For a
    # combined row the number's width is unavailable; accept only a repeat
    # of the row indent, and abstain from uncertain hanging indents.
    if abs(following.bbox.x0 - title.bbox.x0) > 0.35 * size:
        return False
    if following.bbox.x1 > anchor.bbox.x1 + size:
        return False
    return True


def _level_three_title(row: _Row) -> tuple[str, PdfTextLine] | None:
    # Recover the separator when PDF extraction joins a numbered span directly
    # to the title. The bound on split rows is the same as for wrapped headings.
    title = row.lines[0] if len(row.lines) == 1 else _title_line(row)
    if title is None or not _bold(title) or _font(title) is None:
        return None
    baseline = title.baseline_y
    if baseline is None or any(
        line.baseline_y is None or abs(line.baseline_y - baseline) > _ROW_ALIGNMENT_PT
        or line.line_dir not in (None, (1.0, 0.0))
        for line in row.lines
    ):
        return None
    text = join_content_span_texts(title.spans)
    if len(row.lines) == 2:
        text = f"{row.lines[0].text} {text}"
    match = _LEVEL_THREE_HEADING.fullmatch(" ".join(text.split()))
    if match is None or not _is_qualified_heading(match[2]):
        return None
    return match[1], title


@dataclass(frozen=True)
class _ProseLine:
    left: float
    baseline: float
    font: str
    size: float


def _prose_sample(row: _Row, page: PdfPage) -> _ProseLine | None:
    if len(row.lines) != 1:
        return None
    line = row.lines[0]
    if (
        line.baseline_y is None or not line.bbox.y0 < line.baseline_y <= line.bbox.y1
        or line.line_dir not in (None, (1.0, 0.0))
        or not _is_body_text_line(line, page.height)
    ):
        return None
    # Use the opening prose span. Inline emphasis or a mathematical
    # subscript later in the row does not set its baseline rhythm.
    span = next((item for item in line.spans if item.text.strip()), None)
    if span is None or span.bold or span.italic or not span.font or not span.size:
        return None
    return _ProseLine(line.bbox.x0, line.baseline_y, span.font, span.size)


def _anchored_as_caption_or_list(
    page: PdfPage, rows: list[_Row], first: _ProseLine, pitch: float,
) -> bool:
    """Reject a continuous run that began with a caption or list marker."""
    next_baseline = first.baseline
    for row in reversed(rows):
        if len(row.lines) != 1:
            break
        baseline = row.lines[0].baseline_y
        if baseline is None or abs(next_baseline - baseline - pitch) > _ROW_ALIGNMENT_PT:
            break
        bullet = BULLET_PREFIX_RE.match(row.text)
        if CAPTION_PREFIX_RE.match(row.text) or (bullet and bullet[0][-1].isspace()):
            return True
        sample = _prose_sample(row, page)
        if sample is None or abs(sample.left - first.left) > _ROW_ALIGNMENT_PT:
            break
        if (sample.font, sample.size) != (first.font, first.size):
            break
        next_baseline = baseline
    return False


def _preceding_heading_gap(
    page: PdfPage, rows: list[_Row], index: int, title: PdfTextLine,
) -> tuple[float, float, BBox, BBox] | None:
    heading = rows[index]
    baseline = title.baseline_y
    if index < _PRECEDING_PROSE_LINES or baseline is None:
        return None
    preceding = rows[index - _PRECEDING_PROSE_LINES:index]
    paragraph_end = preceding[-1]
    if not re.search(r"[.!?][\])\"’”]*$", paragraph_end.text):
        return None
    following = index + 1
    # Support clean heading wraps without measuring the title's own spacing
    # as if it were a gap between the previous paragraph and this heading.
    while following < len(rows) and _continuation_matches(
        heading, title, rows[following]
    ):
        before = rows[following - 1].bbox
        after = rows[following].bbox
        if not 0 < after.y0 - before.y0 <= 1.3 * before.height:
            break
        following += 1
    if following + 1 >= len(rows):
        return None
    evidence = [_prose_sample(row, page) for row in (*preceding, *rows[following:following + 2])]
    if any(sample is None for sample in evidence):
        return None
    upper = [sample for sample in evidence[:_PRECEDING_PROSE_LINES] if sample is not None]
    lower = [sample for sample in evidence[_PRECEDING_PROSE_LINES:] if sample is not None]
    first = upper[0]
    if any((row.font, row.size) != (first.font, first.size) for row in (*upper, *lower)):
        return None
    if any(abs(left - first.left) > _ROW_ALIGNMENT_PT
           for left in [heading.bbox.x0, *(row.left for row in upper), lower[-1].left]):
        return None
    if not first.left - _ROW_ALIGNMENT_PT <= lower[0].left <= first.left + 3 * first.size:
        return None
    pitches = [b.baseline - a.baseline for a, b in zip(upper, upper[1:])]
    pitch = median(pitches)
    if not 1.7 * first.size <= pitch <= 2.5 * first.size:
        return None
    pitches.append(lower[1].baseline - lower[0].baseline)
    if any(abs(value - pitch) > _ROW_ALIGNMENT_PT for value in pitches):
        return None
    gap = baseline - upper[-1].baseline
    # A whole additional blank body line requires room for two body pitches.
    # Compare at the same tenth-point precision used to serialize the result.
    if round(gap, 1) < round(2 * pitch, 1):
        return None
    if _anchored_as_caption_or_list(page, rows[:index - _PRECEDING_PROSE_LINES], first, pitch):
        return None
    if any(box.y0 < heading.bbox.y0 and paragraph_end.bbox.y1 < box.y1
           for box in [*(graphic.bbox for graphic in page.graphic_blocks), *page.horizontal_rules]):
        return None
    # Inset the band from each text box to avoid rasterization at the edges.
    band = BBox(x0=first.left, x1=max(row.bbox.x1 for row in preceding),
                y0=paragraph_end.bbox.y1 + 1, y1=heading.bbox.y0 - 1)
    return gap, pitch, _union([row.bbox for row in rows[index:following]]), band


def _appears_blank(path: str, page: PdfPage, band: BBox) -> bool:
    # Text extraction can miss vector rules, outlined text and small artwork.
    # Render only the candidate gap on its physical page, without annotations.
    if not (0 <= band.x0 < band.x1 <= page.width and 0 <= band.y0 < band.y1 <= page.height):
        return False
    try:
        with pymupdf.open(path) as source:
            original = source[page_identity(page).original_page_index]
            pixels = original.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                colorspace=pymupdf.csGRAY,
                clip=pymupdf.Rect(band.x0, band.y0, band.x1, band.y1),
                annots=False,
            )
            return bool(pixels.width and pixels.height) and min(pixels.samples) >= 250
    except (OSError, RuntimeError, ValueError, IndexError):
        return False


def _check_level_three_preceding_spacing(
    path: str, page: PdfPage, rows: list[_Row],
) -> list[AuditFinding]:
    if page.page_rotation or page.is_visually_landscape or page.text_extraction_unavailable:
        return []
    findings = []
    for index, row in enumerate(rows):
        heading = _level_three_title(row)
        if heading is None:
            continue
        number, title = heading
        measurement = _preceding_heading_gap(page, rows, index, title)
        if measurement is None:
            continue
        gap, pitch, bbox, band = measurement
        if not _appears_blank(path, page, band):
            continue
        findings.append(AuditFinding(
            rule_id="P023", severity=Severity.WARNING, page=page.page_number,
            message="There appears to be a blank line above this level-three heading.",
            details={
                "issue_type": "blank_line_above_level_three_heading",
                "heading_number": number,
                "bbox": format_bbox_detail(bbox),
                "preceding_baseline_gap_pt": f"{gap:.1f}",
                "body_pitch_pt": f"{pitch:.1f}",
                "confidence": "high",
                "source_feedback_id": "F05",
            },
        ))
    return findings


def check_pdf_body_heading_spacing(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P023 for clearly supported internal or preceding heading gaps."""
    body_start = find_body_start_page(pdf_doc)
    if body_start is None:
        return []
    reference_pages = references_section_page_numbers(pdf_doc)
    findings: list[AuditFinding] = []
    for page in pdf_doc.pages:
        if page.page_number < body_start or page.page_number in reference_pages:
            continue
        rows = _rows(page)
        if any(row.text.upper() in _EXCLUDED_PAGE_HEADINGS for row in rows):
            continue
        findings.extend(_check_level_three_preceding_spacing(pdf_doc.path, page, rows))
        metrics = _body_metrics(rows)
        if metrics is None:
            continue
        prose_pitch, prose_size, prose_right = metrics
        for anchor, following in zip(rows, rows[1:]):
            title = _title_line(anchor)
            if title is None or not _continuation_matches(anchor, title, following):
                continue
            font = _font(title)
            if font is None:
                continue
            size = font[1]
            pitch = following.bbox.y0 - title.bbox.y0
            # The first title line must reach the body text's right edge: a
            # short heading followed by a subtitle or separate heading is
            # otherwise indistinguishable from a wrap at this wide gap.
            if abs(title.bbox.x1 - prose_right) > 1.5 * size:
                continue
            if not (1.7 * size <= pitch <= 2.5 * size):
                continue
            if abs(pitch / size - prose_pitch / prose_size) > 0.15 * (prose_pitch / prose_size):
                continue
            bbox = _union([title.bbox, following.bbox])
            findings.append(AuditFinding(
                rule_id="P023", severity=Severity.WARNING, page=page.page_number,
                message=(
                    f"A wrapped numbered heading on page {page.page_number} appears "
                    "double-spaced within the heading. Single-space its lines."
                ),
                details={
                    "issue_type": "multiline_body_heading_not_single_spaced",
                    "bbox": format_bbox_detail(bbox),
                    "heading_pitch_pt": f"{pitch:.1f}",
                    "body_pitch_pt": f"{prose_pitch:.1f}",
                    "font_size_pt": f"{size:.1f}",
                    "confidence": "high",
                },
            ))
    return findings
