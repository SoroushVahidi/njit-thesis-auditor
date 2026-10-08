"""Structural checks for the private, target-level Ester replay gate."""

from scripts.ester_judgment_replay import find_unexpected_removals, matches, verify_case


def _raw(rule: str, issue: str, bbox: str) -> dict:
    return {
        "rule_id": rule,
        "page": 11,
        "details": {"issue_type": issue, "bbox": bbox},
    }


def _card(rule: str, issue: str, bbox: list[float], highlight: bool = True) -> dict:
    return {
        "rule_id": rule,
        "page": 11,
        "issue_type": issue,
        "bbox": bbox,
        "has_highlight": highlight,
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
