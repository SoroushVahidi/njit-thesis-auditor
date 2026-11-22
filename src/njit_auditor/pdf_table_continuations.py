"""Opt-in, recognition-only metadata for a table spanning one page boundary.

No detector consumes logical table continuations. Page-local ruled regions can
also be measured without changing the input layout. Text in continuation metadata
is private source material and must stay out of diagnostics and public fixtures.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Literal

import fitz

from njit_auditor.pdf_layout import _drawing_is_visible, _horizontal_rule_bboxes
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_captions import CAPTION_START_RE, CaptionLine, detect_caption_lines

Box = tuple[float, float, float, float]
Role = Literal["title", "continuation_identifier", "header", "cell", "note", "source"]
_CONTINUED = re.compile(r"^Table\s+(\d+(?:\.\d+)*)\s+\(continued\)[.:]?\s*$", re.I)
_NUMBER = re.compile(r"^Table\s+(\d+(?:\.\d+)*)\b", re.I)
_NOTE = re.compile(r"^([a-z])[.)]\s+", re.I)
_SOURCE = re.compile(r"^Source\s*:", re.I)
_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\s+[A-Za-z]|chapter\b|references\b|appendix\b)", re.I)
# These are new association gates, not changes to any existing detector tolerance.
_EDGE_PT = 2.0
_BOTTOM = 0.87
_TOP = 0.20


@dataclass(frozen=True)
class TablePart:
    page_number: int
    role: Role
    text: str
    bbox: Box


@dataclass(frozen=True)
class TableFragment:
    page_number: int
    document_page_label: str
    bbox: Box
    horizontal_rules: tuple[Box, ...]
    column_edges: tuple[float, ...]
    parts: tuple[TablePart, ...]


@dataclass(frozen=True)
class LogicalTable:
    number: str
    anchor_page: int
    fragments: tuple[TableFragment, TableFragment]
    association: Literal["marked", "notes"]


@dataclass
class _Region:
    rules: list[BBox]
    edges: tuple[float, ...]
    header: list[PdfTextLine]
    content: list[PdfTextLine]
    signature: tuple[str, ...]
    style: tuple[str, float]

    @property
    def bbox(self) -> BBox:
        first, last = self.rules[0], self.rules[-1]
        return BBox(x0=first.x0, y0=first.y0, x1=first.x1, y1=last.y1)


def _box(bbox: BBox) -> Box:
    return bbox.x0, bbox.y0, bbox.x1, bbox.y1


def _lines(page: PdfPage) -> list[PdfTextLine]:
    return sorted((line for block in page.text_blocks for line in block.lines
                   if line.text.strip() and page.height * 0.06 <= line.bbox.y0
                   and line.bbox.y1 < page.height * 0.94),
                  key=lambda line: (line.bbox.y0, line.bbox.x0))


def _upright(page: PdfPage) -> bool:
    return not (page.page_rotation or page.is_visually_landscape) and all(
        line.wmode in (None, 0) and (line.line_dir is None or (
            abs(line.line_dir[0] - 1) <= 0.01 and abs(line.line_dir[1]) <= 0.01
        )) for line in _lines(page)
    )


def _header_signature(
    lines: list[PdfTextLine], edges: tuple[float, ...],
) -> tuple[tuple[str, ...], tuple[str, float]] | None:
    spans = [span for line in lines for span in line.spans
             if any(c.isalpha() for c in span.text) and span.font and span.size]
    if not spans or sum(span.bold for span in spans) < len(spans) * 0.6:
        return None
    size = median(span.size for span in spans if span.size is not None)
    fonts: set[str] = set()
    columns = ["" for _ in edges[1:]]
    for span in spans:
        if span.size is None or span.size < size * 0.8:
            continue  # citation superscripts do not define a column heading
        fonts.add(re.sub(r"^[A-Z]{6}\+", "", span.font or "").casefold())
        center = (span.bbox.x0 + span.bbox.x1) / 2
        for index, (left, right) in enumerate(zip(edges, edges[1:])):
            if left <= center <= right:
                columns[index] += re.sub(r"[^a-z]", "", span.text.casefold())
                break
    if len(fonts) != 1 or any(not column for column in columns):
        return None
    return tuple(columns), (next(iter(fonts)), size)


def _regions(page: PdfPage, raw_page: fitz.Page) -> list[_Region]:
    """Use the existing paint/segment rules, privately, on a selected page."""
    groups: list[list[BBox]] = []
    for rule in _horizontal_rule_bboxes(raw_page):
        group = next((g for g in groups if abs(g[0].x0 - rule.x0) <= _EDGE_PT
                      and abs(g[0].x1 - rule.x1) <= _EDGE_PT), None)
        if group is None:
            groups.append([rule])
        else:
            group.append(rule)
    result = []
    lines = _lines(page)
    drawings = raw_page.get_drawings()
    for group in groups:
        rules = sorted(group, key=lambda rule: rule.y0)
        if len(rules) < 3:
            continue
        top, separator, bottom = rules[0], rules[1], rules[-1]
        if top.y0 < page.height * 0.06 or bottom.y1 > page.height * 0.94:
            continue
        verticals = sorted(
            float(d["rect"].x0) for d in drawings if _drawing_is_visible(d)
            and 0 <= d["rect"].width <= _EDGE_PT
            and top.x0 - _EDGE_PT <= d["rect"].x0 <= top.x1 + _EDGE_PT
            and d["rect"].y0 <= top.y1 + _EDGE_PT
            and d["rect"].y1 >= separator.y0 - _EDGE_PT
        )
        edges: list[float] = []
        for x in verticals:
            if not edges or x - edges[-1] > _EDGE_PT:
                edges.append(x)
        if (len(edges) < 3 or abs(edges[0] - top.x0) > _EDGE_PT
                or abs(edges[-1] - top.x1) > _EDGE_PT):
            continue
        inside = [line for line in lines
                  if top.y0 <= (line.bbox.y0 + line.bbox.y1) / 2 <= bottom.y1]
        if not inside or any(line.bbox.x0 < top.x0 - _EDGE_PT
                             or line.bbox.x1 > top.x1 + _EDGE_PT for line in inside):
            continue  # parallel columns or text outside the candidate region
        header = [line for line in inside
                  if (line.bbox.y0 + line.bbox.y1) / 2 < separator.y0]
        content = [line for line in inside if line not in header]
        signature = _header_signature(header, tuple(edges))
        if not content or signature is None:
            continue
        result.append(_Region(rules, tuple(edges), header, content, *signature))
    return result


def measure_ruled_table_boxes(pdf_path: str, page: PdfPage) -> tuple[BBox, ...]:
    """Measure page-local table boxes on an upright page's original PDF sheet."""
    if not pdf_path or not Path(pdf_path).is_file() or not _upright(page):
        return ()
    index = page.original_page_index
    if index is None:
        index = page.page_number - 1
    try:
        with fitz.open(pdf_path) as pdf:
            if not 0 <= index < len(pdf):
                return ()
            source = pdf[index]
            if (
                source.rotation or abs(source.rect.width - page.width) > 1
                or abs(source.rect.height - page.height) > 1
            ):
                return ()
            return tuple(region.bbox for region in _regions(page, source))
    except (OSError, fitz.FileDataError):
        return ()


