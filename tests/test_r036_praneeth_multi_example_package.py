"""Regression tests for the R036/Praneeth all-page-11-examples package
generator (scripts/ester_batch/build_r036_praneeth_multi_example_package.py).

Background: the standard per-rule Ester package
(``scripts/ester_batch/build_rule_package.py``) always narrows a document's
findings down to one via ``lib.select_weakest_finding`` before rendering
evidence. For R036/Praneeth that narrowing is exactly the thing under
dispute (see
``docs/status/p036_praneeth_forensic_investigation_20260908.md``): Praneeth
physical PDF page 11 currently produces 12 P036 findings that all share the
same ~1.19 gap ratio, and the single finding Ester reviewed was picked from
those 12 by an arbitrary geometric tie-break, not a distinguishing
structural signal.

These tests exercise the new module's selection/labeling logic against
synthetic finding dicts (no private dissertation PDF required, so they run
in CI). They exist specifically to guard against this workflow silently
regressing back to a single selected example.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ester_batch"))

from build_r036_praneeth_multi_example_package import (  # noqa: E402
    MAP_LEGEND_ADDITIONAL_TEXT,
    MAP_LEGEND_REVIEWED_TEXT,
    REVIEWED_NEXT_PREVIEW,
    REVIEWED_PREVIOUS_PREVIEW,
    XLSX_COLUMN_WIDTHS,
    XLSX_HEADERS,
    _normalize_display_whitespace,
    build_example_rows,
    is_previously_reviewed,
    select_all_findings_for_page,
)


def _finding(
    page: int,
    pair_index: int,
    previous_preview: str,
    next_preview: str,
    gap_ratio: str = "1.19",
) -> dict:
    return {
        "rule_id": "P036",
        "page": page,
        "severity": "WARNING",
        "problem_number": pair_index,
        "message": (
            "Consecutive TOC/List entries appear to have insufficient "
            "inter-entry vertical spacing."
        ),
        "details": {
            "page_number": str(page),
            "section_type": "table_of_contents",
            "issue_type": "toc_inter_entry_spacing_too_tight",
            "entry_pair_index": str(pair_index),
            "gap_points": "14.3",
            "required_gap_points": "16.8",
            "local_line_height_points": "12.0",
            "gap_ratio": gap_ratio,
            "triage_tier": "medium",
            "previous_entry_preview": previous_preview,
            "next_entry_preview": next_preview,
            "bbox": "126.0,196.2,523.4,210.5",
        },
    }


def _synthetic_twelve_findings() -> list[dict]:
    # Twelve non-consecutive pair indices, mirroring the real gaps left by
    # exempt/skipped pairs on the real document -- selection must not
    # assume contiguous indices.
    indices = [1, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15]
    findings = []
    for i, pair_index in enumerate(indices):
        if pair_index == 1:
            prev, nxt = REVIEWED_PREVIOUS_PREVIEW, REVIEWED_NEXT_PREVIEW
        else:
            prev, nxt = f"{i}.{i} Some entry", f"{i}.{i + 1} Next entry"
        findings.append(_finding(11, pair_index, prev, nxt))
    # A finding on a different page must never be picked up.
    findings.append(_finding(20, 1, "Unrelated previous", "Unrelated next"))
    return findings


def test_select_all_findings_for_page_returns_every_candidate_not_one() -> None:
    findings = _synthetic_twelve_findings()
    page11 = select_all_findings_for_page(findings, 11)
    assert len(page11) == 12
    assert all(f["page"] == 11 for f in page11)


def test_select_all_findings_for_page_is_sorted_by_entry_pair_index() -> None:
    findings = _synthetic_twelve_findings()
    page11 = select_all_findings_for_page(findings, 11)
    pair_indices = [int(f["details"]["entry_pair_index"]) for f in page11]
    assert pair_indices == sorted(pair_indices)


def test_select_all_findings_for_page_excludes_other_pages() -> None:
    findings = _synthetic_twelve_findings()
    page11 = select_all_findings_for_page(findings, 11)
    assert all(f["page"] != 20 for f in page11)


def test_is_previously_reviewed_matches_only_the_recovered_pair() -> None:
    reviewed = _finding(11, 1, REVIEWED_PREVIOUS_PREVIEW, REVIEWED_NEXT_PREVIEW)
    sibling = _finding(11, 3, "1.2.1 Introduction", "1.2.2 Relative protein quantification")

    assert is_previously_reviewed(reviewed["details"]) is True
    assert is_previously_reviewed(sibling["details"]) is False


def test_is_previously_reviewed_requires_exact_match_on_both_sides() -> None:
    partial = _finding(11, 3, REVIEWED_PREVIOUS_PREVIEW, "Something else entirely")
    assert is_previously_reviewed(partial["details"]) is False


def test_build_example_rows_flags_exactly_one_reviewed_example() -> None:
    findings = _synthetic_twelve_findings()
    page11 = select_all_findings_for_page(findings, 11)
    doc_report = {"findings": []}

    rows = build_example_rows(page11, doc_report)

    assert len(rows) == 12
    reviewed_rows = [r for r in rows if r["previously_reviewed"]]
    assert len(reviewed_rows) == 1
    assert reviewed_rows[0]["example_number"] == 1


def test_build_example_rows_never_classifies_true_or_false_positive() -> None:
    findings = _synthetic_twelve_findings()
    page11 = select_all_findings_for_page(findings, 11)
    rows = build_example_rows(page11, {"findings": []})

    forbidden_terms = (
        "true positive",
        "false positive",
        "tp",
        "fp",
        "valid",
        "invalid",
        "correct",
        "incorrect",
    )
    for row in rows:
        for key in ("transition_label", "message"):
            text = str(row[key]).lower()
            for term in forbidden_terms:
                assert term not in text, (
                    f"row {row['example_number']} field {key} contains {term!r}"
                )


def test_build_example_rows_preserves_entry_text_verbatim() -> None:
    findings = _synthetic_twelve_findings()
    page11 = select_all_findings_for_page(findings, 11)
    rows = build_example_rows(page11, {"findings": []})

    reviewed_row = next(r for r in rows if r["previously_reviewed"])
    assert reviewed_row["previous_entry"] == REVIEWED_PREVIOUS_PREVIEW
    assert reviewed_row["next_entry"] == REVIEWED_NEXT_PREVIEW


# --- Presentation-polish regression tests -----------------------------------
#
# These cover the four QA-identified presentation fixes (overview header
# collision, map-page legend, xlsx header readability, PDF/xlsx whitespace
# consistency) without pinning exact pixel positions, column-width numbers,
# or font metrics -- only the properties QA actually asked for.


def test_display_whitespace_normalization_collapses_runs_but_preserves_content() -> None:
    raw = "1.4.2 Ultrafast microdroplet digestion.…  …"
    normalized = _normalize_display_whitespace(raw)

    assert normalized == "1.4.2 Ultrafast microdroplet digestion.… …"
    # No run of two-or-more plain spaces should survive.
    assert "  " not in normalized


def test_display_whitespace_normalization_never_changes_reviewed_match() -> None:
    # The reviewed-pair match must key off the RAW details text, not the
    # normalized display copy -- normalizing must not be able to break
    # identification of the previously-reviewed example.
    raw_details = {
        "previous_entry_preview": REVIEWED_PREVIOUS_PREVIEW,
        "next_entry_preview": REVIEWED_NEXT_PREVIEW,
    }
    assert is_previously_reviewed(raw_details) is True
    assert _normalize_display_whitespace(REVIEWED_PREVIOUS_PREVIEW) == REVIEWED_PREVIOUS_PREVIEW


def test_build_example_rows_display_text_has_no_double_spaces() -> None:
    findings = [
        _finding(
            11,
            13,
            "1.4.1 Acceleration of reaction in charged microdroplets.…",
            "1.4.2 Ultrafast microdroplet digestion.…  …",
        )
    ]
    rows = build_example_rows(findings, {"findings": []})

    assert "  " not in rows[0]["previous_entry"]
    assert "  " not in rows[0]["next_entry"]


def test_map_legend_text_is_neutral_and_distinguishes_reviewed_from_additional() -> None:
    for legend_text in (MAP_LEGEND_REVIEWED_TEXT, MAP_LEGEND_ADDITIONAL_TEXT):
        lowered = legend_text.lower()
        for forbidden in ("false positive", "true positive", "valid", "invalid", "accepted"):
            assert forbidden not in lowered

    assert "reviewed" in MAP_LEGEND_REVIEWED_TEXT.lower()
    assert "additional" in MAP_LEGEND_ADDITIONAL_TEXT.lower()
    # The two legend lines must remain visually/textually distinguishable
    # from one another.
    assert MAP_LEGEND_REVIEWED_TEXT != MAP_LEGEND_ADDITIONAL_TEXT


def test_xlsx_headers_include_all_reviewer_facing_fields() -> None:
    expected_fields = {
        "Example #",
        "Previously reviewed by Ester?",
        "Physical PDF page",
        "Previous entry",
        "Next entry",
        "Transition type / levels",
        "Gap ratio",
        "Required threshold (gap ratio)",
        "Brief neutral description",
        "Ester decision",
        "Ester notes",
    }
    assert set(XLSX_HEADERS) == expected_fields


def test_xlsx_column_widths_fit_their_own_header_text() -> None:
    # A width in openpyxl's units is roughly one default-font character;
    # requiring width >= header length (with a little slack) is enough to
    # catch a column too narrow for its own header without pinning an exact
    # number that would make this test brittle against minor style tweaks.
    assert len(XLSX_COLUMN_WIDTHS) == len(XLSX_HEADERS)
    for header, width in zip(XLSX_HEADERS, XLSX_COLUMN_WIDTHS):
        assert width >= len(header) - 5, (
            f"column for {header!r} (width {width}) looks too narrow for its own header"
        )
