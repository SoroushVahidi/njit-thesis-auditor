"""R011 margin geometry on landscape and ``/Rotate`` pages (synthetic PDFs only).

NJIT margins belong to the bound portrait sheet (1.5 in binding edge, 1 in
elsewhere) and page numbers stay in portrait on landscape pages, so a landscape
page is the sheet turned sideways: the binding margin lies along a long edge,
identified by the portrait page number's text direction.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox
from njit_auditor.polished_comments import _p011_margin_comment
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    LEFT_MARGIN_PT,
    RIGHT_MARGIN_PT,
    TOP_MARGIN_PT,
    _margin_frame,
    run_pdf_margin_rule,
)

LANDSCAPE_W, LANDSCAPE_H = 792.0, 612.0
BODY = "Synthetic landscape table row with enough words to be a real line"


def _warnings(path: Path) -> list:
    model = load_pdf_layout(str(path))
    return [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]


def _landscape_pdf(
    tmp_path: Path,
    lines: list[tuple[float, float, str]],
    *,
    page_number: str | None = "81",
    page_number_rotate: int = 270,
) -> Path:
    """Intrinsic landscape page; the page number "stays portrait" (vertical text).

    ``page_number_rotate=270`` gives text running down the page (the sheet turned
    clockwise, portrait bottom on the left edge); ``90`` runs up (turned
    counter-clockwise, portrait bottom on the right edge).
    """
    doc = fitz.open()
    page = doc.new_page(width=LANDSCAPE_W, height=LANDSCAPE_H)
    for x, y, text in lines:
        page.insert_text((x, y), text, fontsize=11)
    if page_number is not None:
        x = 50.0 if page_number_rotate == 270 else LANDSCAPE_W - 50.0
        page.insert_text((x, LANDSCAPE_H / 2), page_number, fontsize=12, rotate=page_number_rotate)
    path = tmp_path / "landscape.pdf"
    doc.save(path)
    doc.close()
    return path


def test_portrait_frame_is_the_existing_constants(tmp_path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=612, height=792).insert_text((120, 300), BODY, fontsize=11)
    path = tmp_path / "portrait.pdf"
    doc.save(path)
    frame = _margin_frame(load_pdf_layout(str(path)).pages[0])
    assert (frame.allowed_x0, frame.allowed_y0, frame.allowed_x1, frame.allowed_y1) == (
        LEFT_MARGIN_PT,
        TOP_MARGIN_PT,
        612 - RIGHT_MARGIN_PT,
        792 - BOTTOM_MARGIN_PT,
    )
    assert frame.binding_edge == "left" and frame.page_number_bands == ()


def test_page_number_direction_identifies_binding_edge(tmp_path: Path) -> None:
    path = _landscape_pdf(tmp_path, [(80, 130, BODY)])
    page = load_pdf_layout(str(path)).pages[0]
    numbers = [line for block in page.text_blocks for line in block.lines if line.text == "81"]
    assert numbers and numbers[0].line_dir == pytest.approx((0.0, 1.0), abs=1e-6)
    frame = _margin_frame(page)
    assert frame.binding_edge == "top"
    assert (frame.allowed_x0, frame.allowed_y0) == (BOTTOM_MARGIN_PT, LEFT_MARGIN_PT)


def test_correctly_placed_landscape_content_and_page_number_do_not_warn(tmp_path: Path) -> None:
    # Body text 1 in from the left (portrait bottom) edge, below the 1.5 in
    # binding edge at the top; portrait page number in the left band.
    path = _landscape_pdf(tmp_path, [(75, 130, BODY), (75, 520, BODY)])
    assert _warnings(path) == []


@pytest.mark.parametrize(
    ("x", "y", "side"),
    [
        (40.0, 300.0, "left_margin"),  # portrait-bottom edge (1 in)
        (560.0, 300.0, "right_margin"),  # runs past 792 - 72
        (120.0, 100.0, "top_margin"),  # inside the 1.5 in binding edge
        (120.0, 570.0, "bottom_margin"),  # past 612 - 72 by more than the bottom tolerance
    ],
)
def test_genuine_landscape_violations_still_warn(
    tmp_path: Path, x: float, y: float, side: str
) -> None:
    path = _landscape_pdf(tmp_path, [(x, y, BODY)])
    sides = [f.details["side"] for f in _warnings(path)]
    assert sides == [side]


def test_binding_side_finding_is_labelled_and_highlights_the_offending_line(
    tmp_path: Path,
) -> None:
    path = _landscape_pdf(tmp_path, [(120, 100, BODY), (120, 300, BODY)])
    (finding,) = _warnings(path)
    details = finding.details
    assert details["side"] == "top_margin"
    assert details["page_orientation"] == "landscape" and details["binding_edge"] == "top"
    comment = _p011_margin_comment(page=finding.page, details=details)
    assert "top margin (the 1.5-inch binding margin on this landscape page)" in comment
    x0, y0, x1, y1 = (float(v) for v in details["bbox"].split(","))
    assert y1 < 120 and x0 >= 110  # only the offending line, not the page number at x~50
    boundary = [float(v) for v in details["margin_boundary_bbox"].split(",")]
    assert boundary[1] < LEFT_MARGIN_PT < boundary[3]  # guide drawn at the 1.5 in binding line
    assert float(details["worst_overflow_pt"]) == pytest.approx(LEFT_MARGIN_PT - y0, abs=0.05)


def test_counter_clockwise_sheet_puts_binding_at_the_bottom(tmp_path: Path) -> None:
    path = _landscape_pdf(tmp_path, [(120, 520, BODY), (120, 130, BODY)], page_number_rotate=90)
    frame = _margin_frame(load_pdf_layout(str(path)).pages[0])
    assert frame.binding_edge == "bottom"
    sides = [f.details["side"] for f in _warnings(path)]
    assert sides == ["bottom_margin"]  # 520 is inside 612 - 108


def test_undetermined_binding_edge_reports_only_certain_violations(tmp_path: Path) -> None:
    # No portrait page number: the binding edge could be top or bottom, so only
    # content inside the 1 in margin on every edge is certain.
    uncertain = _landscape_pdf(tmp_path, [(120, 100, BODY)], page_number=None)
    assert _margin_frame(load_pdf_layout(str(uncertain)).pages[0]).binding_edge == "undetermined"
    assert _warnings(uncertain) == []
    certain = _landscape_pdf(tmp_path, [(120, 60, BODY)], page_number=None)
    assert [f.details["side"] for f in _warnings(certain)] == ["top_margin"]


def _portrait_pdf(tmp_path: Path, name: str, rotation: int) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((120, 700), BODY, fontsize=11)  # valid portrait position
    page.insert_text((80, 400), BODY, fontsize=11)  # 1.5 in left-margin violation
    page.set_rotation(rotation)
    path = tmp_path / name
    doc.save(path)
    doc.close()
    return path


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_rotate_flag_does_not_change_the_verdict(tmp_path: Path, rotation: int) -> None:
    def summary(path: Path) -> list[tuple[str, str, str]]:
        return [
            (f.details["side"], f.details["worst_overflow_pt"], f.details["bbox"])
            for f in _warnings(path)
        ]

    plain = summary(_portrait_pdf(tmp_path, "plain.pdf", 0))
    rotated = summary(_portrait_pdf(tmp_path, f"rot{rotation}.pdf", rotation))
    assert plain == rotated
    assert [side for side, _, _ in rotated] == ["left_margin"]


def test_portrait_and_non_binding_side_labels_are_unchanged() -> None:
    from njit_auditor.p011_margin_presentation import margin_side_label

    assert margin_side_label({"side": "top_margin"}) == "top margin"
    assert margin_side_label({"side": "left_margin"}) == "left margin"
    landscape = {"side": "left_margin", "page_orientation": "landscape", "binding_edge": "top"}
    assert margin_side_label(landscape) == "left margin"
    assert margin_side_label({"side": "nowhere"}) == "required page margin"


def test_page_number_band_only_exempts_numeric_text() -> None:
    from njit_auditor.rules.pdf_margins import _in_page_number_band

    band = (BBox(x0=0.0, y0=0.0, x1=72.0, y1=612.0),)
    inside = BBox(x0=43.0, y0=300.0, x1=56.0, y1=315.0)
    assert _in_page_number_band("81", inside, band)
    assert not _in_page_number_band("Table A.1", inside, band)
    assert not _in_page_number_band("81", BBox(x0=60.0, y0=300.0, x1=90.0, y1=315.0), band)
    assert not _in_page_number_band("81", inside, ())
