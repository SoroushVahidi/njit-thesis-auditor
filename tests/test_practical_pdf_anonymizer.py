"""Synthetic fixtures for the local, practical PDF content anonymizer."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from subprocess import run
from unittest.mock import patch

import pymupdf as fitz
import pytest
from pypdf import PdfReader

from njit_auditor.practical_pdf_anonymizer import UnsupportedPDF, anonymize
from scripts.generate_anonymizer_adversarial_fixtures import make_extended_thesis


@pytest.fixture(autouse=True)
def pinned_editor() -> None:
    pytest.importorskip("pdf_edit_engine")
    pytest.importorskip("pikepdf")


def _embedded_fixture(path: Path) -> Path:
    fonts = {
        "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "italic": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    }
    if not all(Path(font).is_file() for font in fonts.values()):
        pytest.skip("Synthetic DejaVu test fonts unavailable")
    with fitz.open() as doc:
        first = doc.new_page(width=612, height=792)
        for label, font in fonts.items():
            first.insert_font(fontname=label, fontfile=font)
        first.insert_text((108, 100), "ABSTRACT", fontname="bold", fontsize=14)
        first.insert_text(
            (108, 155),
            "Mira Fictional explores α β ∑ in a made-up study.",
            fontname="regular",
            fontsize=12,
        )
        first.insert_text(
            (144, 179),
            "A second invented line starts with an indent.",
            fontname="regular",
            fontsize=12,
        )
        first.insert_text((108, 215), "Mixed regular ", fontname="regular", fontsize=12)
        first.insert_text((210, 215), "bold fabricated", fontname="bold", fontsize=12)
        first.insert_text((325, 215), " italic invented", fontname="italic", fontsize=12)
        first.insert_text((300, 740), "i", fontname="regular", fontsize=12)
        second = doc.new_page(width=792, height=612)
        second.insert_font(fontname="regular", fontfile=fonts["regular"])
        second.insert_text((108, 110), "CHAPTER 1", fontname="regular", fontsize=13)
        second.insert_text(
            (108, 155),
            "An imaginary landscape paragraph has fabricated results.",
            fontname="regular",
            fontsize=12,
        )
        second.set_cropbox(fitz.Rect(20, 20, 772, 592))
        second.set_rotation(90)
        doc.set_metadata(
            {"title": "SYNTHETIC PRIVATE_TITLE_CEDAR_521", "author": "PRIVATE_AUTHOR_CEDAR_521"}
        )
        doc.save(path, garbage=4, deflate=True)
    return path


def test_embedded_unicode_styles_mixed_spans_and_page_geometry(tmp_path: Path) -> None:
    import pikepdf

    source = _embedded_fixture(tmp_path / "source.pdf")
    output = tmp_path / "output.pdf"
    report = anonymize(source, output, authorized=True, seed=42, verify_auditor=True)
    assert report["status"] == "COMPLETED_SUCCESS"
    assert report["pages"] == 2
    assert report["font_families"] == 3
    assert report["fidelity"]["max_line_end_delta_pt"] < 1
    assert report["fidelity"]["auditor"]["lost"] == 0
    assert report["fidelity"]["auditor"]["introduced"] == 0
    with fitz.open(source) as before, fitz.open(output) as after:
        assert [(p.mediabox, p.cropbox, p.rotation) for p in before] == [
            (p.mediabox, p.cropbox, p.rotation) for p in after
        ]
        assert [p.get_text() for p in before] != [p.get_text() for p in after]
        assert "ABSTRACT" in after[0].get_text()
        assert "CHAPTER 1" in after[1].get_text()
        assert "Mira Fictional" not in after[0].get_text()
        assert not any(
            after.metadata.get(key) for key in ("title", "author", "subject", "keywords")
        )
    independent = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "Mira Fictional" not in independent
    assert "ABSTRACT" in independent
    assert b"PRIVATE_TITLE_CEDAR_521" not in output.read_bytes()
    assert b"PRIVATE_AUTHOR_CEDAR_521" not in output.read_bytes()
    with pikepdf.Pdf.open(source) as before, pikepdf.Pdf.open(output) as after:
        assert not (
            {bytes(value) for value in before.trailer.get("/ID", [])}
            & {bytes(value) for value in after.trailer.get("/ID", [])}
        )


def test_five_page_auditor_and_seeded_content(tmp_path: Path) -> None:
    source = make_extended_thesis(tmp_path / "source.pdf")
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    first = anonymize(source, a, authorized=True, seed=42, verify_auditor=True)
    anonymize(source, b, authorized=True, seed=42, verify_auditor=True)
    assert first["fidelity"]["auditor"]["source"] >= 1
    assert first["fidelity"]["auditor"]["lost"] == 0
    assert first["fidelity"]["auditor"]["introduced"] == 0
    with fitz.open(a) as left, fitz.open(b) as right:
        assert [page.get_text() for page in left] == [page.get_text() for page in right]


def test_subset_font_uses_local_font_redraw(tmp_path: Path) -> None:
    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
    if not font.is_file():
        pytest.skip("Synthetic DejaVu test font unavailable")
    source = tmp_path / "subset.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_font(fontname="dv", fontfile=str(font))
        page.insert_text(
            (108, 120),
            "Fabricated academic α β content. Invented references.",
            fontname="dv",
            fontsize=12,
        )
        doc.subset_fonts()
        doc.save(source, garbage=4, deflate=True)
    output = tmp_path / "output.pdf"
    report = anonymize(source, output, authorized=True, seed=10)
    assert report["method"] == "local-font-redraw"
    assert report["fidelity"]["font_mismatches"] == 0
    assert report["fidelity"]["max_line_end_delta_pt"] < 1
    with fitz.open(output) as doc:
        assert "Fabricated academic" not in doc[0].get_text()
        assert doc[0].get_text().strip()


def test_equation_superscript_is_replaced_with_same_style(tmp_path: Path) -> None:
    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
    if not font.is_file():
        pytest.skip("Synthetic DejaVu test font unavailable")
    source = tmp_path / "equation.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_font(fontname="math", fontfile=str(font))
        page.insert_text((108, 120), "α + β = 42; ∑ x²", fontname="math", fontsize=12)
        page.insert_text((108, 170), "Fabricated explanatory prose is invented.")
        doc.save(source)
    output = tmp_path / "output.pdf"
    report = anonymize(source, output, authorized=True, verify_auditor=True)
    assert report["status"] == "COMPLETED_SUCCESS"
    with fitz.open(output) as doc:
        text = doc[0].get_text()
        assert any(char in text for char in "⁰¹³⁴⁵⁶⁷⁸⁹")
        assert "²" not in text
        assert "Fabricated explanatory" not in text
        assert "α + β = 42" not in text


def test_raster_figure_is_replaced_in_same_region(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    with fitz.open() as doc, fitz.open() as donor:
        donor_page = donor.new_page(width=200, height=100)
        donor_page.insert_text((8, 50), "PIXEL_SECRET_CEDAR_521", fontsize=12)
        page = doc.new_page(width=612, height=792)
        page.insert_text((108, 100), "Figure 1.1: A fabricated diagram.")
        page.insert_image(fitz.Rect(108, 140, 408, 290), pixmap=donor_page.get_pixmap())
        doc.save(source, garbage=4, deflate=True)
    output = tmp_path / "output.pdf"
    report = anonymize(source, output, authorized=True, seed=42, verify_auditor=True)
    assert report["method"] == "local-redraw-with-synthetic-images"
    assert report["synthetic_image_placeholders"] == 1
    assert report["fidelity"]["auditor"]["lost"] == 0
    assert report["fidelity"]["auditor"]["introduced"] == 0
    with fitz.open(source) as before, fitz.open(output) as after:
        old_block = next(b for b in before[0].get_text("dict")["blocks"] if b["type"] == 1)
        new_block = next(b for b in after[0].get_text("dict")["blocks"] if b["type"] == 1)
        assert old_block["bbox"] == new_block["bbox"]
        assert old_block["image"] != new_block["image"]
        assert "Figure 1.1" in after[0].get_text()


@pytest.mark.parametrize("surface", ["image", "drawing", "annotation", "hidden", "attachment"])
def test_unsupported_content_refuses_without_output(tmp_path: Path, surface: str) -> None:
    source = tmp_path / "source.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((100, 120), "An entirely fabricated example paragraph.")
        if surface == "image":
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 2, 2), False)
            pix.clear_with(255)
            page.insert_image(fitz.Rect(100, 200, 150, 250), pixmap=pix)
        elif surface == "drawing":
            page.draw_rect(fitz.Rect(100, 200, 150, 250), color=(0, 0, 0))
        elif surface == "annotation":
            page.add_text_annot((100, 200), "SECRET_COMMENT_CEDAR_521")
        elif surface == "hidden":
            xref = page.get_contents()[0]
            stream = doc.xref_stream(xref) or b""
            doc.update_stream(
                xref,
                stream + b"\nBT /helv 12 Tf 3 Tr 1 0 0 1 100 500 Tm "
                b"(SECRET_HIDDEN_CEDAR_521) Tj ET\n",
            )
        else:
            doc.embfile_add("secret.txt", b"SECRET_ATTACHMENT_CEDAR_521")
        doc.save(source, garbage=4, deflate=True)
    output = tmp_path / "output.pdf"
    with pytest.raises(UnsupportedPDF, match="image|vector|annotation|invisible|/Names|hidden"):
        anonymize(source, output, authorized=True)
    assert not output.exists()


def test_authorization_and_cli_output_directory(tmp_path: Path) -> None:
    source = _embedded_fixture(tmp_path / "input.pdf")
    with pytest.raises(UnsupportedPDF, match="--authorized-local-input"):
        anonymize(source, tmp_path / "refused.pdf")
    destination = tmp_path / "outputs"
    report = tmp_path / "report.json"
    command = [
        sys.executable,
        "-m",
        "njit_auditor.practical_pdf_anonymizer",
        str(source),
        "--output-dir",
        str(destination),
        "--authorized-local-input",
        "--seed",
        "7",
        "--strategy",
        "random",
        "--report",
        str(report),
    ]
    completed = run(command, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert (destination / "input-anonymized.pdf").is_file()
    assert json.loads(report.read_text())["strategy"] == "random"


def test_upstream_events_are_recorded_and_material_failures_refuse(tmp_path: Path) -> None:
    from pdf_edit_engine import batch_replace
    from pdf_edit_engine.models import Degradation

    source = _embedded_fixture(tmp_path / "source.pdf")
    real_batch = batch_replace

    def with_info(*args: object, **kwargs: object) -> object:
        results = real_batch(*args, **kwargs)
        results[0].fidelity_report.degradations.append(
            Degradation(kind="kerning_widened", detail="synthetic harmless event", severity="info")
        )
        return results

    with patch("pdf_edit_engine.batch_replace", side_effect=with_info):
        report = anonymize(source, tmp_path / "accepted.pdf", authorized=True, seed=42)
    assert report["upstream_degradations"]["kerning_widened:info"] == 1

    def with_error(*args: object, **kwargs: object) -> object:
        results = real_batch(*args, **kwargs)
        results[0].fidelity_report.degradations.append(
            Degradation(kind="font_extension_failed", detail="synthetic failure", severity="error")
        )
        return results

    refused = tmp_path / "refused.pdf"
    with patch("pdf_edit_engine.batch_replace", side_effect=with_error):
        with pytest.raises(UnsupportedPDF, match="degradation"):
            anonymize(source, refused, authorized=True, seed=42)
    assert not refused.exists()


def test_long_synthetic_document(tmp_path: Path) -> None:
    source = tmp_path / "long.pdf"
    with fitz.open() as doc:
        for number in range(1, 31):
            page = doc.new_page(width=612, height=792)
            page.insert_text((108, 100), f"CHAPTER {number}", fontname="hebo", fontsize=14)
            page.insert_text((108, 160), f"Invented observations on page {number} are fabricated.")
            page.insert_text((144, 185), "A second fictional line is indented for this example.")
            page.insert_text((300, 740), str(number))
        doc.save(source, garbage=4, deflate=True)
    report = anonymize(source, tmp_path / "long-out.pdf", authorized=True, seed=42)
    assert report["pages"] == 30
    assert report["spans"] == 120
    assert report["batched_spans"] >= 25


@pytest.mark.parametrize(
    "surface", ["page_tree_metadata", "page_tree_custom", "user_unit", "trim_box"]
)
def test_unverified_page_tree_and_print_geometry_refuse(tmp_path: Path, surface: str) -> None:
    import pikepdf

    source = _embedded_fixture(tmp_path / "base.pdf")
    modified = tmp_path / "modified.pdf"
    with pikepdf.Pdf.open(source) as pdf:
        if surface == "page_tree_metadata":
            pdf.Root.Pages.Metadata = pdf.make_stream(b"PRIVATE_TREE_CEDAR_521")
        elif surface == "page_tree_custom":
            pdf.Root.Pages.PrivateNote = "PRIVATE_TREE_CEDAR_521"
        elif surface == "user_unit":
            pdf.pages[0].obj.UserUnit = 2
        else:
            pdf.pages[0].obj.TrimBox = pikepdf.Array([10, 10, 600, 780])
        pdf.save(modified)
    output = tmp_path / "output.pdf"
    with pytest.raises(UnsupportedPDF, match="/Pages tree|page dictionary"):
        anonymize(modified, output, authorized=True)
    assert not output.exists()


def test_partial_opacity_refuses(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((100, 120), "A fabricated semitransparent paragraph.", fill_opacity=0.5)
        doc.save(source)
    output = tmp_path / "output.pdf"
    with pytest.raises(UnsupportedPDF, match="translucent"):
        anonymize(source, output, authorized=True)
    assert not output.exists()


@pytest.mark.parametrize("surface", ["font", "unicode_map"])
def test_custom_font_object_data_refuses(tmp_path: Path, surface: str) -> None:
    import pikepdf

    source = _embedded_fixture(tmp_path / "base.pdf")
    modified = tmp_path / "modified.pdf"
    with pikepdf.Pdf.open(source) as pdf:
        font = next(iter(pdf.pages[0].obj["/Resources"]["/Font"].values()))
        target = font if surface == "font" else font["/ToUnicode"]
        target["/PrivateNote"] = pikepdf.String("HIDDEN_SECRET_CEDAR_521")
        pdf.save(modified)
    output = tmp_path / "output.pdf"
    with pytest.raises(UnsupportedPDF, match="unverified font dictionary|Unicode map stream"):
        anonymize(modified, output, authorized=True)
    assert not output.exists()


def test_custom_content_stream_data_refuses(tmp_path: Path) -> None:
    import pikepdf

    source = _embedded_fixture(tmp_path / "base.pdf")
    modified = tmp_path / "modified.pdf"
    with pikepdf.Pdf.open(source) as pdf:
        contents = pdf.pages[0].obj["/Contents"]
        stream = contents[0] if isinstance(contents, pikepdf.Array) else contents
        stream["/PrivateNote"] = pikepdf.String("HIDDEN_SECRET_CEDAR_521")
        pdf.save(modified)
    output = tmp_path / "output.pdf"
    with pytest.raises(UnsupportedPDF, match="unverified content stream data"):
        anonymize(modified, output, authorized=True)
    assert not output.exists()


def test_seed_is_stable_across_python_hash_seeds(tmp_path: Path) -> None:
    source = _embedded_fixture(tmp_path / "source.pdf")
    for hash_seed in ("1", "91"):
        completed = run(
            [
                sys.executable, "-m", "njit_auditor.practical_pdf_anonymizer", str(source),
                "-o", str(tmp_path / f"out-{hash_seed}.pdf"), "--authorized-local-input",
                "--seed", "41", "--strategy", "random",
            ],
            capture_output=True, text=True, check=False,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
        )
        assert completed.returncode == 0, completed.stderr
    with fitz.open(tmp_path / "out-1.pdf") as a, fitz.open(tmp_path / "out-91.pdf") as b:
        assert [page.get_text() for page in a] == [page.get_text() for page in b]


def test_partial_edit_cannot_pass_verification(tmp_path: Path) -> None:
    from pdf_edit_engine import Edit, batch_replace

    source = _embedded_fixture(tmp_path / "source.pdf")

    def skip_one_span(
        input_path: str, edits: list[Edit], output_path: str, **kwargs: object
    ) -> object:
        changed = list(edits)
        victim = next(index for index, edit in enumerate(changed) if "Mixed regular" in edit.find)
        changed[victim] = Edit(changed[victim].find, changed[victim].find)
        return batch_replace(input_path, changed, output_path, **kwargs)

    output = tmp_path / "output.pdf"
    with patch("pdf_edit_engine.batch_replace", side_effect=skip_one_span):
        with pytest.raises(UnsupportedPDF, match="planned text span was not replaced"):
            anonymize(source, output, authorized=True, seed=42)
    assert not output.exists()
