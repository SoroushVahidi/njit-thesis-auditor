"""Tests for P012 page-level annotation rollup in student-facing reports."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p012_student_preview import (
    consume_p012_display_slot,
    p012_location_label,
    p012_rolled_up_comment,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule


def _p012_finding(
    *,
    page: int,
    rect: str = "72.0,100.0,200.0,120.0",
    annotation_type: str = "Text",
    content: str = "Private reviewer note should never appear.",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P012",
        severity=Severity.WARNING,
        page=page,
        message=f"PDF annotation/comment detected ({annotation_type}).",
        details={
            "issue_type": "pdf_annotation_detected",
            "annotation_type": annotation_type,
            "content": content,
            "rect": rect,
        },
    )


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def test_p012_location_label_includes_page_and_count() -> None:
    assert p012_location_label(7, 1) == "Page 7 — PDF annotations/comments detected"
    assert p012_location_label(7, 4) == "Page 7 — 4 PDF annotations/comments detected"


def test_multiple_p012_findings_on_same_page_roll_up_to_one_card() -> None:
    findings = [
        _p012_finding(page=4, rect="50.0,50.0,150.0,100.0"),
        _p012_finding(page=4, rect="200.0,200.0,300.0,260.0", annotation_type="Highlight"),
        _p012_finding(page=4, rect="0.0,0.0,0.0,0.0", annotation_type="Text"),
    ]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P012"]
    assert len(cards) == 1
    assert cards[0].location_label == "Page 4 — 3 PDF annotations/comments detected"
    assert "3 annotations or comments on page 4" in cards[0].polished_comment


def test_p012_findings_on_different_pages_remain_distinguishable() -> None:
    findings = [_p012_finding(page=3), _p012_finding(page=8)]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P012"]
    assert len(cards) == 2
    labels = {card.location_label for card in cards}
    assert labels == {
        "Page 3 — PDF annotations/comments detected",
        "Page 8 — PDF annotations/comments detected",
    }


def test_consume_p012_display_slot_keeps_first_page_only() -> None:
    seen: set[str] = set()
    assert consume_p012_display_slot(4, seen) is True
    assert consume_p012_display_slot(4, seen) is False
    assert consume_p012_display_slot(5, seen) is True


def test_p012_rollup_student_facing_text_has_no_private_leaks() -> None:
    findings = [_p012_finding(page=2, content="Reviewer: fix this paragraph now.")]
    view = build_report_view(_payload(findings))
    card = view.findings[0]
    for forbidden in (
        "Reviewer:",
        "fix this paragraph",
        "72.0",
        "100.0",
        "Private reviewer",
    ):
        assert forbidden not in card.location_label
        assert forbidden not in card.polished_comment
        assert forbidden not in card.detailed_explanation


def test_markdown_report_aligns_p012_problem_numbering_with_web(tmp_path: Path) -> None:
    findings = [
        _p012_finding(page=4, rect="50.0,50.0,150.0,100.0"),
        _p012_finding(page=4, rect="200.0,200.0,300.0,260.0"),
        _p012_finding(page=9),
    ]
    payload = _payload(findings)
    view = build_report_view(payload)
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert text.count("### Problem") == len(view.findings)
    assert "Page 4 — 2 PDF annotations/comments detected" in text
    assert "Page 9 — PDF annotations/comments detected" in text
    assert "2 annotations or comments on page 4" in text
    assert "Reviewer:" not in text


def test_detector_raw_p012_findings_unchanged_by_report_view() -> None:
    findings = [_p012_finding(page=1), _p012_finding(page=1)]
    payload = _payload(findings)
    before = len(payload["findings"])
    build_report_view(payload)
    assert len(payload["findings"]) == before


def test_p012_rolled_up_comment_uses_review_prefix() -> None:
    comment = p012_rolled_up_comment(page=5, annotation_count=2)
    assert comment.startswith("Review needed:")
    assert "page 5" in comment


def test_run_pdf_annotation_rule_emits_per_annotation_findings(tmp_path: Path) -> None:
    import fitz

    pdf_path = tmp_path / "annotated.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.add_text_annot((72, 72), "secret reviewer note")
    page.add_text_annot((120, 120), "second note")
    doc.save(pdf_path)
    doc.close()

    findings = run_pdf_annotation_rule(str(pdf_path))
    assert len(findings) == 2
    assert all(f.rule_id == "P012" for f in findings)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    assert len([f for f in view.findings if f.rule_id == "P012"]) == 1
