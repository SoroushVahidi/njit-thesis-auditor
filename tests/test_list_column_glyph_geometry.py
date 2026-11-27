"""Regression coverage for paired list headings stored in one PDF text span."""

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_lot_lof_column_headers import check_pdf_lot_lof_column_headers
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type


def make_list_page(
    path: Path,
    *,
    figures: bool = False,
    left: str = "Table",
    right: str = "Page",
    spaces: int = 121,
    leaders: bool = True,
    figure_entry: bool = False,
) -> None:
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_text(
            (186, 90), "LIST OF FIGURES" if figures else "LIST OF TABLES",
            fontname="tibo", fontsize=12,
        )
        page.insert_text((108, 127), left + " " * spaces + right, fontname="tibo", fontsize=12)
        for index in range(3):
            y = 165 + index * 24
            prefix = "Figure " if figure_entry and index == 1 else ""
            title = f"{prefix}2.{index + 1} An Ordinary List Entry"
            page.insert_text((108, y), title + (" .........." if leaders else ""))
            page.insert_text((505, y), str(index + 21))
        pdf.save(path)


@pytest.mark.parametrize(
    ("figures", "left", "right", "leaders"),
    [
        (False, "Table", "Page", True),
        (False, "TABLE", "PAGE", False),
        (False, "Tables", "Pages", True),
        (True, "Figure", "Page", False),
    ],
)
def test_paired_list_headers_use_measured_column_positions(
    tmp_path: Path, figures: bool, left: str, right: str, leaders: bool
) -> None:
    path = tmp_path / "paired-columns.pdf"
    make_list_page(path, figures=figures, left=left, right=right, leaders=leaders)
    model = load_pdf_layout(str(path))
    lines = [line for block in model.pages[0].text_blocks for line in block.lines]
    header, = [line for line in lines if line.text.startswith(left) and right in line.text]
    assert len(header.spans) == 1
    assert check_pdf_lot_lof_column_headers(model) == []
    if not figures:
        assert check_pdf_lot_lof_entry_type(model) == []


@pytest.mark.parametrize(
    ("left", "right", "spaces"),
    [("Table", "Page", 1), ("Figure", "Page", 121), ("Table", "Reference", 121),
     ("Table", "Page", 50)],
)
def test_pairs_without_valid_column_ownership_remain_unqualified(
    tmp_path: Path, left: str, right: str, spaces: int
) -> None:
    path = tmp_path / "unqualified-columns.pdf"
    make_list_page(path, left=left, right=right, spaces=spaces)
    model = load_pdf_layout(str(path))
    assert "missing_left_column_header" in {
        finding.details["issue_type"] for finding in check_pdf_lot_lof_column_headers(model)
    }
    assert {finding.details["issue_type"] for finding in check_pdf_lot_lof_entry_type(model)} == {
        "lot_entry_missing_table_prefix"
    }


def test_paired_table_label_does_not_excuse_a_figure_entry(tmp_path: Path) -> None:
    path = tmp_path / "wrong-entry-kind.pdf"
    make_list_page(path, figure_entry=True)
    model = load_pdf_layout(str(path))
    assert [finding.details["issue_type"] for finding in check_pdf_lot_lof_entry_type(model)] == [
        "lot_entry_is_figure"
    ]


def test_paired_labels_work_through_the_full_pdf_auditor(tmp_path: Path) -> None:
    path = tmp_path / "paired-columns-full-audit.pdf"
    make_list_page(path, leaders=False, figure_entry=True)
    findings = run_pdf_audit_full(path)
    assert [finding.details["issue_type"] for finding in findings if finding.rule_id == "P055"] == [
        "lot_entry_is_figure"
    ]
    assert not any(finding.rule_id == "P031" for finding in findings)
