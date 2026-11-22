"""PDF layout extraction using PyMuPDF."""

from __future__ import annotations

import re
from statistics import median as _median

import fitz

from njit_auditor.pdf_models import (
    LANDSCAPE_ASPECT_THRESHOLD,
    BBox,
    PdfDocument,
    PdfGraphicBlock,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
    reading_frame_rotation,
)

# When whitespace-only spans are omitted from the model, recover word breaks from
# horizontal gaps between remaining content spans (same heuristic as P051 notice
# reconstruction). Gaps below this floor are treated as kerning/subscript joins.
_MIN_SPAN_SPACE_GAP_PT = 1.0
_MIN_GRAPHIC_WIDTH_PT = 12.0
_MIN_GRAPHIC_HEIGHT_PT = 12.0
_TABLE_CAPTION_HINT_RE = re.compile(r"(?im)^\s*Table\s+\d+(?:[.\-]\d+)*\b")
_MAX_HORIZONTAL_RULE_HEIGHT_PT = 2.0
_MIN_HORIZONTAL_SEGMENT_WIDTH_PT = 8.0
_MIN_COMPLETE_RULE_WIDTH_PT = 72.0
_RULE_ROW_Y_TOLERANCE_PT = 1.0
_RULE_SEGMENT_GAP_PT = 2.0
_WHITE_PAINT_MIN_COMPONENT = 0.95
# A visible dot-leader run: four or more periods (optionally single-spaced,
# as LaTeX dotfill leaders extract), a Unicode ellipsis, or a run of middle
# dots. Pages containing one get per-character x-extents recorded on their
# spans (``PdfTextSpan.char_x_bounds``) so TOC/List rules can measure where a
# title ends and where its leader begins inside a single extracted span.
_LEADER_RUN_RE = re.compile(r"(?:\.\s?){4,}|\u2026|\u00b7(?:\s?\u00b7){2,}")
_LEADER_ONLY_SPAN_RE = re.compile(r"^[.\u2026\u00b7]+$")
# LaTeX dotfill leaders extract as one span per dot; a line carrying at least
# this many dot-only spans is treated as a leader-bearing line.
_MIN_DOT_ONLY_SPANS_FOR_LEADER = 4
_PREFIXLESS_SECTION_HINT_RE = re.compile(r"^\s*\.[0-9]")


def _parse_line_dir(raw_dir: object) -> tuple[float, float] | None:
    if not isinstance(raw_dir, (list, tuple)) or len(raw_dir) < 2:
        return None
    return (float(raw_dir[0]), float(raw_dir[1]))


def _is_visually_landscape(width: float, height: float) -> bool:
    return width > height * LANDSCAPE_ASPECT_THRESHOLD


def _style_flags_from_font_name(font_name: str | None) -> tuple[bool, bool]:
    """Infer bold/italic from PDF font name including Computer Modern variants."""
    if not font_name:
        return False, False
    lowered = font_name.lower()
    base = lowered.split("+")[-1]
    bold = (
        "bold" in lowered
        or "black" in lowered
        or "heavy" in lowered
        or base.startswith("cmbx")
    )
    italic = (
        "italic" in lowered
        or "oblique" in lowered
        or base.startswith("cmti")
        or base.startswith("cmsl")
    )
    return bold, italic


def _span_space_gap_threshold(spans: list[PdfTextSpan]) -> float:
    """Minimum horizontal gap that indicates a word space between content spans."""
    sizes = [span.size for span in spans if span.size]
    if not sizes:
        return _MIN_SPAN_SPACE_GAP_PT
    return max(_MIN_SPAN_SPACE_GAP_PT, min(sizes) * 0.10)


def _spans_have_script_offset(prev: PdfTextSpan, span: PdfTextSpan) -> bool:
    """True when span looks vertically shifted like a super/subscript relative to prev."""
    prev_mid = (prev.bbox.y0 + prev.bbox.y1) / 2.0
    span_mid = (span.bbox.y0 + span.bbox.y1) / 2.0
    sizes = [s for s in (prev.size, span.size) if s]
    size = min(sizes) if sizes else 12.0
    if prev.baseline_y is not None and span.baseline_y is not None:
        return abs(span.baseline_y - prev.baseline_y) >= size * 0.15
    return abs(span_mid - prev_mid) >= size * 0.15


