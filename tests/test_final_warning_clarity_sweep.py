"""Tests for final warning clarity sweep presentation improvements."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.p011_student_preview import p011_page_location_label
from njit_auditor.pdf_highlight import sub_page_location_label
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, enriched_pdf_location_label


def _p011_finding(*, page: int, side: str) -> AuditFinding:
    return AuditFinding(
        rule_id="P011",
        severity=Severity.WARNING,
        page=page,
        message="Margin issue.",
        details={
            "issue_type": "margin_boundary_violation",
            "side": side,
            "bbox": "72.0,100.0,200.0,120.0",
        },
    )


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def test_p011_same_page_multiple_sides_roll_up_to_one_card() -> None:
    findings = [
        _p011_finding(page=11, side="right_margin"),
        _p011_finding(page=11, side="bottom_margin"),
    ]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P011"]
    assert len(cards) == 1
    assert cards[0].location_label == "Page 11 — bottom and right margins"
    assert "2 margin-boundary issues" in cards[0].polished_comment


def test_p011_single_side_page_keeps_side_specific_label() -> None:
    findings = [_p011_finding(page=4, side="left_margin")]
    view = build_report_view(_payload(findings))
    card = view.findings[0]
    assert card.location_label == "Page 4 — left margin"


def test_p038_required_heading_missing_has_front_matter_label() -> None:
    label = enriched_pdf_location_label(
        "P038",
        "required_heading_missing",
        {"expected_heading": "TABLE OF CONTENTS"},
        None,
    )
    assert label == "Front matter — required heading missing: TABLE OF CONTENTS"


def test_visible_problems_have_non_blank_location_labels() -> None:
    findings = [
        _p011_finding(page=2, side="right_margin"),
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            message="Missing heading.",
            details={
                "issue_type": "required_heading_missing",
                "expected_heading": "BIOGRAPHICAL SKETCH",
            },
        ),
    ]
    view = build_report_view(_payload(findings))
    for card in view.findings:
        assert card.location_label.strip()


def test_sub_page_location_label_uses_body_text_not_body_area() -> None:
    label = sub_page_location_label((250.0, 259.0, 350.0, 279.0), (612.0, 792.0))
    assert label == "body text"
    assert "Body area" not in label
    assert sub_page_location_label((500.0, 400.0, 580.0, 420.0), (612.0, 792.0)) == "Right margin"


def test_markdown_aligns_p011_combined_location(tmp_path: Path) -> None:
    findings = [
        _p011_finding(page=11, side="right_margin"),
        _p011_finding(page=11, side="bottom_margin"),
    ]
    payload = _payload(findings)
    view = build_report_view(payload)
    output_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert len([f for f in view.findings if f.rule_id == "P011"]) == 1
    assert "Page 11 — bottom and right margins" in text


def test_p011_page_location_label_formats_three_sides() -> None:
    label = p011_page_location_label(7, ("left_margin", "right_margin", "bottom_margin"))
    assert label == "Page 7 — bottom, left, and right margins"
