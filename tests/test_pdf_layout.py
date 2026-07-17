from pathlib import Path

import fitz

from njit_auditor.pdf_layout import (
    _join_content_span_texts,
    join_content_span_texts,
    load_pdf_layout,
)
from njit_auditor.pdf_models import BBox, PdfTextSpan


def _make_simple_pdf(path: Path, text: str = "Hello PDF", x: float = 120, y: float = 120) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((x, y), text, fontsize=12)
    doc.save(path)
    doc.close()


def _span(text: str, x0: float, x1: float, *, y0: float = 100.0, y1: float = 112.0,
          size: float = 12.0) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
        font="Times-Bold",
        size=size,
        bold=True,
        italic=False,
    )


def test_pdf_layout_loads_page_size_and_blocks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "simple.pdf"
    _make_simple_pdf(pdf_path, text="Sample")
    model = load_pdf_layout(str(pdf_path))
    assert model.pages
    assert model.pages[0].width == 612
    assert model.pages[0].height == 792
    assert model.pages[0].text_blocks


def test_join_content_spans_inserts_space_for_word_gaps() -> None:
    """Adjacent content spans with a word-sized gap reconstruct as separate words."""
    spans = [
        _span("in", 100.0, 110.0),
        _span("power", 114.5, 140.0),  # ~4.5pt gap at 12pt
        _span("systems", 144.5, 180.0),
    ]
    assert _join_content_span_texts(spans) == "in power systems"


def test_join_content_spans_and_performance_pattern() -> None:
    spans = [
        _span("and", 100.0, 120.0),
        _span("Performance", 124.5, 190.0),
    ]
    assert _join_content_span_texts(spans) == "and Performance"


def test_join_content_spans_skips_subscript_vertical_offset() -> None:
    """Super/subscript spans that abut horizontally must not gain a fake space."""
    base = _span("Π", 100.0, 110.0, y0=100.0, y1=112.0, size=12.0)
    sub = _span("Jet", 110.0, 125.0, y0=105.0, y1=113.0, size=8.0)
    assert _join_content_span_texts([base, sub]) == "ΠJet"


def test_pdf_layout_restores_spaces_from_separated_word_spans(tmp_path: Path) -> None:
    """Geometry-aware join recovers spaces even when line.text is still glued."""
    from njit_auditor.pdf_models import BBox, PdfTextLine

    spans = [
        _span("Graph", 100.0, 140.0),
        _span("Attention", 144.5, 200.0),
        _span("in", 204.5, 214.0),
        _span("power", 218.5, 250.0),
        _span("systems", 254.5, 300.0),
    ]
    # Historical line.text remains concatenated when whitespace spans are dropped.
    glued = PdfTextLine(
        spans=spans,
        bbox=BBox(x0=100.0, y0=100.0, x1=300.0, y1=112.0),
        text="GraphAttentioninpowersystems",
    )
    assert glued.text == "GraphAttentioninpowersystems"
    assert join_content_span_texts(glued.spans) == "Graph Attention in power systems"
