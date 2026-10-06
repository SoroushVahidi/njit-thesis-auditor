"""Check the XLSX that the future reviewer-package generator actually writes."""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ester_batch"))

from build_rule_package import (  # noqa: E402
    REVIEW_WORKBOOK_SCHEMA,
    _write_xlsx,
    review_workbook_filename,
    review_workbook_path_for_manifest,
)
from lib import DOCS  # noqa: E402
from qa.structural_qa import audit_xlsx  # noqa: E402


def _rows() -> list[dict]:
    rows = []
    for index, (document, _filename) in enumerate(DOCS):
        if index == 0:
            rows.append(
                {
                    "document": document,
                    "no_finding": False,
                    "physical_page": 12,
                    "printed_page": "8",
                    "location": (
                        "A long first line with enough words to require wrapping in the sheet"
                    ),
                    "affected_lines": ["Synthetic line one", "Synthetic line two"],
                    "message": "Synthetic finding with a detailed explanation\nAnd another line",
                    "measured_amount": "12 pt",
                    "confidence": "MEDIUM",
                    "question": "Does this synthetic example need a correction?",
                }
            )
        else:
            rows.append({"document": document, "no_finding": True})
    return rows


def test_review_workbook_name_is_date_first_and_manifest_keeps_archived_names(
    tmp_path: Path,
) -> None:
    review_date = dt.date(2026, 10, 5)
    name = review_workbook_filename("R024E", review_date)
    assert re.match(r"^\d{4}-\d{2}-\d{2}_", name)
    assert name == "2026-10-05_R024E_NJIT_Thesis_Auditor_Review.xlsx"
    assert review_workbook_path_for_manifest(
        "R024E",
        {"review_workbook_schema": REVIEW_WORKBOOK_SCHEMA, "review_date": "2026-10-05"},
        tmp_path,
    ) == tmp_path / name
    assert review_workbook_path_for_manifest("R024E", {}, tmp_path) == (
        tmp_path / "R024E_Ester_Auditor_Feedback.xlsx"
    )


def test_generated_xlsx_human_schema_layout_and_reload(tmp_path: Path) -> None:
    workbook_path = tmp_path / review_workbook_filename("R024E", dt.date(2026, 10, 5))
    pdf_path = tmp_path / "R024E_Ester_Auditor_Feedback.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    _write_xlsx("R024E", _rows(), workbook_path)

    wb = openpyxl.load_workbook(workbook_path)
    assert wb.sheetnames == ["R024E"]
    assert [sheet.sheet_state for sheet in wb.worksheets] == ["visible"]
    ws = wb.active
    assert ws.freeze_panes == "A2"
    assert ws.max_row == len(DOCS) + 1
    headers = [ws.cell(1, column).value for column in range(1, 5)]
    assert headers[0] == "DOCUMENT"
    assert "R024E" in headers[1]
    assert headers[2:] == ["Question 1", "Comment"]
    assert all(
        banned not in str(header)
        for header in headers
        for banned in ("Ester's", "Ester Question", "Questions for Ester")
    )
    assert ws["B1"].hyperlink is not None
    assert ws["B1"].hyperlink.target == pdf_path.name
    assert (workbook_path.parent / ws["B1"].hyperlink.target).exists()
    assert [ws.column_dimensions[column].width for column in "ABCD"] == [18, 76, 48, 44]
    for row in ws:
        for cell in row[:4]:
            assert cell.alignment.wrap_text is True
            assert cell.alignment.vertical == "top"
    assert ws["B2"].value.count("\n") >= 2
    assert ws["C2"].value == "Does this synthetic example need a correction?"
    assert ws["D2"].value is None
    assert "No new review needed." in ws["B3"].value
    assert ws["C3"].value is None
    assert ws["D3"].value is None
    assert all(ws.row_dimensions[row].height is None for row in range(2, ws.max_row + 1))
    assert audit_xlsx("R024E", workbook_path, current_schema=True) == ([], [DOCS[0][0]])
    wb.close()

    # Regenerate from identical inputs: schema, values, links and styles are stable.
    second_path = tmp_path / "second.xlsx"
    _write_xlsx("R024E", _rows(), second_path)
    second = openpyxl.load_workbook(second_path)
    first = openpyxl.load_workbook(workbook_path)
    assert first.sheetnames == second.sheetnames
    assert first.active.freeze_panes == second.active.freeze_panes
    for row in first.active:
        for cell in row:
            other = second.active[cell.coordinate]
            assert (cell.value, cell.style_id) == (other.value, other.style_id)
            assert (cell.hyperlink.target if cell.hyperlink else None) == (
                other.hyperlink.target if other.hyperlink else None
            )
    first.close()
    second.close()


def test_current_question_defaults_only_for_current_cases(tmp_path: Path) -> None:
    rows = _rows()
    rows[0].pop("question")
    path = tmp_path / "R011.xlsx"
    _write_xlsx("R011", rows, path)
    wb = openpyxl.load_workbook(path)
    assert wb.active["C2"].value == "Should the auditor report this as an R011 violation?"
    assert wb.active["C3"].value is None
    wb.close()


def test_archived_workbook_qa_keeps_old_review_columns(tmp_path: Path) -> None:
    path = tmp_path / "R011_Ester_Auditor_Feedback.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "R011"
    ws.append(["DOCUMENT", "Possible R011 violation", "Correct? (Y/N)", "Notes"])
    for document, _filename in DOCS:
        ws.append([document, "No current auditor R011 finding.", None, None])
    wb.save(path)
    wb.close()
    assert audit_xlsx("R011", path) == ([], [])
