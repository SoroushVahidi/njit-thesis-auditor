"""Production page-relative R036 policy tests.

These tests pin the *production* R036 semantics introduced by
``njit_auditor.rules.r036_production_page_relative_spacing`` (see
``docs/status/r036_production_page_relative_suppression_design_20260916.md``):

* SUPPRESS when the gap matches normal local page rhythm;
* ABSTAIN when context is unreliable (sparse page, ambiguous reconstruction,
  untrustworthy neighborhood);
* REPORT only under a strong multi-signal gate that is intentionally DISABLED
  (``suppression_abstention_only``) because no Ester-confirmed R036 true
  positive exists to validate positive detection.

The retired fixed 1.6 ratio must not produce findings, and all 24
Ester-confirmed false positives must be suppressed or abstained (never
reported).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_list_entry_spacing import (
    MIN_INTER_ENTRY_GAP_RATIO,
    check_pdf_toc_list_entry_spacing,
)
from njit_auditor.rules.r036_production_page_relative_spacing import (
    CandidateOutcome,
    ProductionOutcome,
    classify_r036_spacing_candidates,
    run_r036_production,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GT_PATH = REPO_ROOT / "data/evaluation/r036_ester_false_positive_ground_truth_20260916.json"
PRIVATE_DATA_DIR = REPO_ROOT / "data/evaluation/private"

DISSERTATION_FILES = {
    "Youra": "5_Youra_Shin_PhD_Dissertation_Document_3rd review.pdf",
    "Anthony": "Anthony.Sena 3rd Review Draft.pdf",
    "Muyeed": "Muyeed_Dissertation (4).pdf",
    "Philip": "Philip_Zaleski_Thesis_Revised (1).pdf",
    "Praneeth": "Praneeth Ivan Joel. FNU_3rd review draft.pdf",
    "Sebastian": "Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf",
    "Patrick": "Thesis Patrick Grice July 22.pdf",
}


def _requires_private_pdf() -> None:
    if not PRIVATE_DATA_DIR.is_dir():
        pytest.skip("private evaluation PDFs not present in this environment")


# ---------------------------------------------------------------------------
# Helpers to build small synthetic TOC/LOF/LOT pages.
# ---------------------------------------------------------------------------


def _line(text: str, y0: float, x0: float = 108.0, height: float = 12.0):
    return (text, x0, y0, y0 + height)


def _make_page(
    page_number: int,
    lines: list[tuple[str, float, float, float]],
    page_type: str = "table_of_contents",
) -> PdfPage:
    header_text = {
        "table_of_contents": "TABLE OF CONTENTS",
        "list_of_tables": "LIST OF TABLES",
        "list_of_figures": "LIST OF FIGURES",
    }[page_type]
    page = PdfPage(
        page_number=page_number,
        original_page_index=page_number - 1,
        original_page_number=page_number,
        manuscript_page_index=page_number - 1,
        manuscript_page_number=page_number,
        width=612.0,
        height=792.0,
        is_visually_landscape=False,
        text_blocks=[],
        graphic_blocks=[],
    )
    header_bbox = BBox(x0=108.0, y0=100.0, x1=540.0, y1=115.0)
    header_span = PdfTextSpan(text=header_text, bbox=header_bbox)
    page.text_blocks.append(
        PdfTextBlock(
            lines=[PdfTextLine(spans=[header_span], bbox=header_bbox, text=header_text)],
            bbox=header_bbox,
            text=header_text,
        )
    )
    for text, x0, y0, y1 in lines:
        bbox = BBox(x0=x0, y0=y0, x1=540.0, y1=y1)
        span = PdfTextSpan(text=text, bbox=bbox)
        page.text_blocks.append(
            PdfTextBlock(
                lines=[PdfTextLine(spans=[span], bbox=bbox, text=text)],
                bbox=bbox,
                text=text,
            )
        )
    return page


def _make_doc(lines_by_page: dict[int, list], page_type: str = "table_of_contents") -> PdfDocument:
    pages = [
        _make_page(page_number, lines, page_type)
        for page_number, lines in sorted(lines_by_page.items())
    ]
    return PdfDocument(path="synthetic.pdf", pages=pages)


def _outcome(records: list[dict]) -> list[CandidateOutcome]:
    return [r["outcome"] for r in records]


# ---------------------------------------------------------------------------
# Phase 4 / 11: the retired fixed 1.6 must not control reporting.
# ---------------------------------------------------------------------------


def test_fixed_1_6_ratio_is_retired_and_does_not_report() -> None:
    """A candidate whose normalized ratio is below the retired 1.6 threshold
    must NOT produce a student-facing finding. The rule is wired to the
    page-relative policy, which abstains (no real true positive validated).
    This is a 2-entry page (sparse) so it abstains for a second, independent
    reason, but the assertion is on the *finding* outcome, not the reason."""
    assert MIN_INTER_ENTRY_GAP_RATIO == 1.6  # constant retained for compat only
    doc = _make_doc(
        {1: [_line("1.1 Alpha ......... 1", 150.0), _line("1.2 Beta ......... 2", 170.0)]}
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


def test_abstain_emits_no_internal_wording_to_students() -> None:
    """When the policy abstains, no finding is emitted at all -- so no
    internal wording (anomaly score / MAD / neighbor floor / diagnostic
    model / insufficient confidence) can reach a student. A 2-entry sparse
    page exercises the abstain path."""
    doc = _make_doc(
        {1: [_line("1.1 Alpha ......... 1", 150.0), _line("1.2 Beta ......... 2", 170.0)]}
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    assert records and records[0]["outcome"].outcome is ProductionOutcome.ABSTAIN


# ---------------------------------------------------------------------------
# Phase 12.1: all 24 Ester false positives suppressed or abstained.
# ---------------------------------------------------------------------------


def test_all_24_ester_false_positives_are_not_reported() -> None:
    """Hard requirement: every one of the 24 Ester-confirmed R036 false
    positives must classify as SUPPRESS or ABSTAIN under the production
    policy -- never REPORT. Mapped individually by (dissertation, physical
    page, entry_pair_index) from the ground-truth file."""
    _requires_private_pdf()
    payload = json.loads(GT_PATH.read_text(encoding="utf-8"))
    labels = payload["labels"]
    assert len(labels) == 24

    outcomes: dict[tuple, ProductionOutcome] = {}
    for document, filename in DISSERTATION_FILES.items():
        pdf_path = PRIVATE_DATA_DIR / filename
        if not pdf_path.exists():
            pytest.skip(f"private PDF missing: {filename}")
        _findings, records = run_r036_production(load_pdf_layout(str(pdf_path)))
        for record in records:
            outcomes[(document, record["page_number"], record["entry_pair_index"])] = (
                record["outcome"].outcome
            )

    for label in labels:
        key = (
            label["dissertation"],
            int(label["physical_pdf_page"]),
            int(label["entry_pair_index"]),
        )
        outcome = outcomes.get(key)
        assert outcome is not ProductionOutcome.REPORT, (
            f"Ester false positive {label['id']} at {key} was REPORTED: "
            f"{outcome}"
        )
        # Every known FP is present as a candidate (none is exempted away)
        # and resolves to a suppress-or-abstain outcome.
        assert outcome in (ProductionOutcome.SUPPRESS, ProductionOutcome.ABSTAIN), (
            f"Ester false positive {label['id']} at {key} classified as {outcome}"
        )


# ---------------------------------------------------------------------------
# Phase 12.2 / 9-11: uniform page rhythm -> suppress (TOC, LOF, LOT).
# ---------------------------------------------------------------------------


def _uniform_page_lines(count: int = 8, pitch: float = 22.0, start_y: float = 150.0) -> list:
    lines = []
    for i in range(count):
        y = start_y + i * pitch
        lines.append(_line(f"Section {i + 1} Title ......... {10 + i}", y))
    return lines


def test_uniform_toc_rhythm_suppressed() -> None:
    doc = _make_doc({1: _uniform_page_lines(8, pitch=22.0)})
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    interior = [r for r in records if 0 < r["entry_pair_index"] < len(records) - 1]
    assert interior
    assert all(
        r["outcome"].outcome is ProductionOutcome.SUPPRESS for r in interior
    ), [r["outcome"].outcome for r in interior]


def test_uniform_lof_rhythm_suppressed() -> None:
    doc = _make_doc(
        {1: _uniform_page_lines(8, pitch=22.0)},
        page_type="list_of_figures",
    )
    records = classify_r036_spacing_candidates(doc)
    interior = [r for r in records if 0 < r["entry_pair_index"] < len(records) - 1]
    assert interior
    assert all(
        r["outcome"].outcome is ProductionOutcome.SUPPRESS for r in interior
    )


def test_uniform_lot_rhythm_suppressed() -> None:
    doc = _make_doc(
        {1: _uniform_page_lines(8, pitch=22.0)},
        page_type="list_of_tables",
    )
    records = classify_r036_spacing_candidates(doc)
    interior = [r for r in records if 0 < r["entry_pair_index"] < len(records) - 1]
    assert interior
    assert all(
        r["outcome"].outcome is ProductionOutcome.SUPPRESS for r in interior
    )


# ---------------------------------------------------------------------------
# Phase 12.3: sparse page -> abstain.
# ---------------------------------------------------------------------------


def test_sparse_page_abstains() -> None:
    doc = _make_doc({1: _uniform_page_lines(2, pitch=22.0)})
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    assert records
    assert all(
        r["outcome"].outcome is ProductionOutcome.ABSTAIN
        and r["outcome"].abstain_reason.value == "sparse_page"
        for r in records
    )


# ---------------------------------------------------------------------------
# Phase 12.4: reconstructed continuation entry (LOF) -> abstain.
# ---------------------------------------------------------------------------


def test_reconstructed_lof_continuation_entry_abstains() -> None:
    """An LOF page where a single-line entry's first visual line starts at
    the caption-continuation indent (right of the page's entry-number
    column) is a reassembly artifact. The gap into it must abstain
    (reconstruction uncertainty), not report. Modeled on the resolved
    Patrick p11 LOF shape: entry-number column at x0=108, the
    reconstructed (continuation) entry at x0=150 (>= 108 + 12)."""
    lines = []
    y = 150.0
    # Entry-number column at x0=108 for the true entries.
    for i in range(4):
        lines.append(_line(f"Figure 2.{i + 1} Caption text here ......... {10 + i}", y, x0=108.0))
        y += 22.0
    # A single-line "entry" that is actually a continuation line (indented).
    lines.append(_line("continuation caption words here ......... 14", y, x0=150.0))
    y += 22.0
    for i in range(4):
        lines.append(_line(f"Figure 3.{i + 1} Caption text here ......... {20 + i}", y, x0=108.0))
        y += 22.0

    doc = _make_doc({11: lines}, page_type="list_of_figures")
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    # The gap INTO the reconstructed entry (pair index 4) must abstain for
    # reconstruction uncertainty.
    reconstructed = [
        r for r in records if r["previous_entry_is_reconstructed"]
    ]
    assert reconstructed, [
        (r["entry_pair_index"], r["previous_entry_is_reconstructed"]) for r in records
    ]
    for r in reconstructed:
        assert (
            r["outcome"].outcome is ProductionOutcome.ABSTAIN
            and r["outcome"].abstain_reason.value == "reconstruction_uncertainty"
        )
    # The specific gap into the indented entry (pair 4) abstains.
    pair4 = next(r for r in records if r["entry_pair_index"] == 4)
    assert pair4["previous_entry_is_reconstructed"]
    assert pair4["outcome"].outcome is ProductionOutcome.ABSTAIN
    assert pair4["outcome"].abstain_reason.value == "reconstruction_uncertainty"


# ---------------------------------------------------------------------------
# Phase 12.5: clean wrapped LOF/LOT neighborhood -> suppress (not abstain).
# ---------------------------------------------------------------------------


def test_clean_wrapped_lof_neighborhood_suppressed() -> None:
    """A wrapped LOF entry (two physical lines) followed by a properly
    spaced next entry, with clean neighbors on BOTH sides, is normal rhythm.
    The gap OUT of the wrapped entry (a clean, comparable inter-entry gap)
    must SUPPRESS -- the wrapped entry alone does not force an abstention
    when the candidate has a trustworthy two-sided neighborhood."""
    lines = []
    y = 150.0
    # A clean leading neighbor so the wrapped entry is interior.
    lines.append(_line("Figure 2.0 Intro caption text ......... 9", y, x0=108.0))
    y += 22.0
    # Wrapped entry: two physical lines 12pt apart, then a 22pt gap to next.
    lines.append(_line("Figure 2.1 A very long caption that wraps", y, x0=108.0))
    lines.append(_line("across a second physical line ......... 10", y + 12.0, x0=108.0))
    y += 12.0 + 22.0
    # Several clean single-line neighbors after the wrapped entry.
    for i in range(8):
        lines.append(_line(f"Figure 2.{i + 2} Caption text here ......... {11 + i}", y, x0=108.0))
        y += 22.0

    doc = _make_doc({1: lines}, page_type="list_of_figures")
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    assert records
    # The gap OUT of the wrapped entry is pair 1; it must be a clean,
    # suppressable rhythm (not a reconstruction abstention, not reported).
    wrapped_gap = next(r for r in records if r["entry_pair_index"] == 1)
    assert wrapped_gap["previous_wraps"] is True
    assert wrapped_gap["outcome"].outcome is ProductionOutcome.SUPPRESS
    # No reconstruction abstention anywhere on this clean page.
    assert not any(
        r["outcome"].outcome is ProductionOutcome.ABSTAIN
        and r["outcome"].abstain_reason.value == "reconstruction_uncertainty"
        for r in records
    )


# ---------------------------------------------------------------------------
# Phase 12.6: synthetic isolated tight gap -> behavior per selected gate.
# ---------------------------------------------------------------------------


def test_synthetic_isolated_tight_gap_abstains_under_selected_gate() -> None:
    """A page with a uniform 22pt rhythm except one isolated 15pt gap:
    under the selected ``suppression_abstention_only`` gate the candidate is
    NOT reported (no real true positive validated) -- it abstains. This is
    the production answer to 'the synthetic algorithm can detect an isolated
    tight gap': the detection is real, but production does not surface it
    until a true positive is confirmed."""
    lines = []
    y = 150.0
    # Establish rhythm: 150 -> 172 -> 194 (22pt gaps).
    lines.append(_line("Section 1 Alpha ......... 10", y))
    y += 22.0
    lines.append(_line("Section 2 Beta ......... 11", y))
    y += 22.0
    lines.append(_line("Section 3 Gamma ......... 12", y))
    # Isolated tight gap: only 15pt to the next entry.
    y += 15.0
    lines.append(_line("Section 4 Delta ......... 13", y))
    y += 22.0
    lines.append(_line("Section 5 Epsilon ......... 14", y))
    y += 22.0
    lines.append(_line("Section 6 Zeta ......... 15", y))

    doc = _make_doc({1: lines})
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    tight = [
        r for r in records if abs(r["pitch_pt"] - 15.0) < 0.5
    ]
    assert tight, "expected the isolated 15pt gap to be present as a candidate"
    # Under the selected gate it abstains (tight but reporting is disabled).
    assert all(
        r["outcome"].outcome is ProductionOutcome.ABSTAIN
        and r["outcome"].abstain_reason.value == "unreliable_neighborhood"
        for r in tight
    )


def test_synthetic_isolated_tight_gap_reports_under_strong_gate() -> None:
    """An isolated, clearly-extreme tight gap DOES report when the strong
    multi-signal gate is explicitly enabled -- proving the reporting path is
    intact and only disabled by policy. This is the future extension point
    once a true positive is validated. Uses a 12pt gap among 22pt neighbors
    (local ratio ~0.55, page-tail, two-sided, and above the absolute
    visual-separation sanity floor, i.e. a tight-but-visible gap)."""
    lines = []
    y = 150.0
    lines.append(_line("Section 1 Alpha ......... 10", y))
    y += 22.0
    lines.append(_line("Section 2 Beta ......... 11", y))
    y += 22.0
    lines.append(_line("Section 3 Gamma ......... 12", y))
    y += 12.0
    lines.append(_line("Section 4 Delta ......... 13", y))
    y += 22.0
    lines.append(_line("Section 5 Epsilon ......... 14", y))
    y += 22.0
    lines.append(_line("Section 6 Zeta ......... 15", y))

    doc = _make_doc({1: lines})
    findings, records = run_r036_production(doc, reporting_gate="strong_multi_signal")
    reported = [r for r in records if r["outcome"].outcome is ProductionOutcome.REPORT]
    assert reported, "strong gate should report the isolated tight gap"
    assert findings
    assert all(f.rule_id == "P036" for f in findings)


# ---------------------------------------------------------------------------
# Phase 12.7 / 8: ambiguous / contaminated neighborhood -> abstain.
# ---------------------------------------------------------------------------


def test_one_sided_anomaly_abstains() -> None:
    """A candidate tighter than one side's neighbor but with an unreliable
    single-sided neighborhood must abstain, not report."""
    lines = []
    y = 150.0
    lines.append(_line("Section 1 Alpha ......... 10", y))
    y += 22.0
    lines.append(_line("Section 2 Beta ......... 11", y))
    y += 22.0
    lines.append(_line("Section 3 Gamma ......... 12", y))
    # Tight gap to the right neighbor.
    y += 15.0
    lines.append(_line("Section 4 Delta ......... 13", y))
    y += 22.0
    lines.append(_line("Section 5 Epsilon ......... 14", y))
    y += 22.0
    lines.append(_line("Section 6 Zeta ......... 15", y))
    doc = _make_doc({1: lines})
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    assert all(
        r["outcome"].outcome
        in (ProductionOutcome.SUPPRESS, ProductionOutcome.ABSTAIN)
        for r in records
    )


def test_contaminated_lower_tail_neighbor_abstains() -> None:
    """When the local neighborhood is contaminated by a lower-tail outlier
    (a baseline dragged down by one tight gap), the candidate cannot be
    trusted and must abstain rather than be forced to a decision."""
    lines = []
    y = 150.0
    for i in range(3):
        lines.append(_line(f"Section {i + 1} Alpha ......... {10 + i}", y))
        y += 22.0
    # A very tight outlier gap contaminates the local neighborhood.
    y += 10.0
    lines.append(_line("Section 4 Outlier ......... 13", y))
    y += 22.0
    lines.append(_line("Section 5 Beta ......... 14", y))
    y += 22.0
    lines.append(_line("Section 6 Gamma ......... 15", y))
    doc = _make_doc({1: lines})
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    assert records
    assert all(
        r["outcome"].outcome in (ProductionOutcome.SUPPRESS, ProductionOutcome.ABSTAIN)
        for r in records
    )


# ---------------------------------------------------------------------------
# Phase 12.13 / 14: Anthony and Praneeth remain clean.
# ---------------------------------------------------------------------------


def test_anthony_remains_clean() -> None:
    _requires_private_pdf()
    pdf_path = PRIVATE_DATA_DIR / DISSERTATION_FILES["Anthony"]
    if not pdf_path.exists():
        pytest.skip("private PDF missing")
    findings = check_pdf_toc_list_entry_spacing(load_pdf_layout(str(pdf_path)))
    assert findings == []


def test_praneeth_remains_clean() -> None:
    _requires_private_pdf()
    pdf_path = PRIVATE_DATA_DIR / DISSERTATION_FILES["Praneeth"]
    if not pdf_path.exists():
        pytest.skip("private PDF missing")
    findings = check_pdf_toc_list_entry_spacing(load_pdf_layout(str(pdf_path)))
    assert findings == []
