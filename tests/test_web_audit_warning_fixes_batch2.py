"""Tests for web-audit warning fixes batch 2 (highlight precision, wording, wrappers, P035)."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.digital_commons_wrapper import (
    detect_digital_commons_wrapper_pages,
    is_digital_commons_wrapper_page,
    is_layout_warning_suppressed_on_wrapper_page,
)
from njit_auditor.highlight_targeting import (
    estimate_word_bbox_in_line_bbox,
    parse_highlight_bboxes_from_details,
    resolve_primary_highlight_bbox,
    word_bbox_in_line,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p011_student_preview import (
    P011PagePresentationStats,
    p011_combined_rolled_up_comment,
    p011_combined_suggested_fix,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfTextLine, PdfTextSpan
from njit_auditor.polished_comments import build_polished_comment
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout


def _line_with_word(word: str) -> PdfTextLine:
    before, after = "A study of perceptions related to ", " readiness"
    text = f"{before}{word}{after}"
    span_before = PdfTextSpan(
        text=before,
        bbox=BBox(x0=72.0, y0=100.0, x1=220.0, y1=112.0),
    )
    span_word = PdfTextSpan(
        text=word,
        bbox=BBox(x0=220.0, y0=100.0, x1=250.0, y1=112.0),
    )
    span_after = PdfTextSpan(
        text=after,
        bbox=BBox(x0=250.0, y0=100.0, x1=360.0, y1=112.0),
    )
    return PdfTextLine(
        text=text,
        bbox=BBox(x0=72.0, y0=100.0, x1=360.0, y1=112.0),
        spans=[span_before, span_word, span_after],
    )


def test_token_bbox_prefers_narrow_span_over_full_line_bbox() -> None:
    line = _line_with_word("study")
    token_bbox = word_bbox_in_line(line, "study")
    assert token_bbox is not None
    assert token_bbox.width < line.bbox.width
    resolved = resolve_primary_highlight_bbox(
        {
            "bbox": "72.0,100.0,360.0,112.0",
            "token_bbox": "220.0,100.0,250.0,112.0",
            "flagged_word": "study",
            "line_preview": line.text,
        },
        rule_id="P020",
        issue_type="possible_title_capitalization_issue",
    )
    assert resolved == (220.0, 100.0, 250.0, 112.0)


def test_token_bbox_estimates_from_line_preview_when_only_line_bbox_exists() -> None:
    line_bbox = (72.0, 100.0, 372.0, 112.0)
    preview = "A study of perceptions related to readiness"
    estimated = estimate_word_bbox_in_line_bbox(line_bbox, preview, "study")
    assert estimated is not None
    assert estimated[2] - estimated[0] < line_bbox[2] - line_bbox[0]
    resolved = resolve_primary_highlight_bbox(
        {
            "bbox": "72.0,100.0,372.0,112.0",
            "flagged_word": "study",
            "line_preview": preview,
        },
        rule_id="P020",
        issue_type="possible_title_capitalization_issue",
    )
    assert resolved is not None
    assert resolved[2] - resolved[0] < 300.0


def test_p020_report_view_uses_token_bbox_for_highlight() -> None:
    findings = [
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=1,
            message="Title case issue.",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "flagged_word": "study",
                "corrected_word": "Study",
                "line_preview": "A study of perceptions related to readiness",
                "bbox": "72.0,100.0,360.0,112.0",
                "token_bbox": "220.0,100.0,250.0,112.0",
                "source": "heading",
                "expected_or_reason": "major_word",
            },
        )
    ]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    card = view.findings[0]
    assert card.has_highlight is True
    assert card.bbox == (220.0, 100.0, 250.0, 112.0)
    assert card.action_kind == "highlight"


def test_p015_and_p044_avoid_later_paragraph_wording() -> None:
    p015 = build_polished_comment(
        rule_id="P015",
        issue_type="missing_later_indent",
        severity="WARNING",
        page=31,
        details={"paragraph_index": "2"},
        category="indentation",
    )
    p044 = build_polished_comment(
        rule_id="P044",
        issue_type="abstract_subsequent_paragraph_not_indented",
        severity="WARNING",
        page=4,
        details={"paragraph_index": "1"},
        category="indentation",
    )
    for text in (p015, p044):
        lowered = text.lower()
        assert "later paragraph" not in lowered
        assert "later-paragraph" not in lowered
        assert "review needed: problem:" not in lowered
    assert "paragraph after the first" in p015.lower() or "body paragraph 2" in p015.lower()
    assert "abstract paragraph after the first" in p044.lower()


def test_p011_combined_comment_uses_plain_language_and_margin_grammar() -> None:
    stats = P011PagePresentationStats(
        page=11,
        sides=("right_margin", "top_margin"),
        raw_finding_count=2,
        highlight_bboxes=((500.0, 40.0, 540.0, 60.0), (400.0, 30.0, 450.0, 50.0)),
    )
    comment = p011_combined_rolled_up_comment(stats)
    fix = p011_combined_suggested_fix(stats)
    assert "right and top margins" in comment
    assert "Review needed:" not in comment
    assert "right and top margins" in fix
    assert "right, top margins" not in fix


def test_p011_multi_side_card_keeps_highlight_action_when_bboxes_exist() -> None:
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=11,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "right_margin",
                "bbox": "500.0,40.0,540.0,60.0",
            },
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=11,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "top_margin",
                "bbox": "400.0,30.0,450.0,50.0",
            },
        ),
    ]
    view = build_report_view(
        audit_findings_to_json_dict(findings, {"audit_type": "pdf"}),
        pdf_page_sizes=[(612.0, 792.0)] * 20,
    )
    card = next(f for f in view.findings if f.rule_id == "P011")
    assert card.has_highlight is True
    assert card.action_kind == "highlight"
    assert "right and top margins" in card.polished_comment


def _make_digital_commons_wrapper_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Digital Commons @ NJIT", fontsize=14)
    page.insert_text((72, 100), "Electronic Theses and Dissertations", fontsize=11)
    page.insert_text((72, 130), "Recommended Citation", fontsize=11)
    page.insert_text(
        (72, 150),
        "This Thesis is brought to you for free and open access by Digital Commons.",
        fontsize=11,
    )
    page.insert_text((72, 170), "https://digitalcommons.njit.edu/theses/123", fontsize=10)
    page.insert_text(
        (72, 220),
        "New Jersey Institute of Technology, ta244@njit.edu",
        fontsize=11,
    )
    doc.save(path)
    doc.close()


def test_digital_commons_wrapper_page_detection_is_conservative(tmp_path: Path) -> None:
    pdf_path = tmp_path / "ordinary_citation.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "CHAPTER 1 INTRODUCTION", fontsize=14)
    page.insert_text(
        (72, 120),
        "See https://digitalcommons.njit.edu/theses/123 for related work.",
        fontsize=11,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not is_digital_commons_wrapper_page(model.pages[0])


def test_digital_commons_wrapper_suppresses_layout_warnings_and_emits_notice(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "digital_commons_wrapper.pdf"
    _make_digital_commons_wrapper_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    assert detect_digital_commons_wrapper_pages(model) == {1}
    assert is_layout_warning_suppressed_on_wrapper_page("P011", 1, {1}) is True
    assert is_layout_warning_suppressed_on_wrapper_page("P011", 2, {1}) is False

    from njit_auditor.audit_runner import collect_pdf_layout_findings

    findings = collect_pdf_layout_findings(model, pdf_path)
    assert not any(f.rule_id == "P011" and f.page == 1 for f in findings)
    wrapper_findings = [
        f
        for f in findings
        if f.details.get("issue_type") == "digital_commons_wrapper_pages_detected"
    ]
    assert len(wrapper_findings) == 1


def test_digital_commons_notice_labeled_notice_not_problem(tmp_path: Path) -> None:
    """The DC wrapper-pages finding is a preprocessing notice, not a formatting
    problem: it should render as "Notice N", use the audit-accuracy-framed
    suggested fix, and remain actionable via the original-page link even
    though it has no highlight bbox."""
    pdf_path = tmp_path / "digital_commons_wrapper_notice.pdf"
    _make_digital_commons_wrapper_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    from njit_auditor.audit_runner import collect_pdf_layout_findings

    findings = collect_pdf_layout_findings(model, pdf_path)
    wrapper_finding = next(
        f
        for f in findings
        if f.details.get("issue_type") == "digital_commons_wrapper_pages_detected"
    )
    assert "upload the thesis manuscript PDF without" in wrapper_finding.details.get(
        "suggested_fix", ""
    )
    assert "before submitting" not in wrapper_finding.details.get("suggested_fix", "")

    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(report)
    problem = next(
        p
        for p in view.grouped_problems
        if p.issue_type == "digital_commons_wrapper_pages_detected"
    )
    assert problem.problem_number_label.startswith("Notice")
    assert not problem.problem_number_label.startswith("Problem")

    wrapper_view = next(
        f for f in view.findings if f.issue_type == "digital_commons_wrapper_pages_detected"
    )
    assert wrapper_view.action_kind == "original_page"


def test_p035_figure_caption_below_body_with_following_prose_does_not_flag(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p035_image_only_figure_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 2 RESULTS", fontsize=14, fontname="Times-Bold")
    page.insert_text(
        (108, 260),
        "Figure 1.1 Biomechanical representation of trunk support.",
        fontsize=11,
    )
    page.insert_text(
        (108, 280),
        "The results in Figure 1.1 show a clear pattern across participants.",
        fontsize=11,
    )
    page.insert_text(
        (108, 298),
        "Additional analysis confirmed the same trend in every subgroup.",
        fontsize=11,
    )
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert not any(
        w.details.get("issue_type") == "figure_caption_not_below_body" for w in warnings
    )


def test_p035_placement_finding_includes_body_and_caption_highlight_boxes(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p035_figure_caption_above.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 2 RESULTS", fontsize=14, fontname="Times-Bold")
    page.insert_text(
        (180, 180),
        "Row alpha value and row beta value for synthetic figure body",
        fontsize=11,
    )
    page.insert_text(
        (180, 198),
        "Row gamma value and row delta value for synthetic figure body",
        fontsize=11,
    )
    page.insert_text(
        (108, 140),
        "Figure 1.1 Biomechanical representation of trunk support.",
        fontsize=11,
    )
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [
        f
        for f in check_pdf_figure_table_layout(model)
        if f.details.get("issue_type") == "figure_caption_not_below_body"
    ]
    assert warnings
    boxes = parse_highlight_bboxes_from_details(
        warnings[0].details,
        rule_id="P035",
        issue_type="figure_caption_not_below_body",
    )
    assert len(boxes) == 2


def test_p035_report_view_uses_figure_specific_suggested_fix() -> None:
    findings = [
        AuditFinding(
            rule_id="P035",
            severity=Severity.WARNING,
            page=21,
            message="Figure caption placement issue.",
            details={
                "issue_type": "figure_caption_not_below_body",
                "float_type": "figure",
                "float_number": "1.1",
                "bbox": "108.0,260.0,420.0,272.0",
                "body_bbox": "180.0,180.0,420.0,210.0",
                "caption_bbox": "108.0,260.0,420.0,272.0",
            },
        )
    ]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    card = view.findings[0]
    assert "Figure 1.1" in card.suggested_fix
    assert "table caption" not in card.suggested_fix.lower()
    assert card.has_highlight is True
