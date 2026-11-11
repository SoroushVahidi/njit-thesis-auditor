"""Tests for scripts/ester_rule_consistency_audit.py helper behavior."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

from njit_auditor.specs.q_rule_coverage import QRuleCoverage

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


def test_matrix_json_matches_tracked_xlsx_including_sections(audit_module):
    xlsx = audit_module.parse_matrix_xlsx(audit_module._MATRIX_XLSX)
    mirror = audit_module.parse_matrix_json(audit_module._Q_MATRIX_JSON)
    assert [item["id"] for item in mirror] == [f"Q{n:03d}" for n in range(1, 80)]
    assert xlsx == mirror
    assert all(item["section"] for item in mirror)


def test_load_matrix_q_rules_prefers_tracked_xlsx(audit_module):
    assert audit_module.matrix_q_source() == audit_module._MATRIX_XLSX
    assert audit_module.load_matrix_q_rules() == audit_module.parse_matrix_xlsx(
        audit_module._MATRIX_XLSX
    )


def test_load_matrix_q_rules_uses_legacy_xlsx_before_json(audit_module, monkeypatch, tmp_path):
    original = audit_module._MATRIX_XLSX
    monkeypatch.setattr(audit_module, "_MATRIX_XLSX", tmp_path / "missing-canonical.xlsx")
    monkeypatch.setattr(audit_module, "_MATRIX_XLSX_LEGACY", original)
    assert audit_module.matrix_q_source() == original
    assert audit_module.load_matrix_q_rules() == audit_module.parse_matrix_xlsx(original)


def test_both_authorities_fall_back_to_json_without_xlsx(audit_module, monkeypatch, tmp_path):
    monkeypatch.setattr(audit_module, "_FORMATTING_XLSX", tmp_path / "formatting.xlsx")
    monkeypatch.setattr(audit_module, "_MATRIX_XLSX", tmp_path / "canonical.xlsx")
    monkeypatch.setattr(audit_module, "_MATRIX_XLSX_LEGACY", tmp_path / "legacy.xlsx")
    assert audit_module.formatting_p_source() == audit_module._P_FEEDBACK_JSON
    assert audit_module.matrix_q_source() == audit_module._Q_MATRIX_JSON
    assert len(audit_module.load_formatting_p_rules()) == 19
    assert len(audit_module.load_matrix_q_rules()) == 79


def test_q029_q074_audit_distinguishes_history_from_effective_authority(
    audit_module, tmp_path,
):
    audit_module.generate_report(tmp_path)
    import csv

    with (tmp_path / "q_rule_consistency.csv").open(newline="", encoding="utf-8") as source:
        rows = {row["Q-rule"]: row for row in csv.DictReader(source)}
    assert rows["Q029"]["Status"] == "superseded by later Ester authority"
    assert "hanging indent" in rows["Q029"]["Matrix question"]
    assert "optional" in rows["Q029"]["Effective current authority"]
    assert rows["Q029"]["Effective implementation status"] == "optional_not_enforced"
    assert rows["Q074"]["Status"] == "superseded by later Ester authority"
    assert "sentence case" in rows["Q074"]["Matrix question"]
    assert "sentence case" in rows["Q074"]["Effective current authority"]
    assert rows["Q074"]["Effective implementation status"] == "partially_implemented"
    assert rows["Q030"]["Status"] == "missing"
    assert rows["Q030"]["Effective implementation status"] == "unimplemented"
    mismatches = json.loads((tmp_path / "mismatch_inventory.json").read_text())
    assert not {"Q029", "Q074"} & {
        row.get("Q-rule") for row in mismatches if row["kind"] == "Q-rule"
    }


@pytest.mark.parametrize(
    "contents",
    [
        "{bad json",
        '{"rules": {}}',
        '{"rules": [{"id": "Q001"}]}',
        '{"metadata": [], "rules": []}',
    ],
)
def test_parse_matrix_json_rejects_malformed_source(audit_module, tmp_path, contents):
    path = tmp_path / "bad-matrix.json"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid Q-matrix JSON"):
        audit_module.parse_matrix_json(path)


def test_missing_all_authority_representations_fails_clearly(audit_module, monkeypatch, tmp_path):
    for name in (
        "_FORMATTING_XLSX",
        "_P_FEEDBACK_JSON",
        "_MATRIX_XLSX",
        "_MATRIX_XLSX_LEGACY",
        "_Q_MATRIX_JSON",
    ):
        monkeypatch.setattr(audit_module, name, tmp_path / name)
    with pytest.raises(FileNotFoundError, match="No P-rule feedback source found"):
        audit_module.load_formatting_p_rules()
    with pytest.raises(FileNotFoundError, match="No YES/NO Q-matrix source found"):
        audit_module.load_matrix_q_rules()


def test_end_to_end_audit_runs_without_local_xlsx_in_separate_process(tmp_path):
    """No private results/ spreadsheet is present or created by the audit."""
    program = """
