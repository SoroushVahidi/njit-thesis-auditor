"""Canonical Medium confidence for structural heuristics, independent of triage."""

from pathlib import Path

import pytest
from test_pdf_rules import _make_lof_terminal_punct_pdf, _make_toc_hierarchy_pdf
from test_r045_no_numbering_20261006 import _biosketch, _entry

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    check_pdf_biosketch_publication_layout,
)
from njit_auditor.rules.pdf_lof_terminal_punctuation import check_pdf_lof_terminal_punctuation
from njit_auditor.rules.pdf_toc_entry_hierarchy import check_pdf_toc_entry_hierarchy


def _assert_medium(findings):
    assert findings
    assert all(f.details["confidence"] == "medium" for f in findings)
    assert all(f.details["confidence_reason"] for f in findings)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    assert view.findings
    assert all(f.confidence_level == "medium" for f in view.findings)
    assert all(f.has_highlight for f in view.findings)


@pytest.mark.parametrize("level", [2, 3])
def test_hierarchy_confidence_is_not_promoted_from_high_triage(tmp_path: Path, level):
    path = tmp_path / "hierarchy.pdf"
    _make_toc_hierarchy_pdf(
        path,
        l1_x=108,
        l2_x=108 if level == 2 else 126,
        l3_x=126 if level == 3 else None,
        l3_count=2 if level == 3 else 0,
    )
    findings = check_pdf_toc_entry_hierarchy(load_pdf_layout(str(path)))
    assert any(f.details["triage_tier"] == "high" for f in findings)
    _assert_medium(findings)


def test_missing_list_punctuation_has_explicit_bounded_confidence(tmp_path: Path):
    path = tmp_path / "punctuation.pdf"
    _make_lof_terminal_punct_pdf(
        path, [("Figure 1. Synthetic Missing End", "4"), ("Figure 2. Synthetic Complete End.", "5")]
    )
    _assert_medium(check_pdf_lof_terminal_punctuation(load_pdf_layout(str(path))))


@pytest.mark.parametrize("line_step,entry_step", [(24, 40), (14, 14)])
def test_publication_spacing_is_medium_for_both_spacing_types(tmp_path, line_step, entry_step):
    path = _biosketch(
        tmp_path / "publications.pdf",
        [_entry("Author, A.", lines=3), _entry("Author, B.", lines=3)],
        line_step=line_step,
        entry_step=entry_step,
    )
    _assert_medium(check_pdf_biosketch_publication_layout(load_pdf_layout(str(path))))
