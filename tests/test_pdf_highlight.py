"""Tests for highlighted-PDF generation, including degenerate-bbox safety."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_highlight import (
    build_highlighted_pdf,
    clip_box_to_page,
    get_pdf_page_sizes,
    has_visible_highlight,
    is_drawable_bbox,
)


def _make_pdf(path: Path, page_count: int = 3) -> None:
    doc = fitz.open()
    for _ in range(page_count):
        doc.new_page(width=612, height=792)
    doc.save(path)
    doc.close()


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        ((100.0, 200.0, 300.0, 260.0), True),
        ((300.0, 260.0, 100.0, 200.0), False),  # inverted
        ((0.0, 0.0, 0.0, 0.0), False),  # zero-area
        ((100.0, 200.0, 100.0, 200.0), False),  # degenerate point
        ((float("nan"),) * 4, False),
        ((float("inf"),) * 4, False),
        ((-1000.0, -1000.0, -500.0, -500.0), True),  # off-page but still drawable
    ],
)
def test_is_drawable_bbox(box: tuple[float, float, float, float], expected: bool) -> None:
    assert is_drawable_bbox(box) is expected


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        ((100.0, 200.0, 300.0, 260.0), (100.0, 200.0, 300.0, 260.0)),  # fully on-page
        ((500.0, 700.0, 700.0, 850.0), (500.0, 700.0, 612.0, 792.0)),  # partial overlap, clipped
        ((-1000.0, -1000.0, -500.0, -500.0), None),  # entirely off-page
        ((1000.0, 1000.0, 1400.0, 1200.0), None),  # entirely off-page, other direction
        ((0.1, 0.1, 0.5, 0.5), None),  # normalized/wrong-coordinate-space: too thin once on-page
        ((300.0, 260.0, 100.0, 200.0), None),  # inverted, not drawable at all
    ],
)
def test_clip_box_to_page(
    box: tuple[float, float, float, float],
    expected: tuple[float, float, float, float] | None,
) -> None:
    assert clip_box_to_page(box, 612.0, 792.0) == expected


def test_has_visible_highlight_requires_bbox_and_page() -> None:
    assert has_visible_highlight(None, page=1) is False
    assert has_visible_highlight((1.0, 1.0, 50.0, 50.0), page=None) is False
    assert has_visible_highlight((1.0, 1.0, 50.0, 50.0), page=0) is False


def test_has_visible_highlight_rejects_out_of_range_page() -> None:
    assert has_visible_highlight((1.0, 1.0, 50.0, 50.0), page=5, page_count=3) is False
    assert has_visible_highlight((1.0, 1.0, 50.0, 50.0), page=3, page_count=3) is True


def test_has_visible_highlight_uses_page_size_when_known() -> None:
    on_page = (100.0, 200.0, 300.0, 260.0)
    off_page = (-1000.0, -1000.0, -500.0, -500.0)
    normalized = (0.1, 0.1, 0.5, 0.5)
    assert has_visible_highlight(on_page, page=1, page_size=(612.0, 792.0)) is True
    assert has_visible_highlight(off_page, page=1, page_size=(612.0, 792.0)) is False
    assert has_visible_highlight(normalized, page=1, page_size=(612.0, 792.0)) is False


def test_has_visible_highlight_degrades_gracefully_without_page_geometry() -> None:
    # No page_count/page_size available (e.g. PDF unreadable at render time):
    # fall back to a shape-only check rather than blocking the highlight.
    assert has_visible_highlight((100.0, 200.0, 300.0, 260.0), page=1) is True
    assert has_visible_highlight((300.0, 260.0, 100.0, 200.0), page=1) is False


def test_get_pdf_page_sizes(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.new_page(width=300, height=400)
    doc.save(source)
    doc.close()

    assert get_pdf_page_sizes(source) == [(612.0, 792.0), (300.0, 400.0)]


def test_build_highlighted_pdf_draws_valid_box(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source)
    original_bytes = source.read_bytes()

    result = build_highlighted_pdf(source, output, {2: [(100.0, 200.0, 300.0, 260.0)]})

    assert result.drawn_count == 1
    assert result.skipped_count == 0
    assert result.pages_highlighted == [2]
    assert result.has_highlight is True
    assert output.exists()
    with fitz.open(output) as doc:
        assert len(list(doc[1].annots() or [])) == 1
    # The original uploaded PDF must never be modified.
    assert source.read_bytes() == original_bytes


def test_build_highlighted_pdf_skips_degenerate_boxes_without_writing_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source)

    result = build_highlighted_pdf(
        source,
        output,
        {
            1: [(100.0, 200.0, 100.0, 200.0)],  # degenerate point
            2: [(300.0, 260.0, 100.0, 200.0)],  # inverted
            3: [(float("nan"),) * 4],  # NaN
        },
    )

    assert result.drawn_count == 0
    assert result.skipped_count == 3
    assert result.pages_highlighted == []
    assert result.has_highlight is False
    # Nothing was drawn, so no "highlighted" copy is written at all.
    assert not output.exists()


def test_build_highlighted_pdf_skips_out_of_range_pages_without_writing_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source, page_count=2)

    result = build_highlighted_pdf(
        source,
        output,
        {0: [(100.0, 200.0, 300.0, 260.0)], 99: [(100.0, 200.0, 300.0, 260.0)]},
    )

    assert result.drawn_count == 0
    assert result.skipped_count == 2
    assert result.has_highlight is False
    assert not output.exists()


def test_build_highlighted_pdf_mixed_valid_and_degenerate_boxes_on_same_page(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source)

    result = build_highlighted_pdf(
        source,
        output,
        {1: [(100.0, 200.0, 300.0, 260.0), (0.0, 0.0, 0.0, 0.0)]},
    )

    assert result.drawn_count == 1
    assert result.skipped_count == 1
    assert result.pages_highlighted == [1]
    with fitz.open(output) as doc:
        assert len(list(doc[0].annots() or [])) == 1


def test_build_highlighted_pdf_clips_partially_off_page_box(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source, page_count=1)

    result = build_highlighted_pdf(source, output, {1: [(500.0, 700.0, 700.0, 850.0)]})

    # Exact clipped coordinates are covered by test_clip_box_to_page; here we
    # only confirm the partially off-page box still produces a real,
    # on-page annotation rather than being dropped outright.
    assert result.drawn_count == 1
    assert result.has_highlight is True
    with fitz.open(output) as doc:
        assert len(list(doc[0].annots() or [])) == 1


def test_build_highlighted_pdf_multi_box_finding_draws_all_valid_boxes(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source, page_count=1)

    result = build_highlighted_pdf(
        source,
        output,
        {
            1: [
                (50.0, 50.0, 150.0, 100.0),
                (200.0, 200.0, 300.0, 260.0),
                (0.0, 0.0, 0.0, 0.0),  # invalid, must be skipped
            ]
        },
    )

    assert result.drawn_count == 2
    assert result.skipped_count == 1
    with fitz.open(output) as doc:
        assert len(list(doc[0].annots() or [])) == 2
