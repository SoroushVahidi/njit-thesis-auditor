"""Student-facing R037 text follows Ester's continuous Roman sequence ruling."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import _RULE_TEXT_OVERRIDES, audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view

ROOT = Path(__file__).resolve().parents[1]


def test_r037_public_card_and_rules_page_show_continuation() -> None:
    import njit_auditor.web_app as wa

    response = TestClient(wa.app).get("/rules")
    assert response.status_code == 200
    html = response.text.lower()
    assert "biographical sketch page display iv" in html
    assert "continue the lowercase roman numeral sequence" in html
    assert "including continuation pages" in html
    catalog = json.loads((ROOT / "data/processed/rules/project_added_rules.json").read_text())
    rule = next(item for item in catalog if item["id"] == "P037")
    for field in ("question", "rule_definition", "remediation", "notes"):
        assert "fixed njit template slots" not in rule[field].lower()
        assert "dedication (v" not in rule[field].lower()
        assert "acknowledgements vi" not in rule[field].lower()
    assert "continue lowercase Roman numerals by one" in rule["remediation"]
    canonical = _RULE_TEXT_OVERRIDES["P037"]["rule_definition"].lower()
    assert "preceding numbered front-matter page" in canonical
    assert "fixed njit template slots" not in canonical


def test_r037_rendered_finding_agrees_with_detector_sequence() -> None:
    finding = AuditFinding(
        rule_id="P037",
        severity=Severity.WARNING,
        page=8,
        message="Synthetic section numeral mismatch.",
        details={
            "issue_type": "roman_section_wrong_value",
            "section_key": "table_of_contents",
            "observed_sequence": "vii",
            "expected_sequence": "viii",
            "observed_roman": "vii",
            "expected_roman": "viii",
        },
    )
    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    card = view.findings[0]
    for rendered in (
        card.polished_comment,
        card.issue_type_explanation,
        card.detailed_explanation,
        card.suggested_fix,
    ):
        assert "fixed template position" not in rendered.lower()
        assert "fixed roman numeral" not in rendered.lower()
    assert "Biographical Sketch page iv" in card.polished_comment
    assert "preceding front-matter page" in card.detailed_explanation
    assert "next Roman numeral" in card.suggested_fix
    assert card.issue_type_label == "Wrong page-number sequence"
