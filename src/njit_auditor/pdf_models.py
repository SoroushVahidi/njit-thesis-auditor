"""Layout-aware PDF models used by Phase 2 extraction."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

# A page whose width exceeds its height by more than this factor is landscape.
LANDSCAPE_ASPECT_THRESHOLD = 1.02


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
    baseline_y: float | None = None
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


def _turn_box(bbox: BBox, width: float, height: float, rotation: int) -> BBox:
    """Turn *bbox*, given in a ``width`` x ``height`` space, clockwise by *rotation*.

    The same mapping as PyMuPDF's ``box * page.rotation_matrix`` (how a viewer
    turns an unrotated page by ``/Rotate``), as pure math on stored sizes.
    """
    x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
    if rotation == 90:
        return BBox(x0=height - y1, y0=x0, x1=height - y0, y1=x1)
    if rotation == 180:
        return BBox(x0=width - x1, y0=height - y1, x1=width - x0, y1=height - y0)
    if rotation == 270:
        return BBox(x0=y0, y0=width - x1, x1=y1, y1=width - x0)
    return bbox


@dataclass(frozen=True)
class PdfReadingFrame:
    """The frame a detector rule makes layout decisions in (rotation-frames ADR).

    Three page sizes exist and must not be mixed:

    * **box size** -- the unrotated, CropBox-relative space every extracted box
      (text, image, drawing rule) is stored in (:func:`text_space_size`);
    * **reading-frame size** -- box space turned by ``reading_rotation``, the
      frame in which the page's authored content reads upright. Policy
      orientation (portrait/landscape) and every detector measurement come
      from here;
    * **display size** -- ``PdfPage.width``/``height``, the sheet as a viewer
      shows it after ``/Rotate``. It is presentation geometry only and is
      deliberately not exposed by this object.

    A viewer-only ``/Rotate`` (upright content, ``reading_rotation == 0``) leaves
    the reading frame equal to box space, so it measures exactly like the same
    page at ``/Rotate 0``. A content-turned page (e.g. pdflscape) has
    ``reading_rotation == page_rotation``, so its reading frame is the
    displayed page.

    ``reading_rotation`` is the existing :func:`page_reading_frame_rotation`
    inference, used unchanged: it carries no confidence signal, and ties or
    textless pages fall back to 0 (the ADR's legacy fallback; B2 is deferred).

    This object never mutates a page and never normalizes extraction; boxes
    are mapped explicitly with :meth:`to_reading` / :meth:`from_reading`.
    """

    box_width: float
    box_height: float
    page_rotation: int
    reading_rotation: int

    @classmethod
    def for_page(cls, page: PdfPage) -> PdfReadingFrame:
        box_width, box_height = text_space_size(page)
        return cls(
            box_width=box_width,
            box_height=box_height,
            page_rotation=page.page_rotation % 360,
            reading_rotation=page_reading_frame_rotation(page),
        )

    @property
    def box_size(self) -> tuple[float, float]:
        return self.box_width, self.box_height

    @property
    def reading_size(self) -> tuple[float, float]:
        if self.reading_rotation % 180 == 90:
            return self.box_height, self.box_width
        return self.box_width, self.box_height

    @property
    def reading_width(self) -> float:
        return self.reading_size[0]

    @property
    def reading_height(self) -> float:
        return self.reading_size[1]

    @property
    def is_landscape(self) -> bool:
        """Policy orientation, from the reading-frame aspect (never the display)."""
        width, height = self.reading_size
        return width > height * LANDSCAPE_ASPECT_THRESHOLD

    @property
    def policy_orientation(self) -> Literal["portrait", "landscape"]:
        return "landscape" if self.is_landscape else "portrait"

    def to_reading(self, bbox: BBox) -> BBox:
        """Map a box-space *bbox* into the reading frame."""
        return _turn_box(bbox, self.box_width, self.box_height, self.reading_rotation)

    def from_reading(self, bbox: BBox) -> BBox:
        """Map a reading-frame *bbox* back into box space."""
        width, height = self.reading_size
        return _turn_box(bbox, width, height, (360 - self.reading_rotation) % 360)

    def page_in_reading_frame(self, page: PdfPage) -> PdfPage:
        """*page*'s text, graphics and rules as laid out in this reading frame.

        Returns *page* itself when the reading frame is box space
        (``reading_rotation == 0``). Otherwise returns a copy whose boxes and
        line writing directions are mapped with :meth:`to_reading` and whose
        ``page_rotation`` is 0, so the copy describes the upright authored page
        (its displayed size already equals the reading-frame size). Per-glyph
        ``char_x_bounds`` are horizontal-only measurements and are dropped on
        a turned copy. *page* is never modified; map reported boxes back with
        :meth:`from_reading`. This is a rule-local view, not extraction
        normalization.
        """
        rotation = self.reading_rotation
        if rotation == 0:
            return page
        to_frame = self.to_reading

        def direction(value: tuple[float, float] | None) -> tuple[float, float] | None:
            return None if value is None else _displayed_direction(value, rotation)

        return page.model_copy(
            update={
                "page_rotation": 0,
                "text_blocks": [
                    block.model_copy(
                        update={
                            "bbox": to_frame(block.bbox),
                            "lines": [
                                line.model_copy(
                                    update={
                                        "bbox": to_frame(line.bbox),
                                        "line_dir": direction(line.line_dir),
                                        "spans": [
                                            span.model_copy(
                                                update={
                                                    "bbox": to_frame(span.bbox),
                                                    "char_x_bounds": None,
                                                }
                                            )
                                            for span in line.spans
                                        ],
                                    }
                                )
                                for line in block.lines
                            ],
                        }
                    )
                    for block in page.text_blocks
                ],
                "graphic_blocks": [
                    graphic.model_copy(update={"bbox": to_frame(graphic.bbox)})
                    for graphic in page.graphic_blocks
                ],
                "horizontal_rules": [to_frame(rule) for rule in page.horizontal_rules],
            }
        )


class PdfDocument(BaseModel):
    """Extracted PDF document layout model."""

    path: str
    pages: list[PdfPage] = Field(default_factory=list)
