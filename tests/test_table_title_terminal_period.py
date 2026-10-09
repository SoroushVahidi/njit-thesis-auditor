"""Body table titles do not end with a period (Ester, Sample B feedback).

Ester confirmed a table title in title-case violation and added: "this table
title ends with a period and table titles do not end in periods". P017 now
reports the period as its own finding, alongside any capitalization issue.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_text import write_text_report
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_captions import check_pdf_captions


def _render(tmp_path: Path, title: str) -> Path:
    path = tmp_path / "table.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    y = 120.0
    for _ in range(6):
        page.insert_text(
            (108, y),
            "Body paragraph text that introduces the following synthetic table here.",
            fontsize=12,
        )
        y += 24.0
    page.insert_text((108, y), title, fontsize=12)
    y += 24.0
    for row in ("Method   Accuracy   Recall", "Alpha   0.91   0.88", "Beta   0.87   0.85"):
        page.insert_text((180, y), row, fontsize=11)
        y += 16.0
    doc.save(path)
    doc.close()
    return path


def _issue_types(path: Path) -> list[str]:
    return sorted(
        f.details["issue_type"]
        for f in check_pdf_captions(load_pdf_layout(str(path)))
        if f.page == 1
    )


def test_table_title_ending_with_a_period_is_reported(tmp_path: Path) -> None:
    assert "unexpected_terminal_period" in _issue_types(
        _render(tmp_path, "Table 3.1 Accuracy of Synthetic Survey Methods.")
    )


def test_period_is_reported_alongside_a_title_case_issue(tmp_path: Path) -> None:
    path = _render(tmp_path, "Table 3.1 Accuracy of synthetic survey methods across sites.")
    findings = check_pdf_captions(load_pdf_layout(str(path)))
    types = sorted(f.details["issue_type"] for f in findings if f.page == 1)
    assert "unexpected_terminal_period" in types
    assert "possible_title_case_issue" in types

    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    cards = {f.issue_type: f for f in view.findings if f.rule_id == "P017"}
    period = cards["unexpected_terminal_period"]
    case = cards["possible_title_case_issue"]
    assert period.suggested_fix == "Remove the final period from this table title."
    assert "table title" in period.polished_comment.lower()
    assert "full sentence" not in period.polished_comment.lower()
    assert "figure" not in period.suggested_fix.lower()
    assert "period" not in case.suggested_fix.lower()
    assert "period" not in case.polished_comment.lower()

    report_path = tmp_path / "report.txt"
    write_text_report(
        findings,
        {"audit_type": "pdf", "input_file_name": "synthetic.pdf"},
        report_path,
    )
    report_text = report_path.read_text()
    assert "Remove the final period from this table title." in report_text
    assert "For figure captions:" not in report_text


def test_table_title_without_a_period_is_clean(tmp_path: Path) -> None:
    assert "unexpected_terminal_period" not in _issue_types(
        _render(tmp_path, "Table 3.1 Accuracy of Synthetic Survey Methods")
    )
