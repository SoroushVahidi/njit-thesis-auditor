"""Tests for the Review needed prefix policy on student-facing polished comments."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.polished_comments import REVIEW_PREFIX, build_polished_comment
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    check_pdf_lot_lof_entry_number_alignment,
)
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing


def _assert_no_generic_review_prefix(comment: str) -> None:
    assert not comment.startswith(REVIEW_PREFIX), (
        f"deterministic comment should not use generic prefix: {comment!r}"
    )


def test_p011_margin_comment_is_direct_without_generic_prefix() -> None:
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        )
    ]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    comment = view.findings[0].polished_comment
    _assert_no_generic_review_prefix(comment)
    assert comment.startswith("Problem:")
    assert "page 3" in comment
    assert "left margin" in comment.lower()


def test_p019_missing_page_number_comment_is_direct_without_generic_prefix() -> None:
    findings = [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=8,
            message="Missing page number.",
            details={"issue_type": "missing_page_number"},
        )
    ]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    comment = view.findings[0].polished_comment
    _assert_no_generic_review_prefix(comment)
    assert comment.startswith("Problem:")
    assert "did not find a clear page number" in comment


def test_p026_font_comment_uses_problem_prefix_not_review_needed() -> None:
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=4,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "observed_font": "Helvetica",
                "confidence": "medium",
            },
        )
    ]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    comment = view.findings[0].polished_comment
    _assert_no_generic_review_prefix(comment)
    assert comment.startswith("Likely problem:")
    assert "Helvetica" in comment
    assert view.findings[0].confidence_label == "Medium confidence"


def test_p044_abstract_indent_comment_is_direct_instruction() -> None:
    comment = build_polished_comment(
        rule_id="P044",
        issue_type="abstract_subsequent_paragraph_not_indented",
        page=2,
        details={"paragraph_index": "2"},
    )
    _assert_no_generic_review_prefix(comment)
    assert "indent" in comment.lower()
    assert "Abstract" in comment


def test_p036_spacing_comment_names_section_without_generic_prefix(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_prefix_policy.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 140), "Chapter 3 Literature Review and Background ....", fontsize=12)
    page.insert_text((500, 140), "10", fontsize=12)
    page.insert_text((108, 170), "Chapter 4 Extended Dissertation Topic Title ....", fontsize=12)
    page.insert_text((500, 170), "12", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    finding = next(f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036")
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    comment = view.findings[0].polished_comment
    _assert_no_generic_review_prefix(comment)
    assert "Table of Contents" in comment
    assert "spacing" in comment.lower()


def test_p046_alignment_comment_stays_direct(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p046_prefix_policy.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 115), "Table")
    page.insert_text((500, 115), "Page")
    entries = [
        ("Table 1 Synthetic setup overview entry text here.", 108.0),
        ("Table 2 Synthetic performance comparison entry text here.", 130.0),
        ("Table 3 Synthetic regression coefficients overview entry text.", 108.0),
    ]
    for idx, (label, x) in enumerate(entries):
        y = 140 + idx * 20
        page.insert_text((x, y), label)
        page.insert_text((500, y), "12")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    finding = next(
        f
        for f in check_pdf_lot_lof_entry_number_alignment(model)
        if f.rule_id == "P046"
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    comment = view.findings[0].polished_comment
    _assert_no_generic_review_prefix(comment)
    assert "aligned" in comment.lower()
    for label, _ in entries:
        assert label not in comment


def test_unknown_rule_fallback_keeps_review_prefix_for_uncertainty() -> None:
    comment = build_polished_comment(
        rule_id="P999",
        issue_type="unknown_issue",
        page=1,
        details={},
    )
    assert comment.startswith(REVIEW_PREFIX)
    assert "P999" in comment


def test_p013_candidate_uses_confirm_wording_not_generic_prefix() -> None:
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=5,
            message="Candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
            },
        )
    ]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
  # P013 candidates are informational inventory, not problem cards.
    assert not view.findings
    assert view.inventory_findings
    inv_comment = view.inventory_findings[0].polished_comment
    _assert_no_generic_review_prefix(inv_comment)
    assert inv_comment.startswith("Please confirm:")


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "details", "needle"),
    [
        (
            "P011",
            "margin_boundary_violation",
            {"side": "left_margin", "confidence": "high"},
            "left margin",
        ),
        (
            "P019",
            "missing_page_number",
            {},
            "page number",
        ),
        (
            "P020",
            "possible_title_capitalization_issue",
            {
                "flagged_word": "background",
                "corrected_word": "Background",
                "source": "heading",
                "expected_or_reason": "major_word_requires_capital",
            },
            "capitalized",
        ),
    ],
)
def test_markdown_individual_comments_match_web_without_generic_prefix(
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    needle: str,
    tmp_path: Path,
) -> None:
    finding = AuditFinding(
        rule_id=rule_id,
        severity=Severity.WARNING,
        page=7,
        message="Synthetic warning.",
        details={"issue_type": issue_type, **details},
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    web_comment = view.findings[0].polished_comment
    _assert_no_generic_review_prefix(web_comment)
    assert needle.lower() in web_comment.lower()

    md_path = tmp_path / "prefix_policy.md"
    write_markdown_report([finding], {"audit_type": "pdf"}, md_path)
    md_text = md_path.read_text(encoding="utf-8")
    assert needle.lower() in md_text.lower()
    assert "Review needed:" not in md_text or md_text.count("Review needed:") == 0


def test_p014_heading_comment_is_direct_without_generic_prefix(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p014_prefix_policy.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((120, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    finding = next(f for f in check_named_frontmatter_headings(model) if f.rule_id == "P014")
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    comment = view.findings[0].polished_comment
    _assert_no_generic_review_prefix(comment)
    assert "heading" in comment.lower() or "centered" in comment.lower()
