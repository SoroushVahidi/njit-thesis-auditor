"""Generate highlighted PDF copies for the web finding viewer.

Draws translucent rectangle annotations on a *copy* of an uploaded PDF so a
student can see exactly where a finding is located. The original uploaded
PDF is never modified.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import fitz

_HIGHLIGHT_STROKE_RGB = (1.0, 0.55, 0.0)
_HIGHLIGHT_FILL_RGB = (1.0, 1.0, 0.0)
_HIGHLIGHT_OPACITY = 0.35

# Caps annotations per page in case a single request matches many findings.
MAX_HIGHLIGHT_BOXES_PER_PAGE = 25

# A clipped box narrower or shorter than this (in PDF points) is treated as
# invisible once drawn, even though it is technically non-degenerate. This
# also catches boxes supplied in the wrong coordinate space (e.g. 0-1
# normalized fractions mistaken for PDF points).
MIN_HIGHLIGHT_DIMENSION_PT = 2.0

BoxesByPage = dict[int, list[tuple[float, float, float, float]]]
PageSize = tuple[float, float]


def is_drawable_bbox(box: tuple[float, float, float, float]) -> bool:
    """Return True when *box* is a finite, positive-area (x0, y0, x1, y1) rectangle.

    PyMuPDF's annotation reader (``annot.rect``) does not validate the rect
    stored in an arbitrary uploaded PDF, so degenerate values (zero-area,
    inverted, NaN, or infinite coordinates) can reach this code from real
    documents. ``add_rect_annot`` raises ``ValueError`` on such rects, so
    callers must filter them out *before* constructing a ``fitz.Rect``.

    This check is shape-only: it does not know about any particular page's
    size, so an off-page box is still considered "drawable" here. Use
    :func:`clip_box_to_page` to additionally confirm a box is visible on a
    specific page.
    """
    if len(box) != 4 or not all(math.isfinite(v) for v in box):
        return False
    x0, y0, x1, y1 = box
    return x1 > x0 and y1 > y0


def clip_box_to_page(
    box: tuple[float, float, float, float], page_width: float, page_height: float
) -> tuple[float, float, float, float] | None:
    """Clip *box* to a page of size (*page_width*, *page_height*).

    Returns the clipped ``(x0, y0, x1, y1)`` box, or ``None`` when *box* is
    not drawable, does not overlap the page at all, or the overlap is too
    thin (see :data:`MIN_HIGHLIGHT_DIMENSION_PT`) to be visible once drawn.
    """
    if not is_drawable_bbox(box):
        return None
    x0, y0, x1, y1 = box
    cx0, cy0 = max(x0, 0.0), max(y0, 0.0)
    cx1, cy1 = min(x1, page_width), min(y1, page_height)
    if cx1 - cx0 < MIN_HIGHLIGHT_DIMENSION_PT or cy1 - cy0 < MIN_HIGHLIGHT_DIMENSION_PT:
        return None
    return (cx0, cy0, cx1, cy1)


def has_visible_highlight(
    bbox: tuple[float, float, float, float] | None,
    *,
    page: int | None,
    page_count: int | None = None,
    page_size: PageSize | None = None,
) -> bool:
    """Return True when *bbox* would draw a real, visible highlight on *page*.

    This is the single source of truth for whether the UI may offer a
    "highlighted PDF" action for a finding: ``page`` must be a known,
    in-range 1-based page number, and *bbox* must be a drawable box that
    still has visible area after clipping to the page bounds.

    *page_count* and *page_size* are best-effort: when the PDF isn't
    available at render time, this degrades to a shape-only check rather
    than blocking the highlight outright.
    """
    if bbox is None or page is None or page < 1:
        return False
    if page_count is not None and page > page_count:
        return False
    if page_size is not None:
        return clip_box_to_page(bbox, *page_size) is not None
    return is_drawable_bbox(bbox)


# Sub-page location label bands (fractions of page width/height). These
# describe a rough visual area for student orientation only -- they are
# independent of any rule's margin-violation thresholds (e.g. P011's allowed
# margin box), which decide whether something is a *defect*, not where it
# roughly sits on the page.
_HEADER_BAND = 0.08
_TOP_BAND = 0.22
_FOOTER_BAND = 0.92
_BOTTOM_BAND = 0.78
_LEFT_BAND = 0.20
_RIGHT_BAND = 0.80
_CENTER_BAND = (0.35, 0.65)

_QUADRANT_LABELS = {
    ("header", "left"): "Header area",
    ("header", "center"): "Header area",
    ("header", "right"): "Header area",
    ("footer", "left"): "Footer area",
    ("footer", "center"): "Footer area",
    ("footer", "right"): "Footer area",
    ("top", "left"): "Upper-left area",
    ("top", "center"): "Top of page",
    ("top", "right"): "Upper-right area",
    ("bottom", "left"): "Lower-left area",
    ("bottom", "center"): "Bottom of page",
    ("bottom", "right"): "Lower-right area",
    ("middle", "left"): "Left margin area",
    ("middle", "right"): "Right margin area",
}


def sub_page_location_label(
    bbox: tuple[float, float, float, float] | None,
    page_size: PageSize | None,
) -> str:
    """Return a rough, student-friendly description of where *bbox* sits on a page.

    Returns "" whenever there is not enough reliable geometry to describe a
    location -- callers must never fabricate a label from missing or
    untrustworthy data. This is intentionally independent of
    :func:`has_visible_highlight`: a finding can have a known rough area on
    the page even when its box does not qualify for an exact PDF highlight
    (e.g. it fails the minimum-visible-dimension check after clipping).
    """
    if bbox is None or page_size is None or not is_drawable_bbox(bbox):
        return ""
    page_width, page_height = page_size
    if page_width <= 0 or page_height <= 0:
        return ""
    x0, y0, x1, y1 = bbox
    if x1 <= 0 or x0 >= page_width or y1 <= 0 or y0 >= page_height:
        # Box does not overlap the page at all -- likely a unit/coordinate
        # mismatch rather than a real position; do not guess.
        return ""
    cx = (max(x0, 0.0) + min(x1, page_width)) / 2
    cy = (max(y0, 0.0) + min(y1, page_height)) / 2
    rel_x = cx / page_width
    rel_y = cy / page_height

    if rel_y < _HEADER_BAND:
        vertical = "header"
    elif rel_y < _TOP_BAND:
        vertical = "top"
    elif rel_y > _FOOTER_BAND:
        vertical = "footer"
    elif rel_y > _BOTTOM_BAND:
        vertical = "bottom"
    else:
        vertical = "middle"

    if rel_x < _LEFT_BAND:
        horizontal = "left"
    elif rel_x > _RIGHT_BAND:
        horizontal = "right"
    else:
        horizontal = "center"

    if vertical == "middle" and horizontal == "center":
        lo, hi = _CENTER_BAND
        if lo <= rel_x <= hi and lo <= rel_y <= hi:
            return "Near page center"
        return "Body area"

    return _QUADRANT_LABELS[(vertical, horizontal)]


def get_pdf_page_sizes(path: Path) -> list[PageSize]:
    """Return the (width, height) of every page in the PDF at *path*, in order."""
    with fitz.open(path) as doc:
        return [(page.rect.width, page.rect.height) for page in doc]


@dataclass(frozen=True)
class HighlightDrawResult:
    """Outcome of attempting to draw highlights into a PDF copy.

    ``has_highlight`` is the authoritative answer to "did this produce a PDF
    with a real, visible annotation a caller may serve as 'highlighted'?" --
    callers must check it and fall back to the original PDF when False,
    since no output file is written in that case.
    """

    drawn_count: int = 0
    skipped_count: int = 0
    pages_highlighted: list[int] = field(default_factory=list)

    @property
    def has_highlight(self) -> bool:
        return self.drawn_count > 0


def build_highlighted_pdf(
    source_pdf: Path, output_pdf: Path, boxes_by_page: BoxesByPage
) -> HighlightDrawResult:
    """Write a copy of *source_pdf* to *output_pdf* with highlight rectangles added.

    ``boxes_by_page`` maps 1-based page numbers to (x0, y0, x1, y1) boxes in
    PDF coordinate space. Page numbers outside the document and boxes that
    are not visible on their page (see :func:`clip_box_to_page`) are skipped
    rather than raising, so a single bad finding never breaks the whole
    response.

    *output_pdf* is only written when at least one highlight was actually
    drawn -- a "highlighted" PDF that is byte-for-byte indistinguishable
    from the original (because nothing could be drawn) must never be
    produced. Callers should check the returned result's ``has_highlight``
    and serve the original PDF instead when it is False.
    """
    drawn = 0
    skipped = 0
    pages_highlighted: list[int] = []
    with fitz.open(source_pdf) as doc:
        for page_number, boxes in boxes_by_page.items():
            page_index = page_number - 1
            if page_index < 0 or page_index >= doc.page_count:
                skipped += len(boxes)
                continue
            page = doc[page_index]
            capped_boxes = boxes[:MAX_HIGHLIGHT_BOXES_PER_PAGE]
            skipped += len(boxes) - len(capped_boxes)
            page_drawn = 0
            for box in capped_boxes:
                clipped = clip_box_to_page(box, page.rect.width, page.rect.height)
                if clipped is None:
                    skipped += 1
                    continue
                annot = page.add_rect_annot(fitz.Rect(*clipped))
                annot.set_colors(stroke=_HIGHLIGHT_STROKE_RGB, fill=_HIGHLIGHT_FILL_RGB)
                annot.set_opacity(_HIGHLIGHT_OPACITY)
                annot.update()
                drawn += 1
                page_drawn += 1
            if page_drawn:
                pages_highlighted.append(page_number)
        if drawn:
            output_pdf.parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_pdf)
    return HighlightDrawResult(
        drawn_count=drawn, skipped_count=skipped, pages_highlighted=pages_highlighted
    )
