"""Reviewer annotation artwork must not become dissertation text."""

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule


def _lines(path: Path) -> list[str]:
    document = load_pdf_layout(str(path))
    return [line.text for block in document.pages[0].text_blocks for line in block.lines]


def test_annotation_label_is_excluded_but_authored_margin_overflow_survives(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "annotated.pdf"
    with fitz.open() as document:
        page = document.new_page(width=612, height=792)
        page.insert_text((120, 120), "Authored body content", fontsize=12)
        page.insert_text((510, 120), "Real overflow", fontsize=12)
        annotation = page.add_freetext_annot(
            fitz.Rect(290, 20, 390, 50), "Reviewer label", fontsize=10
        )
        annotation.update()
        document.save(pdf_path)

    with fitz.open(pdf_path) as document:
        assert "Reviewer label" in document[0].get_text()

    model = load_pdf_layout(str(pdf_path))
    lines = _lines(pdf_path)
    assert any("Authored body content" in line for line in lines)
    assert any("Real overflow" in line for line in lines)
    assert not any("Reviewer label" in line for line in lines)
    findings = run_pdf_margin_rule(model)
    assert any(f.details.get("side") == "right_margin" for f in findings)
    assert not any(f.details.get("side") == "top_margin" for f in findings)


def test_highlight_annotation_does_not_erase_underlying_page_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "highlighted.pdf"
    with fitz.open() as document:
        page = document.new_page(width=612, height=792)
        page.insert_text((120, 120), "Genuine dissertation text", fontsize=12)
        matches = page.search_for("Genuine dissertation text")
        assert len(matches) == 1
        annotation = page.add_highlight_annot(matches[0])
        annotation.update()
        document.save(pdf_path)

    assert any("Genuine dissertation text" in line for line in _lines(pdf_path))
