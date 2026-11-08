"""Synthetic spacing capability must not bypass the real-positive reporting gate."""

import pytest
from test_rules.test_r036_production_page_relative_spacing import _line, _make_doc

from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.r036_production_page_relative_spacing import (
    PRODUCTION_REPORTING_GATE,
    run_r036_production,
)


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
def test_synthetic_positive_does_not_authorize_production_reporting(section):
    doc = _spacing_doc(section)
    # The diagnostic comparator can emit, but synthetic evidence cannot satisfy
    # the real independently validated positive required by the production gate.
    findings, _ = run_r036_production(doc, reporting_gate="strong_multi_signal")
    assert findings
    assert all(f.rule_id == "P036" for f in findings)
    assert PRODUCTION_REPORTING_GATE == "suppression_abstention_only"
    assert check_pdf_toc_list_entry_spacing(doc) == []
