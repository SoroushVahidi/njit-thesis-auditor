"""Regression tests for P013/P019/P037 page-numbering false positives."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    detect_page_number_candidates,
    is_plausible_page_number_candidate,
    run_pdf_page_number_candidates_rule,
)
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence


def _make_body_page_with_protocol_id_and_footer(
    path: Path,
    *,
    footer_page_number: str = "27",
    body_tokens: list[tuple[float, float, str]] | None = None,
    footer_tokens: list[tuple[float, float, str]] | None = None,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 200), "3.4 Methods Overview", fontsize=12)
    page.insert_text((108, 230), "Protocol ID: 2503052525", fontsize=12)
    for x, y, text in body_tokens or []:
        page.insert_text((x, y), text, fontsize=12)
    for x, y, text in footer_tokens or []:
        page.insert_text((x, y), text, fontsize=12)
    page.insert_text((300, 770), footer_page_number, fontsize=12)
    doc.save(path)
    doc.close()


def test_protocol_id_with_footer_page_number_no_p013_duplicate(tmp_path: Path) -> None:
    pdf_path = tmp_path / "protocol_id_page.pdf"
    _make_body_page_with_protocol_id_and_footer(
        pdf_path,
        footer_tokens=[(108, 760, "2503052525.")],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    page_findings = [
        f
        for f in findings
        if f.rule_id == "P013" and f.page == 1
    ]
    assert len(page_findings) <= 1
    if page_findings:
        assert page_findings[0].details.get("plausible_candidate_count", "1") == "1"
        assert "2503052525" not in page_findings[0].details.get("candidate_sample", "")


def test_protocol_id_with_footer_page_number_no_p019_duplicate(tmp_path: Path) -> None:
    pdf_path = tmp_path / "protocol_id_page_p019.pdf"
    _make_body_page_with_protocol_id_and_footer(
        pdf_path,
        footer_tokens=[(108, 760, "2503052525.")],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert not [
        f
        for f in findings
        if f.details.get("issue_type") == "multiple_page_numbers"
    ]


def test_long_numeric_id_in_margin_not_plausible() -> None:
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
    assert is_plausible_page_number_candidate(candidate) is False


def test_two_plausible_footer_page_numbers_still_warn_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "duplicate_footer.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((300, 770), "27", fontsize=12)
    page.insert_text((560, 770), "27", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    duplicate = [
        f for f in findings if f.details.get("issue_type") == "multiple_page_numbers"
    ]
    assert duplicate


def test_roman_front_matter_and_arabic_body_no_document_wide_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "roman_arabic_regime.pdf"
    doc = fitz.open()
    for roman in ["iv", "v", "vi"]:
        page = doc.new_page(width=612, height=792)
        page.insert_text((180, 90), "ACKNOWLEDGEMENTS", fontsize=14)
        page.insert_text((300, 760), roman, fontsize=12)
    body = doc.new_page(width=612, height=792)
    body.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    body.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert not [
        f
        for f in findings
        if f.details.get("issue_type") == "mixed_numbering_style" and f.page is None
    ]


def test_arabic_on_front_matter_page_warns_p028(tmp_path: Path) -> None:
    pdf_path = tmp_path / "arabic_front_matter.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((180, 90), "ACKNOWLEDGEMENTS", fontsize=14)
    page.insert_text((300, 760), "6", fontsize=12)
    body = doc.new_page(width=612, height=792)
    body.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    body.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_numbering_regime(model)
    assert any(f.rule_id == "P028" for f in findings)


def test_roman_on_body_page_warns_p028(tmp_path: Path) -> None:
    pdf_path = tmp_path / "roman_body.pdf"
    doc = fitz.open()
    front = doc.new_page(width=612, height=792)
    front.insert_text((180, 90), "ACKNOWLEDGEMENTS", fontsize=14)
    front.insert_text((300, 760), "vi", fontsize=12)
    body = doc.new_page(width=612, height=792)
    body.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    body.insert_text((300, 760), "iv", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_numbering_regime(model)
    assert any(
        f.rule_id == "P028"
        and f.details.get("issue_type") == "roman_number_on_body_page"
        for f in findings
    )


def test_p037_does_not_force_list_of_tables_viii(tmp_path: Path) -> None:
    pdf_path = tmp_path / "lot_ix_ok.pdf"
    doc = fitz.open()
    pages = [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("TABLE OF CONTENTS", None, "vii"),
        ("TABLE OF CONTENTS", None, "viii"),
        ("LIST OF TABLES", None, "ix"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ]
    for heading, chapter, page_num in pages:
        page = doc.new_page(width=612, height=792)
        if heading:
            page.insert_text((180, 90), heading, fontsize=14, fontname="Times-Bold")
        if chapter:
            page.insert_text((108, 200), chapter, fontsize=14)
        if page_num:
            page.insert_text((300, 760), page_num, fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    p037 = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert not p037


def test_p029_still_flags_skipped_roman_numeral(tmp_path: Path) -> None:
    pdf_path = tmp_path / "roman_gap.pdf"
    doc = fitz.open()
    for roman in ["iv", "vi"]:
        page = doc.new_page(width=612, height=792)
        page.insert_text((180, 90), "ACKNOWLEDGEMENTS", fontsize=14)
        page.insert_text((300, 760), roman, fontsize=12)
    body = doc.new_page(width=612, height=792)
    body.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    body.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    assert any(f.details.get("issue_type") == "roman_sequence_gap" for f in findings)


def test_p013_ui_does_not_show_protocol_id_as_duplicate() -> None:
    from njit_auditor.models import AuditFinding, Severity

    finding = AuditFinding(
        rule_id="P013",
        severity=Severity.WARNING,
        page=42,
        message="Page number candidate.",
        details={
            "issue_type": "page_number_candidate",
            "position_type": "bottom_center",
            "candidate_count_on_page": "1",
            "plausible_candidate_count": "1",
            "candidate_sample": "27",
        },
    )
    payload = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(payload)
    duplicate = [
        f
        for f in view.findings
        if f.rule_id == "P013"
        and f.issue_type == "duplicate_or_ambiguous_page_number"
    ]
    assert not duplicate


def test_body_text_decimal_not_detected_as_page_number_candidate(tmp_path: Path) -> None:
    pdf_path = tmp_path / "decimal_body.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 400), "3.4", fontsize=12)
    page.insert_text((300, 770), "27", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    candidates = detect_page_number_candidates(model)
    texts = {c.text for c in candidates if c.page_number == 1}
    assert "3.4" not in texts
