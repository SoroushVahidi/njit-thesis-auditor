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


class PdfTextSpan(BaseModel):
    """Smallest text run with style metadata."""

    text: str
    bbox: BBox
    font: str | None = None
    size: float | None = None
    bold: bool = False
    italic: bool = False


class PdfTextLine(BaseModel):
    """Line of text spans."""

    spans: list[PdfTextSpan] = Field(default_factory=list)
    bbox: BBox
    text: str


class PdfTextBlock(BaseModel):
    """Block of one or more text lines."""

    lines: list[PdfTextLine] = Field(default_factory=list)
    bbox: BBox
    text: str


class PdfPage(BaseModel):
    """Single PDF page with geometric and text-block content."""

    page_number: int
    width: float
    height: float
    text_blocks: list[PdfTextBlock] = Field(default_factory=list)


class PdfDocument(BaseModel):
    """Extracted PDF document layout model."""

    path: str
    pages: list[PdfPage] = Field(default_factory=list)
