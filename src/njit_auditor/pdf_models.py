"""Layout-aware PDF models used by Phase 2 extraction."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Rectangular bounding box in PDF points."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


def format_bbox_detail(bbox: BBox | tuple[float, float, float, float]) -> str:
    """Serialize a bbox into the comma-separated string ``AuditFinding.details["bbox"]`` expects.

    Shared by detector modules so every rule that propagates geometry uses the
    same on-disk shape that :func:`njit_auditor.report_view._parse_bbox_from_details`
    parses back out.
    """
    if isinstance(bbox, BBox):
        x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
    else:
        x0, y0, x1, y1 = bbox
    return f"{x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}"


class PdfTextSpan(BaseModel):
    """Smallest text run with style metadata."""

    text: str
    bbox: BBox
    font: str | None = None
    size: float | None = None
    bold: bool = False
    italic: bool = False
    # Optional per-character horizontal extents, one ``(x0, x1)`` pair per
    # character of ``text``. Only populated for pages whose layout needs
    # sub-span geometry (TOC/List-style pages with dot-leader runs); ``None``
    # everywhere else, and consumers must treat ``None`` as "unmeasured".
    char_x_bounds: list[tuple[float, float]] | None = None


class PdfTextLine(BaseModel):
    """Line of text spans."""

    spans: list[PdfTextSpan] = Field(default_factory=list)
    bbox: BBox
    text: str
    line_dir: tuple[float, float] | None = None
    wmode: int | None = None


class PdfTextBlock(BaseModel):
    """Block of one or more text lines."""

    lines: list[PdfTextLine] = Field(default_factory=list)
    bbox: BBox
    text: str


class PdfGraphicBlock(BaseModel):
    """Detected non-text graphic region such as a raster image."""

    bbox: BBox
    kind: str = "image"


class PdfPage(BaseModel):
    """Single PDF page with geometric and text-block content."""

    page_number: int
    original_page_index: int | None = None
    original_page_number: int | None = None
    manuscript_page_index: int | None = None
    manuscript_page_number: int | None = None
    display_page_label: str = ""
    width: float
    height: float
    page_rotation: int = 0
    is_visually_landscape: bool = False
    text_blocks: list[PdfTextBlock] = Field(default_factory=list)
    graphic_blocks: list[PdfGraphicBlock] = Field(default_factory=list)
    # Thin PDF drawing paths grouped into visible horizontal rules. Used by
    # R035 only when repeated, aligned rules bound a real table body.
    # "Horizontal" means in the page's reading frame (see
    # reading_frame_rotation); the boxes are stored in unrotated text space
    # like every other box on the page.
    horizontal_rules: list[BBox] = Field(default_factory=list)


def text_space_size(page: PdfPage) -> tuple[float, float]:
    """Width and height of the coordinate space extracted boxes are reported in.

    PyMuPDF reports text, image and drawing boxes in the page's *unrotated*,
    CropBox-relative space, while ``PdfPage.width``/``height`` hold the
    displayed size after ``/Rotate``. The two differ only by a swap on a
    quarter-turned page (e.g. a pdflscape landscape page: portrait MediaBox,
    ``/Rotate 90``), so geometry compared against extracted boxes must use this
    size, not the displayed one.
    """
    if page.page_rotation % 180 == 90:
        return page.height, page.width
    return page.width, page.height


def _displayed_direction(direction: tuple[float, float], rotation: int) -> tuple[float, float]:
    """Writing direction *direction* (unrotated space) as seen after /Rotate."""
    dx, dy = direction
    if rotation == 90:
        return -dy, dx
    if rotation == 180:
        return -dx, -dy
    if rotation == 270:
        return dy, -dx
    return dx, dy


def reading_frame_rotation(
    page_rotation: int, line_directions: Iterable[tuple[tuple[float, float] | None, int]]
) -> int:
    """Return the /Rotate under which the page's text reads upright, else 0.

    *line_directions* pairs each text line's writing direction (unrotated
    space) with a weight such as its character count. A pdflscape landscape
    page (portrait MediaBox, ``/Rotate 90``) carries its text sideways in
    unrotated space so that it reads upright once displayed; geometry that
    asks a visual question about such a page must be measured in the
    displayed frame. When the text already reads upright without the
    rotation (``/Rotate`` used only to turn the sheet in the viewer), or the
    page is unrotated, the unrotated frame is kept and 0 is returned.
    """
    rotation = page_rotation % 360
    if rotation not in {90, 180, 270}:
        return 0
    upright_displayed = 0
    upright_unrotated = 0
    for direction, weight in line_directions:
        if direction is None or weight <= 0:
            continue
        if direction[0] > 0.9:
            upright_unrotated += weight
        if _displayed_direction(direction, rotation)[0] > 0.9:
            upright_displayed += weight
    return rotation if upright_displayed > upright_unrotated else 0


def page_reading_frame_rotation(page: PdfPage) -> int:
    """:func:`reading_frame_rotation` for an extracted page."""
    return reading_frame_rotation(
        page.page_rotation,
        (
            (line.line_dir, len(line.text.strip()))
            for block in page.text_blocks
            for line in block.lines
        ),
    )


class PdfDocument(BaseModel):
    """Extracted PDF document layout model."""

    path: str
    pages: list[PdfPage] = Field(default_factory=list)
