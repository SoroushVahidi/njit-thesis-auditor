"""Detect clearly double-spaced wraps inside numbered body headings (P023).

Ester's reviewed body heading and the P023 multi-line-title exception establish
the spacing requirement.  A wide first title line, matching bold continuation,
and the page's own double-spaced prose pitch are all required.  Ambiguous pairs
are left for manual review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_headings import find_body_start_page
from njit_auditor.rules.pdf_references_citations_structural import references_section_page_numbers

# Level 2 and 3 are stand-alone bold headings.  Level 4 is run-in and Level 5
# is italic, so their wrapped prose cannot safely be grouped as heading text.
_NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+){1,2}(?:\.)?(?:\s+|$)")
_NUMBER_ONLY = re.compile(r"^\d+(?:\.\d+){1,2}\.?$")
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
        if groups and abs(line.bbox.y0 - groups[-1][0].bbox.y0) <= 1.5:
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


def check_pdf_body_heading_spacing(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P023 only for an unambiguous double-pitch numbered heading wrap."""
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
