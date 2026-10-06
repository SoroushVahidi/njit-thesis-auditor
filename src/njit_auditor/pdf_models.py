"""Layout-aware PDF models used by Phase 2 extraction."""

from __future__ import annotations

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
    horizontal_rules: list[BBox] = Field(default_factory=list)


class PdfDocument(BaseModel):
    """Extracted PDF document layout model."""

    path: str
    pages: list[PdfPage] = Field(default_factory=list)