def join_content_span_texts(spans: list[PdfTextSpan]) -> str:
    """Join non-empty span texts, inserting spaces where geometry implies a gap.

    PyMuPDF often emits whitespace as its own span. Those spans are omitted from
    the layout model (they are not useful as styled content), which concatenates
    adjacent words in ``line.text`` (``in`` + ``power`` → ``inpower``). Callers
    that need readable title/caption phrases can rebuild from span geometry:
    when the horizontal gap between consecutive content spans is at least a
    fraction of the font size — and the spans share a baseline (not
    super/subscript) — restore a single ASCII space.
    """
    if not spans:
        return ""
    threshold = _span_space_gap_threshold(spans)
    pieces: list[str] = []
    prev: PdfTextSpan | None = None
    for span in spans:
        raw = span.text.replace("\u00a0", " ")
        clean = raw.strip()
        if not clean:
            continue
        if pieces and prev is not None:
            gap = span.bbox.x0 - prev.bbox.x1
            if gap >= threshold and not _spans_have_script_offset(prev, span):
                pieces.append(" ")
        pieces.append(clean)
        prev = span
    return "".join(pieces)


# Backwards-compatible private alias used by unit tests.
_join_content_span_texts = join_content_span_texts


def _page_has_leader_run(page_dict: dict) -> bool:
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []) or []:
            dot_only_spans = 0
            for span in line.get("spans", []) or []:
                text = str(span.get("text", ""))
                if _LEADER_RUN_RE.search(text):
                    return True
                if _LEADER_ONLY_SPAN_RE.match(text.strip()):
                    dot_only_spans += 1
                    if dot_only_spans >= _MIN_DOT_ONLY_SPANS_FOR_LEADER:
                        return True
    return False


def _prefixless_section_lines(page_dict: dict) -> set[tuple[int, int]]:
    """Find lines that may need precise geometry for a leading .1-style identifier."""
    return {
        (block_index, line_index)
        for block_index, block in enumerate(page_dict.get("blocks", []))
        for line_index, line in enumerate(block.get("lines", []))
        if _PREFIXLESS_SECTION_HINT_RE.match(
            "".join(span["text"] for span in line.get("spans", []))
        )
    }


def _char_x_bounds_by_span(
    page: fitz.Page,
    *,
    exclude_annotation_appearances: bool = False,
) -> dict[tuple[int, int, int], tuple[str, list[tuple[float, float]]]]:
    """Map (block, line, span) indices to that span's per-character x-extents.

    ``rawdict`` is the same extraction as ``dict`` with character detail kept,
    so indices line up; callers still verify the joined characters equal the
    ``dict`` span text before trusting a mapping.
    """
    raw = _page_text_dict(
        page, raw=True, exclude_annotation_appearances=exclude_annotation_appearances
    )
    out: dict[tuple[int, int, int], tuple[str, list[tuple[float, float]]]] = {}
    for bi, block in enumerate(raw.get("blocks", [])):
        for li, line in enumerate(block.get("lines", []) or []):
            for si, span in enumerate(line.get("spans", []) or []):
                chars = span.get("chars") or []
                text = "".join(str(ch.get("c", "")) for ch in chars)
                bounds = [(float(ch["bbox"][0]), float(ch["bbox"][2])) for ch in chars]
                out[(bi, li, si)] = (text, bounds)
    return out


def _page_text_dict(
    page: fitz.Page, *, raw: bool = False, exclude_annotation_appearances: bool = False
) -> dict:
    """Extract authored page text without treating annotation artwork as content.

    PyMuPDF's usual text extraction includes visible annotation appearances,
    including reviewer labels drawn outside the dissertation margins. A display
    list with annotations disabled retains the underlying page content, even
    where an annotation overlaps genuine text. Use matching extraction flags
    for the span and character-detail dictionaries.
    """
    kind = "rawdict" if raw else "dict"
    if not exclude_annotation_appearances:
        return page.get_text(kind)
    flags = fitz.TEXTFLAGS_RAWDICT if raw else fitz.TEXTFLAGS_DICT
    textpage = fitz.TextPage(page.get_displaylist(annots=False).get_textpage(flags=flags))
    return textpage.extractRAWDICT() if raw else textpage.extractDICT()


def _page_has_table_caption_hint(page_dict: dict) -> bool:
    lines = (
        "".join(str(span.get("text", "")) for span in line.get("spans", []) or [])
        for block in page_dict.get("blocks", [])
        if block.get("type") == 0
        for line in block.get("lines", []) or []
    )
    return any(_TABLE_CAPTION_HINT_RE.match(line) for line in lines)


