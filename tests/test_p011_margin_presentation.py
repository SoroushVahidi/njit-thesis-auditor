"""Regression tests for P011 margin-boundary presentation quality."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p011_margin_presentation import margin_confidence
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule

_FORBIDDEN_FIX_TOKENS = (
    "figure caption",
    "table caption",
    "header",
    "footer",
    "tables, figures",
)


def _finding_view(details: dict[str, str], *, page: int = 4) -> object:
    finding = AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message="Margin issue.",
        details={"issue_type": "margin_boundary_violation", **details},
    )
    report = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(report)
    return next(f for f in view.findings if f.rule_id == "P011")


def test_abstract_margin_comment_does_not_say_body_content() -> None:
    rendered = _finding_view(
        {
            "side": "right_margin",
            "worst_overflow_pt": "3.5",
            "affected_line_count": "2",
            "confidence": "low",
            "page_context": "abstract",
            "margin_content_kind": "text_paragraph",
            "affected_line_texts": "logistics network, employing more than 200,000 workers…",
        },
        page=4,
    )
    assert "body content" not in rendered.polished_comment.lower()
    assert "abstract content" in rendered.polished_comment.lower()


def test_approval_page_date_uses_specific_remediation() -> None:
    rendered = _finding_view(
        {
            "side": "right_margin",
            "worst_overflow_pt": "35.0",
            "affected_line_count": "1",
            "confidence": "high",
            "page_context": "approval_page",
            "margin_content_kind": "approval_date_layout",
            "affected_line_texts": "Date",
        },
        page=8,
    )
    assert "Date label" in rendered.suggested_fix
    assert "approval-page" in rendered.suggested_fix.lower()
    for token in _FORBIDDEN_FIX_TOKENS:
        assert token not in rendered.suggested_fix.lower()


def test_references_margin_uses_hanging_indent_remediation() -> None:
    rendered = _finding_view(
        {
            "side": "left_margin",
            "worst_overflow_pt": "9.0",
            "affected_line_count": "5",
            "confidence": "medium",
            "page_context": "references",
            "margin_content_kind": "references_hanging_indent",
            "affected_line_texts": "Harris-Adamson, C., et al. (2021)...",
        },
        page=74,
    )
    assert "hanging-indent" in rendered.suggested_fix.lower()
    assert "references" in rendered.suggested_fix.lower()
    assert "body content" not in rendered.polished_comment.lower()


def test_text_paragraph_fix_does_not_mention_tables_or_footers() -> None:
    rendered = _finding_view(
        {
            "side": "right_margin",
            "worst_overflow_pt": "6.0",
            "affected_line_count": "1",
            "confidence": "medium",
            "page_context": "body",
            "margin_content_kind": "text_paragraph",
        },
        page=20,
    )
    lower = rendered.suggested_fix.lower()
    for token in _FORBIDDEN_FIX_TOKENS:
        assert token not in lower
    assert "highlighted text" in lower or "paragraph" in lower


def test_multiple_affected_lines_produce_multiple_highlight_boxes() -> None:
    details = {
        "issue_type": "margin_boundary_violation",
        "side": "right_margin",
        "affected_line_bboxes": "500.0,100.0,540.0,112.0|500.0,120.0,540.0,132.0",
        "bbox": "500.0,100.0,540.0,112.0",
    }
    boxes = parse_highlight_bboxes_from_details(
        details,
        rule_id="P011",
        issue_type="margin_boundary_violation",
    )
    assert len(boxes) == 2


def test_confidence_calibration_thresholds() -> None:
    assert (
        margin_confidence(3.5, 2, page_context="abstract", content_kind="text_paragraph")
        == "low"
    )
    assert (
        margin_confidence(
            35.0,
            1,
            page_context="approval_page",
            content_kind="approval_date_layout",
        )
        == "high"
    )
    assert (
        margin_confidence(
            9.0,
            5,
            page_context="references",
            content_kind="references_hanging_indent",
        )
        == "medium"
    )


def test_reference_continuation_page_inferred_from_line_previews() -> None:
    from njit_auditor.p011_margin_presentation import (
        infer_margin_content_kind,
        infer_page_margin_context,
    )

    previews = [
        "Harris-Adamson, C., et al. (2021). Evaluation of industrial…",
        "Huysamen, K., Bosch, T., de Looze, M. P., Stadler, K….…",
    ]
    assert infer_page_margin_context("", previews) == "references"
    assert infer_margin_content_kind("general", previews) == "references_hanging_indent"


def test_toc_right_margin_uses_toc_specific_wording() -> None:
    rendered = _finding_view(
        {
            "side": "right_margin",
            "worst_overflow_pt": "21.2",
            "affected_line_count": "1",
            "confidence": "medium",
            "page_context": "table_of_contents",
            "margin_content_kind": "toc_entry_right_margin",
            "affected_line_texts": (
                "3.3 The Off-Diagonal Weingarten Loss for CAD-Type Neural SDF "
                "Reconstruction 36"
            ),
        },
        page=9,
    )
    assert "table of contents entry" in rendered.polished_comment.lower()
    assert "21.2 pt" in rendered.polished_comment
    assert "right margin" in rendered.polished_comment.lower()


def test_toc_right_margin_fix_mentions_wrapping_leaders_or_tab_stop() -> None:
    rendered = _finding_view(
        {
            "side": "right_margin",
            "worst_overflow_pt": "21.2",
            "affected_line_count": "1",
            "confidence": "medium",
            "page_context": "table_of_contents",
            "margin_content_kind": "toc_entry_right_margin",
        },
        page=9,
    )
    lower = rendered.suggested_fix.lower()
    assert "table of contents entry wrapping" in lower
    assert "leader dots" in lower
    assert "page-number tab stop" in lower
    for token in _FORBIDDEN_FIX_TOKENS:
        assert token not in lower
    assert "adjust the paragraph" not in lower


def test_toc_bottom_margin_uses_toc_specific_wording() -> None:
    rendered = _finding_view(
        {
            "side": "bottom_margin",
            "worst_overflow_pt": "9.2",
            "affected_line_count": "1",
            "confidence": "medium",
            "page_context": "table_of_contents",
            "margin_content_kind": "toc_entry_bottom_margin",
            "affected_line_texts": "4.5.1 Experimental setup .......... 62",
        },
        page=9,
    )
    assert "table of contents entry" in rendered.polished_comment.lower()
    assert "9.2 pt" in rendered.polished_comment
    assert "bottom" in rendered.polished_comment.lower()
    assert "page number" not in rendered.polished_comment.lower()


def test_toc_bottom_margin_fix_mentions_pagination_spacing_or_page_break() -> None:
    rendered = _finding_view(
        {
            "side": "bottom_margin",
            "worst_overflow_pt": "9.2",
            "affected_line_count": "1",
            "confidence": "medium",
            "page_context": "table_of_contents",
            "margin_content_kind": "toc_entry_bottom_margin",
        },
        page=9,
    )
    lower = rendered.suggested_fix.lower()
    assert "pagination" in lower
    assert "spacing" in lower or "page break" in lower
    for token in _FORBIDDEN_FIX_TOKENS:
        assert token not in lower
    assert "adjust the paragraph" not in lower


def test_toc_bottom_margin_does_not_blame_printed_page_number() -> None:
    rendered = _finding_view(
        {
            "side": "bottom_margin",
            "worst_overflow_pt": "9.2",
            "affected_line_count": "1",
            "confidence": "medium",
            "page_context": "table_of_contents",
            "margin_content_kind": "toc_entry_bottom_margin",
        },
        page=9,
    )
    lower = rendered.detailed_explanation.lower()
    assert "not about the page's printed page number" in lower


def test_tiny_toc_overflow_is_low_confidence() -> None:
    assert (
        margin_confidence(
            4.3, 1, page_context="table_of_contents", content_kind="toc_entry_right_margin"
        )
        == "low"
    )


def test_tiny_toc_overflow_repeated_across_entries_is_medium() -> None:
    assert (
        margin_confidence(
            4.3, 3, page_context="table_of_contents", content_kind="toc_entry_right_margin"
        )
        == "medium"
    )


def test_large_toc_overflow_remains_medium_not_high() -> None:
    assert (
        margin_confidence(
            21.2, 1, page_context="table_of_contents", content_kind="toc_entry_right_margin"
        )
        == "medium"
    )
    assert (
        margin_confidence(
            9.2, 1, page_context="table_of_contents", content_kind="toc_entry_bottom_margin"
        )
        == "medium"
    )


def test_toc_entry_content_kind_inferred_from_side_and_page_context() -> None:
    from njit_auditor.p011_margin_presentation import infer_margin_content_kind

    toc_previews = ["3.3 The Off-Diagonal Weingarten Loss Reconstruction 36"]
    assert (
        infer_margin_content_kind("table_of_contents", toc_previews, side="right_margin")
        == "toc_entry_right_margin"
    )
    assert (
        infer_margin_content_kind("table_of_contents", toc_previews, side="bottom_margin")
        == "toc_entry_bottom_margin"
    )


def test_toc_entry_pdf_end_to_end_produces_toc_content_kind(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_margin.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((350, 150), "3.3 The Off-Diagonal Weingarten Loss  545")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in run_pdf_margin_rule(model)
        if f.details.get("issue_type") == "margin_boundary_violation"
    ]
    assert findings
    finding = findings[0]
    assert finding.details.get("page_context") == "table_of_contents"
    assert finding.details.get("margin_content_kind") == "toc_entry_right_margin"


def test_off_center_margin_pdf_stores_all_line_bboxes(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_two_lines.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    page.insert_text((520, 130), "Line one crossing the right margin boundary here.")
    page.insert_text((520, 150), "Line two also crossing the right margin boundary.")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in run_pdf_margin_rule(model)
        if f.details.get("issue_type") == "margin_boundary_violation"
    ]
    assert findings
    finding = findings[0]
    assert finding.details.get("page_context") == "abstract"
    assert int(finding.details.get("affected_line_count", "0")) >= 2
    assert "|" in finding.details.get("affected_line_bboxes", "")
