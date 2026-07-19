"""Tests for non-P020 page-number warning distinctness and location labels."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.page_number_student_preview import (
    classify_visible_page_number_issue,
    consume_page_number_display_slot,
    page_number_display_dedup_key,
    page_number_location_label,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view


def _payload(findings: list[AuditFinding]) -> dict:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def _p029_finding(
    *,
    page: int = 7,
    observed: str = "vii",
    expected: str = "viii",
    issue_type: str = "roman_sequence_gap",
    bbox: str = "500.0,720.0,520.0,735.0",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P029",
        severity=Severity.WARNING,
        page=page,
        message="Roman sequence issue.",
        details={
            "issue_type": issue_type,
            "observed_sequence": observed,
            "expected_sequence": expected,
            "document_page_label": observed,
            "document_page_label_confidence": "medium",
            "page_region": "front_matter",
            "bbox": bbox,
        },
    )


def _p037_finding(
    *,
    page: int = 11,
    observed: str = "vi",
    expected: str = "iv",
    section_key: str = "biographical_sketch",
) -> AuditFinding:
    return AuditFinding(
        rule_id="P037",
        severity=Severity.WARNING,
        page=page,
        message="Section Roman numeral issue.",
        details={
            "issue_type": "roman_bio_sketch_not_iv",
            "section_key": section_key,
            "observed_sequence": observed,
            "expected_sequence": expected,
            "document_page_label": observed,
            "document_page_label_confidence": "medium",
        },
    )


def test_p029_location_label_names_printed_and_expected_values() -> None:
    label = page_number_location_label(
        "P029",
        "wrong_page_number_sequence",
        {
            "observed_sequence": "vii",
            "expected_sequence": "viii",
            "document_page_label": "vii",
            "document_page_label_confidence": "medium",
        },
        7,
    )
    assert label == (
        'Document page: vii · PDF page: 7 — printed page number "vii" '
        '(expected "viii")'
    )


def test_p037_location_label_names_section_and_values() -> None:
    label = page_number_location_label(
        "P037",
        "wrong_page_number_sequence",
        {
            "section_key": "biographical_sketch",
            "observed_sequence": "vi",
            "expected_sequence": "iv",
            "document_page_label": "vi",
            "document_page_label_confidence": "medium",
        },
        11,
    )
    assert label == (
        'Document page: vi · PDF page: 11 — Biographical Sketch, '
        'printed page number "vi" (expected "iv")'
    )


def test_missing_page_number_location_falls_back_to_physical_pdf_page() -> None:
    label = page_number_location_label(
        "P019",
        "missing_page_number",
        {"issue_type": "missing_page_number"},
        9,
    )
    assert label == "PDF page 9 — no printed page number detected"


def test_document_level_p019_style_warning_has_document_wide_location() -> None:
    label = page_number_location_label(
        "P019",
        "wrong_page_numbering_style",
        {"observed_style": "Arabic and Roman numerals"},
        None,
    )
    assert label.startswith("Document-wide")
    assert "Arabic and Roman numerals" in label


def test_distinct_p029_same_page_different_observed_values_have_distinct_locations() -> None:
    findings = [
        _p029_finding(page=7, observed="vii", expected="viii", bbox="500.0,720.0,520.0,735.0"),
        _p029_finding(page=7, observed="viii", expected="ix", bbox="500.0,700.0,520.0,715.0"),
    ]
    view = build_report_view(_payload(findings))
    cards = [f for f in view.findings if f.rule_id == "P029"]
    assert len(cards) == 2
    locations = {card.location_label for card in cards}
    assert len(locations) == 2
    assert all('printed page number "' in loc for loc in locations)
    assert all("PDF page: 7" in loc for loc in locations)


def test_exact_duplicate_p029_findings_produce_one_visible_card() -> None:
    duplicate = _p029_finding()
    view = build_report_view(_payload([duplicate, duplicate]))
    cards = [f for f in view.findings if f.rule_id == "P029"]
    assert len(cards) == 1


def test_p029_and_p037_on_same_page_remain_distinct_with_clear_locations() -> None:
    findings = [_p029_finding(page=11, observed="vi", expected="v"), _p037_finding(page=11)]
    view = build_report_view(_payload(findings))
    cards = {f.rule_id: f for f in view.findings if f.rule_id in {"P029", "P037"}}
    assert set(cards) == {"P029", "P037"}
    assert "front-matter sequence" in cards["P029"].polished_comment
    assert "NJIT front-matter template" in cards["P037"].polished_comment
    assert "Biographical Sketch" in cards["P037"].location_label
    assert cards["P029"].location_label != cards["P037"].location_label


def test_page_number_dedup_key_uses_rounded_bbox() -> None:
    details = {
        "issue_type": "roman_sequence_gap",
        "observed_sequence": "vii",
        "expected_sequence": "viii",
        "bbox": "500.04,720.02,520.01,735.08",
    }
    key_a = page_number_display_dedup_key(
        "P029", "wrong_page_number_sequence", details, page=7
    )
    details["bbox"] = "500.01,720.01,520.01,735.06"
    key_b = page_number_display_dedup_key(
        "P029", "wrong_page_number_sequence", details, page=7
    )
    assert key_a == key_b

    details["bbox"] = "500.0,700.0,520.0,715.0"
    key_other = page_number_display_dedup_key(
        "P029", "wrong_page_number_sequence", details, page=7
    )
    assert key_a != key_other


def test_consume_page_number_display_slot_suppresses_second_exact_duplicate() -> None:
    seen: set[tuple] = set()
    details = {
        "issue_type": "roman_sequence_gap",
        "observed_sequence": "vii",
        "expected_sequence": "viii",
        "bbox": "500.0,720.0,520.0,735.0",
    }
    assert (
        consume_page_number_display_slot(
            "P029",
            "wrong_page_number_sequence",
            details,
            seen,
            page=7,
        )
        is True
    )
    assert (
        consume_page_number_display_slot(
            "P029",
            "wrong_page_number_sequence",
            details,
            seen,
            page=7,
        )
        is False
    )


def test_markdown_report_suppresses_exact_duplicate_p029_problems(tmp_path: Path) -> None:
    duplicate = _p029_finding()
    output_path = tmp_path / "report.md"
    write_markdown_report([duplicate, duplicate], {"audit_type": "pdf"}, output_path)
    text = output_path.read_text(encoding="utf-8")
    assert text.count("### Problem") == 1


def test_page_number_student_facing_text_has_no_raw_coordinates() -> None:
    view = build_report_view(_payload([_p029_finding()]))
    card = next(f for f in view.findings if f.rule_id == "P029")
    assert "500.0" not in card.polished_comment
    assert "500.0" not in card.location_label
    assert "720.0" not in card.detailed_explanation


def test_page_number_warning_card_badge_uses_document_label_without_changing_page() -> None:
    view = build_report_view(_payload([_p029_finding(page=7, observed="viii", expected="ix")]))
    card = next(f for f in view.findings if f.rule_id == "P029")
    assert card.page == 7
    assert card.page_display_label == "Page viii (PDF page 7)"
    assert card.page_action_suffix == "viii (PDF page 7)"


def test_json_export_keeps_page_and_adds_page_label_metadata() -> None:
    payload = _payload([_p029_finding(page=7, observed="viii", expected="ix")])
    finding = next(f for f in payload["findings"] if f["rule_id"] == "P029")
    assert finding["page"] == 7
    assert finding["pdf_page"] == 7
    assert finding["document_page_label"] == "viii"


def test_markdown_location_uses_document_label_and_pdf_page(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    write_markdown_report(
        [_p029_finding(page=7, observed="viii", expected="ix")],
        {"audit_type": "pdf"},
        output_path,
    )
    text = output_path.read_text(encoding="utf-8")
    assert "Document page: viii · PDF page: 7" in text


def test_classify_visible_page_number_issue_hides_routine_p013_candidate() -> None:
    visible_issue_type, is_visible = classify_visible_page_number_issue(
        "P013",
        "page_number_candidate",
        {"position_type": "bottom_center", "candidate_count_on_page": "1"},
    )
    assert visible_issue_type is None
    assert is_visible is False
