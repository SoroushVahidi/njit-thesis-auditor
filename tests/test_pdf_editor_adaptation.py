"""Synthetic-only regression tests for the optional upstream editor adapter."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from pypdf import PdfReader

from scripts.evaluate_synthetic_obfuscation import evaluate_pair
from scripts.experimental_pdf_engine_adapter import (
    UnsupportedEditorPDF,
    _planned_lines,
    transform_with_pdf_edit_engine,
)
from scripts.generate_synthetic_obfuscation_fixtures import generate_fixtures


def _planted_pdf(path: Path) -> None:
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((108, 100), "TABLE OF CONTENTS", fontname="hebo", fontsize=14)
        page.insert_text((108, 160), "DR_ASTRA_9C73 studies quasar secrets.", fontsize=12)
        page.insert_text((300, 736), "i", fontsize=12)
        doc.set_metadata({"title": "SYNTHETIC Quasar Secrets", "author": "Dr Astra"})
        doc.save(path, garbage=4, deflate=True)


def test_preflight_rejects_incremental_history(tmp_path: Path) -> None:
    source = tmp_path / "incremental.pdf"
    _planted_pdf(source)
    with fitz.open(source) as doc:
        doc.set_metadata({"title": "SYNTHETIC amended history"})
        doc.saveIncr()
    with pytest.raises(UnsupportedEditorPDF, match="Incremental"):
        _planned_lines(source, "random")


@pytest.mark.parametrize(
    "feature",
    [
        "custom_metadata", "hidden_layer", "invisible_operator", "actual_text",
        "compatibility_operator", "font_payload",
        "show_outside_text", "show_without_font", "zero_font", "off_page_text",
        "fontmap_payload", "font_encoding_payload",
        "page_tree_payload",
        "catalog_info_payload",
        "font_alias_payload",
    ],
)
def test_preflight_rejects_unverified_pdf_surfaces(tmp_path: Path, feature: str) -> None:
    source = tmp_path / "source.pdf"
    modified = tmp_path / f"{feature}.pdf"
    _planted_pdf(source)
    with fitz.open(source) as doc:
        if feature == "custom_metadata":
            _kind, reference = doc.xref_get_key(-1, "Info")
            doc.xref_set_key(int(reference.split()[0]), "CustomSecret", "(SYNTHETIC hidden)")
        elif feature == "hidden_layer":
            doc.add_ocg("SYNTHETIC hidden layer")
        elif feature == "invisible_operator":
            xref = doc[0].get_contents()[0]
            doc.update_stream(xref, (doc.xref_stream(xref) or b"") + b"\n3 Tr\n")
        elif feature == "actual_text":
            xref = doc[0].get_contents()[0]
            marked = b"\n/Span << /ActualText (SYNTHETIC_SECRET_ACTUALTEXT_9C73) >> BDC EMC\n"
            doc.update_stream(xref, (doc.xref_stream(xref) or b"") + marked)
        elif feature == "compatibility_operator":
            xref = doc[0].get_contents()[0]
            hidden = b"\nBX (SYNTHETIC_SECRET_BX_STREAM_9C73) XSECRET EX\n"
            doc.update_stream(xref, (doc.xref_stream(xref) or b"") + hidden)
        elif feature in {
            "show_outside_text", "show_without_font", "zero_font", "off_page_text"
        }:
            xref = doc[0].get_contents()[0]
            hidden = {
                "show_outside_text": b"\n(SYNTHETIC_SECRET_OUTSIDE_BT_9C73) Tj\n",
                "show_without_font": b"\nBT (SYNTHETIC_SECRET_NO_FONT_9C73) Tj ET\n",
                "zero_font": (
                    b"\nBT /helv 0 Tf 1 0 0 1 100 100 Tm "
                    b"(SYNTHETIC_SECRET_ZERO_FONT_9C73) Tj ET\n"
                ),
                "off_page_text": (
                    b"\nBT /helv 12 Tf 1 0 0 1 10000 10000 Tm "
                    b"(SYNTHETIC_SECRET_OFFPAGE_9C73) Tj ET\n"
                ),
            }[feature]
            doc.update_stream(xref, (doc.xref_stream(xref) or b"") + hidden)
        elif feature == "fontmap_payload":
            resource_xref = int(doc.xref_get_key(doc[0].xref, "Resources")[1].split()[0])
            doc.xref_set_key(
                resource_xref, "Font",
                "<</hebo 5 0 R/helv 7 0 R/Secret (SYNTHETIC_FONTMAP_SECRET)>>",
            )
        elif feature == "font_encoding_payload":
            xref = doc[0].get_fonts(full=True)[0][0]
            doc.xref_set_key(
                xref, "Encoding",
                "<</Type/Encoding/BaseEncoding/WinAnsiEncoding"
                "/Differences[255/SYNTHETIC_SECRET_ENCODING_9C73]>>",
            )
        elif feature == "page_tree_payload":
            tree_xref = int(doc.xref_get_key(doc.pdf_catalog(), "Pages")[1].split()[0])
            doc.xref_set_key(tree_xref, "Secret", "(SYNTHETIC_SECRET_PAGETREE_9C73)")
        elif feature == "catalog_info_payload":
            doc.xref_set_key(
                doc.pdf_catalog(), "Info",
                "<</Producer(SYNTHETIC_SECRET_CATALOG_INFO_9C73)>>",
            )
        elif feature == "font_alias_payload":
            resource_xref = int(doc.xref_get_key(doc[0].xref, "Resources")[1].split()[0])
            doc.xref_set_key(
                resource_xref, "Font",
                "<</hebo 5 0 R/SYNTHETIC_SECRET_FONTNAME_9C73 7 0 R>>",
            )
            for xref in doc[0].get_contents():
                stream = doc.xref_stream(xref) or b""
                doc.update_stream(
                    xref, stream.replace(b"/helv", b"/SYNTHETIC_SECRET_FONTNAME_9C73")
                )
        else:
            xref = doc[0].get_fonts(full=True)[0][0]
            doc.xref_set_key(xref, "CustomSecret", "(SYNTHETIC hidden font data)")
        doc.save(modified, garbage=4, deflate=True)
    with pytest.raises(UnsupportedEditorPDF):
        _planned_lines(modified, "random")


@pytest.mark.parametrize("feature", ["annotation", "attachment", "drawing", "image"])
def test_preflight_rejects_nontext_content(tmp_path: Path, feature: str) -> None:
    source = tmp_path / f"{feature}.pdf"
    _planted_pdf(source)
    with fitz.open(source) as doc:
        page = doc[0]
        if feature == "annotation":
            page.add_text_annot((40, 40), "SYNTHETIC hidden note")
        elif feature == "attachment":
            doc.embfile_add("secret.txt", b"SYNTHETIC hidden attachment")
        elif feature == "drawing":
            page.draw_rect(fitz.Rect(50, 50, 60, 60))
        else:
            pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 2, 2), False)
            pixmap.clear_with(255)
            page.insert_image(fitz.Rect(50, 50, 60, 60), pixmap=pixmap)
        modified = tmp_path / f"{feature}-modified.pdf"
        doc.save(modified, garbage=4, deflate=True)
    with pytest.raises((UnsupportedEditorPDF, ValueError)):
        _planned_lines(modified, "random")


def test_structural_strategy_removes_planted_text_and_metadata(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    source = tmp_path / "planted.pdf"
    output = tmp_path / "output.pdf"
    _planted_pdf(source)
    summary = transform_with_pdf_edit_engine(source, output, "structural")
    assert summary.font_preserved_edits == summary.edited_lines
    with fitz.open(output) as doc:
        extracted = "\n".join(page.get_text() for page in doc)
        objects = "\n".join(
            doc.xref_object(xref)
            + (doc.xref_stream(xref) or b"").decode("latin-1", errors="ignore")
            for xref in range(1, doc.xref_length())
        )
        assert doc.metadata["author"] == ""
        assert doc.embfile_count() == 0
    pypdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    for planted in ("DR_ASTRA_9C73", "Quasar Secrets", "Dr Astra", "quasar secrets"):
        assert planted.lower() not in extracted.lower()
        assert planted.lower() not in pypdf_text.lower()
        assert planted.lower() not in objects.lower()
        assert planted.lower().encode() not in output.read_bytes().lower()
    assert "TABLE OF CONTENTS" in extracted  # Intentional structural disclosure.


def test_source_trailer_id_is_replaced(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    pikepdf = pytest.importorskip("pikepdf")
    source = tmp_path / "source.pdf"
    planted = tmp_path / "planted.pdf"
    output = tmp_path / "output.pdf"
    _planted_pdf(source)
    secret = b"SECRET_ID_9C73_AB"
    with pikepdf.Pdf.open(source) as pdf:
        pdf.trailer.ID = pikepdf.Array([pikepdf.String(secret), pikepdf.String(secret)])
        pdf.save(planted)
    transform_with_pdf_edit_engine(planted, output, "structural")
    assert secret not in output.read_bytes()
    with pikepdf.Pdf.open(output) as pdf:
        assert bytes(pdf.trailer.ID[0]) != secret


def test_structural_strategy_preserves_synthetic_findings(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    sources = generate_fixtures(tmp_path)
    matched = original = 0
    for source in sources:
        output = source.with_name(source.stem + "_edited.pdf")
        transform_with_pdf_edit_engine(source, output, "structural")
        result = evaluate_pair(source, output)
        assert result["page_sizes_identical"]
        assert result["original_lines"] == result["transformed_lines"]
        assert result["font_name_matches"] == result["original_characters"]
        assert result["max_font_size_delta_pt"] == 0
        matched += result["matched_findings"]
        original += result["original_findings"]
    assert original == 38
    assert matched >= 34
