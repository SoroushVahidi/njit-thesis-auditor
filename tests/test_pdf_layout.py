from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout


def _make_simple_pdf(path: Path, text: str = "Hello PDF", x: float = 120, y: float = 120) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((x, y), text, fontsize=12)
    doc.save(path)
    doc.close()


def test_pdf_layout_loads_page_size_and_blocks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "simple.pdf"
    _make_simple_pdf(pdf_path, text="Sample")
    model = load_pdf_layout(str(pdf_path))
    assert model.pages
    assert model.pages[0].width == 612
    assert model.pages[0].height == 792
    assert model.pages[0].text_blocks
