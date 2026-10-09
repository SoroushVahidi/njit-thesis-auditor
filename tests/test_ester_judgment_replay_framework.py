"""Structural checks for the private, target-level Ester replay gate."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ester_judgment_replay.py"
_SPEC = importlib.util.spec_from_file_location("ester_judgment_replay", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
find_unexpected_removals = _MODULE.find_unexpected_removals
find_disabled_or_retired_emissions = _MODULE.find_disabled_or_retired_emissions
matches = _MODULE.matches
verify_case = _MODULE.verify_case


def _raw(rule: str, issue: str, bbox: str) -> dict:
    return {
        "rule_id": rule,
        "page": 11,
        "details": {"issue_type": issue, "bbox": bbox},
    }


def _card(
    rule: str, issue: str, bbox: list[float], highlight: bool = True, finding_id: str = "f0"
) -> dict:
    return {
        "rule_id": rule,
        "page": 11,
        "issue_type": issue,
        "bbox": bbox,
        "has_highlight": highlight,
        "finding_id": finding_id,
    }


def test_rejected_target_can_coexist_with_another_finding_under_same_rule() -> None:
    selector = {
        "rule_id": "P018",
        "page": 11,
        "issue_types": ["wrapped_title_continuation_misaligned"],
        "target_bbox": [100, 100, 150, 115],
    }
    report = {
        "raw": {"findings": [_raw("P018", selector["issue_types"][0], "100,200,150,215")]},
        "findings": [_card("P018", selector["issue_types"][0], [100, 200, 150, 215])],
    }
    assert not matches(report["raw"]["findings"][0], selector)
    assert verify_case({"judgment": "FP", "target": selector}, report) == []


def test_true_positive_needs_its_own_visible_highlighted_target() -> None:
    selector = {
        "rule_id": "P039",
        "page": 11,
        "issue_types": ["toc_l3_not_indented_relative_to_l2"],
        "target_bbox": [100, 100, 150, 115],
    }
    report = {
        "raw": {"findings": [_raw("P039", selector["issue_types"][0], "100,100,150,115")]},
        "findings": [_card("P039", selector["issue_types"][0], [100, 100, 150, 115], False)],
    }
    errors = verify_case({"judgment": "TP", "target": selector, "highlight_required": True}, report)
    assert errors == ["student card has no highlight"]
    report["findings"][0]["has_highlight"] = True
    assert (
        verify_case({"judgment": "TP", "target": selector, "highlight_required": True}, report)
        == []
    )


def test_unrelated_same_page_card_cannot_satisfy_true_positive() -> None:
    selector = {
        "rule_id": "P039",
        "page": 11,
        "issue_types": ["toc_l3_not_indented_relative_to_l2"],
        "target_bbox": [100, 100, 150, 115],
        "detail_equals": {"entry_index": "3"},
    }
    target = _raw("P039", selector["issue_types"][0], "100,100,150,115")
    target["details"]["entry_index"] = "3"
    other = _raw("P039", selector["issue_types"][0], "100,200,150,215")
    other["details"]["entry_index"] = "4"
    report = {
        "raw": {"findings": [target, other]},
        "findings": [_card("P039", selector["issue_types"][0], [100, 100, 150, 115], True, "f1")],
    }
    errors = verify_case({"judgment": "TP", "target": selector, "highlight_required": True}, report)
    assert "target absent from student cards" in errors
    report["findings"] = [_card("P039", selector["issue_types"][0], [100, 200, 150, 215])]
    errors = verify_case({"judgment": "TP", "target": selector, "highlight_required": True}, report)
    assert "target absent from student cards" in errors


def test_required_subtarget_needs_a_linked_visible_highlight() -> None:
    selector = {"rule_id": "P032", "page": 11, "issue_types": ["wrapped_entry_internal_spacing"]}
    raw = _raw("P032", selector["issue_types"][0], "100,100,150,115")
    raw["details"]["highlight_bboxes"] = "100,100,150,115"
    report = {
        "raw": {"findings": [raw]},
        "findings": [_card("P032", selector["issue_types"][0], [100, 200, 150, 215])],
    }
    errors = verify_case(
        {
            "judgment": "REVIEWER_VIOLATION",
            "target": selector,
            "highlight_required": True,
            "required_highlight_targets": [[100, 100, 150, 115]],
        },
        report,
    )
    assert "required highlighted subtarget absent" in errors


def test_other_corpus_findings_cannot_disappear_without_an_explicit_allowance() -> None:
    old = _card("P011", "margin_boundary_violation", [100, 100, 150, 115])
    baseline = {"Synthetic": {"findings": [old]}}
    current = {"Synthetic": {"findings": []}}
    assert find_unexpected_removals({}, baseline, current)
    allowance = {
        "allowed_removed": [
            {
                "document": "Synthetic",
                "target": {
                    "rule_id": "P011",
                    "page": 11,
                    "issue_types": ["margin_boundary_violation"],
                    "target_bbox": [100, 100, 150, 115],
                },
            }
        ]
    }
    assert find_unexpected_removals(allowance, baseline, current) == []


def test_issue_substitution_and_duplicate_loss_are_reported() -> None:
    old = _raw("P017", "unexpected_terminal_period", "100,100,150,115")
    new_issue = _raw("P017", "possible_title_case_issue", "100,100,150,115")
    baseline = {"Synthetic": {"findings": [old]}}
    current = {"Synthetic": {"findings": [new_issue]}}
    result = find_unexpected_removals({}, baseline, current)
    assert len(result) == 1
    assert result[0]["issue_type"] == "unexpected_terminal_period"

    baseline = {"Synthetic": {"findings": [old, dict(old)]}}
    current = {"Synthetic": {"findings": [old]}}
    assert len(find_unexpected_removals({}, baseline, current)) == 1


def test_retired_issue_stays_silent_without_disabling_other_issues() -> None:
    cases = [
        {
            "judgment": "FP",
            "disposition": "retired",
            "target": {"rule_id": "P068", "issue_types": ["approval_page_signature_blocks_sparse"]},
        }
    ]
    other = _raw("P068", "advisor_role_label_missing", "100,100,150,115")
    retired = _raw("P068", "approval_page_signature_blocks_sparse", "100,200,150,215")
    reports = {"Synthetic": {"raw": {"findings": [other]}}}
    assert find_disabled_or_retired_emissions(cases, reports) == []
    reports["Synthetic"]["raw"]["findings"].append(retired)
    assert find_disabled_or_retired_emissions(cases, reports)
