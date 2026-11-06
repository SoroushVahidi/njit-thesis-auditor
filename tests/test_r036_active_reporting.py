"""Positive R036 capability and the abstentions needed by Ester's acceptances."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from test_rules.test_r036_production_page_relative_spacing import _line, _make_doc

from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.r036_production_page_relative_spacing import run_r036_production


def _spacing_doc(section="table_of_contents", tight_index=3, count=8, tight_pitch=12):
    prefix = {
        "table_of_contents": "1.",
        "list_of_tables": "Table 1.",
        "list_of_figures": "Figure 1.",
    }[section]
    y = 150.0
    lines = []
    for i in range(count):
        if i:
            y += tight_pitch if i == tight_index else 24
        lines.append(
            _line(f"{prefix}{i + 1} Synthetic Entry Title ......... {10 + i}", y, height=10)
        )
    return _make_doc({1: lines}, page_type=section)


@pytest.mark.parametrize("section", ["table_of_contents", "list_of_tables", "list_of_figures"])
def test_genuine_isolated_single_spaced_entry_gap_reports_in_production(section):
    doc = _spacing_doc(section)
    (finding,) = check_pdf_toc_list_entry_spacing(doc)
    assert finding.rule_id == "P036"
    assert finding.page == 1
    assert finding.details["entry_pair_index"] == "2"
    assert finding.details["gap_points"] == "12.0"
    assert finding.details["confidence"] == "medium"
    raw = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    view = build_report_view(raw)
    assert len(view.findings) == 1
    assert view.findings[0].has_highlight
    assert view.findings[0].confidence_level == "medium"


@pytest.mark.parametrize("section", ["table_of_contents", "list_of_tables", "list_of_figures"])
@pytest.mark.parametrize("pitch", [12, 20, 24])
def test_uniform_rhythm_is_not_absolute_line_spacing_evidence(section, pitch):
    doc = _spacing_doc(section)
    for i, block in enumerate(doc.pages[0].text_blocks[1:]):
        line = block.lines[0]
        line.bbox.y0 = 150 + i * pitch
        line.bbox.y1 = line.bbox.y0 + 10
    assert check_pdf_toc_list_entry_spacing(doc) == []


@pytest.mark.parametrize("index", [1, 7])
def test_tight_gap_with_only_one_sided_support_abstains(index):
    assert check_pdf_toc_list_entry_spacing(_spacing_doc(tight_index=index)) == []


def test_sparse_page_and_moderately_tighter_gap_still_abstain():
    assert check_pdf_toc_list_entry_spacing(_spacing_doc(count=4)) == []
    assert check_pdf_toc_list_entry_spacing(_spacing_doc(tight_pitch=17)) == []


def test_diagnostic_suppression_override_does_not_mutate_production_gate():
    doc = _spacing_doc()

    def run(gate):
        return len(run_r036_production(doc, reporting_gate=gate)[0])

    gates = ["strong_multi_signal", "suppression_abstention_only"] * 10
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(run, gates)) == [1, 0] * 10
    assert len(check_pdf_toc_list_entry_spacing(doc)) == 1
