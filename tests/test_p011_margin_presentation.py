"""Regression tests for P011 margin-boundary presentation quality."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.models import AuditFinding, Severity
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
        "highlight_bboxes": "500.0,100.0,540.0,112.0 | 500.0,120.0,540.0,132.0",
        "bbox": "500.0,100.0,540.0,132.0",
    }
    boxes = parse_highlight_bboxes_from_details(
        details,
        rule_id="P011",
        issue_type="margin_boundary_violation",
    )
    assert len(boxes) == 2


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


def test_numbered_reference_continuation_page_inferred_from_page_text() -> None:
    """Regression for the "[24]H. Oshitani..." IEEE/numeric citation style,
    which does not match the APA "Lastname, F. (YYYY)" pattern. A continuation
    page of a numbered reference list has no "References" heading of its own,
    so the page text itself (not just the violating line previews) must carry
    the signal."""
    from njit_auditor.p011_margin_presentation import infer_page_margin_context

    page_text = (
        "[24]H.Oshitani,T.Kamigaki,andA.Suzuki,“Majorissuesandchallengesof"
        "influenzapandemicpreparednessindevelopingcountries,” Emerging "
        "infectious diseases, vol. 14, pp. 875-80, 07 2008.\n"
        "[25]S.Müller,M.Balmer,W.Charlton,R.Ewert,A.Neumann,C.Rakow,"
        "T.Schlenther"
    )
    assert infer_page_margin_context(page_text, []) == "references"


def test_reference_page_with_abstract_html_citation_url_not_misclassified() -> None:
    """Regression for pages that cite NeurIPS/OpenReview papers, whose landing
    pages are literally named "Abstract.html" (e.g.
    proceedings.neurips.cc/paper/1999/hash/<id>-Abstract.html). The lone word
    "Abstract" inside that URL previously outranked the numbered-reference
    signal and mislabeled the page as Abstract-section content."""
    from njit_auditor.p011_margin_presentation import infer_page_margin_context

    page_text = (
        "[47]R.S.Sutton,D.McAllester,S.Singh,andY.Mansour,“PolicyGradient"
        "MethodsforReinforcementLearningwithFunctionApproximation,” in "
        "Advances in Neural Information Processing Systems, vol. 12. MIT "
        "Press, 1999. [Online]. Available: https://proceedings.neurips.cc/"
        "paper/1999/hash/464d828b85b0bed98e80ade0a5c43b0f-Abstract.html\n"
        "[48]R.J.Williams,“Simplestatisticalgradient-followingalgorithms"
        "forconnectionistreinforcementlearning,” Machine learning, 1992."
    )
    assert infer_page_margin_context(page_text, []) == "references"


def test_single_inline_bracket_citation_does_not_trigger_references_page_signal() -> None:
    """A single inline body citation shaped like "[12] Recent work..." can
    coincidentally match the numbered-reference-entry pattern once, but body
    prose should not be misclassified as a references page on that alone."""
    from njit_auditor.p011_margin_presentation import infer_page_margin_context

    page_text = (
        "This approach builds on prior work. As shown in [12] Recent studies "
        "demonstrate that the proposed method generalizes well across domains "
        "and datasets used throughout this chapter."
    )
    assert infer_page_margin_context(page_text, []) != "references"


def test_numbered_reference_left_margin_overflow_stays_high_confidence_with_correct_wording(
    tmp_path: Path,
) -> None:
    """End-to-end regression for the reported live bug: a references
    continuation page (no "References" heading on the page itself, IEEE-style
    numbered entries, and a citation URL containing the word "Abstract")
    should keep its high-confidence left-margin warning, label it as
    references content, and suggest hanging-indent remediation -- not
    "Abstract content" / "Thesis content" and not a line-spacing fix."""
    pdf_path = tmp_path / "numbered_reference_continuation.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    lines = [
        "[47]R.S.Sutton, D. McAllester, S. Singh, and Y. Mansour, Policy",
        "Gradient Methods, .../hash/abc123-Abstract.html, 1999.",
        "[48]R.J.Williams, Simple statistical gradient-following algorithms,",
        "Machine learning, 1992.",
        "[49]A.Corana, M. Marchesi, C. Martini, and S. Ridella, Minimizing",
        "multimodal functions, ACM TOMS, 1987.",
    ]
    y = 100
    for line in lines:
        page.insert_text((60, y), line, fontsize=11)
        y += 20
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
    assert finding.details.get("page_context") == "references"
    assert finding.details.get("confidence") == "high"

    report = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(report)
    rendered = next(f for f in view.findings if f.rule_id == "P011")

    comment_lower = rendered.polished_comment.lower()
    assert "references content" in comment_lower or "reference-list content" in comment_lower
    assert "abstract content" not in comment_lower
    assert "thesis content" not in comment_lower

    fix_lower = rendered.suggested_fix.lower()
    assert "hanging-indent" in fix_lower or "hanging indent" in fix_lower
    assert "reference" in fix_lower
    assert "line spacing" not in fix_lower


def test_body_text_fix_uses_body_wording_not_line_spacing() -> None:
    """Horizontal (left/right) body-text overflow must say "body text" (not the
    generic "thesis content") and must not suggest line spacing, since line
    spacing does not fix horizontal overflow."""
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
    assert "body text" in lower
    assert "line spacing" not in lower
    assert "thesis content" not in lower
    for token in _FORBIDDEN_FIX_TOKENS:
        assert token not in lower


def test_body_text_vertical_overflow_may_mention_line_spacing() -> None:
    """Top/bottom overflow is itself vertical evidence, so line spacing is a
    legitimate suggestion there (unlike for horizontal overflow)."""
    from njit_auditor.p011_margin_presentation import margin_suggested_fix

    fix = margin_suggested_fix(
        page_context="body",
        content_kind="text_paragraph",
        side_label="bottom margin",
    )
    assert "line spacing" in fix.lower()
    assert "body text" in fix.lower()


def test_table_content_kind_suggests_table_specific_remediation() -> None:
    from njit_auditor.p011_margin_presentation import (
        infer_margin_content_kind,
        margin_suggested_fix,
    )

    assert infer_margin_content_kind("body", ["Table 3: Summary of results"]) == "table_layout"
    fix = margin_suggested_fix(
        page_context="body", content_kind="table_layout", side_label="right margin"
    ).lower()
    assert "table" in fix
    assert "column" in fix or "width" in fix
    assert "line spacing" not in fix


def test_figure_content_kind_suggests_figure_specific_remediation() -> None:
    from njit_auditor.p011_margin_presentation import (
        infer_margin_content_kind,
        margin_suggested_fix,
    )

    assert infer_margin_content_kind("body", ["Figure 2: Architecture diagram"]) == "figure_layout"
    fix = margin_suggested_fix(
        page_context="body", content_kind="figure_layout", side_label="right margin"
    ).lower()
    assert "figure" in fix
    assert "caption" in fix
    assert "line spacing" not in fix


def test_code_listing_content_kind_suggests_listing_specific_remediation() -> None:
    from njit_auditor.p011_margin_presentation import (
        infer_margin_content_kind,
        margin_suggested_fix,
    )

    assert (
        infer_margin_content_kind("general", ["Listing 4.1: Training loop"]) == "code_listing"
    )
    fix = margin_suggested_fix(
        page_context="general", content_kind="code_listing", side_label="right margin"
    ).lower()
    assert "listing" in fix
    assert "wrap" in fix or "indentation" in fix
    assert "line spacing" not in fix


def test_toc_content_kind_suggests_toc_specific_remediation() -> None:
    from njit_auditor.p011_margin_presentation import (
        infer_margin_content_kind,
        margin_suggested_fix,
    )

    assert infer_margin_content_kind("table_of_contents", []) == "toc_entry"
    fix = margin_suggested_fix(
        page_context="table_of_contents", content_kind="toc_entry", side_label="right margin"
    ).lower()
    assert "tab stop" in fix or "dot leader" in fix
    assert "indentation" in fix or "entry" in fix
    assert "line spacing" not in fix


def test_unknown_generic_content_gets_safe_fallback_without_line_spacing() -> None:
    from njit_auditor.p011_margin_presentation import margin_suggested_fix

    fix = margin_suggested_fix(
        page_context="general", content_kind="text_paragraph", side_label="right margin"
    ).lower()
    assert "line spacing" not in fix
    assert "1.5 inches" in fix
    assert "1 inch" in fix


def test_approval_page_date_wording_unchanged_by_content_aware_update() -> None:
    """The approval-page Date-label remediation is a specific, already-correct
    fix and must not be replaced by any of the new generic/body wording."""
    from njit_auditor.p011_margin_presentation import margin_suggested_fix

    fix = margin_suggested_fix(
        page_context="approval_page",
        content_kind="approval_date_layout",
        side_label="right margin",
    )
    assert fix == (
        "Set left margin to 1.5 inches and top, bottom, and right margin to 1 inch. "
        "Move the Date label and signature/date line layout left, or shorten the line, "
        "so all approval-page content stays within the required margin."
    )


def test_margin_fix_content_aware_update_preserves_confidence_and_overflow(
    tmp_path: Path,
) -> None:
    """Content-aware wording changes must never affect confidence, overflow
    measurement, rule ID, or highlight targeting -- only the suggested-fix text."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((520, 130), "Table 1: crossing the right margin boundary here.", fontsize=11)
    pdf_path = tmp_path / "table_caption_overflow.pdf"
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
    assert finding.rule_id == "P011"
    assert finding.details.get("margin_content_kind") == "table_layout"

    report = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(report)
    rendered = next(f for f in view.findings if f.rule_id == "P011")
    assert rendered.confidence == finding.details.get("confidence")
    assert "table" in rendered.suggested_fix.lower()

    boxes = parse_highlight_bboxes_from_details(
        finding.details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    assert boxes, "table-specific wording must not remove highlight targeting"


def test_off_center_margin_pdf_stores_page_context_and_highlight_bboxes(tmp_path: Path) -> None:
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
    assert finding.details.get("highlight_bboxes")
    assert finding.details.get("margin_boundary_bbox")