def _drawing_is_visible(drawing: dict) -> bool:
    """Return True when a drawing paints a non-white fill or stroke."""
    for key, opacity_key in (("fill", "fill_opacity"), ("color", "stroke_opacity")):
        paint = drawing.get(key)
        opacity = drawing.get(opacity_key)
        if not paint or (opacity is not None and opacity <= 0.0):
            continue
        if min(float(component) for component in paint) < _WHITE_PAINT_MIN_COMPONENT:
            return True
    return False


def _page_dict_reading_rotation(page: fitz.Page, page_dict: dict) -> int:
    """Reading-frame rotation (see ``reading_frame_rotation``) from raw text."""
    directions: list[tuple[tuple[float, float] | None, int]] = []
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            weight = sum(len(str(span.get("text", "")).strip()) for span in line.get("spans", []))
            directions.append((_parse_line_dir(line.get("dir")), weight))
    return reading_frame_rotation(int(page.rotation), directions)


def _horizontal_rule_bboxes(page: fitz.Page, reading_rotation: int = 0) -> list[BBox]:
    """Join adjacent thin drawing segments into full visible horizontal rules.

    PDF table borders are often emitted as several touching filled rectangles,
    one per cell. The text layer does not include these visible outer bounds.
    The R035 detector later requires at least two aligned rules around table
    text before using them, so isolated underlines are inert.

    Rules are horizontal in the page's reading frame: on a page whose text
    reads upright only after ``/Rotate`` (*reading_rotation* != 0, e.g. a
    pdflscape landscape page) a visually horizontal rule is vertical in
    unrotated space, so segments are grouped in the displayed frame and the
    resulting rules are mapped back to unrotated space.
    """
    to_frame = page.rotation_matrix if reading_rotation else fitz.Identity
    segments: list[fitz.Rect] = []
    for drawing in page.get_drawings():
        rect = drawing["rect"] * to_frame
        if not _drawing_is_visible(drawing):
            continue
        if (
            0 <= rect.height <= _MAX_HORIZONTAL_RULE_HEIGHT_PT
            and rect.width >= _MIN_HORIZONTAL_SEGMENT_WIDTH_PT
        ):
            segments.append(rect)

    segments.sort(key=lambda rect: (rect.y0, rect.x0))
    rows: list[list[fitz.Rect]] = []
    for rect in segments:
        if rows and abs(rect.y0 - rows[-1][0].y0) <= _RULE_ROW_Y_TOLERANCE_PT:
            rows[-1].append(rect)
        else:
            rows.append([rect])

    rules: list[BBox] = []
    for row in rows:
        ordered = sorted(row, key=lambda rect: rect.x0)
        runs: list[list[fitz.Rect]] = []
        for rect in ordered:
            if runs and rect.x0 <= max(item.x1 for item in runs[-1]) + _RULE_SEGMENT_GAP_PT:
                runs[-1].append(rect)
            else:
                runs.append([rect])
        for run in runs:
            x0 = min(rect.x0 for rect in run)
            x1 = max(rect.x1 for rect in run)
            if x1 - x0 >= _MIN_COMPLETE_RULE_WIDTH_PT:
                rule = fitz.Rect(x0, min(rect.y0 for rect in run), x1, max(rect.y1 for rect in run))
                if reading_rotation:
                    rule = rule * page.derotation_matrix
                rules.append(
                    BBox(
                        x0=float(rule.x0), y0=float(rule.y0),
                        x1=float(rule.x1), y1=float(rule.y1),
                    )
                )
    return rules


