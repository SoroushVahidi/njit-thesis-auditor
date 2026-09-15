"""Regression tests for the R036 "remaining findings" reviewer-validation
package generator
(scripts/ester_batch/build_r036_remaining_findings_validation_package.py).

These exercise the module's pure selection/labeling logic against
synthetic data (no private dissertation PDF required, so they run in CI) --
they do not build the actual PDF/xlsx package (that requires the real,
gitignored corpus and is exercised manually/in the evaluation package's own
build run, not in the regular test suite).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ester_batch"))

from build_r036_remaining_findings_validation_package import (  # noqa: E402
    NEWLY_SURFACED,
    SELECTED_EXAMPLES,
    XLSX_COLUMN_WIDTHS,
    XLSX_HEADERS,
    _find_finding,
    _normalize_display_whitespace,
    _similar_findings_count,
    _transition_type_label,
    _yes_no_unknown,
)


def test_selected_examples_count_within_target_range():
    assert 10 <= len(SELECTED_EXAMPLES) <= 18


def test_selected_examples_no_duplicates():
    keys = [(name, page, pair) for name, page, pair, _note in SELECTED_EXAMPLES]
    assert len(keys) == len(set(keys))


def test_selected_examples_cover_required_dissertations():
    docs = {name for name, _page, _pair, _note in SELECTED_EXAMPLES}
    for required in ("Youra", "Muyeed", "Philip", "Patrick"):
        assert required in docs


def test_selected_examples_include_all_three_newly_surfaced():
    selected_keys = {(name, page, pair) for name, page, pair, _note in SELECTED_EXAMPLES}
    assert NEWLY_SURFACED <= selected_keys
    assert len(NEWLY_SURFACED) == 3


def test_no_unreviewed_dissertations_selected():
    """Anthony/Praneeth/Sebastian are at zero R036 findings post-fix; the
    task explicitly says no examples are needed from them."""
    docs = {name for name, _page, _pair, _note in SELECTED_EXAMPLES}
    assert docs.isdisjoint({"Anthony", "Praneeth", "Sebastian"})


def test_xlsx_headers_and_widths_same_length():
    assert len(XLSX_HEADERS) == len(XLSX_COLUMN_WIDTHS)


def test_xlsx_headers_have_no_internal_identifiers():
    joined = " ".join(XLSX_HEADERS)
    for leaked in ("P036", "Q057", "Q067", "Q077"):
        assert leaked not in joined


def test_yes_no_unknown():
    assert _yes_no_unknown(True) == "YES"
    assert _yes_no_unknown(False) == "NO"
    assert _yes_no_unknown(None) == "unknown"


def test_normalize_display_whitespace_collapses_runs():
    assert _normalize_display_whitespace("a   b\n\tc") == "a b c"


def test_transition_type_label_structural_heading():
    label = _transition_type_label("APPENDIX ... 80", "REFERENCES ... 117", False, False)
    assert "structural heading" in label
    assert "wraps" not in label


def test_transition_type_label_same_level_with_wrap_flags():
    label = _transition_type_label("Introduction", "Assumptions", False, True)
    assert "same-level entries" in label
    assert "next entry wraps" in label
    assert "previous entry wraps" not in label


def test_transition_type_label_level_change():
    label = _transition_type_label("1.2.3 Study limitations", "1.3 Next Section", False, False)
    assert "level-3 (X.X.X)" in label
    assert "level-2 (X.X)" in label


def test_transition_type_label_both_wrap():
    label = _transition_type_label("First tail", "Second start", True, True)
    assert "previous entry wraps" in label
    assert "next entry wraps" in label


def _finding(page: int, pair_index: int, gap_ratio: str) -> dict:
    return {
        "page": page,
        "details": {"entry_pair_index": str(pair_index), "gap_ratio": gap_ratio},
    }


def test_find_finding_matches_page_and_pair_index():
    findings = [_finding(11, 0, "1.0"), _finding(11, 1, "1.2"), _finding(12, 0, "1.0")]
    found = _find_finding(findings, 11, 1)
    assert found is not None
    assert found["details"]["gap_ratio"] == "1.2"


def test_find_finding_returns_none_when_absent():
    findings = [_finding(11, 0, "1.0")]
    assert _find_finding(findings, 11, 5) is None


def test_similar_findings_count_groups_by_rounded_ratio():
    findings = [
        _finding(1, 0, "1.00"),
        _finding(1, 1, "1.04"),
        _finding(1, 2, "1.20"),
        _finding(1, 3, "0.98"),
    ]
    target = findings[0]
    # 1.00, 1.04, and 0.98 all round to 1.0; 1.20 rounds to 1.2.
    assert _similar_findings_count(findings, target) == 3