def _content_parts(page: PdfPage, region: _Region) -> tuple[TablePart, ...] | None:
    parts = []
    blocks = {id(line): index for index, block in enumerate(page.text_blocks)
              for line in block.lines}
    role: Role = "cell"
    previous: PdfTextLine | None = None
    for line in region.content:
        text = line.text.strip()
        if CAPTION_START_RE.match(text) or (_HEADING.match(text)
                                           and any(s.bold for s in line.spans)):
            return None
        if _SOURCE.match(text):
            role = "source"
        elif _NOTE.match(text):
            if role == "source":
                return None
            role = "note"
        elif role == "cell":
            # A full-width prose paragraph is not a row of cells. Merged data
            # cells are deliberately outside this first-stage recognizer.
            if not any(left - _EDGE_PT <= line.bbox.x0
                       and line.bbox.x1 <= right + _EDGE_PT
                       for left, right in zip(region.edges, region.edges[1:])):
                return None
        elif previous is not None:
            sizes = [s.size for s in line.spans if s.size]
            if (not sizes or blocks[id(line)] != blocks[id(previous)]
                    or line.bbox.y0 - previous.bbox.y0 > 1.8 * median(sizes)
                    or any(s.bold for s in line.spans)):
                return None
        parts.append(TablePart(page.page_number, role, text, _box(line.bbox)))
        previous = line
    # A source citation may sit just below the last border. Capture only its
    # own tightly spaced block, never the following ordinary prose block.
    following = [line for line in _lines(page) if line.bbox.y0 > region.bbox.y1]
    if following and _SOURCE.match(following[0].text.strip()):
        lead = following[0]
        sizes = [span.size for span in lead.spans if span.size]
        if (sizes and lead.bbox.y0 - region.bbox.y1 <= 2 * median(sizes)
                and abs(lead.bbox.x0 - region.bbox.x0) <= 8):
            block = next(block for block in page.text_blocks if lead in block.lines)
            previous = None
            for line in sorted(block.lines, key=lambda item: item.bbox.y0):
                if line.bbox.y0 < lead.bbox.y0:
                    continue
                line_sizes = [span.size for span in line.spans if span.size]
                if (not line_sizes or abs(median(line_sizes) - median(sizes)) > 0.5
                        or CAPTION_START_RE.match(line.text.strip())
                        or _HEADING.match(line.text.strip())
                        or (previous is not None
                            and line.bbox.y0 - previous.bbox.y0 > 1.8 * median(sizes))):
                    break
                parts.append(TablePart(page.page_number, "source", line.text, _box(line.bbox)))
                previous = line
    return tuple(parts)


