"""Tests for the fail-closed new-review-round gate."""

from __future__ import annotations

from njit_auditor.review_ledger.ground_truth import replay_ledger
from njit_auditor.review_ledger.models import AdjudicationVerdict
from njit_auditor.review_ledger.new_review_gate import check_new_review_gate


def _clean_report():
    case = {
        "case_id": "C1",
        "internal_rule_id": "P900",
        "issue_type": "a",
        "physical_page": 1,
        "thesis_version_id": "TV-1",
    }
    return replay_ledger(
        [case], {"C1": {"verdict": AdjudicationVerdict.FALSE_POSITIVE.value}}, current_findings=[]
    )


def _regressed_report():
    from njit_auditor.review_ledger.ground_truth import CurrentFinding

    case = {
        "case_id": "C1",
        "internal_rule_id": "P900",
        "issue_type": "a",
        "physical_page": 1,
        "thesis_version_id": "TV-1",
    }
    current = [CurrentFinding("TV-1", "P900", "a", 1)]
    return replay_ledger(
        [case],
        {"C1": {"verdict": AdjudicationVerdict.FALSE_POSITIVE.value}},
        current_findings=current,
    )


def test_gate_allows_when_clean() -> None:
    result = check_new_review_gate(_clean_report())
    assert result.allowed is True
    assert result.fp_remaining == 0
    assert result.overridden is False


def test_gate_blocks_when_fp_regression_present() -> None:
    result = check_new_review_gate(_regressed_report())
    assert result.allowed is False
    assert result.fp_remaining == 1
    assert "blocked" in result.reason


def test_gate_is_fail_closed_by_default() -> None:
    """No override argument at all -> blocks, does not silently pass."""
    result = check_new_review_gate(_regressed_report(), override=False)
    assert result.allowed is False


def test_override_without_reason_is_rejected() -> None:
    result = check_new_review_gate(_regressed_report(), override=True, override_reason="")
    assert result.allowed is False


def test_override_with_reason_unblocks_explicitly() -> None:
    result = check_new_review_gate(
        _regressed_report(), override=True, override_reason="known flaky case, tracked in TICKET-1"
    )
    assert result.allowed is True
    assert result.overridden is True
    assert "TICKET-1" in result.reason


def test_override_has_no_effect_when_already_clean() -> None:
    result = check_new_review_gate(_clean_report(), override=True, override_reason="unused")
    assert result.allowed is True
    assert result.overridden is False
