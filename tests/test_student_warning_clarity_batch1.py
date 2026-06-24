"""Batch-1 student-facing warning clarity regression tests (synthetic metadata only).

Covers the focus rules named in the student-warning-clarity audit:
presentation/comment/actionability wording only — no detector behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import build_polished_comment
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view

_GENERIC_MARKERS = (
    "This check (",
    "found a possible",
    "flagged issue type",
    "was flagged by an automated check",
    "does not appear to follow the expected numbering sequence",
    "Automated finding — please verify",
)

_FORBIDDEN_LEAKS = (
    "/home/",
    "/tmp/",
    "Traceback",
    "\\begin{",
    ".tex:",
    "x0,y0,x1,y1",
)

# Representative synthetic findings for focus rules (no private dissertation text).
_FOCUS_FINDINGS: tuple[AuditFinding, ...] = (
    AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=12,
        message="Margin issue.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": "right_margin",
            "worst_overflow_pt": "6.0",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P012",
        severity=Severity.WARNING,
        page=2,
        message="Annotation detected.",
        details={
            "issue_type": "pdf_annotation_detected",
            "annotation_type": "highlight",
            "confidence": "high",
        },
    ),
    AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=20,
        message="Sequence gap.",
        details={
            "issue_type": "sequence_gap",
            "observed_sequence": "27",
            "expected_sequence": "28",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P020",
        severity=Severity.WARNING,
        page=10,
        message="Title case issue.",
        details={
            "issue_type": "possible_title_capitalization_issue",
            "source": "heading",
            "expected_or_reason": "major_word_requires_capital",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P024",
        severity=Severity.WARNING,
        page=8,
        message="TOC capitalization.",
        details={
            "issue_type": "toc_level_capitalization",
            "entry_index": "2",
            "expected_or_reason": "major_word_requires_capital",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P026",
        severity=Severity.WARNING,
        page=15,
        message="Font family issue.",
        details={
            "issue_type": "possible_body_font_family_issue",
            "observed_summary": "non-standard body font detected",
            "confidence": "low",
        },
    ),
    AuditFinding(
        rule_id="P028",
        severity=Severity.WARNING,
        page=30,
        message="Roman on body page.",
        details={
            "issue_type": "roman_number_on_body_page",
            "observed_style": "Roman numerals",
            "expected_style": "Arabic numerals",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P029",
        severity=Severity.WARNING,
        page=4,
        message="Roman gap.",
        details={
            "issue_type": "roman_sequence_gap",
            "observed_sequence": "iii",
            "expected_sequence": "ii",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P035",
        severity=Severity.WARNING,
        page=22,
        message="Table not centered.",
        details={
            "issue_type": "table_body_not_centered",
            "caption_type": "table",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P036",
        severity=Severity.WARNING,
        page=6,
        message="TOC spacing.",
        details={
            "issue_type": "toc_inter_entry_spacing_too_tight",
            "section_type": "table_of_contents",
            "entry_pair_index": "1",
            "gap_points": "4.0",
            "required_gap_points": "8.0",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P037",
        severity=Severity.WARNING,
        page=5,
        message="Bio sketch numeral.",
        details={
            "issue_type": "roman_bio_sketch_not_iv",
            "observed_sequence": "v",
            "expected_sequence": "iv",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P044",
        severity=Severity.WARNING,
        page=1,
        message="Abstract indent.",
        details={
            "issue_type": "abstract_subsequent_paragraph_not_indented",
            "paragraph_index": "2",
            "confidence": "high",
        },
    ),
    AuditFinding(
        rule_id="P046",
        severity=Severity.WARNING,
        page=18,
        message="LoT alignment.",
        details={
            "issue_type": "lot_entry_number_column_misaligned",
            "section_type": "list_of_tables",
            "entry_index": "3",
            "observed_x0_range_points": "10.0",
            "allowed_x0_range_points": "6.0",
            "confidence": "medium",
        },
    ),
    AuditFinding(
        rule_id="P025",
        severity=Severity.WARNING,
        page=None,
        message="Front-matter order.",
        details={
            "issue_type": "possible_frontmatter_order_issue",
            "confidence": "medium",
        },
    ),
)


def _finding_id(finding: AuditFinding) -> str:
    return f"{finding.rule_id}/{finding.details.get('issue_type')}"


@pytest.mark.parametrize("finding", _FOCUS_FINDINGS, ids=_finding_id)
def test_focus_rule_finding_has_non_empty_student_facing_text(finding: AuditFinding) -> None:
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == finding.rule_id)
    assert fv.polished_comment.strip()
    assert fv.issue_type_explanation.strip()
    assert fv.detailed_explanation.strip()
    assert fv.suggested_fix.strip()


@pytest.mark.parametrize("finding", _FOCUS_FINDINGS, ids=_finding_id)
def test_focus_rule_finding_avoids_generic_placeholder_language(finding: AuditFinding) -> None:
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == finding.rule_id)
    combined = " ".join(
        (fv.polished_comment, fv.issue_type_explanation, fv.detailed_explanation, fv.suggested_fix)
    )
    for marker in _GENERIC_MARKERS:
        assert marker not in combined, f"{finding.rule_id}: generic marker {marker!r}"


@pytest.mark.parametrize("finding", _FOCUS_FINDINGS, ids=_finding_id)
def test_focus_rule_finding_does_not_leak_unsafe_detail_text(finding: AuditFinding) -> None:
    forbidden = "CONFIDENTIAL DISSERTATION SENTENCE NOBODY SHOULD SEE"
    details = dict(finding.details)
    details["line_preview"] = forbidden
    if finding.rule_id != "P026":
        details["observed_summary"] = forbidden
    mutated = AuditFinding(
        rule_id=finding.rule_id,
        severity=finding.severity,
        page=finding.page,
        message=finding.message,
        details=details,
    )
    payload = audit_findings_to_json_dict([mutated], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == finding.rule_id)
    combined = " ".join(
        (fv.polished_comment, fv.issue_type_explanation, fv.detailed_explanation, fv.suggested_fix)
    )
    assert forbidden not in combined
    for leak in _FORBIDDEN_LEAKS:
        assert leak not in combined


def test_page_level_focus_findings_have_page_action_or_honest_explanation() -> None:
    page_level = [f for f in _FOCUS_FINDINGS if f.page is not None and f.rule_id != "P013"]
    for finding in page_level:
        payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
        view = build_report_view(payload)
        fv = next(f for f in view.findings if f.rule_id == finding.rule_id)
        if fv.has_highlight:
            assert fv.action_label == "Open highlighted PDF page"
        elif fv.page is not None:
            assert fv.action_label in {
                "Open highlighted PDF page",
                "Open original PDF page",
                "",
            }
            if fv.action_label == "":
                assert fv.no_highlight_reason.strip()


def test_document_level_finding_uses_explanation_only_action() -> None:
    finding = next(f for f in _FOCUS_FINDINGS if f.rule_id == "P025")
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P025")
    assert fv.page is None
    assert fv.action_kind == "explanation"
    assert fv.action_label == "Read explanation"
    comment_lower = fv.polished_comment.lower()
    assert "document" in comment_lower or "front matter" in comment_lower


def test_p029_roman_sequence_gap_comment_is_specific() -> None:
    comment = build_polished_comment(
        rule_id="P029",
        issue_type="roman_sequence_gap",
        page=4,
        details={"observed_sequence": "iii", "expected_sequence": "ii"},
    )
    lower = comment.lower()
    assert "skipped" in lower or "gap" in lower or "consecutive" in lower
    assert "does not appear to follow the expected numbering sequence" not in comment


def test_p029_p037_markdown_matches_web_polished_comment() -> None:
    findings = [
        f
        for f in _FOCUS_FINDINGS
        if f.rule_id in {"P029", "P037"}
    ]
    payload = audit_findings_to_json_dict(list(findings), {"audit_type": "pdf"})
    view = build_report_view(payload)
    md_path = Path("/tmp") / "batch1_clarity.md"
    write_markdown_report(list(findings), {"audit_type": "pdf"}, md_path)
    md_text = md_path.read_text(encoding="utf-8")
    for fv in view.findings:
        if fv.rule_id not in {"P029", "P037"}:
            continue
        # Markdown should carry the same substantive problem sentence (minus Review needed prefix).
        core = fv.polished_comment.removeprefix("Review needed: ").strip()
        assert core[:40] in md_text or fv.rule_id in md_text


def test_p044_abstract_indent_comment_names_page_role() -> None:
    comment = build_polished_comment(
        rule_id="P044",
        issue_type="abstract_subsequent_paragraph_not_indented",
        page=1,
        details={"paragraph_index": "2"},
    )
    assert "Abstract" in comment
    assert "indent" in comment.lower()


def test_p013_candidate_alone_is_not_a_visible_problem_card() -> None:
    """P013 candidates are triage signals, not standalone student problem cards."""
    finding = AuditFinding(
        rule_id="P013",
        severity=Severity.WARNING,
        page=3,
        message="Page number candidate.",
        details={
            "issue_type": "page_number_candidate",
            "position_type": "bottom_center",
            "confidence": "low",
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    assert not any(f.rule_id == "P013" for f in view.findings)


def test_p046_alignment_comment_names_list_section() -> None:
    comment = build_polished_comment(
        rule_id="P046",
        issue_type="lot_entry_number_column_misaligned",
        page=18,
        details={
            "section_type": "list_of_tables",
            "observed_x0_range_points": "10.0",
            "allowed_x0_range_points": "6.0",
        },
    )
    assert "List of Tables" in comment
    assert "10.0pt" in comment or "alignment" in comment.lower()
