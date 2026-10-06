"""Tests for the ground-truth replay gate. All synthetic dict-shaped
ReviewCase/Adjudication records -- no EsterReviewLedger or real corpus
needed, since replay_ledger is storage-shape agnostic by design."""

from __future__ import annotations

from njit_auditor.review_ledger.ground_truth import (
    CurrentFinding,
    qualify_issue_type,
    replay_ledger,
)
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


def test_qualify_issue_type_p011_discriminates_by_side() -> None:
    """Regression guard for the real collision found during migration: a
    reviewed right-margin FP and an unrelated bottom-margin finding on the
    same page must not be treated as equivalent."""
    right = qualify_issue_type("P011", "margin_boundary_violation", {"side": "right_margin"})
    bottom = qualify_issue_type("P011", "margin_boundary_violation", {"side": "bottom_margin"})
    assert right != bottom
    assert right == "margin_boundary_violation:right_margin"


def test_qualify_issue_type_p024_discriminates_by_flagged_word() -> None:
    casein = qualify_issue_type(
        "P024",
        "list_of_tables_title_case",
        {},
        "List of Tables entry may have title-case issue: 'casein' may need to be capitalized.",
    )
    peptide = qualify_issue_type(
        "P024",
        "list_of_tables_title_case",
        {},
        "List of Tables entry may have title-case issue: 'peptide' may need to be capitalized.",
    )
    assert casein != peptide
    assert casein == "list_of_tables_title_case:casein"


def test_qualify_issue_type_falls_back_when_no_discriminator_available() -> None:
    """A rule with no configured discriminator, or one where the expected
    field/message pattern is missing, must return the plain issue_type
    rather than raising or silently dropping the finding."""
    assert qualify_issue_type("P900", "some_issue", {}) == "some_issue"
    assert (
        qualify_issue_type("P011", "margin_boundary_violation", {}) == "margin_boundary_violation"
    )
    assert (
        qualify_issue_type("P024", "list_of_tables_title_case", {}, "no quoted word here")
        == "list_of_tables_title_case"
    )


def test_nuanced_correct_but_root_cause_elsewhere_does_not_force_tp_requirement() -> None:
    """Mirrors how the R028/Patrick case was first migrated (later
    superseded by FALSE_POSITIVE): Ester marked something 'CORRECT'
    but explained the actual defect's responsibility sits with a different
    rule. Migrated as NEEDS_CLARIFICATION, this must be excluded from
    pass/fail scoring entirely -- never scored as a missing TRUE_VIOLATION
    for the rule that no longer owns the defect, and never silently
    counted as a clean FALSE_POSITIVE either."""
    case = _case("C1", "P028", "page_number_regime", 13)
    report = replay_ledger(
        [case],
        {"C1": _adjudication(AdjudicationVerdict.NEEDS_CLARIFICATION)},
        current_findings=[],  # P028 does not currently fire here -- irrelevant either way
    )
    assert report.results[0].outcome == RegressionOutcome.NOT_APPLICABLE
    assert report.ester_reviewed_fp_total == 0
    assert report.ester_reviewed_tp_total == 0
    assert report.ester_fp_remaining == 0
    assert report.ester_tp_missing == 0
    assert report.unresolved_policy_cases == 1
    assert report.per_rule["P028"].status == "PARTIAL"


def test_p011_side_discrimination_prevents_false_regression_in_replay() -> None:
    """End-to-end: without qualify_issue_type, an unrelated bottom-margin
    finding on the same page as a reviewed right-margin FP would report a
    false FP_REGRESSION. With it applied consistently to both the case and
    the current finding, the reviewed case correctly PASSes."""
    case = {
        "case_id": "C1",
        "internal_rule_id": "P011",
        "issue_type": qualify_issue_type(
            "P011", "margin_boundary_violation", {"side": "right_margin"}
        ),
        "physical_page": 56,
        "thesis_version_id": "TV-1",
    }
    unrelated_current = CurrentFinding(
        "TV-1",
        "P011",
        qualify_issue_type("P011", "margin_boundary_violation", {"side": "bottom_margin"}),
        56,
    )
    report = replay_ledger(
        [case],
        {"C1": {"verdict": AdjudicationVerdict.FALSE_POSITIVE.value}},
        current_findings=[unrelated_current],
    )
    assert report.results[0].outcome == RegressionOutcome.PASS
