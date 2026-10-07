"""PdfReadingFrame: box, reading-frame and policy geometry (synthetic only).

See ``docs/architecture/pdf_rotation_frames_adr.md``. Box space is the
unrotated, CropBox-relative space extracted boxes live in; the reading frame is
box space turned by the inferred reading rotation; the displayed size
(``PdfPage.width``/``height``) is presentation geometry and must not leak in.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfPage, PdfReadingFrame, PdfTextBlock, PdfTextLine

UPRIGHT = (1.0, 0.0)
# Writing directions (unrotated space) that read upright after /Rotate R.
UPRIGHT_AFTER = {90: (0.0, -1.0), 180: (-1.0, 0.0), 270: (0.0, 1.0)}


def _page(
    display: tuple[float, float], rotation: int, direction: tuple[float, float] = UPRIGHT
) -> PdfPage:
    width, height = display
    line = PdfTextLine(
        bbox=BBox(x0=100, y0=100, x1=300, y1=112),
        text="Synthetic body text that sets the reading direction of the page",
        line_dir=direction,
    )
    return PdfPage(
        page_number=1,
        width=width,
        height=height,
        page_rotation=rotation,
        is_visually_landscape=width > height * 1.02,
        text_blocks=[PdfTextBlock(bbox=line.bbox, text=line.text, lines=[line])],
    )


def test_rotate_0_portrait() -> None:
    frame = PdfReadingFrame.for_page(_page((612, 792), 0))
    assert frame.box_size == frame.reading_size == (612, 792)
    assert (frame.page_rotation, frame.reading_rotation) == (0, 0)
    assert frame.policy_orientation == "portrait" and not frame.is_landscape


def test_rotate_0_landscape() -> None:
    frame = PdfReadingFrame.for_page(_page((792, 612), 0))
    assert frame.box_size == frame.reading_size == (792, 612)
    assert frame.policy_orientation == "landscape" and frame.is_landscape


@pytest.mark.parametrize("rotation", (90, 270))
def test_viewer_only_quarter_turn_keeps_portrait_reading_frame(rotation: int) -> None:
    # Upright portrait content; the viewer shows a sideways (landscape) sheet.
    page = _page((792, 612), rotation)
    assert page.is_visually_landscape
    frame = PdfReadingFrame.for_page(page)
    assert frame.page_rotation == rotation
    assert frame.reading_rotation == 0
    assert frame.box_size == frame.reading_size == (612, 792)
    assert frame.policy_orientation == "portrait"


@pytest.mark.parametrize("rotation", (90, 270))
def test_viewer_only_quarter_turn_keeps_landscape_reading_frame(rotation: int) -> None:
    # Upright intrinsic-landscape content; the viewer shows a portrait sheet.
    page = _page((612, 792), rotation)
    assert not page.is_visually_landscape
    frame = PdfReadingFrame.for_page(page)
    assert frame.reading_rotation == 0
    assert frame.reading_size == (792, 612)
    assert frame.policy_orientation == "landscape"


@pytest.mark.parametrize("rotation", (90, 270))
def test_pdflscape_reading_frame_is_landscape(rotation: int) -> None:
    # Portrait MediaBox, content drawn sideways so it reads upright as displayed.
    frame = PdfReadingFrame.for_page(_page((792, 612), rotation, UPRIGHT_AFTER[rotation]))
    assert frame.box_size == (612, 792)
    assert frame.reading_rotation == rotation
    assert frame.reading_size == (792, 612)
    assert frame.policy_orientation == "landscape"


@pytest.mark.parametrize("direction", (UPRIGHT, UPRIGHT_AFTER[180]))
def test_rotate_180_keeps_dimensions(direction: tuple[float, float]) -> None:
    frame = PdfReadingFrame.for_page(_page((612, 792), 180, direction))
    assert frame.reading_rotation == (0 if direction == UPRIGHT else 180)
    assert frame.box_size == frame.reading_size == (612, 792)
    assert frame.policy_orientation == "portrait"
    box = BBox(x0=10, y0=20, x1=110, y1=60)
    expected = box if direction == UPRIGHT else BBox(x0=502, y0=732, x1=602, y1=772)
    assert frame.to_reading(box) == expected


@pytest.mark.parametrize("reading", (0, 90, 180, 270))
def test_box_reading_box_round_trip(reading: int) -> None:
    frame = PdfReadingFrame(
        box_width=612, box_height=792, page_rotation=reading, reading_rotation=reading
    )
    box = BBox(x0=72.5, y0=101.25, x1=300.0, y1=180.75)
    turned = frame.to_reading(box)
    width, height = frame.reading_size
    assert 0 <= turned.x0 < turned.x1 <= width and 0 <= turned.y0 < turned.y1 <= height
    assert frame.from_reading(turned) == box


def _content_turned_pdf(path: Path, rotation: int, cropbox: fitz.Rect | None) -> Path:
    """A page whose text reads upright only after ``/Rotate``; optional CropBox."""
    src = fitz.open()
    upright = src.new_page(width=792, height=612)
    for k in range(6):
        upright.insert_text((108, 120 + 20 * k), "Synthetic body text for tests.", fontsize=12)
    out = fitz.open()
    page = out.new_page(width=612, height=792)
    page.show_pdf_page(page.rect, src, 0, rotate=rotation)
    if cropbox is not None:
        page.set_cropbox(cropbox)
    page.set_rotation(rotation)
    out.save(path)
    return path


@pytest.mark.parametrize("cropbox", (None, fitz.Rect(20, 30, 590, 770)))
@pytest.mark.parametrize("rotation", (90, 270))
def test_frame_matches_pymupdf_rotation_with_cropbox_offset(
    tmp_path: Path, rotation: int, cropbox: fitz.Rect | None
) -> None:
    path = _content_turned_pdf(tmp_path / "turned.pdf", rotation, cropbox)
    model = load_pdf_layout(str(path))
    frame = PdfReadingFrame.for_page(model.pages[0])
    with fitz.open(path) as doc:
        page = doc[0]
        assert frame.reading_rotation == rotation
        assert frame.reading_size == (page.rect.width, page.rect.height)
        assert frame.box_size == (page.rect.height, page.rect.width)
        assert frame.policy_orientation == "landscape"
        for block in model.pages[0].text_blocks:
            mine = frame.to_reading(block.bbox)
            theirs = fitz.Rect(block.bbox.x0, block.bbox.y0, block.bbox.x1, block.bbox.y1)
            theirs = theirs * page.rotation_matrix
            assert mine.x0 == pytest.approx(theirs.x0, abs=1e-3)
            assert mine.y0 == pytest.approx(theirs.y0, abs=1e-3)
            assert mine.x1 == pytest.approx(theirs.x1, abs=1e-3)
            assert mine.y1 == pytest.approx(theirs.y1, abs=1e-3)
            assert frame.from_reading(mine).x0 == pytest.approx(block.bbox.x0, abs=1e-6)


def test_frame_never_exposes_or_mutates_display_geometry() -> None:
    page = _page((792, 612), 90)
    before = page.model_dump()
    frame = PdfReadingFrame.for_page(page)
    assert page.model_dump() == before
    assert not any(
        name in {"width", "height", "display_size", "is_visually_landscape"} for name in dir(frame)
    )
