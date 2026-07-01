"""Regression tests for P026A font-family policy aligned with Ester guidance."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.polished_comments import build_polished_comment
from njit_auditor.rules.pdf_font_compliance import (
    check_pdf_font_compliance,
    classify_font,
    is_accepted_body_font_family,
)

_LONG_BODY_LINE = (
    "An ordinary body text paragraph line for PDF font compliance testing here."
)


def _make_body_font_doc(font: str, fontsize: float = 12.0, line_count: int = 12) -> PdfDocument:
    spans_per_line: list[PdfTextLine] = []
    y = 150.0
    for _ in range(line_count):
        bbox = BBox(x0=108.0, y0=y, x1=500.0, y1=y + 14.0)
        span = PdfTextSpan(
            text=_LONG_BODY_LINE,
            bbox=bbox,
            font=font,
            size=fontsize,
            bold=False,
            italic=False,
        )
        line = PdfTextLine(spans=[span], bbox=bbox, text=_LONG_BODY_LINE)
        spans_per_line.append(line)
        y += 28.0
    block = PdfTextBlock(
        lines=spans_per_line,
        bbox=BBox(x0=108.0, y0=150.0, x1=500.0, y1=y),
        text=_LONG_BODY_LINE,
    )
    page = PdfPage(page_number=1, width=612.0, height=792.0, text_blocks=[block])
    return PdfDocument(path="synthetic", pages=[page])


def _family_findings(doc: PdfDocument) -> list:
    return [
        f
        for f in check_pdf_font_compliance(doc)
        if f.details.get("issue_type") == "possible_body_font_family_issue"
    ]


def _size_findings(doc: PdfDocument) -> list:
    return [
        f
        for f in check_pdf_font_compliance(doc)
        if f.details.get("issue_type") == "possible_body_font_size_issue"
    ]


@pytest.mark.parametrize(
    ("font_name", "expected_class"),
    [
        ("TimesNewRomanPSMT", "times"),
        ("ArialMT", "arial"),
        ("Arial", "arial"),
        ("CMR12", "computer_modern"),
        ("CMBX12", "computer_modern"),
        ("LMRoman10-Regular", "computer_modern"),
        ("Computer Modern Roman", "computer_modern"),
        ("Latin Modern Roman", "computer_modern"),
        ("ABCDEE+CMR10", "computer_modern"),
        ("ABCDEE+LMRoman10-Regular", "computer_modern"),
        ("ABCDEF+TimesNewRomanPSMT", "times"),
        ("Calibri", "other"),
        ("Helvetica", "other"),
    ],
)
def test_classify_font_ester_accepted_families(font_name: str, expected_class: str) -> None:
    assert classify_font(font_name) == expected_class


@pytest.mark.parametrize(
    "font_name",
    [
        "CMR12",
        "LMRoman10-Regular",
        "ABCDEE+CMR10",
        "ABCDEE+LMRoman10-Regular",
        "Arial",
        "TimesNewRomanPSMT",
    ],
)
def test_accepted_body_font_classes_include_ester_families(font_name: str) -> None:
    assert is_accepted_body_font_family(classify_font(font_name))


def test_computer_modern_class_is_accepted() -> None:
    assert is_accepted_body_font_family("computer_modern")


@pytest.mark.parametrize(
    "font_name",
    ["TimesNewRomanPSMT", "Arial", "CMR12", "LMRoman10-Regular", "ABCDEE+CMR10"],
)
def test_p026a_no_family_warning_for_accepted_fonts(font_name: str) -> None:
    doc = _make_body_font_doc(font_name)
    assert not _family_findings(doc)


def test_p026a_warns_for_calibri() -> None:
    doc = _make_body_font_doc("Calibri")
    findings = _family_findings(doc)
    assert len(findings) == 1
    assert "Calibri" in findings[0].details.get("observed_summary", "")


def test_p026a_warns_for_helvetica() -> None:
    doc = _make_body_font_doc("Helvetica")
    assert _family_findings(doc)


def test_p026b_still_warns_for_wrong_size_with_accepted_font() -> None:
    doc = _make_body_font_doc("CMR12", fontsize=10.0)
    assert not _family_findings(doc)
    assert _size_findings(doc)


def test_p026a_family_comment_does_not_mention_font_size() -> None:
    comment = build_polished_comment(
        rule_id="P026",
        issue_type="possible_body_font_family_issue",
        page=3,
        details={
            "issue_type": "possible_body_font_family_issue",
            "observed_summary": "Calibri",
            "expected": "Times New Roman, Arial, Computer Modern, or Latin Modern",
        },
    )
    lower = comment.lower()
    assert "12pt" not in lower
    assert "font size" not in lower
    assert "times new roman" in lower
    assert "computer modern" in lower


def test_p026b_size_comment_does_not_mention_font_family_names() -> None:
    comment = build_polished_comment(
        rule_id="P026",
        issue_type="possible_body_font_size_issue",
        page=3,
        details={
            "issue_type": "possible_body_font_size_issue",
            "observed_summary": "10.0pt",
            "expected": "12pt",
        },
    )
    lower = comment.lower()
    assert "computer modern" not in lower
    assert "arial" not in lower
    assert "12pt" in lower


def test_public_p026a_card_matches_detector_policy(tmp_path: Path) -> None:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    catalog = wa._build_rule_catalog()
    by_id = {rule["id"]: rule for rule in catalog["student_rules"]}
    family = by_id["P026A"]
    size = by_id["P026B"]

    family_text = (family["title"] + " " + family["how_to_correct"]).lower()
    assert "times new roman" in family_text
    assert "arial" in family_text
    assert "computer modern" in family_text
    assert "latin modern" in family_text
    assert "12pt" not in family["title"].lower()

    size_text = (size["title"] + " " + size["how_to_correct"]).lower()
    assert "12pt" in size_text
    assert "computer modern" not in size_text
    assert "arial" not in size_text

    client = TestClient(wa.app, raise_server_exceptions=False)
    response = client.get("/rules")
    assert response.status_code == 200
    assert "P026A" in response.text
