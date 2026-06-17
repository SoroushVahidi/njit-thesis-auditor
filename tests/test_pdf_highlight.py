"""Tests for highlighted-PDF generation, including degenerate-bbox safety."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_highlight import build_highlighted_pdf, is_drawable_bbox


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


def test_build_highlighted_pdf_draws_valid_box(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source)
    original_bytes = source.read_bytes()

    build_highlighted_pdf(source, output, {2: [(100.0, 200.0, 300.0, 260.0)]})

    assert output.exists()
    with fitz.open(output) as doc:
        assert len(list(doc[1].annots() or [])) == 1
    # The original uploaded PDF must never be modified.
    assert source.read_bytes() == original_bytes


def test_build_highlighted_pdf_skips_degenerate_boxes_without_crashing(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source)

    build_highlighted_pdf(
        source,
        output,
        {
            1: [(100.0, 200.0, 100.0, 200.0)],  # degenerate point
            2: [(300.0, 260.0, 100.0, 200.0)],  # inverted
            3: [(float("nan"),) * 4],  # NaN
        },
    )

    assert output.exists()
    with fitz.open(output) as doc:
        for page in doc:
            assert list(page.annots() or []) == []


def test_build_highlighted_pdf_skips_out_of_range_pages_without_crashing(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source, page_count=2)

    build_highlighted_pdf(
        source,
        output,
        {0: [(100.0, 200.0, 300.0, 260.0)], 99: [(100.0, 200.0, 300.0, 260.0)]},
    )

    assert output.exists()
    with fitz.open(output) as doc:
        assert doc.page_count == 2


def test_build_highlighted_pdf_mixed_valid_and_degenerate_boxes_on_same_page(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "highlighted.pdf"
    _make_pdf(source)

    build_highlighted_pdf(
        source,
        output,
        {1: [(100.0, 200.0, 300.0, 260.0), (0.0, 0.0, 0.0, 0.0)]},
    )

    with fitz.open(output) as doc:
        assert len(list(doc[0].annots() or [])) == 1
