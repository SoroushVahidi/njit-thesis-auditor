"""Synthetic-only checks for the bounded PDF text replacement experiment."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest
import reportlab
from pypdf import PdfReader

from njit_auditor.experimental_pdf_text import UnsupportedPDF, transform_synthetic_pdf
from scripts.evaluate_synthetic_obfuscation import evaluate_pair
from scripts.generate_synthetic_obfuscation_fixtures import generate_fixtures


@pytest.mark.parametrize("fixture_index", [0, 1, 2])
def test_synthetic_layout_and_audit_comparison(tmp_path: Path, fixture_index: int) -> None:
    source = generate_fixtures(tmp_path)[fixture_index]
    transformed = tmp_path / "transformed.pdf"
    summary = transform_synthetic_pdf(source, transformed)
    report = evaluate_pair(source, transformed)

    assert summary.pages == report["pages"]
    assert summary.replaced_characters > 0
    assert summary.max_glyph_width_delta_pt <= 0.25
    assert report["page_sizes_identical"]
    assert report["original_blocks"] == report["transformed_blocks"]
    assert report["original_lines"] == report["transformed_lines"]
    assert report["original_characters"] == report["transformed_characters"]
    assert report["font_name_matches"] == report["original_characters"]
    assert report["max_font_size_delta_pt"] == 0
    assert report["max_character_bbox_delta_pt"] <= 0.25
    assert report["max_line_bbox_delta_pt"] <= 0.25

    # Matching geometry is not enough: word-dependent findings disappear.
    assert report["lost_findings"] > 0
    assert report["per_rule"]["P038"]["original"] > 0
    assert report["per_rule"]["P038"]["transformed"] == 0

    checks = report["content_checks"]
    assert checks["original_words_5plus_in_extracted_output"] == []
    assert checks["original_words_5plus_in_pypdf_output"] == []
    assert checks["original_lines_in_pdf_objects"] == []
    assert not checks["source_title_in_output_metadata"]
    assert not checks["source_title_in_output_bytes"]
    assert all(checks[key] == 0 for key in (
        "output_attachments", "pypdf_attachments", "output_images", "output_annotations",
        "output_links",
    ))
    with fitz.open(transformed) as doc:
        assert "QUASAR" not in "\n".join(page.get_text() for page in doc)
        assert doc.metadata["author"] == ""
    assert "QUASAR" not in "\n".join(page.extract_text() for page in PdfReader(transformed).pages)


@pytest.mark.parametrize(
    "feature",
    ["unmarked", "drawing", "image", "font", "annotation", "rotation", "attachment", "link"],
)
def test_unsupported_features_leave_no_output(tmp_path: Path, feature: str) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((108, 130), "A synthetic test line.", fontname="helv", fontsize=12)
    doc.set_metadata({"title": "SYNTHETIC unsupported-case test"})
    if feature == "unmarked":
        doc.set_metadata({"title": "Unmarked source"})
    elif feature == "drawing":
        page.draw_rect(fitz.Rect(100, 150, 140, 170), color=(0, 0, 0))
    elif feature == "image":
        pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
        page.insert_image(fitz.Rect(100, 150, 120, 170), pixmap=pixmap)
    elif feature == "font":
        fontfile = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        page.insert_font(fontname="custom", fontfile=str(fontfile))
        page.insert_text((108, 160), "Custom font", fontname="custom", fontsize=12)
    elif feature == "annotation":
        page.add_text_annot((100, 160), "A synthetic note")
    elif feature == "rotation":
        page.set_rotation(90)
    elif feature == "attachment":
        doc.embfile_add("note.txt", b"synthetic attachment")
    elif feature == "link":
        page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(100, 100, 140, 130), "uri": "https://example.invalid"})
    doc.save(source)
    doc.close()

    with pytest.raises(UnsupportedPDF):
        transform_synthetic_pdf(source, output)
    assert not output.exists()


def test_transform_refuses_to_overwrite(tmp_path: Path) -> None:
    source = generate_fixtures(tmp_path)[0]
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"keep this file")
    with pytest.raises(FileExistsError):
        transform_synthetic_pdf(source, output)
    assert output.read_bytes() == b"keep this file"
