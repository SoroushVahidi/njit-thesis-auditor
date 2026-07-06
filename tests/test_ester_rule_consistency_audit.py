"""Tests for scripts/ester_rule_consistency_audit.py helper behavior."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "ester_rule_consistency_audit.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("ester_rule_consistency_audit", _SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit_module():
    return _load_audit_module()


def test_p026_detector_public_contradiction_aligned_when_cmr_accepted(audit_module, monkeypatch):
    public = {
        "by_id": {
            "P026A": {
                "question": "Does the body text use an accepted font family?",
                "remediation": (
                    "Use Times New Roman or Arial in Word, or Computer Modern / "
                    "Latin Modern in Overleaf."
                ),
            }
        }
    }
    result = audit_module._p026_detector_public_contradiction(public)
    assert result["status"] == "aligned"
    assert result["detector_flags_cmr"] == "False"
    assert "contradiction" not in result["detail"].lower()


def test_ester_priority_review_font_section_derives_from_mismatch_check(audit_module):
    p026_contradiction = {
        "status": "aligned",
        "detail": (
            "P026A/P026B split is in place. Public P026A cites Times/Arial (Word) and "
            "Computer Modern/Latin Modern (Overleaf); pdf_font_compliance.py accepts "
            "those families without emitting possible_body_font_family_issue."
        ),
    }
    public = {
        "atomic_specs": {
            "P026A": type("Spec", (), {"id": "P026A", "parent_rule_id": "P026"})(),
            "P026B": type("Spec", (), {"id": "P026B", "parent_rule_id": "P026"})(),
        }
    }
    findings = audit_module._ester_priority_review([], public, [], {}, p026_contradiction)
    font_section = next(item for item in findings if item["area"].startswith("C. Font rules"))
    assert font_section["status"] == "aligned"
    assert "still flags" not in font_section["detail"].lower()
    assert "contradiction" not in font_section["status"]


def test_load_matrix_q_rules_uses_tracked_repo_xlsx(audit_module):
    rules = audit_module.load_matrix_q_rules()
    assert any(rule["id"] == "Q060" for rule in rules)


def test_parse_formatting_json_includes_p011(audit_module):
    records = audit_module.parse_formatting_json(audit_module._P_FEEDBACK_JSON)
    p011 = next(item for item in records if item["id"] == "P011")
    assert "entirely within the required page margins" in p011["proposed_question"]


def test_load_formatting_p_rules_falls_back_to_json_without_xlsx(
    audit_module, monkeypatch, tmp_path
):
    missing = tmp_path / "missing-formatting.xlsx"
    monkeypatch.setattr(audit_module, "_FORMATTING_XLSX", missing)
    records = audit_module.load_formatting_p_rules()
    assert any(item["id"] == "P011" for item in records)
