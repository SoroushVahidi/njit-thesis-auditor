"""Regression tests for web-audit batch 3: P019 page numbers and P014 headings."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    is_plausible_page_number_candidate,
)


def _make_pdf_with_body_noise_and_footer_page_number(
    path: Path,
    *,
    footer_page_number: str,
    extra_margin_tokens: list[tuple[float, float, str]] | None = None,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 200), "3.4 Methods Overview", fontsize=12)
    page.insert_text((108, 230), "3.5 Results Summary", fontsize=12)
    page.insert_text((108, 280), "2503052525", fontsize=12)
    if extra_margin_tokens:
        for x, y, text in extra_margin_tokens:
            page.insert_text((x, y), text, fontsize=12)
    page.insert_text((300, 770), footer_page_number, fontsize=12)
    doc.save(path)
    doc.close()


def test_is_plausible_page_number_candidate_rejects_long_ids_and_decimals() -> None:
    from njit_auditor.rules.pdf_page_numbers import PageNumberCandidate

    long_id = PageNumberCandidate(
        page_number=1,
        text="2503052525",
        location="bottom",
        line_number_like="1",
        number_style="arabic",
        position_type="bottom_center",
        value=2503052525,
    )
    assert is_plausible_page_number_candidate(long_id) is False

    decimal_like = PageNumberCandidate(
        page_number=1,
        text="3.4",
        location="bottom",
        line_number_like="1",
        number_style="other",
        position_type="bottom_center",
        value=None,
    )
    assert is_plausible_page_number_candidate(decimal_like) is False


def test_footer_page_number_with_body_noise_no_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "page_noise_single_footer.pdf"
    _make_pdf_with_body_noise_and_footer_page_number(
        pdf_path,
        footer_page_number="27",
        extra_margin_tokens=[(108, 760, "2503052525")],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    duplicate = [
        f for f in findings if f.details.get("issue_type") == "multiple_page_numbers"
    ]
    assert not duplicate


def test_protocol_id_in_margin_does_not_seed_absurd_sequence_expected_value(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "page_noise_sequence.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((108, 280), "2503052525", fontsize=12)
    page1.insert_text((108, 760), "2503052525", fontsize=12)
    page1.insert_text((300, 770), "27", fontsize=12)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((300, 770), "28", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    sequence = [f for f in findings if f.details.get("issue_type") == "sequence_gap"]
    assert not any(
        f.details.get("expected_sequence") == "2503052526" for f in sequence
    )
    assert not sequence


def test_multiple_plausible_footer_page_numbers_lists_candidate_tokens(tmp_path: Path) -> None:
    pdf_path = tmp_path / "duplicate_footer_tokens.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((300, 770), "27", fontsize=12)
    page.insert_text((560, 770), "27", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    duplicate = next(
        f for f in findings if f.details.get("issue_type") == "multiple_page_numbers"
    )
    tokens = duplicate.details.get("candidate_tokens", "")
    assert "bottom center: 27" in tokens
    assert "bottom right: 27" in tokens


def test_centered_biographical_sketch_passes_p014(tmp_path: Path) -> None:
    pdf_path = tmp_path / "biosketch_centered.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(
        fitz.Rect(108, 70, 540, 110),
        "BIOGRAPHICAL SKETCH",
        fontsize=16,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_named_frontmatter_headings(model)
    assert not any(f.rule_id == "P014" for f in findings)


def test_p014_student_facing_title_not_internal_checklist_question() -> None:
    finding = AuditFinding(
        rule_id="P014",
        severity=Severity.WARNING,
        page=9,
        message="Named heading formatting issue.",
        details={
            "heading": "BIOGRAPHICAL SKETCH",
            "centered": "False",
            "near_top": "True",
            "bold": "True",
            "all_caps": "True",
            "issue_type": "frontmatter_heading_not_centered",
            "centering_confidence": "medium",
            "confidence": "medium",
            "center_offset_pt": "32.4",
            "center_offset_direction": "left",
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P014")
    assert fv.issue_type_label == "Front-matter heading may not be centered"
    assert "follow expected layout/style checks" not in fv.issue_type_label.lower()
    assert "32.4 pt left" in fv.polished_comment or "pt left" in fv.polished_comment
    assert "BIOGRAPHICAL SKETCH" in fv.polished_comment


def test_p019_duplicate_warning_lists_candidate_positions_in_ui() -> None:
    finding = AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=42,
        message="Multiple plausible page-number candidates detected on one page.",
        details={
            "issue_type": "multiple_page_numbers",
            "candidate_tokens": "bottom center: 27; bottom right: 27",
            "candidate_sample": "27",
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P019")
    assert "bottom center: 27" in fv.polished_comment
    assert "bottom right: 27" in fv.polished_comment
    assert "bottom center: 27" in fv.location_label


def test_p019_sequence_warning_shows_neighbors_in_ui() -> None:
    finding = AuditFinding(
        rule_id="P019",
        severity=Severity.WARNING,
        page=43,
        message="Arabic page-number candidate sequence shows an obvious gap/break.",
        details={
            "issue_type": "sequence_gap",
            "observed_sequence": "28",
            "expected_sequence": "29",
            "previous_sequence_value": "27",
            "next_sequence_value": "30",
            "sequence_confidence": "medium",
            "bbox": "280,760,320,780",
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    fv = next(f for f in view.findings if f.rule_id == "P019")
    assert "'28'" in fv.polished_comment or "28" in fv.polished_comment
    assert "'29'" in fv.polished_comment or "29" in fv.polished_comment
    assert "previous detected page number: 27" in fv.polished_comment
    assert fv.has_highlight is True


def test_detect_page_number_candidates_still_finds_margin_tokens_for_p013() -> None:
    from njit_auditor.rules.pdf_page_numbers import PageNumberCandidate

    candidate = PageNumberCandidate(
        page_number=1,
        text="2503052525",
        location="bottom",
        line_number_like="1",
        number_style="arabic",
        position_type="bottom_center",
        value=2503052525,
    )
    assert candidate.text == "2503052525"
    assert is_plausible_page_number_candidate(candidate) is False
