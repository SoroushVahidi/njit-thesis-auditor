"""Synthetic tests for P068 — Approval Page committee block structural check.

All PDFs use clearly fake placeholder text only. No real committee names,
advisor names, signatures, or dissertation content appear in findings.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfDocument, PdfPage
from njit_auditor.rules.pdf_approval_page_committee_blocks import (
    check_pdf_approval_page_committee_blocks,
)

_PAGE_W = 612.0
_PAGE_H = 792.0
_MARGIN_L = 108.0
_CENTER_X = _PAGE_W / 2

_PLACEHOLDER_MEMBER = "Placeholder Member Synthetic"
_PLACEHOLDER_ADVISOR = "Placeholder Advisor Synthetic"


def _save_and_load(doc: fitz.Document) -> PdfDocument:
    path = Path("/tmp") / f"p068_test_{id(doc)}.pdf"
    doc.save(path)
    doc.close()
    loaded = load_pdf_layout(str(path))
    path.unlink(missing_ok=True)
    return loaded


def _make_approval_doc(
    *,
    include_heading: bool = True,
    body_lines: list[str] | None = None,
    second_heading_page: bool = False,
) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    y = 100.0
    if include_heading:
        page.insert_text((_CENTER_X - 55, y), "APPROVAL PAGE", fontsize=14)
        y += 40.0
    if body_lines:
        for line in body_lines:
            page.insert_text((_MARGIN_L, y), line, fontsize=11)
            y += 24.0
    if second_heading_page:
        page2 = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        page2.insert_text((_CENTER_X - 55, 100.0), "APPROVAL PAGE", fontsize=14)
    return doc


def _complete_approval_lines() -> list[str]:
    return [
        "Dissertation Advisor",
        f"{_PLACEHOLDER_ADVISOR}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]


def _issue_types(findings: list) -> set[str]:
    return {finding.details.get("issue_type", "") for finding in findings}


def test_no_approval_page_no_findings() -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_MARGIN_L, 100.0), "ABSTRACT", fontsize=14)
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_complete_approval_page_no_findings() -> None:
    doc = _make_approval_doc(body_lines=_complete_approval_lines())
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_missing_advisor_role_label_emits_finding() -> None:
    lines = [
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert _issue_types(findings) == {"approval_page_advisor_role_label_missing"}
    assert findings[0].rule_id == "P068"


def test_sparse_signature_blocks_emits_finding() -> None:
    lines = [
        "Dissertation Advisor",
        f"{_PLACEHOLDER_ADVISOR}",
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Placeholder Member Three Synthetic",
        "Placeholder Member Four Synthetic",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert "approval_page_signature_blocks_sparse" in _issue_types(findings)


def test_below_gates_no_findings() -> None:
    lines = [
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_multiple_approval_headings_skipped() -> None:
    doc = _make_approval_doc(
        body_lines=_complete_approval_lines(),
        second_heading_page=True,
    )
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_image_only_page_skipped() -> None:
    pdf_doc = PdfDocument(
        path="synthetic_image_only.pdf",
        pages=[
            PdfPage(
                page_number=1,
                width=_PAGE_W,
                height=_PAGE_H,
                text_blocks=[],
            )
        ],
    )
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_underscore_blanks_count_as_indicators() -> None:
    lines = [
        "Dissertation Advisor",
        f"{_PLACEHOLDER_ADVISOR}",
        "____________________",
        "Date: ____________________",
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "____________________",
        "Date: ____________________",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_thesis_advisor_label_no_finding() -> None:
    lines = [
        "Thesis Advisor",
        f"{_PLACEHOLDER_ADVISOR}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert "approval_page_advisor_role_label_missing" not in _issue_types(findings)


def test_thesis_advisor_on_name_line_no_finding() -> None:
    lines = [
        "Dr. Placeholder Advisor Synthetic, Thesis Advisor",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert "approval_page_advisor_role_label_missing" not in _issue_types(findings)


def test_major_professor_counts_as_advisor_label() -> None:
    lines = [
        "Major Professor",
        f"{_PLACEHOLDER_ADVISOR}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert "approval_page_advisor_role_label_missing" not in _issue_types(findings)


def test_committee_word_in_body_prose_not_selected() -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_MARGIN_L, 100.0), "CHAPTER 1", fontsize=14)
    page.insert_text(
        (_MARGIN_L, 140.0),
        "This chapter discusses committee selection in general terms only.",
        fontsize=11,
    )
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_privacy_no_names_in_finding_details() -> None:
    lines = [
        "Committee Member",
        f"{_PLACEHOLDER_MEMBER}",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Committee Member",
        "Placeholder Member Three Synthetic",
        "Committee Member",
        "Placeholder Member Four Synthetic",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert findings
    serialized = " ".join(str(value) for finding in findings for value in finding.details.values())
    assert _PLACEHOLDER_MEMBER not in serialized
    assert _PLACEHOLDER_ADVISOR not in serialized
    assert "Placeholder" not in serialized
    assert "Synthetic" not in serialized


def test_zero_role_labels_below_gate_no_findings() -> None:
    lines = [
        "Placeholder line one synthetic",
        "Placeholder line two synthetic",
        "Placeholder line three synthetic",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


def test_manual_only_semantics_not_emitted() -> None:
    lines = [
        "Dr. Placeholder Advisor Synthetic",
        "Dissertation Advisor",
        "Committee Member",
        "Placeholder Member Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    doc = _make_approval_doc(body_lines=lines)
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    for finding in findings:
        assert finding.details.get("issue_type") in {
            "approval_page_advisor_role_label_missing",
            "approval_page_signature_blocks_sparse",
        }
        assert "honorific" not in finding.message.lower()
        assert "rank" not in finding.message.lower()
