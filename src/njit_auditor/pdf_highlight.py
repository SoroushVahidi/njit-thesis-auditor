"""Generate highlighted PDF copies for the web finding viewer.

Draws translucent rectangle annotations on a *copy* of an uploaded PDF so a
student can see exactly where a finding is located. The original uploaded
PDF is never modified.
"""

from __future__ import annotations

import math
from pathlib import Path

import fitz

_HIGHLIGHT_STROKE_RGB = (1.0, 0.55, 0.0)
_HIGHLIGHT_FILL_RGB = (1.0, 1.0, 0.0)
_HIGHLIGHT_OPACITY = 0.35

# Caps annotations per page in case a single request matches many findings.
MAX_HIGHLIGHT_BOXES_PER_PAGE = 25

BoxesByPage = dict[int, list[tuple[float, float, float, float]]]


def is_drawable_bbox(box: tuple[float, float, float, float]) -> bool:
    """Return True when *box* is a finite, positive-area (x0, y0, x1, y1) rectangle.

    PyMuPDF's annotation reader (``annot.rect``) does not validate the rect
    stored in an arbitrary uploaded PDF, so degenerate values (zero-area,
    inverted, NaN, or infinite coordinates) can reach this code from real
    documents. ``add_rect_annot`` raises ``ValueError`` on such rects, so
    callers must filter them out *before* constructing a ``fitz.Rect``.
    """
    if len(box) != 4 or not all(math.isfinite(v) for v in box):
        return False
    x0, y0, x1, y1 = box
    return x1 > x0 and y1 > y0


def build_highlighted_pdf(source_pdf: Path, output_pdf: Path, boxes_by_page: BoxesByPage) -> None:
    """Write a copy of *source_pdf* to *output_pdf* with highlight rectangles added.

    ``boxes_by_page`` maps 1-based page numbers to (x0, y0, x1, y1) boxes in
    PDF coordinate space. Page numbers outside the document and boxes that
    are not drawable (see :func:`is_drawable_bbox`) are skipped rather than
    raising, so a single bad finding never breaks the whole response.
    """
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source_pdf) as doc:
        for page_number, boxes in boxes_by_page.items():
            page_index = page_number - 1
            if page_index < 0 or page_index >= doc.page_count:
                continue
            page = doc[page_index]
            for box in boxes[:MAX_HIGHLIGHT_BOXES_PER_PAGE]:
                if not is_drawable_bbox(box):
                    continue
                annot = page.add_rect_annot(fitz.Rect(*box))
                annot.set_colors(stroke=_HIGHLIGHT_STROKE_RGB, fill=_HIGHLIGHT_FILL_RGB)
                annot.set_opacity(_HIGHLIGHT_OPACITY)
                annot.update()
        doc.save(output_pdf)
