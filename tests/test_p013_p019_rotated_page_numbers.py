"""P013/P019 page-number geometry on ``/Rotate`` pages (synthetic PDFs only).

PyMuPDF reports text boxes in the page's unrotated, CropBox-relative space,
while ``PdfPage.width``/``height`` are the displayed (rotated) size. A pdflscape
landscape page keeps a portrait MediaBox with ``/Rotate 90`` (or 270), so its
portrait folio is an ordinary bottom-centre number in text space. Page-number
positions must be classified against bounds in that same space.

Every rotated variant here is built to look identical on screen to its
``/Rotate 0`` control (asserted by rendering), so the verdicts must agree.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfPage, text_space_size
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    detect_page_number_candidates,
    run_pdf_page_number_candidates_rule,
)

BODY = "Synthetic body sentence used only for page number geometry testing"
LANDSCAPE_PAGE = 4


def _centered_x(text: str, center: float) -> float:
    return center - fitz.get_text_length(text, fontsize=12) / 2


def _portrait(doc: fitz.Document, folio: str | None) -> None:
    page = doc.new_page(width=612, height=792)
    for k in range(20):
        page.insert_text((108, 110 + 26 * k), BODY, fontsize=12)
    if folio is not None:
        page.insert_text((_centered_x(folio, 306), 750), folio, fontsize=12)


def _landscape(
    doc: fitz.Document,
    folio: str | None,
    *,
    sheet: str,
    folio_center: float = 306.0,
    extra: list[tuple[float, float, str]] | None = None,
) -> None:
    """Intrinsic 792x612 page whose portrait folio stays on the sheet's portrait
    bottom: the left edge reading down for a clockwise-turned sheet, the right
    edge reading up for a counter-clockwise one."""
    page = doc.new_page(width=792, height=612)
    for k in range(14):
        page.insert_text((90, 130 + 26 * k), BODY + " wide table row", fontsize=12)
    for x, y, text in extra or []:
        page.insert_text((x, y), text, fontsize=12)
    if folio is None:
        return
    half = fitz.get_text_length(folio, fontsize=12) / 2
    if sheet == "cw":
        page.insert_text((40, folio_center - half), folio, fontsize=12, rotate=270)
    else:
        page.insert_text((752, folio_center + half), folio, fontsize=12, rotate=90)


def _with_rotation(src: fitz.Document, rotation: int, pages: set[int]) -> fitz.Document:
    """Re-encode *pages* (0-based) with ``/Rotate rotation`` so they display
    exactly as before: the displayed content is placed pre-rotated into an
    unrotated MediaBox, which is how pdflscape writes landscape pages."""
    out = fitz.open()
    for index, src_page in enumerate(src):
        if index not in pages or rotation == 0:
            out.insert_pdf(src, from_page=index, to_page=index)
            continue
        width, height = src_page.rect.width, src_page.rect.height
        if rotation % 180 == 90:
            width, height = height, width
        page = out.new_page(width=width, height=height)
        page.show_pdf_page(page.rect, src, index, rotate=rotation)
        page.set_rotation(rotation)
    return out


def _same_pixels(a: fitz.Document, b: fitz.Document) -> bool:
    for page_a, page_b in zip(a, b, strict=True):
        pix_a, pix_b = page_a.get_pixmap(dpi=30), page_b.get_pixmap(dpi=30)
        if (pix_a.width, pix_a.height, pix_a.samples) != (pix_b.width, pix_b.height, pix_b.samples):
            return False
    return True


def _build(
    tmp_path: Path,
    name: str,
    *,
    rotation: int = 0,
    sheet: str = "cw",
    landscape_folio: str | None = "4",
    folio_center: float = 306.0,
    extra: list[tuple[float, float, str]] | None = None,
) -> Path:
    src = fitz.open()
    for number in range(1, 8):
        if number == LANDSCAPE_PAGE:
            _landscape(src, landscape_folio, sheet=sheet, folio_center=folio_center, extra=extra)
        else:
            _portrait(src, str(number))
    control = fitz.open("pdf", src.tobytes())
    doc = _with_rotation(control, rotation, {LANDSCAPE_PAGE - 1})
    assert _same_pixels(control, doc)
    path = tmp_path / f"{name}.pdf"
    doc.save(path)
    return path


def _page_candidates(path: Path, page: int = LANDSCAPE_PAGE) -> list[tuple[str, str, str]]:
    model = load_pdf_layout(str(path))
    return [
        (c.text, c.position_type, c.location)
        for c in detect_page_number_candidates(model)
        if c.page_number == page
    ]


def _p019(path: Path) -> list[tuple[int | None, str]]:
    model = load_pdf_layout(str(path))
    return [(f.page, f.details["issue_type"]) for f in check_pdf_page_number_sequence(model)]


def _p013_page(path: Path, page: int = LANDSCAPE_PAGE) -> list[tuple[str, str]]:
    model = load_pdf_layout(str(path))
    return [
        (f.details["issue_type"], f.details["position_type"])
        for f in run_pdf_page_number_candidates_rule(model)
        if f.page == page
    ]


def test_text_space_size_swaps_only_quarter_turns() -> None:
    def page(rotation: int) -> PdfPage:
        return PdfPage(page_number=1, width=792.0, height=612.0, page_rotation=rotation)

    assert text_space_size(page(0)) == (792.0, 612.0)
    assert text_space_size(page(90)) == (612.0, 792.0)
    assert text_space_size(page(180)) == (792.0, 612.0)
    assert text_space_size(page(270)) == (612.0, 792.0)


def test_portrait_bottom_center_folio_is_unchanged(tmp_path: Path) -> None:
    path = _build(tmp_path, "portrait")
    assert _page_candidates(path, page=3) == [("3", "bottom_center", "bottom")]


@pytest.mark.parametrize(("sheet", "rotation"), [("cw", 90), ("ccw", 270)])
def test_pdflscape_folio_is_a_bottom_center_page_number(
    tmp_path: Path, sheet: str, rotation: int
) -> None:
    path = _build(tmp_path, f"pdflscape{rotation}", rotation=rotation, sheet=sheet)
    model = load_pdf_layout(str(path))
    assert model.pages[LANDSCAPE_PAGE - 1].page_rotation == rotation
    assert _page_candidates(path) == [("4", "bottom_center", "bottom")]
    assert _p013_page(path) == [("page_number_candidate", "bottom_center")]
    assert _p019(path) == []


@pytest.mark.parametrize(("sheet", "position"), [("cw", "left_center"), ("ccw", "right_center")])
def test_intrinsic_landscape_folio_keeps_the_edge_position(
    tmp_path: Path, sheet: str, position: str
) -> None:
    path = _build(tmp_path, f"intrinsic_{sheet}", sheet=sheet)
    assert _page_candidates(path) == [("4", position, position.split("_")[0])]
    assert _p019(path) == []


@pytest.mark.parametrize(("sheet", "rotation"), [("cw", 0), ("cw", 90), ("ccw", 0), ("ccw", 270)])
def test_missing_landscape_folio_is_still_reported(
    tmp_path: Path, sheet: str, rotation: int
) -> None:
    path = _build(tmp_path, "missing", rotation=rotation, sheet=sheet, landscape_folio=None)
    assert _page_candidates(path) == []
    assert _p019(path) == [(LANDSCAPE_PAGE, "missing_page_number")]


def test_misplaced_pdflscape_folio_is_not_accepted(tmp_path: Path) -> None:
    # On the sheet this is a bottom-left number, not the centred folio.
    path = _build(tmp_path, "misplaced", rotation=90, folio_center=150.0)
    assert [position for _, position, _ in _page_candidates(path)] == ["other"]
    assert _p019(path) == [(LANDSCAPE_PAGE, "missing_page_number")]


def test_turned_table_number_is_not_a_second_folio(tmp_path: Path) -> None:
    # A horizontal table number next to the folio band lands in the sheet's
    # bottom zone, but it runs across the sheet's writing direction.
    extra = [(80.0, 312.0, "57")]
    control = _build(tmp_path, "table_control", extra=extra)
    rotated = _build(tmp_path, "table_rotated", rotation=90, extra=extra)
    assert _page_candidates(control) == [("4", "left_center", "left")]
    assert _page_candidates(rotated) == [("4", "bottom_center", "bottom")]
    assert _p019(control) == _p019(rotated) == []


def test_number_near_displayed_top_edge_is_not_an_edge_folio(tmp_path: Path) -> None:
    # The landscape edge-folio path belongs to a landscape *text space*; on a
    # pdflscape sheet this number sits in the portrait sheet's left band.
    extra = [(200.0, 45.0, "12")]
    control = _build(tmp_path, "edge_control", extra=extra)
    rotated = _build(tmp_path, "edge_rotated", rotation=90, extra=extra)
    assert _p013_page(control) == [("page_number_candidate", "left_center")]
    assert _p013_page(rotated) == [("page_number_candidate", "bottom_center")]
    assert _p019(control) == _p019(rotated) == []


def test_wrong_folio_value_still_breaks_the_sequence(tmp_path: Path) -> None:
    path = _build(tmp_path, "wrong_value", rotation=90, landscape_folio="9")
    assert _page_candidates(path) == [("9", "bottom_center", "bottom")]
    assert "sequence_gap" in {issue for _, issue in _p019(path)}


@pytest.mark.parametrize("text", ["4.2", "123456"])
def test_non_page_number_text_is_not_a_folio(tmp_path: Path, text: str) -> None:
    path = _build(tmp_path, "non_folio", rotation=90, landscape_folio=text)
    assert _p013_page(path) == []
    assert (LANDSCAPE_PAGE, "missing_page_number") in _p019(path)


@pytest.mark.parametrize(("sheet", "rotation"), [("cw", 90), ("ccw", 270)])
def test_pixel_equivalent_encodings_agree_on_p019(
    tmp_path: Path, sheet: str, rotation: int
) -> None:
    control = _build(tmp_path, f"control_{sheet}", sheet=sheet)
    rotated = _build(tmp_path, f"rotated_{sheet}", rotation=rotation, sheet=sheet)
    assert _p019(control) == _p019(rotated) == []


def test_rotate_180_page_is_classified_in_text_space(tmp_path: Path) -> None:
    """A /Rotate 180 page has the same displayed and text-space size, so the
    fix does not change it: its upside-down-stored folio sits at the top of the
    text space and is accepted as a top-centre number. Reading-direction
    semantics for such pages are a separate policy question."""
    src = fitz.open()
    for number in range(1, 8):
        _portrait(src, str(number))
    control = fitz.open("pdf", src.tobytes())
    doc = _with_rotation(control, 180, {LANDSCAPE_PAGE - 1})
    assert _same_pixels(control, doc)
    path = tmp_path / "rot180.pdf"
    doc.save(path)
    assert _page_candidates(path) == [("4", "top_center", "top")]
    assert _p019(path) == []