def _note_markers(parts: tuple[TablePart, ...]) -> list[int]:
    return [ord(match.group(1).lower()) for part in parts if part.role == "note"
            if (match := _NOTE.match(part.text))]


def _folio(page: PdfPage) -> str:
    labels = {line.text.strip() for block in page.text_blocks for line in block.lines
              if line.bbox.y0 > page.height * 0.92
              and abs((line.bbox.x0 + line.bbox.x1) / 2 - page.width / 2) < page.width * 0.08
              and re.fullmatch(r"\d{1,4}|[ivxlcdm]+", line.text.strip(), re.I)}
    return next(iter(labels)) if len(labels) == 1 else ""


def _fragment(
    page: PdfPage, region: _Region, prefix: list[PdfTextLine],
    prefix_role: Literal["title", "continuation_identifier"], parts: tuple[TablePart, ...],
) -> TableFragment:
    return TableFragment(
        page.page_number, _folio(page), _box(region.bbox),
        tuple(_box(rule) for rule in region.rules), region.edges,
        tuple(TablePart(page.page_number, prefix_role, line.text, _box(line.bbox))
              for line in prefix)
        + tuple(TablePart(page.page_number, "header", line.text, _box(line.bbox))
                for line in region.header) + parts,
    )


def _associate(
    caption: CaptionLine, page: PdfPage, following: PdfPage,
    first: _Region, second: _Region,
) -> LogicalTable | None:
    match = _NUMBER.match(caption.raw_text)
    if match is None or caption.bbox is None:
        return None
    if (first.signature != second.signature or first.style[0] != second.style[0]
            or abs(first.style[1] - second.style[1]) > 0.5
            or len(first.edges) != len(second.edges)
            or any(abs(a - b) > _EDGE_PT for a, b in zip(first.edges, second.edges))):
        return None
    before = [line for line in _lines(following) if line.bbox.y1 <= second.bbox.y0]
    if before and (len(before) != 1 or not (label := _CONTINUED.fullmatch(before[0].text.strip()))
                   or label.group(1) != match.group(1)):
        return None
    # A caption or heading inside either table body invalidates its ownership.
    start_parts, end_parts = _content_parts(page, first), _content_parts(following, second)
    if not start_parts or not end_parts:
        return None
    source_boxes = {part.bbox for part in start_parts if part.role == "source"}
    if any(line.bbox.y0 > first.bbox.y1 and _box(line.bbox) not in source_boxes
           for line in _lines(page)):
        return None  # ordinary prose after the first table breaks continuity
    if not before:
        left, right = _note_markers(start_parts), _note_markers(end_parts)
        if (not left or not right or right[0] != left[-1] + 1
                or any(b != a + 1 for a, b in zip(left, left[1:]))
                or any(b != a + 1 for a, b in zip(right, right[1:]))
                or any(p.role == "cell" for p in end_parts)
                or any(p.role == "source" for p in start_parts)):
            return None  # identical schemas alone cannot identify an unlabelled table
    title = [line for block in page.text_blocks if any(
        line.bbox == caption.bbox for line in block.lines
    ) for line in block.lines if caption.bbox.y0 <= line.bbox.y0
             and line.bbox.y1 < first.bbox.y0]
    between = [line for line in _lines(page)
               if caption.bbox.y0 <= line.bbox.y0 and line.bbox.y1 < first.bbox.y0]
    if not title or title != between:
        return None
    return LogicalTable(match.group(1), page.page_number, (
        _fragment(page, first, title, "title", start_parts),
        _fragment(following, second, before, "continuation_identifier", end_parts),
    ), "marked" if before else "notes")


