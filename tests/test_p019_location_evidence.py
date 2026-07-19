"""Regression tests for P019 page-numbering location evidence.

Covers two real detector bugs found by tracing pdf_page_numbers.py:
  1. the per-page "mixed_numbering_style" finding never attached a bbox,
     even though the plausible-candidate list with bboxes was already in
     scope (fixed: attaches the highest-ranked candidate's bbox).
  2. the Roman-numeral sequence_gap branch was missing the bbox-attachment
     step present in the near-identical Arabic branch just above it (a
     code-duplication drift bug).

Also covers two presentation-layer improvements:
  3. sequence_gap details now carry previous_sequence_page/next_sequence_page
     (not just values), so wording can name the exact neighboring pages.
  4. the document-wide mixed_numbering_style finding now carries
     transition_pages when the exact style-transition point is identifiable,
     and the wording layer uses it instead of fully generic text.

All fixtures are synthetic, generic page-numbering documents -- no real
dissertation content, titles, authors, or sample-specific values.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
)

_PAGE_W = 612.0
_PAGE_H = 792.0
_BOTTOM_CENTER_X = 296.0
_BOTTOM_Y = 765.0


def _new_doc() -> fitz.Document:
    return fitz.open()


def _add_bottom_center_number(page: fitz.Page, text: str, *, fontsize: float = 12.0) -> None:
    page.insert_text((_BOTTOM_CENTER_X, _BOTTOM_Y), text, fontsize=fontsize)


def _add_second_bottom_token(page: fitz.Page, text: str, *, x: float = 535.0) -> None:
    """A second margin-zone token in the bottom-right zone, so both this and
    the bottom-center token land in the plausible-candidate set as distinct
    tokens on the same page (an x near the left margin classifies as
    position_type "other" and gets filtered out by the plausibility gate,
    which is not what these fixtures are testing)."""
    page.insert_text((x, _BOTTOM_Y), text, fontsize=12.0)


def _save(doc: fitz.Document, path: Path) -> Path:
    doc.save(path)
    doc.close()
    return path


def _run(path: Path) -> list:
    model = load_pdf_layout(str(path))
    return check_pdf_page_number_sequence(model)


def _findings_of(findings: list, issue_type: str) -> list:
    return [f for f in findings if f.details.get("issue_type") == issue_type]


# ---------------------------------------------------------------------------
# Bug 1: per-page mixed_numbering_style must carry a bbox
# ---------------------------------------------------------------------------


def test_page_mixed_style_finding_carries_bbox_of_a_real_candidate(tmp_path: Path) -> None:
    doc = _new_doc()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    _add_bottom_center_number(page, "5")
    _add_second_bottom_token(page, "v")
    pdf_path = _save(doc, tmp_path / "mixed_style_one_page.pdf")

    findings = _run(pdf_path)
    mixed = _findings_of(findings, "mixed_numbering_style")
    page_level = [f for f in mixed if f.page == 1]
    assert page_level, "expected a per-page mixed_numbering_style finding"
    assert "bbox" in page_level[0].details
    assert page_level[0].details["bbox"]


def test_page_mixed_style_bbox_is_a_real_four_number_box(tmp_path: Path) -> None:
    doc = _new_doc()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    _add_bottom_center_number(page, "5")
    _add_second_bottom_token(page, "v")
    pdf_path = _save(doc, tmp_path / "mixed_style_bbox_shape.pdf")

    findings = _run(pdf_path)
    page_level = [f for f in _findings_of(findings, "mixed_numbering_style") if f.page == 1]
    bbox_str = page_level[0].details["bbox"]
    parts = [p.strip() for p in bbox_str.split(",")]
    assert len(parts) == 4
    for part in parts:
        float(part)  # must parse as a real coordinate, not a placeholder


# ---------------------------------------------------------------------------
# Bug 2: Roman-numeral sequence_gap must carry a bbox, same as Arabic
# ---------------------------------------------------------------------------


def _build_roman_sequence_with_gap(tmp_path: Path, *, values: list[str]) -> Path:
    doc = _new_doc()
    for value in values:
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        _add_bottom_center_number(page, value)
    return _save(doc, tmp_path / "roman_sequence_gap.pdf")


def _build_arabic_sequence_with_gap(tmp_path: Path, *, values: list[str]) -> Path:
    doc = _new_doc()
    for value in values:
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        _add_bottom_center_number(page, value)
    return _save(doc, tmp_path / "arabic_sequence_gap.pdf")


def test_roman_sequence_gap_carries_bbox(tmp_path: Path) -> None:
    pdf_path = _build_roman_sequence_with_gap(tmp_path, values=["i", "ii", "iv"])
    findings = _run(pdf_path)
    gaps = _findings_of(findings, "sequence_gap")
    roman_gaps = [
        f for f in gaps if "style=roman_lower" in f.details.get("expected_or_context", "")
    ]
    assert roman_gaps, "expected a Roman sequence_gap finding"
    assert "bbox" in roman_gaps[0].details
    assert roman_gaps[0].details["bbox"]


def test_roman_sequence_gap_preserves_printed_roman_token_in_p019(tmp_path: Path) -> None:
    pdf_path = _build_roman_sequence_with_gap(tmp_path, values=["vii", "viii", "viii"])
    findings = _run(pdf_path)
    roman_gap = next(
        f
        for f in _findings_of(findings, "sequence_gap")
        if "style=roman_lower" in f.details.get("expected_or_context", "")
    )
    assert roman_gap.details["observed_sequence"] == "viii"
    assert roman_gap.details["expected_sequence"] == "ix"
    assert roman_gap.details["observed_value"] == "8"
    assert roman_gap.details["expected_value"] == "9"
    assert roman_gap.details["document_page_label"] == "viii"


def test_roman_sequence_gap_highlight_targets_footer_not_body_text(tmp_path: Path) -> None:
    doc = _new_doc()
    for token in ("vii", "viii", "viii"):
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        page.insert_text((108, 300), "Musialski 8 viii", fontsize=12.0)
        _add_bottom_center_number(page, token)
    pdf_path = _save(doc, tmp_path / "roman_footer_not_body_text.pdf")

    findings = _run(pdf_path)
    roman_gap = next(
        f
        for f in _findings_of(findings, "sequence_gap")
        if "style=roman_lower" in f.details.get("expected_or_context", "")
    )
    y0 = float(roman_gap.details["bbox"].split(",")[1])
    assert y0 > 740.0


def test_arabic_sequence_gap_still_carries_bbox(tmp_path: Path) -> None:
    """Pre-existing behavior for Arabic must be unchanged by this fix."""
    pdf_path = _build_arabic_sequence_with_gap(tmp_path, values=["1", "2", "4"])
    findings = _run(pdf_path)
    gaps = _findings_of(findings, "sequence_gap")
    arabic_gaps = [f for f in gaps if "style=arabic" in f.details.get("expected_or_context", "")]
    assert arabic_gaps, "expected an Arabic sequence_gap finding"
    assert "bbox" in arabic_gaps[0].details
    assert arabic_gaps[0].details["bbox"]


# ---------------------------------------------------------------------------
# previous_sequence_page / next_sequence_page fields
# ---------------------------------------------------------------------------


def test_sequence_gap_details_include_neighbor_page_numbers(tmp_path: Path) -> None:
    pdf_path = _build_arabic_sequence_with_gap(tmp_path, values=["1", "2", "4"])
    findings = _run(pdf_path)
    gaps = _findings_of(findings, "sequence_gap")
    arabic_gaps = [f for f in gaps if "style=arabic" in f.details.get("expected_or_context", "")]
    details = arabic_gaps[0].details
    assert details["previous_sequence_page"] == "2"
    assert details["previous_sequence_value"] == "2"
    assert details["next_sequence_page"] == ""  # no page after the gap in this 3-page fixture
    assert details["next_sequence_value"] == ""


def test_sequence_gap_details_include_next_page_when_present(tmp_path: Path) -> None:
    pdf_path = _build_arabic_sequence_with_gap(tmp_path, values=["1", "2", "4", "5"])
    findings = _run(pdf_path)
    gaps = _findings_of(findings, "sequence_gap")
    arabic_gaps = [f for f in gaps if "style=arabic" in f.details.get("expected_or_context", "")]
    details = arabic_gaps[0].details
    assert details["previous_sequence_page"] == "2"
    assert details["next_sequence_page"] == "4"
    assert details["next_sequence_value"] == "5"


# ---------------------------------------------------------------------------
# Document-wide mixed style: transition_pages evidence
# ---------------------------------------------------------------------------


def _build_style_transition_doc(
    tmp_path: Path, *, front_matter: list[str], body: list[str]
) -> Path:
    doc = _new_doc()
    for value in front_matter:
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        _add_bottom_center_number(page, value)
    for value in body:
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        _add_bottom_center_number(page, value)
    return _save(doc, tmp_path / "style_transition.pdf")


def test_document_wide_mixed_style_names_exact_transition_pages(tmp_path: Path) -> None:
    pdf_path = _build_style_transition_doc(
        tmp_path, front_matter=["i", "ii", "iii"], body=["1", "2", "3"]
    )
    findings = _run(pdf_path)
    doc_level = [f for f in _findings_of(findings, "mixed_numbering_style") if f.page is None]
    assert doc_level, "expected a document-wide mixed_numbering_style finding"
    transitions = doc_level[0].details.get("transition_pages", "")
    assert transitions, "expected an identifiable style transition"
    # page 3 (last roman) -> page 4 (first arabic)
    assert "3:roman_lower->4:arabic" in transitions


def test_document_wide_mixed_style_wording_names_transition_pages(tmp_path: Path) -> None:
    pdf_path = _build_style_transition_doc(
        tmp_path, front_matter=["i", "ii", "iii"], body=["1", "2", "3"]
    )
    findings = _run(pdf_path)
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    doc_level_views = [
        fv
        for fv in view.findings
        if fv.rule_id == "P019"
        and fv.page is None
        and fv.issue_type == "wrong_page_numbering_style"
    ]
    assert doc_level_views, "expected a visible document-wide wrong_page_numbering_style card"
    comment = doc_level_views[0].polished_comment
    assert "page 3" in comment
    assert "page 4" in comment
    assert "Verify the numbering-style boundary" not in comment


# ---------------------------------------------------------------------------
# Detector invariance: existing firing decisions must not change
# ---------------------------------------------------------------------------


def test_correct_uniform_roman_then_arabic_transition_produces_no_mixed_style_finding(
    tmp_path: Path,
) -> None:
    """A clean, single front-matter/body transition with no candidate-level
    style conflict on any individual page must not fire mixed_numbering_style
    per-page (only the whole-document check can ever fire here, and even
    that requires 2+ distinct styles among ALL plausible candidates, which
    a clean transition does produce by construction -- this asserts the
    page-level check specifically stays silent)."""
    doc = _new_doc()
    for value in ("i", "ii"):
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        _add_bottom_center_number(page, value)
    for value in ("1", "2"):
        page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
        _add_bottom_center_number(page, value)
    pdf_path = _save(doc, tmp_path / "clean_transition.pdf")

    findings = _run(pdf_path)
    page_level_mixed = [
        f for f in _findings_of(findings, "mixed_numbering_style") if f.page is not None
    ]
    assert page_level_mixed == []


def test_skipped_arabic_number_still_flagged_as_sequence_gap(tmp_path: Path) -> None:
    pdf_path = _build_arabic_sequence_with_gap(tmp_path, values=["1", "2", "4"])
    findings = _run(pdf_path)
    assert _findings_of(findings, "sequence_gap")


def test_skipped_roman_number_still_flagged_as_sequence_gap(tmp_path: Path) -> None:
    pdf_path = _build_roman_sequence_with_gap(tmp_path, values=["i", "ii", "iv"])
    findings = _run(pdf_path)
    assert _findings_of(findings, "sequence_gap")


def test_p019_suppresses_roman_frontmatter_sequence_when_p029_owns_it(
    tmp_path: Path,
) -> None:
    doc = _new_doc()
    p = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    p.insert_text((250, 90), "BIOGRAPHICAL SKETCH", fontsize=14)
    _add_bottom_center_number(p, "vii")
    p = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    p.insert_text((250, 90), "TABLE OF CONTENTS", fontsize=14)
    _add_bottom_center_number(p, "viii")
    p = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    p.insert_text((250, 90), "LIST OF TABLES", fontsize=14)
    _add_bottom_center_number(p, "viii")
    p = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    p.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    _add_bottom_center_number(p, "1")
    pdf_path = _save(doc, tmp_path / "frontmatter_roman_owned_by_p029.pdf")

    findings = _run(pdf_path)
    roman_p019 = [
        f
        for f in _findings_of(findings, "sequence_gap")
        if "style=roman_lower" in f.details.get("expected_or_context", "")
    ]
    assert roman_p019 == []


def test_duplicate_candidates_on_one_page_still_flagged_as_multiple_page_numbers(
    tmp_path: Path,
) -> None:
    doc = _new_doc()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    _add_bottom_center_number(page, "12")
    _add_second_bottom_token(page, "13")
    pdf_path = _save(doc, tmp_path / "duplicate_candidates.pdf")

    findings = _run(pdf_path)
    assert _findings_of(findings, "multiple_page_numbers")


def test_body_numeric_id_in_body_text_not_treated_as_page_number(tmp_path: Path) -> None:
    """A numeric ID placed in the body (not the top/bottom margin zone) must
    never become a page-number candidate at all -- confirms this fix did not
    loosen the existing margin-zone gate."""
    doc = _new_doc()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((108, 400), "Reference 42 discusses related work.", fontsize=12)
    _add_bottom_center_number(page, "1")
    pdf_path = _save(doc, tmp_path / "body_numeric_id.pdf")

    findings = _run(pdf_path)
    assert _findings_of(findings, "multiple_page_numbers") == []
    assert _findings_of(findings, "mixed_numbering_style") == []


def test_no_usable_page_number_text_produces_no_p019_findings(tmp_path: Path) -> None:
    doc = _new_doc()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((108, 400), "This page has no page-number-like tokens at all.", fontsize=12)
    pdf_path = _save(doc, tmp_path / "no_page_number_text.pdf")

    findings = _run(pdf_path)
    assert findings == []
