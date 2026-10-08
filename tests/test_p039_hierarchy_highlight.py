"""P039 highlights the TOC entries that lack hierarchy indentation.

Ester confirmed a P039 finding (level-3 TOC entries not indented) and asked why
the auditor was not highlighting the errors. The finding now carries one
highlight box per offending child entry.
"""

from __future__ import annotations

from pathlib import Path

from test_pdf_rules import _make_toc_hierarchy_pdf

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_toc_entry_hierarchy import check_pdf_toc_entry_hierarchy


def _p039(path: Path) -> list:
    return [f for f in check_pdf_toc_entry_hierarchy(load_pdf_layout(str(path))) if f.rule_id == "P039"]


def test_level3_finding_highlights_each_unindented_level3_entry(tmp_path: Path) -> None:
    pdf = tmp_path / "toc.pdf"
    _make_toc_hierarchy_pdf(pdf, l1_x=72.0, l2_x=90.0, l3_x=90.0, l3_count=2)
    (finding,) = [f for f in _p039(pdf) if f.details["issue_type"] == "toc_l3_not_indented_relative_to_l2"]
    boxes = parse_highlight_bboxes_from_details(finding.details)
    # 2 chapters x 2 level-2 entries x 2 level-3 entries
    assert len(boxes) == 8 == int(finding.details["offending_entry_count"])
    assert all(abs(box[0] - 90.0) < 3.0 for box in boxes)
    assert finding.details["bbox"]


def test_level2_finding_highlights_unindented_level2_entries(tmp_path: Path) -> None:
    pdf = tmp_path / "toc.pdf"
    _make_toc_hierarchy_pdf(pdf, l1_x=72.0, l2_x=72.0)
    (finding,) = [f for f in _p039(pdf) if f.details["issue_type"] == "toc_l2_not_indented_relative_to_l1"]
    assert len(parse_highlight_bboxes_from_details(finding.details)) == 4


def test_correctly_indented_toc_still_has_no_finding(tmp_path: Path) -> None:
    pdf = tmp_path / "toc.pdf"
    _make_toc_hierarchy_pdf(pdf, l1_x=72.0, l2_x=90.0, l3_x=108.0, l3_count=2)
    assert _p039(pdf) == []
