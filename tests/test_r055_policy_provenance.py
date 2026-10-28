"""Synthetic PDF checks for distinct column-label and reviewer entry requirements."""

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.polished_comments import resolve_suggested_fix_for_display
from njit_auditor.rules.pdf_lot_lof_column_header_style_alignment import (
    check_pdf_lot_lof_column_header_style_alignment,
    check_pdf_lot_lof_left_column_header_bold,
)
from njit_auditor.rules.pdf_lot_lof_column_headers import check_pdf_lot_lof_column_headers
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type


def _list_pdf(tmp_path, word, prefixes, *, left_header="bold"):
    path = tmp_path / "synthetic-list.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        heading = "LIST OF TABLES" if word == "Table" else "LIST OF FIGURES"
        page.insert_text((220, 95), heading, fontname="Times-Bold", fontsize=12)
        if left_header != "missing":
            font = "Times-Bold" if left_header == "bold" else "Times-Roman"
            page.insert_text((108, 125), word, fontname=font, fontsize=12)
        width = fitz.get_text_length("Page", fontname="Times-Bold", fontsize=12)
        page.insert_text((540 - width, 125), "Page", fontname="Times-Bold", fontsize=12)
        for index, prefix in enumerate(prefixes, 1):
            y = 140 + index * 30
            title = f"{prefix + ' ' if prefix else ''}1.{index} Synthetic Entry Title"
            page.insert_text((108, y), title, fontname="Times-Roman", fontsize=12)
            page.insert_text((420, y), "...............", fontname="Times-Roman", fontsize=12)
            page.insert_text((528, y), str(10 + index), fontname="Times-Roman", fontsize=12)
        doc.save(path)
    return load_pdf_layout(str(path))


@pytest.mark.parametrize("word", ["Table", "Figure"])
def test_correct_column_labels_do_not_replace_numeric_entry_prefixes(tmp_path: Path, word):
    doc = _list_pdf(tmp_path, word, ["", "", ""])
    assert check_pdf_lot_lof_column_headers(doc) == []
    assert check_pdf_lot_lof_column_header_style_alignment(doc) == []
    assert check_pdf_lot_lof_left_column_header_bold(doc) == []
    findings = check_pdf_lot_lof_entry_type(doc)
    issue = (
        "lot_entry_missing_table_prefix" if word == "Table" else "lof_entry_missing_figure_prefix"
    )
    assert [(f.details["entry_index"], f.details["issue_type"]) for f in findings] == [
        (str(index), issue) for index in range(3)
    ]


@pytest.mark.parametrize("word,other", [("Table", "Figure"), ("Figure", "Table")])
def test_mixed_entry_formats_get_only_the_applicable_correction(tmp_path: Path, word, other):
    doc = _list_pdf(tmp_path, word, [word, "", other])
    assert check_pdf_lot_lof_column_headers(doc) == []
    assert check_pdf_lot_lof_column_header_style_alignment(doc) == []
    assert check_pdf_lot_lof_left_column_header_bold(doc) == []
    findings = check_pdf_lot_lof_entry_type(doc)
    missing = (
        "lot_entry_missing_table_prefix" if word == "Table" else "lof_entry_missing_figure_prefix"
    )
    misplaced = "lot_entry_is_figure" if word == "Table" else "lof_entry_is_table"
    assert [(f.details["entry_index"], f.details["issue_type"]) for f in findings] == [
        ("1", missing), ("2", misplaced)
    ]
    prefix_fix = resolve_suggested_fix_for_display("P055", missing)
    assert f"with the word '{word}' before its number" in prefix_fix
    assert "misplaced" not in prefix_fix.lower()
    wrong_list_fix = resolve_suggested_fix_for_display("P055", misplaced)
    assert "misplaced entry" in wrong_list_fix
    assert "before its number" not in wrong_list_fix


@pytest.mark.parametrize("word", ["Table", "Figure"])
@pytest.mark.parametrize("left_header", ["missing", "plain"])
def test_prefixed_entries_do_not_replace_column_heading_requirements(
    tmp_path: Path, word, left_header
):
    doc = _list_pdf(tmp_path, word, [word, word, word], left_header=left_header)
    assert check_pdf_lot_lof_entry_type(doc) == []
    presence = check_pdf_lot_lof_column_headers(doc)
    style = check_pdf_lot_lof_left_column_header_bold(doc)
    if left_header == "missing":
        assert [f.details["issue_type"] for f in presence] == ["missing_left_column_header"]
        assert style == []
    else:
        assert presence == []
        assert len(style) == 1
        assert style[0].rule_id == "P050"
        assert style[0].details["source_q_rule_id"] == ("Q063" if word == "Table" else "Q072")
    assert check_pdf_lot_lof_column_header_style_alignment(doc) == []
