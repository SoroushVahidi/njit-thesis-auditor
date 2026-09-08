"""Tests for the generic Ester review-package .xlsx importer.

Uses only synthetic, invented content -- a small in-memory workbook built
by the test itself, matching the real header shape
(``build_rule_package.py``'s ``_write_xlsx``), never a real package file.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from njit_auditor.review_ledger.importers.xlsx_packages import (
    read_xlsx_package,
    scan_xlsx_packages,
)

_HEADER = [
    "DOCUMENT",
    "Possible R999 violation — page, location, reason, confidence",
    "Correct? (Y/N)",
    "Notes",
]


def _write_synthetic_package(path: Path, rows: list[list[object]]) -> None:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(_HEADER)
    for row in rows:
        worksheet.append(row)
    workbook.save(path)


def test_read_blank_package_has_no_verdicts(tmp_path: Path) -> None:
    path = tmp_path / "R999_Ester_Auditor_Feedback.xlsx"
    _write_synthetic_package(
        path,
        [
            ["Synthetic-A", "No current auditor R999 finding.", None, None],
            [
                "Synthetic-B",
                (
                    "Physical PDF page: 5\nPrinted/document page: 3\n"
                    "Location: body text\nPossible violation: example\n"
                    "Measured amount: n/a\nAuditor confidence: LOW"
                ),
                None,
                None,
            ],
        ],
    )
    rows = read_xlsx_package(path)
    assert len(rows) == 2
    assert rows[0].no_finding is True
    assert rows[1].no_finding is False
    assert rows[1].physical_page == 5
    assert rows[1].verdict_letter is None


def test_read_package_with_filled_verdict(tmp_path: Path) -> None:
    path = tmp_path / "R999_Ester_Auditor_Feedback.xlsx"
    _write_synthetic_package(
        path,
        [
            [
                "Synthetic-C",
                (
                    "Physical PDF page: 9\nPrinted/document page: 7\n"
                    "Location: body text\nPossible violation: example\n"
                    "Measured amount: n/a\nAuditor confidence: HIGH"
                ),
                "N",
                "not a real issue",
            ],
        ],
    )
    rows = read_xlsx_package(path)
    assert len(rows) == 1
    assert rows[0].verdict_letter == "N"
    assert rows[0].notes == "not a real issue"
    assert rows[0].physical_page == 9


def test_scan_directory_aggregates_across_packages(tmp_path: Path) -> None:
    _write_synthetic_package(
        tmp_path / "R900_Ester_Auditor_Feedback.xlsx",
        [["Synthetic-A", "No current auditor R900 finding.", None, None]],
    )
    _write_synthetic_package(
        tmp_path / "R901_Ester_Auditor_Feedback.xlsx",
        [
            [
                "Synthetic-B",
                (
                    "Physical PDF page: 2\nPrinted/document page: 1\n"
                    "Location: front matter\nPossible violation: example\n"
                    "Measured amount: n/a\nAuditor confidence: MEDIUM"
                ),
                "Y",
                None,
            ],
            [
                "Synthetic-C",
                (
                    "Physical PDF page: 3\nPrinted/document page: 2\n"
                    "Location: front matter\nPossible violation: example\n"
                    "Measured amount: n/a\nAuditor confidence: MEDIUM"
                ),
                None,
                None,
            ],
        ],
    )
    summary = scan_xlsx_packages(tmp_path)
    assert summary.packages_scanned == 2
    assert summary.rows_read == 3
    assert summary.rows_with_verdict == 1
    assert summary.rows_blank == 1
    assert summary.verdict_rows[0].ester_id == "R901"