import importlib.util
import json
import sys
from pathlib import Path
script = Path(sys.argv[1])
scratch = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('ester_rule_consistency_audit', script)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module._FORMATTING_XLSX = scratch / 'results/ester_feedback_raw/formatting_rules.xlsx'
module._MATRIX_XLSX = scratch / 'data/raw/ester/missing-matrix.xlsx'
module._MATRIX_XLSX_LEGACY = scratch / 'results/ester_feedback_raw/yesno_audit_matrix.xlsx'
result = module.generate_report(scratch / 'report')
print(json.dumps({'counts': result['counts'], 'sources': result['selected_authority_sources']}))
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(_SCRIPT_PATH), str(tmp_path)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    summary = json.loads(result.stdout.strip().splitlines()[-1])
    assert summary["counts"]["p_rules_audited"] == 19
    assert summary["counts"]["q_rules_audited"] == 79
    assert summary["counts"]["catalog_p_rules"] > 0
    assert summary["counts"]["public_rule_cards"] > 0
    assert summary["sources"] == {
        "p_rules": "data/specs/ester_p_rule_feedback.json",
        "q_matrix": "data/specs/ester_q_matrix.json",
    }
    report = tmp_path / "report"
    assert (report / "ester_rule_consistency_audit.md").exists()
    assert (report / "p_rule_consistency.csv").exists()
    assert (report / "q_rule_consistency.csv").exists()
    assert (report / "mismatch_inventory.json").exists()
    metadata = json.loads((report / "audit_metadata.json").read_text(encoding="utf-8"))
    assert metadata["selected_authority_sources"] == summary["sources"]
    assert "Checked-in JSON mirror" in (report / "ester_rule_consistency_audit.md").read_text(
        encoding="utf-8"
    )
    assert not (tmp_path / "results/ester_feedback_raw").exists()


def test_parse_formatting_json_includes_p011(audit_module):
    records = audit_module.parse_formatting_json(audit_module._P_FEEDBACK_JSON)
    p011 = next(item for item in records if item["id"] == "P011")
    assert "entirely within the required page margins" in p011["proposed_question"]


def test_load_formatting_p_rules_prefers_present_xlsx(audit_module, monkeypatch, tmp_path):
    path = tmp_path / "formatting_rules.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Rule", "Question", "Proposed question", "Remediation", "Proposed remediation"])
    sheet.append(["P999", "Existing?", "Revised?", "Existing fix.", "Revised fix."])
    workbook.save(path)
    workbook.close()
    monkeypatch.setattr(audit_module, "_FORMATTING_XLSX", path)
    assert audit_module.formatting_p_source() == path
    assert audit_module.load_formatting_p_rules() == audit_module.parse_formatting_xlsx(path)
    assert audit_module.load_formatting_p_rules()[0]["id"] == "P999"


def test_load_formatting_p_rules_falls_back_to_json_without_xlsx(
    audit_module, monkeypatch, tmp_path
):
    missing = tmp_path / "missing-formatting.xlsx"
    monkeypatch.setattr(audit_module, "_FORMATTING_XLSX", missing)
    records = audit_module.load_formatting_p_rules()
    assert any(item["id"] == "P011" for item in records)


def test_load_public_catalog_atomic_fallback_retains_question_and_remediation(audit_module):
    """Regression test for the AtomicSpec.question crash.

    build_implementation_inventory reads spec.question/spec.remediation off
    every entry in public["atomic_specs"]; the fallback stand-in built here
    (used because web_app._ATOMIC_PUBLIC_RULE_CARDS has never existed as a
    module attribute) must actually carry those two fields, not just id/
    parent_rule_id/issue_types/source_q_rule_ids.
    """
    public = audit_module._load_public_catalog()
    atomic_specs = public["atomic_specs"]
    assert atomic_specs, "expected at least one atomic public rule card (e.g. P015A/P018A)"
    for aid, spec in atomic_specs.items():
        assert isinstance(spec.question, str), f"{aid} missing string .question"
        assert isinstance(spec.remediation, str), f"{aid} missing string .remediation"


def test_classify_q_rule_survives_missing_confidence_and_gap_reason_attrs(audit_module):
    """Regression test for the QRuleCoverage.coverage_confidence crash.

    QRuleCoverage has no coverage_confidence or gap_reason field -- neither
    concept is implemented anywhere in the data model. classify_q_rule must
    treat them as absent (falling through to normal comparison logic)
    rather than crashing, for the exact "implemented" status that used to
    trigger the AttributeError.
    """
    coverage = QRuleCoverage(
        q_id="Q999",
        section="Test Section",
        question="Some question",
        automatable=True,
        implementation_status="implemented",
        implementing_p_rules=["P011"],
    )
    ester = {"id": "Q999", "question": "Some question"}
    status, detector, notes = audit_module.classify_q_rule(
        ester, coverage, {}, {"atomic_specs": {}}
    )
    assert status == "aligned"
    assert detector == "P011"


def test_classify_q_rule_raises_for_missing_required_implementation_status(audit_module):
    """The getattr-with-default fix must stay scoped to the two genuinely
    optional/nonexistent fields -- a coverage object missing the real,
    required `implementation_status` field must still fail loudly rather
    than being silently swallowed.
    """
    bare_coverage = type("BareCoverage", (), {"implementing_p_rules": ["P011"]})()
    ester = {"id": "Q999", "question": "Some question"}
    with pytest.raises(AttributeError):
        audit_module.classify_q_rule(ester, bare_coverage, {}, {"atomic_specs": {}})
