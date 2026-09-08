"""Tests for the ground-truth replay gate. All synthetic dict-shaped
ReviewCase/Adjudication records -- no EsterReviewLedger or real corpus
needed, since replay_ledger is storage-shape agnostic by design."""

from __future__ import annotations

from njit_auditor.review_ledger.ground_truth import CurrentFinding, replay_ledger
from njit_auditor.review_ledger.models import AdjudicationVerdict, RegressionOutcome


def _case(case_id: str, rule_id: str, issue_type: str, page: int, tv: str = "TV-1") -> dict:
    return {
        "case_id": case_id,
        "internal_rule_id": rule_id,
        "issue_type": issue_type,
        "physical_page": page,
        "thesis_version_id": tv,
    }


def _adjudication(verdict: AdjudicationVerdict) -> dict:
    return {"verdict": verdict.value}


def test_false_positive_pass_when_current_finding_absent() -> None:
    case = _case("C1", "P900", "issue_a", 5)
    report = replay_ledger(
        [case],
        {"C1": _adjudication(AdjudicationVerdict.FALSE_POSITIVE)},
        current_findings=[],
    )
    assert report.results[0].outcome == RegressionOutcome.PASS
    assert report.ester_fp_remaining == 0
    assert report.ester_reviewed_fp_total == 1


def test_false_positive_fail_when_current_finding_present() -> None:
    case = _case("C1", "P900", "issue_a", 5)
    current = [CurrentFinding("TV-1", "P900", "issue_a", 5)]
    report = replay_ledger(
        [case], {"C1": _adjudication(AdjudicationVerdict.FALSE_POSITIVE)}, current_findings=current
    )
    assert report.results[0].outcome == RegressionOutcome.FAIL
    assert report.ester_fp_remaining == 1


def test_true_violation_pass_when_current_finding_present() -> None:
    case = _case("C1", "P900", "issue_a", 5)
    current = [CurrentFinding("TV-1", "P900", "issue_a", 5)]
    report = replay_ledger(
        [case], {"C1": _adjudication(AdjudicationVerdict.TRUE_VIOLATION)}, current_findings=current
    )
    assert report.results[0].outcome == RegressionOutcome.PASS
    assert report.ester_tp_missing == 0
    assert report.ester_reviewed_tp_total == 1


def test_true_violation_fail_when_current_finding_absent() -> None:
    case = _case("C1", "P900", "issue_a", 5)
    report = replay_ledger(
        [case], {"C1": _adjudication(AdjudicationVerdict.TRUE_VIOLATION)}, current_findings=[]
    )
    assert report.results[0].outcome == RegressionOutcome.FAIL
    assert report.ester_tp_missing == 1


def test_acceptable_verdict_uses_suppression_semantics() -> None:
    case = _case("C1", "P900", "issue_a", 5)
    current = [CurrentFinding("TV-1", "P900", "issue_a", 5)]
    report = replay_ledger(
        [case], {"C1": _adjudication(AdjudicationVerdict.ACCEPTABLE)}, current_findings=current
    )
    assert report.results[0].outcome == RegressionOutcome.FAIL
    assert report.ester_fp_remaining == 1


def test_unresolved_and_needs_clarification_excluded_from_totals() -> None:
    cases = [_case("C1", "P900", "a", 1), _case("C2", "P900", "b", 2)]
    adjudications = {
        "C1": _adjudication(AdjudicationVerdict.UNRESOLVED),
        "C2": _adjudication(AdjudicationVerdict.NEEDS_CLARIFICATION),
    }
    report = replay_ledger(cases, adjudications, current_findings=[])
    assert report.ester_fp_remaining == 0
    assert report.ester_tp_missing == 0
    assert report.ester_reviewed_fp_total == 0
    assert report.ester_reviewed_tp_total == 0
    assert report.unresolved_policy_cases == 2
    assert all(r.outcome == RegressionOutcome.NOT_APPLICABLE for r in report.results)


def test_policy_guidance_verdict_excluded_from_case_totals() -> None:
    case = _case("C1", "P900", "a", 1)
    report = replay_ledger(
        [case], {"C1": _adjudication(AdjudicationVerdict.POLICY_GUIDANCE)}, current_findings=[]
    )
    assert report.ester_reviewed_fp_total == 0
    assert report.ester_reviewed_tp_total == 0
    assert report.unresolved_policy_cases == 1


def test_case_without_current_adjudication_is_skipped_entirely() -> None:
    case = _case("C1", "P900", "a", 1)
    report = replay_ledger([case], {}, current_findings=[])
    assert report.results == []


def test_wrong_page_does_not_count_as_equivalent() -> None:
    case = _case("C1", "P900", "issue_a", 5)
    current = [CurrentFinding("TV-1", "P900", "issue_a", 6)]  # different page
    report = replay_ledger(
        [case], {"C1": _adjudication(AdjudicationVerdict.FALSE_POSITIVE)}, current_findings=current
    )
    assert report.results[0].outcome == RegressionOutcome.PASS  # not equivalent -> absent -> PASS


def test_wrong_thesis_version_does_not_count_as_equivalent() -> None:
    case = _case("C1", "P900", "issue_a", 5, tv="TV-1")
    current = [CurrentFinding("TV-2", "P900", "issue_a", 5)]  # different thesis version
    report = replay_ledger(
        [case], {"C1": _adjudication(AdjudicationVerdict.TRUE_VIOLATION)}, current_findings=current
    )
    assert report.results[0].outcome == RegressionOutcome.FAIL  # not found for TV-1 -> missing


def test_per_rule_aggregate_metrics() -> None:
    cases = [
        _case("C1", "P900", "a", 1),
        _case("C2", "P900", "b", 2),
        _case("C3", "P901", "c", 3),
    ]
    adjudications = {
        "C1": _adjudication(AdjudicationVerdict.FALSE_POSITIVE),
        "C2": _adjudication(AdjudicationVerdict.FALSE_POSITIVE),
        "C3": _adjudication(AdjudicationVerdict.TRUE_VIOLATION),
    }
    current = [CurrentFinding("TV-1", "P900", "a", 1)]  # C1 regresses
    report = replay_ledger(cases, adjudications, current_findings=current)

    p900 = report.per_rule["P900"]
    assert p900.fp_total == 2
    assert p900.fp_regressions == 1
    assert p900.status == "REGRESSION"

    p901 = report.per_rule["P901"]
    assert p901.tp_total == 1
    assert p901.tp_regressions == 1  # C3's TRUE_VIOLATION absent from current
    assert p901.status == "REGRESSION"
