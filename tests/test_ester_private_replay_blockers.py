"""Direct regressions for Ester private replay blockers.

These tests intentionally assert only structural metadata: rule, issue type,
page, and public wording. They do not quote dissertation body text.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.latex_abstract import MS_WORD_LIMIT, PHD_WORD_LIMIT
from njit_auditor.web_samples import get_builtin_sample

PRANEETH_PRIVATE_PDF = Path(
    "data/evaluation/private/Praneeth Ivan Joel. FNU_3rd review draft.pdf"
)
_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    not PRANEETH_PRIVATE_PDF.exists(),
    reason="private Praneeth dissertation fixture is not available",
)
def test_praneeth_r024_page14_reviewed_title_case_false_positive_suppressed() -> None:
    findings = run_pdf_audit_full(PRANEETH_PRIVATE_PDF)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p024_title_case_page14 = [
        f
        for f in view.findings
        if f.rule_id == "P024"
        and f.page == 14
        and f.issue_type == "list_of_tables_title_case"
    ]

    assert p024_title_case_page14 == []


def test_sample_b_p015_page23_reviewed_continuation_false_positive_suppressed() -> None:
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        pytest.skip("Sample B fixture is not available")

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    page_23 = [f for f in view.findings if f.rule_id == "P015" and f.page == 23]
    assert page_23 == []

    reviewed_fps = {24, 26, 27, 38}
    p015_pages = {f.page for f in view.findings if f.rule_id == "P015"}
    assert p015_pages.isdisjoint(reviewed_fps)


def test_sample_b_p020_page80_owned_as_table_title_not_generic_heading() -> None:
    sample = get_builtin_sample("ester_sample_b")
    if not sample.abs_path.exists():
        pytest.skip("Sample B fixture is not available")

    findings = run_pdf_audit_full(sample.abs_path)
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))

    p020_page80 = [f for f in view.findings if f.rule_id == "P020" and f.page == 80]
    assert p020_page80 == []

    p017_page80 = [f for f in view.findings if f.rule_id == "P017" and f.page == 80]
    # Ester named two issues on this table title: title case, and the period
    # it ends with ("table titles do not end in periods").
    assert sorted(f.issue_type for f in p017_page80) == [
        "possible_title_case_issue",
        "unexpected_terminal_period",
    ]
    finding = next(f for f in p017_page80 if f.issue_type == "possible_title_case_issue")

    surfaces = " ".join(
        [
            finding.polished_comment,
            finding.detailed_explanation,
            finding.suggested_fix or "",
        ]
    ).lower()
    assert "table title" in surfaces
    assert "heading" not in surfaces
    assert "figure" not in surfaces
    assert "period" in surfaces
    assert "prepositions" in surfaces or "conjunctions" in surfaces

    assert [f for f in view.findings if f.rule_id == "P020" and f.page == 71] == []


def test_p021_public_rule_registry_uses_current_ester_limits() -> None:
    rules = json.loads((_REPO_ROOT / "data/processed/rules/project_added_rules.json").read_text())
    p021 = next(rule for rule in rules if rule["id"] == "P021")

    current_text = f"{p021['rule_definition']} {p021['remediation']}"
    assert "400" in current_text
    assert "200" in current_text
    assert "350" not in current_text
    assert "150" not in current_text
    assert PHD_WORD_LIMIT == 400
    assert MS_WORD_LIMIT == 200

    architecture = (_REPO_ROOT / "docs/RULE_ARCHITECTURE.md").read_text()
    assert "PhD ≤400, MS ≤200" in architecture
    assert "PhD ≤350, MS ≤150" not in architecture
