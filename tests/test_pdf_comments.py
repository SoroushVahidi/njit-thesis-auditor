from pathlib import Path

import fitz
from typer.testing import CliRunner

from njit_auditor.cli import app
from njit_auditor.pdf_comments import extract_pdf_annotations, remove_pdf_annotations

runner = CliRunner()


def _make_pdf_with_text_annotation(path: Path, comment: str = "Review comment") -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((120, 120), "Synthetic test text", fontsize=12)
    annot = page.add_text_annot((180, 120), comment)
    annot.update()
    doc.save(path)
    doc.close()


def _make_pdf_without_annotations(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((120, 120), "No annotations here", fontsize=12)
    doc.save(path)
    doc.close()


def test_extract_pdf_annotations_returns_expected_fields(tmp_path: Path) -> None:
    pdf_path = tmp_path / "annot.pdf"
    _make_pdf_with_text_annotation(pdf_path, comment="A" * 150)
    annotations = extract_pdf_annotations(pdf_path)
    assert len(annotations) == 1
    item = annotations[0]
    assert item["page_number"] == 1
    assert item["subtype"] == "Text"
    assert item["has_content"] is True
    assert isinstance(item["bbox"], list)
    assert len(item["truncated_preview"]) <= 120


def test_remove_pdf_annotations_clears_annotations(tmp_path: Path) -> None:
    input_pdf = tmp_path / "annot.pdf"
    output_pdf = tmp_path / "clean.pdf"
    _make_pdf_with_text_annotation(input_pdf)
    remove_pdf_annotations(input_pdf, output_pdf)
    annotations = extract_pdf_annotations(output_pdf)
    assert annotations == []


def test_pdf_comments_extract_cli_command(tmp_path: Path) -> None:
    input_pdf = tmp_path / "annot.pdf"
    _make_pdf_with_text_annotation(input_pdf)
    json_out = tmp_path / "out" / "annotations.json"
    md_out = tmp_path / "out" / "annotations.md"
    result = runner.invoke(
        app,
        [
            "pdf-comments",
            "extract",
            str(input_pdf),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
        ],
    )
    assert result.exit_code == 0
    assert json_out.exists()
    assert md_out.exists()


def test_pdf_comments_clean_cli_command(tmp_path: Path) -> None:
    input_pdf = tmp_path / "annot.pdf"
    output_pdf = tmp_path / "out" / "clean.pdf"
    _make_pdf_with_text_annotation(input_pdf)
    result = runner.invoke(
        app,
        ["pdf-comments", "clean", str(input_pdf), "--out", str(output_pdf)],
    )
    assert result.exit_code == 0
    assert output_pdf.exists()
    assert extract_pdf_annotations(output_pdf) == []


def test_extract_no_annotations_does_not_crash(tmp_path: Path) -> None:
    input_pdf = tmp_path / "plain.pdf"
    _make_pdf_without_annotations(input_pdf)
    annotations = extract_pdf_annotations(input_pdf)
    assert annotations == []
