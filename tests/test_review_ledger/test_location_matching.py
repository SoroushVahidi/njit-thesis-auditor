"""Anchor-aware replay preserves distinct verdicts within one coarse page key."""

from __future__ import annotations

from njit_auditor.review_ledger.fingerprint import compute_case_fingerprint
from njit_auditor.review_ledger.ground_truth import (
    CurrentFinding,
    MatchStatus,
    anchor_from_details,
    replay_ledger,
)
from njit_auditor.review_ledger.identifiers import make_case_id, make_thesis_id
from njit_auditor.review_ledger.importers.known_cases import KNOWN_HISTORICAL_CASES
from njit_auditor.review_ledger.locators import (
    LOCATOR_VERSION,
    CaseLocator,
    locators_for_review_cases,
)
from njit_auditor.review_ledger.models import RegressionOutcome
from njit_auditor.review_ledger.new_review_gate import check_new_review_gate


def _case(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "thesis_version_id": "TV-1",
        "internal_rule_id": "P015",
        "issue_type": "missing_later_indent",
        "physical_page": 101,
    }


def _finding(y: float | None, role: str | None = None) -> CurrentFinding:
    return CurrentFinding("TV-1", "P015", "missing_later_indent", 101, 108.4, y, role)


def _locator(case_id: str, y: float, role: str | None = None) -> CaseLocator:
    return CaseLocator(case_id, LOCATOR_VERSION, "tests/source.md", 108.4, y, role)


def _verdicts() -> dict[str, dict]:
    return {"old": {"verdict": "FALSE_POSITIVE"}, "true": {"verdict": "TRUE_VIOLATION"}}


def test_opposite_verdicts_with_two_same_page_findings_match_one_to_one() -> None:
    report = replay_ledger(
        [_case("old"), _case("true")],
        _verdicts(),
        [_finding(376.1, "paragraph_continuation"), _finding(352.2, "paragraph_start")],
        {"old": _locator("old", 376.1, "paragraph_continuation"),
         "true": _locator("true", 352.2, "paragraph_start")},
    )
    assert [r.match_status for r in report.results] == [MatchStatus.MATCHED, MatchStatus.MATCHED]
    assert [r.outcome for r in report.results] == [RegressionOutcome.FAIL, RegressionOutcome.PASS]


def test_youra_old_false_positive_absent_and_real_paragraph_start_present() -> None:
    old, true = (
        next(
            case for case in KNOWN_HISTORICAL_CASES
            if case.document_short_name == "Youra"
            and case.physical_page == 101
            and case.verdict.value == verdict
        )
        for verdict in ("FALSE_POSITIVE", "TRUE_VIOLATION")
    )
    version = "TV-e2a71ddf74e2"
    cases = []
    adjudications = {}
    for known in (old, true):
        fp = compute_case_fingerprint(
            thesis_version_id=version,
            internal_rule_id=known.internal_rule_id,
            issue_type=known.issue_type,
            physical_page=known.physical_page,
            structural_location=known.structural_location,
            volatile_detail=known.volatile_detail,
        )
        case_id = make_case_id(version, known.internal_rule_id, fp.equivalence_key)
        cases.append({**_case(case_id), "thesis_version_id": version})
        adjudications[case_id] = {"verdict": known.verdict.value}
    assert cases[0]["case_id"] == "CASE-c9ef781649a8"
    assert cases[1]["case_id"] != cases[0]["case_id"]
    locators = locators_for_review_cases(cases, {version: make_thesis_id("Youra")})
    assert len(locators) == 2
    current = CurrentFinding(version, "P015", "missing_later_indent", 101, 108.4, 352.2)
    report = replay_ledger(cases, adjudications, [current], locators)
    assert [r.match_status for r in report.results] == [MatchStatus.ABSENT, MatchStatus.MATCHED]
    assert [r.outcome for r in report.results] == [RegressionOutcome.PASS, RegressionOutcome.PASS]
    assert report.ester_fp_remaining == report.ester_tp_missing == 0


