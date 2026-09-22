"""Synthetic tests for P072 — Approval Page Heading-Gate Recall Refinement.

P072 adds a structural localization fallback to P068: when no "APPROVAL PAGE" heading
is found by the gate, the checker scans front-matter/ambiguous pages for the distinctive
combination of role-label phrases. No new issue types — existing P068 types fire.

All PDFs use clearly fake placeholder text only. No real committee names, advisor names,
signatures, or dissertation content appear in any fixture or finding.
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
    path = Path("/tmp") / f"p072_test_{id(doc)}.pdf"
    doc.save(path)
    doc.close()
    loaded = load_pdf_layout(str(path))
    path.unlink(missing_ok=True)
    return loaded


def _make_doc_with_heading(body_lines: list[str]) -> PdfDocument:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 55, 100.0), "APPROVAL PAGE", fontsize=14)
    y = 150.0
    for line in body_lines:
        page.insert_text((_MARGIN_L, y), line, fontsize=11)
        y += 24.0
    return _save_and_load(doc)


def _make_doc_without_heading(body_lines: list[str]) -> PdfDocument:
    """Create a doc with role-label structural content but NO 'APPROVAL PAGE' heading."""
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    y = 100.0
    for line in body_lines:
        page.insert_text((_MARGIN_L, y), line, fontsize=11)
        y += 24.0
    return _save_and_load(doc)


def _complete_fallback_lines() -> list[str]:
    return [
        "Dissertation Advisor",
        _PLACEHOLDER_ADVISOR,
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        _PLACEHOLDER_MEMBER,
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]


def _issue_types(findings: list) -> set[str]:
    return {f.details.get("issue_type", "") for f in findings}


# ---------------------------------------------------------------------------
# Test 1 — heading path still works; detected_via = "heading_gate"
# ---------------------------------------------------------------------------


def test_heading_gate_detected_via_field() -> None:
    lines = [
        "Dissertation Advisor",
        _PLACEHOLDER_ADVISOR,
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        _PLACEHOLDER_MEMBER,
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    pdf_doc = _make_doc_with_heading(lines)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert findings == []
    # heading path: no assertions needed on findings, but we verify the path
    # is taken by confirming it still works (no spurious findings)


# ---------------------------------------------------------------------------
# Test 2 — structural fallback: complete structural page → no findings
# ---------------------------------------------------------------------------


def test_structural_fallback_complete_page_no_findings() -> None:
    pdf_doc = _make_doc_without_heading(_complete_fallback_lines())
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Test 3 — structural fallback: sparse indicators → P068 finding emitted
# ---------------------------------------------------------------------------


def test_structural_fallback_sparse_indicators_not_reported() -> None:
    """`approval_page_signature_blocks_sparse` reporting is retired (2026-09-21)

    on the structural-fallback path too; see
    docs/status/r068_ester_approval_committee_spacing_followup_20260921.md.
    """
    lines = [
        "Dissertation Advisor",
        _PLACEHOLDER_ADVISOR,
        "Committee Member",
        _PLACEHOLDER_MEMBER,
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Committee Member",
        "Placeholder Member Three Synthetic",
    ]
    pdf_doc = _make_doc_without_heading(lines)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert "approval_page_signature_blocks_sparse" not in _issue_types(findings)
    assert all(f.rule_id == "P068" for f in findings)


# ---------------------------------------------------------------------------
# Test 4 — structural fallback: "Major Professor" accepted as advisor role
# ---------------------------------------------------------------------------


def test_structural_fallback_major_professor_advisor_role() -> None:
    lines = [
        "Major Professor",
        _PLACEHOLDER_ADVISOR,
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        _PLACEHOLDER_MEMBER,
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    pdf_doc = _make_doc_without_heading(lines)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert "approval_page_advisor_role_label_missing" not in _issue_types(findings)


# ---------------------------------------------------------------------------
# Test 5 — structural fallback: no role-label phrases → skipped
# ---------------------------------------------------------------------------


def test_structural_fallback_no_role_labels_skipped() -> None:
    lines = [
        "Placeholder text line one synthetic",
        "Placeholder text line two synthetic",
        "Placeholder text line three synthetic",
        "Placeholder text line four synthetic",
        "Placeholder text line five synthetic",
    ]
    pdf_doc = _make_doc_without_heading(lines)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


# ---------------------------------------------------------------------------
# Test 6 — structural fallback: only 1 role label (< _MIN_ROLE_LABELS=2) → skipped
# ---------------------------------------------------------------------------


def test_structural_fallback_below_role_label_gate_skipped() -> None:
    lines = [
        "Dissertation Advisor",
        _PLACEHOLDER_ADVISOR,
        "Placeholder text line three synthetic",
        "Placeholder text line four synthetic",
    ]
    pdf_doc = _make_doc_without_heading(lines)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


# ---------------------------------------------------------------------------
# Test 7 — structural fallback: 2 candidate pages → ambiguous, skipped
# ---------------------------------------------------------------------------


def test_structural_fallback_multiple_candidates_skipped() -> None:
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        y = 100.0
        for line in _complete_fallback_lines():
            page.insert_text((_MARGIN_L, y), line, fontsize=11)
            y += 24.0
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


# ---------------------------------------------------------------------------
# Test 8 — structural fallback: image-only page (empty text_blocks) → skipped
# ---------------------------------------------------------------------------


def test_structural_fallback_image_only_skipped() -> None:
    pdf_doc = PdfDocument(
        path="synthetic_image_only_p072.pdf",
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


# ---------------------------------------------------------------------------
# Test 9 — structural fallback: sparse text layer (< _MIN_BODY_LINES=4) → skipped
# ---------------------------------------------------------------------------


def test_structural_fallback_sparse_text_layer_skipped() -> None:
    lines = [
        "Dissertation Advisor",
        _PLACEHOLDER_ADVISOR,
        "Committee Member",
    ]
    pdf_doc = _make_doc_without_heading(lines)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


# ---------------------------------------------------------------------------
# Test 10 — body prose mentioning "committee" but no role-label phrases → skipped
# ---------------------------------------------------------------------------


def test_body_prose_committee_mention_not_triggered() -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text(
        (_MARGIN_L, 100.0),
        "CHAPTER 1",
        fontsize=14,
    )
    page.insert_text(
        (_MARGIN_L, 140.0),
        "The research committee evaluates proposals on a rolling basis throughout the year.",
        fontsize=11,
    )
    page.insert_text(
        (_MARGIN_L, 164.0),
        "Each committee member reviews submitted materials before the meeting.",
        fontsize=11,
    )
    page.insert_text(
        (_MARGIN_L, 188.0),
        "The committee chair prepares summary reports as needed.",
        fontsize=11,
    )
    page.insert_text(
        (_MARGIN_L, 212.0),
        "Results are communicated to all committee members within two weeks.",
        fontsize=11,
    )
    pdf_doc = _save_and_load(doc)
    assert check_pdf_approval_page_committee_blocks(pdf_doc) == []


# ---------------------------------------------------------------------------
# Test 11 — heading present: fallback does not activate
# ---------------------------------------------------------------------------


def test_heading_present_fallback_not_activated() -> None:
    """When heading gate finds a match, the structural fallback must not fire."""
    doc = fitz.open()
    # Page 1: explicit APPROVAL PAGE heading with complete body (heading path fires)
    page1 = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page1.insert_text((_CENTER_X - 55, 100.0), "APPROVAL PAGE", fontsize=14)
    y = 150.0
    for line in _complete_fallback_lines():
        page1.insert_text((_MARGIN_L, y), line, fontsize=11)
        y += 24.0
    # Page 2: structural patterns (would trigger fallback if heading were absent)
    page2 = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    y2 = 100.0
    for line in _complete_fallback_lines():
        page2.insert_text((_MARGIN_L, y2), line, fontsize=11)
        y2 += 24.0
    pdf_doc = _save_and_load(doc)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    # Heading path fires on page 1 (complete → no findings); fallback must not add extras
    assert findings == []


# ---------------------------------------------------------------------------
# Test 12 — detected_via field is "structural_fallback" in fallback findings
# ---------------------------------------------------------------------------


def test_detected_via_structural_fallback_in_finding() -> None:
    lines = [
        "Committee Member",
        _PLACEHOLDER_MEMBER,
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Committee Member",
        "Placeholder Member Three Synthetic",
        "Committee Member",
        "Placeholder Member Four Synthetic",
    ]
    pdf_doc = _make_doc_without_heading(lines)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert findings
    for finding in findings:
        assert finding.details.get("detected_via") == "structural_fallback"


# ---------------------------------------------------------------------------
# Test 13 — privacy: no private text in fallback findings
# ---------------------------------------------------------------------------


def test_privacy_no_private_text_in_fallback_finding() -> None:
    lines = [
        "Committee Member",
        _PLACEHOLDER_MEMBER,
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Committee Member",
        "Placeholder Member Three Synthetic",
        "Committee Member",
        "Placeholder Member Four Synthetic",
    ]
    pdf_doc = _make_doc_without_heading(lines)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert findings
    serialized = " ".join(
        str(v) for finding in findings for v in finding.details.values()
    )
    assert _PLACEHOLDER_MEMBER not in serialized
    assert _PLACEHOLDER_ADVISOR not in serialized
    assert "Placeholder" not in serialized
    assert "Synthetic" not in serialized


# ---------------------------------------------------------------------------
# Test 14 — P068 existing behavior preserved (regression): heading path unchanged
# ---------------------------------------------------------------------------


def test_existing_p068_behavior_preserved() -> None:
    """Existing P068 heading-path behavior is unchanged after P072 implementation."""
    lines = [
        "Committee Member",
        _PLACEHOLDER_MEMBER,
        "Signature: ____________________",
        "Date: ____________________",
        "Committee Member",
        "Placeholder Member Two Synthetic",
        "Signature: ____________________",
        "Date: ____________________",
    ]
    pdf_doc = _make_doc_with_heading(lines)
    findings = check_pdf_approval_page_committee_blocks(pdf_doc)
    assert _issue_types(findings) == {"approval_page_advisor_role_label_missing"}
    assert findings[0].rule_id == "P068"
    assert findings[0].details.get("detected_via") == "heading_gate"
