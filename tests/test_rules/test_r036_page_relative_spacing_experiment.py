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
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.r036_page_relative_spacing_experiment import (
    DiagnosticModel,
    DiagnosticOutcome,
    collect_r036_spacing_candidates,
    evaluate_page_relative_models,
    selected_candidate_decision,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH_PATH = (
    REPO_ROOT / "data/evaluation/r036_ester_false_positive_ground_truth_20260916.json"
)
PRIVATE_DATA_DIR = REPO_ROOT / "data/evaluation/private"


def _line(text: str, y0: float, x0: float = 108.0) -> tuple[str, float, float, float]:
    return (text, x0, y0, y0 + 12.0)


def _make_page(
    page_number: int,
    lines: list[tuple[str, float, float, float]],
    page_type: str = "table_of_contents",
) -> PdfPage:
    header_text = "TABLE OF CONTENTS"
    if page_type == "list_of_tables":
        header_text = "LIST OF TABLES"
    elif page_type == "list_of_figures":
        header_text = "LIST OF FIGURES"

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


def _make_doc(
    lines: list[tuple[str, float, float, float]],
    page_type: str = "table_of_contents",
) -> PdfDocument:
    return PdfDocument(path="mock.pdf", pages=[_make_page(1, lines, page_type=page_type)])


def _lof_doc(lines: list[tuple[str, float, float, float]]) -> PdfDocument:
    return _make_doc(lines, page_type="list_of_figures")


def _selected_outcomes(doc: PdfDocument) -> list[DiagnosticOutcome]:
    candidates = collect_r036_spacing_candidates(doc, document_name="synthetic")
    evaluated = evaluate_page_relative_models(candidates)
    return [selected_candidate_decision(item).outcome for item in evaluated]


def test_uniform_page_rhythm_has_no_page_relative_anomaly() -> None:
    doc = _make_doc(
        [
            _line("1.1 Alpha ......... 1", 150.0),
            _line("1.2 Beta ......... 2", 178.0),
            _line("1.3 Gamma ......... 3", 206.0),
            _line("1.4 Delta ......... 4", 234.0),
            _line("1.5 Epsilon ......... 5", 262.0),
            _line("1.6 Zeta ......... 6", 290.0),
        ]
    )

    assert _selected_outcomes(doc) == [DiagnosticOutcome.SUPPRESSED] * 5


def test_one_clearly_tighter_gap_among_regular_gaps_is_anomaly() -> None:
    doc = _make_doc(
        [
            _line("1.1 Alpha ......... 1", 150.0),
            _line("1.2 Beta ......... 2", 178.0),
            _line("1.3 Gamma ......... 3", 206.0),
            _line("1.4 Delta ......... 4", 220.0),
            _line("1.5 Epsilon ......... 5", 248.0),
            _line("1.6 Zeta ......... 6", 276.0),
            _line("1.7 Eta ......... 7", 304.0),
        ]
    )

    candidates = collect_r036_spacing_candidates(doc, document_name="synthetic")
    evaluated = evaluate_page_relative_models(candidates)
    anomaly_pairs = [
        item.candidate.entry_pair_index
        for item in evaluated
        if selected_candidate_decision(item).outcome == DiagnosticOutcome.ANOMALY
    ]
    assert anomaly_pairs == [2]


def test_wrapped_title_single_spacing_does_not_contaminate_inter_entry_baseline() -> None:
    doc = _make_doc(
        [
            _line("1.1 A Long Title That Wraps Before", 150.0),
            _line("Finishing With Dot Leaders ......... 1", 164.0),
            _line("1.2 Beta ......... 2", 192.0),
            _line("1.3 Gamma ......... 3", 220.0),
            _line("1.4 Delta ......... 4", 248.0),
            _line("1.5 Epsilon ......... 5", 276.0),
            _line("1.6 Zeta ......... 6", 304.0),
        ]
    )

    candidates = collect_r036_spacing_candidates(doc, document_name="synthetic")
    assert len(candidates) == 5
    assert all(candidate.pitch_pt == pytest.approx(28.0) for candidate in candidates)
    assert _selected_outcomes(doc) == [DiagnosticOutcome.SUPPRESSED] * 5


def test_sparse_page_abstains_instead_of_flagging() -> None:
    doc = _make_doc(
        [
            _line("1.1 Alpha ......... 1", 150.0),
            _line("1.2 Beta ......... 2", 164.0),
            _line("1.3 Gamma ......... 3", 178.0),
        ]
    )

    assert _selected_outcomes(doc) == [
        DiagnosticOutcome.INSUFFICIENT_CONTEXT,
        DiagnosticOutcome.INSUFFICIENT_CONTEXT,
    ]


def test_multimodal_but_legitimate_page_spacing_avoids_overflagging() -> None:
    doc = _make_doc(
        [
            _line("1.1 Alpha ......... 1", 150.0),
            _line("1.2 Beta ......... 2", 174.0),
            _line("1.3 Gamma ......... 3", 202.0),
            _line("1.4 Delta ......... 4", 226.0),
            _line("1.5 Epsilon ......... 5", 254.0),
            _line("1.6 Zeta ......... 6", 278.0),
            _line("1.7 Eta ......... 7", 306.0),
        ]
    )

    assert DiagnosticOutcome.ANOMALY not in _selected_outcomes(doc)


def test_ground_truth_contains_only_the_24_ester_reviewed_false_positives() -> None:
    payload = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    labels = payload["labels"]

    assert len(labels) == 24
    assert {row["label"] for row in labels} == {"ESTER_FALSE_POSITIVE"}
    assert len({row["id"] for row in labels}) == 24


def test_selected_candidate_suppresses_reviewed_false_positive_rhythm_proxy() -> None:
    """The reviewed cases are page-rhythm examples, not isolated dips.

    This synthetic proxy guards the selected model's key behavior without
    requiring private PDFs in CI: a full page of equally spaced reviewed-like
    gaps must suppress every candidate rather than re-create the fixed-ratio
    false-positive pattern.
    """
    payload = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    lines = [
        _line(f"1.{index} Reviewed rhythm proxy ......... {index}", 150.0 + (24.0 * index))
        for index, _row in enumerate(payload["labels"], start=1)
    ]
    doc = _make_doc(lines)

    assert _selected_outcomes(doc) == [DiagnosticOutcome.SUPPRESSED] * 23


def _private_pdf(name: str) -> Path:
    path = PRIVATE_DATA_DIR / name
    if not path.exists():
        pytest.skip(f"private evaluation PDF is unavailable: {path}")
    return path


def test_current_production_r036_praneeth_count_remains_zero() -> None:
    doc = load_pdf_layout(str(_private_pdf("Praneeth Ivan Joel. FNU_3rd review draft.pdf")))

    findings = check_pdf_toc_list_entry_spacing(doc)

    assert len(findings) == 0


def test_current_production_r036_anthony_count_remains_zero() -> None:
    doc = load_pdf_layout(str(_private_pdf("Anthony.Sena 3rd Review Draft.pdf")))

    findings = check_pdf_toc_list_entry_spacing(doc)

    assert len(findings) == 0


def test_production_detector_still_uses_fixed_threshold_for_now() -> None:
    doc = _make_doc(
        [
            _line("1.1 Alpha ......... 1", 150.0),
            _line("1.2 Beta ......... 2", 170.0),
        ]
    )

    production_findings = check_pdf_toc_list_entry_spacing(doc)
    diagnostic = evaluate_page_relative_models(
        collect_r036_spacing_candidates(doc, document_name="synthetic")
    )

    assert len(production_findings) == 1
    assert (
        diagnostic[0].decisions[DiagnosticModel.NEIGHBOR_RELATIVE].outcome
        == DiagnosticOutcome.INSUFFICIENT_CONTEXT
    )


def test_paired_wrapped_entry_lof_anomalies_resolve_to_structural_abstain() -> None:
    """Real-style Patrick p11 LOF pair-2 / pair-7 shape, generalized.

    A wrapped entry whose extracted physical lines are non-contiguous (the
    entry's own lines are detached onto separate baselines by text
    extraction) makes the measured inter-entry pitch an extraction artifact
    rather than a genuine visual gap. When such a wrapped entry sits between
    two clean single-line entries, the two flanking gaps each look like an
    isolated lower-tail dip against the clean page rhythm -- the exact
    shape that produced the two Patrick p11 LOF diagnostic anomalies.

    The neighbor-selection fix must resolve both flanking gaps to
    INSUFFICIENT_CONTEXT (structural abstain) rather than scoring them as
    anomalies, because their baseline is contaminated by the wrapped
    entry's non-contiguous extraction.
    """
    # 7 visual lines, uniform 28pt rhythm, 14pt single-line pitch.
    # line[1] is the continuation of a wrapped entry whose number was
    # detached, so it starts at the caption-continuation indent (x0=149)
    # instead of the entry-number column (x0=108).
    doc = _lof_doc(
        [
            _line("5.1 First entry with a single line caption", 140.0),
            _line("Second entry first visual line of a wrapped caption", 168.0),
            _line("continuation line of the wrapped caption", 182.0, x0=149.0),
            _line("5.3 Third entry with a single line caption", 210.0),
            _line("5.4 Fourth entry with a single line caption", 238.0),
            _line("5.5 Fifth entry with a single line caption", 266.0),
            _line("5.6 Sixth entry with a single line caption", 294.0),
        ]
    )

    candidates = collect_r036_spacing_candidates(doc, document_name="synthetic")
    evaluated = evaluate_page_relative_models(candidates)
    outcomes_by_pair = {
        item.candidate.entry_pair_index: selected_candidate_decision(item).outcome
        for item in evaluated
    }
    # The two gaps flanking the wrapped entry must abstain (structural
    # artifact), not be scored as anomalies.
    assert outcomes_by_pair.get(1) == DiagnosticOutcome.INSUFFICIENT_CONTEXT
    assert outcomes_by_pair.get(2) == DiagnosticOutcome.INSUFFICIENT_CONTEXT
    # No gap on the page may be scored as an anomaly.
    assert DiagnosticOutcome.ANOMALY not in outcomes_by_pair.values()


def test_clean_single_line_lof_page_uniform_rhythm_has_no_anomaly() -> None:
    """A page of single-line LOF captions with uniform rhythm must not flag.

    This is the LOF/LOT counterpart of the TOC uniform-rhythm test and
    guards that the clean-neighbor behavior does not over-abstain on pages
    with no wrapped entries.
    """
    doc = _lof_doc(
        [
            _line("5.1 First entry with a single line caption", 140.0),
            _line("5.2 Second entry with a single line caption", 168.0),
            _line("5.3 Third entry with a single line caption", 196.0),
            _line("5.4 Fourth entry with a single line caption", 224.0),
            _line("5.5 Fifth entry with a single line caption", 252.0),
            _line("5.6 Sixth entry with a single line caption", 280.0),
        ]
    )

    assert _selected_outcomes(doc) == [DiagnosticOutcome.SUPPRESSED] * 5


def test_isolated_genuine_tight_single_line_lof_gap_is_still_detected() -> None:
    """A genuine isolated tight gap among clean single-line LOF entries is
    still detected as an anomaly (the model keeps its lower-tail signal)."""
    doc = _lof_doc(
        [
            _line("5.1 First entry with a single line caption", 140.0),
            _line("5.2 Second entry with a single line caption", 168.0),
            _line("5.3 Third entry with a single line caption", 196.0),
            _line("5.4 Fourth entry with a single line caption", 210.0),
            _line("5.5 Fifth entry with a single line caption", 238.0),
            _line("5.6 Sixth entry with a single line caption", 266.0),
            _line("5.7 Seventh entry with a single line caption", 294.0),
        ]
    )

    candidates = collect_r036_spacing_candidates(doc, document_name="synthetic")
    evaluated = evaluate_page_relative_models(candidates)
    anomaly_pairs = [
        item.candidate.entry_pair_index
        for item in evaluated
        if selected_candidate_decision(item).outcome == DiagnosticOutcome.ANOMALY
    ]
    assert anomaly_pairs == [2]


def test_sparse_unreliable_neighborhood_abstains() -> None:
    """A page with too few eligible gaps abstains rather than flagging."""
    doc = _lof_doc(
        [
            _line("5.1 First entry with a single line caption", 140.0),
            _line("5.2 Second entry with a single line caption", 168.0),
            _line("5.3 Third entry with a single line caption", 196.0),
        ]
    )

    assert _selected_outcomes(doc) == [
        DiagnosticOutcome.INSUFFICIENT_CONTEXT,
        DiagnosticOutcome.INSUFFICIENT_CONTEXT,
    ]