def load_pdf_layout(pdf_path: str) -> PdfDocument:
    """Load a layout-aware PDF model for downstream auditing."""

    pages: list[PdfPage] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)
            page_model = PdfPage(
                page_number=page_index,
                original_page_index=page_index - 1,
                original_page_number=page_index,
                manuscript_page_index=page_index - 1,
                manuscript_page_number=page_index,
                display_page_label=str(page_index),
                width=page_width,
                height=page_height,
                page_rotation=int(page.rotation),
                is_visually_landscape=_is_visually_landscape(page_width, page_height),
                text_blocks=[],
                graphic_blocks=[],
            )

            exclude_annotation_appearances = page.first_annot is not None
            page_dict = _page_text_dict(
                page, exclude_annotation_appearances=exclude_annotation_appearances
            )
            if _page_has_table_caption_hint(page_dict):
                page_model.horizontal_rules = _horizontal_rule_bboxes(
                    page, _page_dict_reading_rotation(page, page_dict)
                )
            seen_graphics: set[tuple[int, int, int, int]] = set()
            for image in page.get_images(full=True):
                xref = int(image[0])
                for rect in page.get_image_rects(xref):
                    if rect.width < _MIN_GRAPHIC_WIDTH_PT or rect.height < _MIN_GRAPHIC_HEIGHT_PT:
                        continue
                    key = (
                        round(rect.x0 * 10),
                        round(rect.y0 * 10),
                        round(rect.x1 * 10),
                        round(rect.y1 * 10),
                    )
                    if key in seen_graphics:
                        continue
                    seen_graphics.add(key)
                    page_model.graphic_blocks.append(
                        PdfGraphicBlock(
                            bbox=BBox(
                                x0=float(rect.x0),
                                y0=float(rect.y0),
                                x1=float(rect.x1),
                                y1=float(rect.y1),
                            ),
                            kind="image",
                        )
                    )

            has_leaders = _page_has_leader_run(page_dict)
            prefixless_lines = _prefixless_section_lines(page_dict) if not has_leaders else set()
            glyph_map = (
                _char_x_bounds_by_span(
                    page, exclude_annotation_appearances=exclude_annotation_appearances
                )
                if has_leaders or prefixless_lines
                else {}
            )
            for block_index, block in enumerate(page_dict.get("blocks", [])):
                if block.get("type") != 0:
                    continue
                if "bbox" not in block:
                    continue

                block_lines: list[PdfTextLine] = []
                block_text_chunks: list[str] = []
                for line_index, line in enumerate(block.get("lines", [])):
                    if "bbox" not in line:
                        continue
                    spans: list[PdfTextSpan] = []
                    span_text_chunks: list[str] = []
                    for span_index, span in enumerate(line.get("spans", [])):
                        text = str(span.get("text", ""))
                        if not text.strip():
                            continue
                        glyphs = (
                            glyph_map.get((block_index, line_index, span_index))
                            if has_leaders or (block_index, line_index) in prefixless_lines
                            else None
                        )
                        char_x_bounds = (
                            glyphs[1]
                            if glyphs is not None
                            and glyphs[0] == text
                            and len(glyphs[1]) == len(text)
                            else None
                        )
                        font_name = span.get("font")
                        bold, italic = _style_flags_from_font_name(
                            str(font_name) if font_name else None
                        )
                        span_model = PdfTextSpan(
                            text=text,
                            bbox=BBox(
                                x0=float(span["bbox"][0]),
                                y0=float(span["bbox"][1]),
                                x1=float(span["bbox"][2]),
                                y1=float(span["bbox"][3]),
                            ),
                            font=str(font_name) if font_name else None,
                            size=float(span["size"]) if span.get("size") is not None else None,
                            bold=bold,
                            italic=italic,
                            char_x_bounds=char_x_bounds,
                            baseline_y=(
                                float(span["origin"][1]) if span.get("origin") else None
                            ),
                        )
                        spans.append(span_model)
                        span_text_chunks.append(text)
                    if not spans:
                        continue
                    # Keep raw concatenation for the stored line.text so downstream
                    # rules that already tolerate/expect historical extraction stay
                    # stable. Callers that need geometry-aware word breaks (P020
                    # titles/captions) use join_content_span_texts(spans) explicitly.
                    line_text = "".join(span_text_chunks).strip()
                    block_text_chunks.append(line_text)
                    baselines = [
                        float(origin[1])
                        for span in line.get("spans", [])
                        if (origin := span.get("origin")) is not None and len(origin) > 1
                    ]
                    wmode_raw = line.get("wmode")
                    block_lines.append(
                        PdfTextLine(
                            spans=spans,
                            bbox=BBox(
                                x0=float(line["bbox"][0]),
                                y0=float(line["bbox"][1]),
                                x1=float(line["bbox"][2]),
                                y1=float(line["bbox"][3]),
                            ),
                            text=line_text,
                            baseline_y=_median(baselines) if baselines else None,
                            line_dir=_parse_line_dir(line.get("dir")),
                            wmode=int(wmode_raw) if wmode_raw is not None else None,
                        )
                    )

                if not block_lines:
                    continue
                block_text = "\n".join(part for part in block_text_chunks if part).strip()
                page_model.text_blocks.append(
                    PdfTextBlock(
                        lines=block_lines,
                        bbox=BBox(
                            x0=float(block["bbox"][0]),
                            y0=float(block["bbox"][1]),
                            x1=float(block["bbox"][2]),
                            y1=float(block["bbox"][3]),
                        ),
                        text=block_text,
                    )
                )
            if not page_model.text_blocks:
                page_model.text_extraction_unavailable = bool(
                    page_model.graphic_blocks or page.get_drawings()
                )
            pages.append(page_model)

    return PdfDocument(path=pdf_path, pages=pages)
