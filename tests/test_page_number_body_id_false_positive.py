"""Regression tests: P013 must not treat long body-text numeric IDs (protocol
IDs, IRB numbers, etc.) as competing printed page numbers.

Live bug reproduced: a page with a real footer page number ("27") and a long
numeric ID (e.g. a protocol ID like "2503052525") landing in a margin zone
produced "Page has 2 page-number-like candidate(s)" and, at the presentation
layer, a "duplicate or ambiguous page number" warning naming the protocol ID
alongside the real page number -- confusing, since only one token is an
actual printed page number.

Root cause: `is_plausible_page_number_candidate()` / `_plausible_candidates()`
(added earlier for P019's sequence-gap logic, and already correctly rejecting
long numeric IDs via `LONG_NUMERIC_ID_RE` / `MAX_ARABIC_PAGE_NUMBER_DIGITS`)
were never wired into P013's own `run_pdf_page_number_candidates_rule()`,
which built its candidate count/sample/primary from the raw, unfiltered
per-page candidate list.

Fix (`rules/pdf_page_numbers.py`): `run_pdf_page_number_candidates_rule()`
now filters each page's candidates through the existing
`_plausible_candidates()` before counting/sampling/picking a primary, and
skips pages with no plausible candidate at all.

(A complementary change moving the margin-zone check in
`detect_page_number_candidates()` from block-level to line-level was
prototyped but not included here: against real Ester samples it also
surfaced a separate, pre-existing false-positive pattern -- a lone,
positionally-plausible header letter like "M." being misread as the Roman
numeral for 1000 -- which is out of scope for this narrow fix and would
have changed warning counts beyond the targeted case. Left as a documented
follow-up.)

No detector threshold, confidence policy, rule ID, or JSON export schema
changed -- this only prevents already-implausible tokens (per an existing,
already-tested classifier) from being counted as P013 candidates.
"""
from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_page_numbers import (
    PageNumberCandidate,
    check_pdf_page_number_sequence,
    is_plausible_page_number_candidate,
    run_pdf_page_number_candidates_rule,
)


def _page_finding(findings: list, page: int) -> object | None:
    matches = [
        f
        for f in findings
        if f.rule_id == "P013"
        and f.page == page
        and f.details.get("issue_type") == "page_number_candidate"
    ]
    assert len(matches) <= 1, "expected at most one P013 candidate finding per page"
    return matches[0] if matches else None


def test_protocol_id_in_margin_zone_not_counted_as_page_number_candidate(
    tmp_path: Path,
) -> None:
    """A long numeric ID that lands in a margin zone must not inflate the
    P013 candidate count or appear in the candidate sample alongside the
    real page number."""
    pdf_path = tmp_path / "protocol_id_footer.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 200), "Protocol ID: 2503052525", fontsize=12)
    page.insert_text(
        (108, 230),
        "3.4 Methods Overview describes the study design in detail.",
        fontsize=12,
    )
    page.insert_text((108, 760), "2503052525.", fontsize=10)
    page.insert_text((300, 770), "27", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    finding = _page_finding(findings, page=1)
    assert finding is not None
    assert finding.details["candidate_count_on_page"] == "1"
    assert finding.details["candidate_sample"] == "27"
    assert "2503052525" not in finding.details["candidate_sample"]


def test_protocol_id_and_footer_page_number_no_p013_duplicate_warning(
    tmp_path: Path,
) -> None:
    """End-to-end through the student-facing presentation layer: this page
    must not be classified as duplicate/ambiguous page numbering."""
    pdf_path = tmp_path / "protocol_id_footer_view.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 200), "Protocol ID: 2503052525", fontsize=12)
    page.insert_text((108, 760), "2503052525.", fontsize=10)
    page.insert_text((300, 770), "27", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    student_facing = [
        fv
        for fv in view.findings
        if fv.rule_id == "P013" and fv.page is not None
    ]
    assert not any(
        fv.issue_type == "duplicate_or_ambiguous_page_number" for fv in student_facing
    )
    # None of the (correctly filtered) findings' location labels mention the
    # protocol ID -- this is the exact student-facing string the live bug
    # produced (e.g. "Page 42 -- multiple page-number-like tokens (e.g.
    # 2503052525., 27)").
    assert not any("2503052525" in fv.location_label for fv in student_facing)


def test_protocol_id_does_not_trigger_p019_multiple_page_numbers(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "protocol_id_p019.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 760), "2503052525.", fontsize=10)
    page.insert_text((300, 770), "27", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert not [
        f for f in findings if f.details.get("issue_type") == "multiple_page_numbers"
    ]


def test_long_numeric_id_rejected_by_plausibility_classifier() -> None:
    """Direct unit check of the classifier P013 now consults."""
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


def test_real_duplicate_footer_page_numbers_still_warn_p013(tmp_path: Path) -> None:
    """Two genuinely plausible page-number tokens on the same page must
    still be reported -- the fix must not broadly suppress real duplicates."""
    pdf_path = tmp_path / "real_duplicate.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((300, 770), "27", fontsize=12)
    page.insert_text((560, 770), "27", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    finding = _page_finding(findings, page=1)
    assert finding is not None
    assert finding.details["candidate_count_on_page"] == "2"

    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    student_facing = [fv for fv in view.findings if fv.rule_id == "P013" and fv.page is not None]
    assert any(
        fv.issue_type == "duplicate_or_ambiguous_page_number" for fv in student_facing
    )


def test_page_with_only_implausible_tokens_has_no_p013_candidate_finding(
    tmp_path: Path,
) -> None:
    """A page whose only margin-zone token is implausible (no real page
    number at all) must not produce a P013 candidate finding for that page."""
    pdf_path = tmp_path / "only_implausible.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 760), "2503052525.", fontsize=10)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    assert _page_finding(findings, page=1) is None
