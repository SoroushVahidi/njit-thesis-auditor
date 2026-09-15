"""Regression tests for the R036 "post-recovery" reviewer-validation
package generator
(scripts/ester_batch/build_r036_post_recovery_validation_package.py).

These exercise the module's pure selection/labeling/wrap-detection logic
against synthetic data (no private dissertation PDF required, so they run
in CI). They do not build the actual PDF/xlsx package.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ester_batch"))

from build_r036_post_recovery_validation_package import (  # noqa: E402
    EXPECTED_TOTAL_COUNTS,
    SELECTED_EXAMPLES,
    XLSX_COLUMN_WIDTHS,
    XLSX_HEADERS,
    _classify_package_entry_level,
    _entry_display_text,
    _find_finding,
    _level_label,
    _normalize_display_whitespace,
    _similar_findings_count,
    _transition_type_label,
    _wraps,
    _yes_no,
)


def _line(y0: float) -> SimpleNamespace:
    return SimpleNamespace(bbox=SimpleNamespace(y0=y0), text="")


def _text_line(text: str, y0: float) -> SimpleNamespace:
    return SimpleNamespace(bbox=SimpleNamespace(y0=y0), text=text)


# ---------------------------------------------------------------------------
# Wrap-label bug fix: a wrap requires genuinely distinct y-levels, not
# merely multiple extracted line objects.
# ---------------------------------------------------------------------------


def test_two_fragments_at_same_y0_not_wrapped():
    """The old package bug: a dot-leader fragment PyMuPDF splits off at
    the *identical* y0 as its title must not count as a wrap."""
    entry = [_line(622.77), _line(622.77)]
    assert _wraps(entry) is False


def test_fragments_at_distinct_y0_are_wrapped():
    entry = [_line(169.09), _line(182.89)]
    assert _wraps(entry) is True


def test_real_style_detached_dot_leader_fragment_not_wrapped():
    """Real corpus case (Youra page 12): a dot-leader run detaches at a
    barely-different y0 (~0.3pt) from its title -- still not a genuine
    second physical line."""
    entry = [_line(139.399), _line(139.692)]
    assert _wraps(entry) is False


def test_single_line_entry_not_wrapped():
    assert _wraps([_line(100.0)]) is False


def test_three_genuinely_distinct_lines_wrapped():
    entry = [_line(100.0), _line(113.8), _line(127.6)]
    assert _wraps(entry) is True


# ---------------------------------------------------------------------------
# Selection invariants
# ---------------------------------------------------------------------------


def test_selected_examples_count_within_target_range():
    assert 10 <= len(SELECTED_EXAMPLES) <= 16


def test_selected_examples_no_duplicates():
    keys = [(name, page, pair) for name, page, pair, _note in SELECTED_EXAMPLES]
    assert len(keys) == len(set(keys))


def test_selected_examples_cover_required_dissertations():
    docs = {name for name, _page, _pair, _note in SELECTED_EXAMPLES}
    for required in ("Muyeed", "Philip", "Patrick"):
        assert required in docs


def test_selected_examples_exclude_zero_finding_dissertations():
    docs = {name for name, _page, _pair, _note in SELECTED_EXAMPLES}
    assert docs.isdisjoint({"Youra", "Anthony", "Praneeth", "Sebastian"})


def test_expected_total_counts_match_zero_finding_dissertations():
    for name in ("Youra", "Anthony", "Praneeth", "Sebastian"):
        assert EXPECTED_TOTAL_COUNTS[name] == 0
    for name in ("Muyeed", "Philip", "Patrick"):
        assert EXPECTED_TOTAL_COUNTS[name] > 0


def test_xlsx_headers_and_widths_same_length():
    assert len(XLSX_HEADERS) == len(XLSX_COLUMN_WIDTHS)


def test_xlsx_headers_have_no_internal_identifiers():
    joined = " ".join(XLSX_HEADERS)
    for leaked in ("P036", "Q057", "Q067", "Q077"):
        assert leaked not in joined


def test_xlsx_headers_include_section_and_level_columns():
    assert "Section Type" in XLSX_HEADERS
    assert "Previous Level" in XLSX_HEADERS
    assert "Next Level" in XLSX_HEADERS


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def test_yes_no():
    assert _yes_no(True) == "YES"
    assert _yes_no(False) == "NO"


def test_level_label_known_and_unknown():
    assert _level_label("toc_level_2") == "level 2 (X.X)"
    assert _level_label("appendix_level_2") == "appendix level 2 (A.N)"
    assert _level_label("something_else") == "something_else"


def test_package_entry_level_recognizes_lettered_appendix_peers():
    assert (
        _classify_package_entry_level("A.2 The Lyapunov Inequality Away From Saddles", "table_of_contents")
        == "appendix_level_2"
    )


def test_entry_display_text_uses_full_wrapped_logical_entry():
    entry = [
        _text_line("5.13 Three Newton iterations (5.6) where the scatterer is a kite and", 100.0),
        _text_line("lambda = 1, mu = 1", 113.8),
    ]
    display = _entry_display_text(entry)
    assert display.startswith("5.13 Three Newton iterations")
    assert "lambda = 1" in display


def test_normalize_display_whitespace_collapses_runs():
    assert _normalize_display_whitespace("a   b\n\tc") == "a b c"


def test_transition_type_label_structural_heading():
    label = _transition_type_label("toc_level_1", "toc_level_2", False, False)
    assert "structural-heading transition" in label


def test_transition_type_label_same_level_with_wraps():
    label = _transition_type_label("table_entry", "table_entry", False, True)
    assert "same-level entries" in label
    assert "next entry wraps" in label
    assert "previous entry wraps" not in label


def test_transition_type_label_level_change():
    label = _transition_type_label("toc_level_3", "toc_level_2", False, False)
    assert "level 3 (X.X.X)" in label
    assert "level 2 (X.X)" in label


def _finding(page: int, pair_index: int, gap_ratio: str) -> dict:
    return {"page": page, "details": {"entry_pair_index": str(pair_index), "gap_ratio": gap_ratio}}


def test_find_finding_matches_page_and_pair_index():
    findings = [_finding(11, 0, "1.0"), _finding(11, 1, "1.2"), _finding(12, 0, "1.0")]
    found = _find_finding(findings, 11, 1)
    assert found is not None
    assert found["details"]["gap_ratio"] == "1.2"


def test_find_finding_returns_none_when_absent():
    assert _find_finding([_finding(11, 0, "1.0")], 11, 5) is None


def test_similar_findings_count_groups_by_rounded_ratio():
    findings = [
        _finding(1, 0, "1.24"),
        _finding(1, 1, "1.244"),
        _finding(1, 2, "1.51"),
        _finding(1, 3, "1.236"),
    ]
    target = findings[0]
    assert _similar_findings_count(findings, target) == 3