def recognize_table_continuations(document: PdfDocument) -> tuple[LogicalTable, ...]:
    """Recognize measured, ruled, repeated-header tables; emit no findings.

    Only unique, portrait, two-page associations are returned. Unlabelled joins
    additionally require consecutive alphabetic notes. Missing/ambiguous source
    geometry is unsupported. Vector evidence remains local to this call and is
    never added to ``PdfPage.horizontal_rules`` or raster ``graphic_blocks``.
    """
    captions = [c for c in detect_caption_lines(document)
                if c.caption_type == "table" and c.context == "body" and c.bbox is not None
                and "continued" not in c.raw_text.casefold()]
    pages = {page.page_number: page for page in document.pages}
    if (not captions or len(pages) != len(document.pages)
            or not document.path or not Path(document.path).is_file()):
        return ()
    candidates: list[LogicalTable] = []
    with fitz.open(document.path) as raw:
        regions: dict[int, list[_Region]] = {}

        def measured(page: PdfPage) -> list[_Region]:
            if page.page_number not in regions:
                index = page.original_page_index
                if index is None:
                    index = page.page_number - 1
                if not 0 <= index < len(raw):
                    return []
                source = raw[index]
                if (source.rotation or abs(source.rect.width - page.width) > 1
                        or abs(source.rect.height - page.height) > 1):
                    return []
                regions[page.page_number] = _regions(page, source)
            return regions[page.page_number]

        for caption in captions:
            page, following = pages[caption.page_number], pages.get(caption.page_number + 1)
            if (following is None or caption.bbox is None or not _upright(page)
                    or not _upright(following)
                    or (following.original_page_number or following.page_number)
                    != (page.original_page_number or page.page_number) + 1
                    or abs(page.width - following.width) > 1
                    or abs(page.height - following.height) > 1):
                continue
            starts = [r for r in measured(page) if 0 < r.bbox.y0 - caption.bbox.y1 <= 80
                      and r.bbox.y1 >= page.height * _BOTTOM]
            if len(starts) != 1:
                continue
            # Vector extraction on the next page happens only after a measured
            # caption-anchored table reaches the lower first-page region.
            tails = [r for r in measured(following) if r.bbox.y0 <= following.height * _TOP
                     and r.bbox.y1 < following.height * _BOTTOM]
            for tail in tails:
                resolved = _associate(caption, page, following, starts[0], tail)
                if resolved is not None:
                    candidates.append(resolved)
    owners: dict[int, int] = defaultdict(int)
    for table in candidates:
        for fragment in table.fragments:
            owners[fragment.page_number] += 1
    return tuple(table for table in candidates
                 if all(owners[f.page_number] == 1 for f in table.fragments))