def test_locator_does_not_cross_thesis_versions_of_different_documents() -> None:
    known = next(
        case for case in KNOWN_HISTORICAL_CASES
        if case.document_short_name == "Youra"
        and case.physical_page == 101
        and case.verdict.value == "FALSE_POSITIVE"
    )
    other_version = "TV-other"
    fingerprint = compute_case_fingerprint(
        thesis_version_id=other_version,
        internal_rule_id=known.internal_rule_id,
        issue_type=known.issue_type,
        physical_page=known.physical_page,
        structural_location=known.structural_location,
        volatile_detail=known.volatile_detail,
    )
    other_id = make_case_id(other_version, known.internal_rule_id, fingerprint.equivalence_key)
    other_case = {**_case(other_id), "thesis_version_id": other_version}
    assert locators_for_review_cases(
        [other_case], {other_version: make_thesis_id("Philip")}
    ) == {}


def test_small_drift_matches_but_large_difference_does_not() -> None:
    case = _case("old")
    locator = {"old": _locator("old", 376.1)}
    adjudication = {"old": {"verdict": "FALSE_POSITIVE"}}
    near = replay_ledger([case], adjudication, [_finding(379.0)], locator)
    far = replay_ledger([case], adjudication, [_finding(352.2)], locator)
    assert near.results[0].match_status == MatchStatus.MATCHED
    assert far.results[0].match_status == MatchStatus.ABSENT
    assert near.results[0].outcome == RegressionOutcome.FAIL
    assert far.results[0].outcome == RegressionOutcome.PASS


def test_two_plausible_findings_abstain_and_block_gate() -> None:
    report = replay_ledger(
        [_case("old")],
        {"old": {"verdict": "FALSE_POSITIVE"}},
        [_finding(376.1), _finding(378.0)],
        {"old": _locator("old", 376.1)},
    )
    assert report.results[0].match_status == MatchStatus.IDENTITY_AMBIGUOUS
    assert report.results[0].outcome == RegressionOutcome.NOT_APPLICABLE
    assert report.identity_ambiguous_cases == 1
    assert report.unresolved_policy_cases == 0
    assert not check_new_review_gate(report).allowed


def test_two_historical_cases_cannot_claim_one_finding() -> None:
    report = replay_ledger(
        [_case("old"), _case("true")],
        _verdicts(),
        [_finding(376.1)],
        {"old": _locator("old", 376.1), "true": _locator("true", 377.0)},
    )
    assert all(r.match_status == MatchStatus.IDENTITY_AMBIGUOUS for r in report.results)
    assert report.identity_ambiguous_cases == 2


def test_legacy_unique_pair_matches_but_multiple_findings_abstain() -> None:
    case = _case("old")
    adjudication = {"old": {"verdict": "FALSE_POSITIVE"}}
    unique = replay_ledger([case], adjudication, [_finding(376.1)])
    multiple = replay_ledger([case], adjudication, [_finding(376.1), _finding(352.2)])
    assert unique.results[0].match_status == MatchStatus.MATCHED
    assert multiple.results[0].match_status == MatchStatus.IDENTITY_AMBIGUOUS


def test_missing_current_coordinate_abstains_for_located_case() -> None:
    report = replay_ledger(
        [_case("old")],
        {"old": {"verdict": "FALSE_POSITIVE"}},
        [_finding(None)],
        {"old": _locator("old", 376.1)},
    )
    assert report.results[0].match_status == MatchStatus.IDENTITY_AMBIGUOUS


def test_role_and_x_mismatch_prevent_cross_match() -> None:
    current = CurrentFinding(
        "TV-1", "P015", "missing_later_indent", 101, 300.0, 376.1, "paragraph_start"
    )
    report = replay_ledger(
        [_case("old")],
        {"old": {"verdict": "FALSE_POSITIVE"}},
        [current],
        {"old": _locator("old", 376.1, "paragraph_continuation")},
    )
    assert report.results[0].match_status == MatchStatus.ABSENT


def test_bbox_anchor_parsing_uses_only_finite_coordinates() -> None:
    assert anchor_from_details({"bbox": "108.4,352.2,365.4,364.2"}) == (108.4, 352.2)
    assert anchor_from_details({"bbox": "nan,352.2,365.4,364.2"}) == (None, None)
    assert anchor_from_details({"bbox": "invalid"}) == (None, None)
