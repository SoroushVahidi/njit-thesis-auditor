"""Synthetic (non-private) factories for review-ledger tests.

No real student names, no real dissertation excerpts -- everything here is
invented. Structural attributes (pages, issue types, measurements) are
plausible but arbitrary. This module is imported by test files in this
directory; it is not itself a test file.

Builds one small demonstration scenario end to end: one thesis with two
versions, two auditor runs, one review round, a false-positive case, a
true-violation case, a policy/unresolved case, a superseding adjudication
example, a resolution, a regression result, and history events.
"""

from __future__ import annotations

import datetime as dt

from njit_auditor.report_outputs import public_display_rule_id
from njit_auditor.review_ledger.confidence import normalize_confidence
from njit_auditor.review_ledger.fingerprint import compute_case_fingerprint
from njit_auditor.review_ledger.identifiers import (
    make_adjudication_id,
    make_case_id,
    make_history_event_id,
    make_regression_result_id,
    make_resolution_id,
    make_review_round_id,
    make_run_id,
    make_thesis_id,
    make_thesis_version_id,
)
from njit_auditor.review_ledger.models import (
    Adjudication,
    AdjudicationVerdict,
    AuditorRun,
    HistoryEvent,
    RegressionOutcome,
    RegressionResult,
    Resolution,
    ResolutionStatus,
    ReviewCase,
    ReviewRound,
    Thesis,
    ThesisVersion,
)

SYNTHETIC_EXTERNAL_KEY = "synthetic-student-alpha"
SYNTHETIC_CODE_SHA = "abc123deadbeef"
SYNTHETIC_PDF_SHA256_V1 = "1" * 64
SYNTHETIC_PDF_SHA256_V2 = "2" * 64


def make_synthetic_thesis() -> Thesis:
    return Thesis(
        thesis_id=make_thesis_id(SYNTHETIC_EXTERNAL_KEY),
        display_label="Synthetic Student Alpha",
        active=True,
        notes="Synthetic fixture -- not a real dissertation.",
    )


def make_synthetic_thesis_versions(thesis: Thesis) -> tuple[ThesisVersion, ThesisVersion]:
    v1 = ThesisVersion(
        thesis_version_id=make_thesis_version_id(thesis.thesis_id, SYNTHETIC_PDF_SHA256_V1),
        thesis_id=thesis.thesis_id,
        sha256=SYNTHETIC_PDF_SHA256_V1,
        source_format="pdf",
        page_count=42,
        first_seen_at="2026-01-01T00:00:00+00:00",
        current=False,
    )
    v2 = ThesisVersion(
        thesis_version_id=make_thesis_version_id(thesis.thesis_id, SYNTHETIC_PDF_SHA256_V2),
        thesis_id=thesis.thesis_id,
        sha256=SYNTHETIC_PDF_SHA256_V2,
        source_format="pdf",
        page_count=45,
        first_seen_at="2026-02-01T00:00:00+00:00",
        current=True,
    )
    return v1, v2


def make_synthetic_auditor_run(thesis_version: ThesisVersion) -> AuditorRun:
    return AuditorRun(
        run_id=make_run_id(SYNTHETIC_CODE_SHA),
        thesis_version_id=thesis_version.thesis_version_id,
        code_sha=SYNTHETIC_CODE_SHA,
        executed_at="2026-02-02T00:00:00+00:00",
        tool_metadata={"pymupdf_version": "1.28.2"},
        finding_counts={"P018": 2, "P024": 1},
    )


def make_synthetic_review_round() -> ReviewRound:
    review_date = dt.date(2026, 2, 3)
    return ReviewRound(
        review_round_id=make_review_round_id(review_date, sequence=1),
        prepared_at="2026-02-03T00:00:00+00:00",
        code_sha=SYNTHETIC_CODE_SHA,
        status="prepared",
        included_rule_ids=("P018", "P024"),
        included_thesis_version_ids=(),
        notes="Synthetic fixture round.",
    )


def make_false_positive_case(
    *, review_round: ReviewRound, run: AuditorRun, thesis_version: ThesisVersion
) -> ReviewCase:
    fp = compute_case_fingerprint(
        thesis_version_id=thesis_version.thesis_version_id,
        internal_rule_id="P018",
        issue_type="inconsistent_leader_dots",
        physical_page=11,
        structural_location="table_of_contents:entry_index=1",
        volatile_detail="center_delta_pt=0",
    )
    return ReviewCase(
        case_id=make_case_id(thesis_version.thesis_version_id, "P018", fp.equivalence_key),
        review_round_id=review_round.review_round_id,
        run_id=run.run_id,
        thesis_version_id=thesis_version.thesis_version_id,
        internal_rule_id="P018",
        public_rule_id=public_display_rule_id("P018"),
        issue_type="inconsistent_leader_dots",
        physical_page=11,
        printed_page="ix",
        structural_location="table_of_contents:entry_index=1",
        summary="Entry appears to be missing a leader-dot run.",
        measurement={"has_leader_dots": False},
        confidence=normalize_confidence("medium"),
        evidence_reference="synthetic-evidence-ref-1",
        exact_fingerprint=fp.exact_fingerprint,
        equivalence_key=fp.equivalence_key,
    )


def make_true_violation_case(
    *, review_round: ReviewRound, run: AuditorRun, thesis_version: ThesisVersion
) -> ReviewCase:
    fp = compute_case_fingerprint(
        thesis_version_id=thesis_version.thesis_version_id,
        internal_rule_id="P018D",
        issue_type="inconsistent_leader_dots",
        physical_page=14,
        structural_location="table_of_contents:entry_index=7",
        volatile_detail="center_delta_pt=0",
    )
    return ReviewCase(
        case_id=make_case_id(thesis_version.thesis_version_id, "P018D", fp.equivalence_key),
        review_round_id=review_round.review_round_id,
        run_id=run.run_id,
        thesis_version_id=thesis_version.thesis_version_id,
        internal_rule_id="P018D",
        public_rule_id=public_display_rule_id("P018D"),
        issue_type="inconsistent_leader_dots",
        physical_page=14,
        printed_page="12",
        structural_location="table_of_contents:entry_index=7",
        summary="Entry genuinely lacks a leader-dot run among dotted peers.",
        measurement={"has_leader_dots": False, "peer_dot_ratio": 0.9},
        confidence=normalize_confidence("medium"),
        evidence_reference="synthetic-evidence-ref-2",
        exact_fingerprint=fp.exact_fingerprint,
        equivalence_key=fp.equivalence_key,
    )


def make_policy_case(
    *, review_round: ReviewRound, run: AuditorRun, thesis_version: ThesisVersion
) -> ReviewCase:
    fp = compute_case_fingerprint(
        thesis_version_id=thesis_version.thesis_version_id,
        internal_rule_id="P024",
        issue_type="list_of_tables_title_case",
        physical_page=20,
        structural_location="list_of_tables:entry_index=3",
        volatile_detail="word=example",
    )
    return ReviewCase(
        case_id=make_case_id(thesis_version.thesis_version_id, "P024", fp.equivalence_key),
        review_round_id=review_round.review_round_id,
        run_id=run.run_id,
        thesis_version_id=thesis_version.thesis_version_id,
        internal_rule_id="P024",
        public_rule_id=public_display_rule_id("P024"),
        issue_type="list_of_tables_title_case",
        physical_page=20,
        printed_page="18",
        structural_location="list_of_tables:entry_index=3",
        summary="Possible title-case issue; wording ambiguity unresolved.",
        measurement={},
        confidence=normalize_confidence("low"),
        evidence_reference="synthetic-evidence-ref-3",
        exact_fingerprint=fp.exact_fingerprint,
        equivalence_key=fp.equivalence_key,
    )


def make_adjudication(case: ReviewCase, verdict: AdjudicationVerdict, comment: str) -> Adjudication:
    return Adjudication(
        adjudication_id=make_adjudication_id(),
        case_id=case.case_id,
        reviewer="synthetic-reviewer",
        verdict=verdict,
        reviewer_comment=comment,
        source_reference="synthetic-source-ref",
        decided_at="2026-02-04T00:00:00+00:00",
    )


def make_superseding_adjudication(
    case: ReviewCase, previous: Adjudication, verdict: AdjudicationVerdict, comment: str
) -> Adjudication:
    return Adjudication(
        adjudication_id=make_adjudication_id(),
        case_id=case.case_id,
        reviewer="synthetic-reviewer-2",
        verdict=verdict,
        reviewer_comment=comment,
        source_reference="synthetic-source-ref-followup",
        decided_at="2026-02-10T00:00:00+00:00",
        supersedes_adjudication_id=previous.adjudication_id,
    )


def make_resolution_for_case(case: ReviewCase) -> Resolution:
    return Resolution(
        resolution_id=make_resolution_id(),
        case_id=case.case_id,
        policy_reference=None,
        status=ResolutionStatus.IMPLEMENTED,
        resolution_commit_sha="fix1234",
        implemented_at="2026-02-05T00:00:00+00:00",
        expected_behavior="Finding must no longer be reported for this case.",
    )


def make_regression_result_for_case(
    case: ReviewCase,
    expected: AdjudicationVerdict,
    *,
    actual_present: bool,
    outcome: RegressionOutcome,
) -> RegressionResult:
    return RegressionResult(
        regression_result_id=make_regression_result_id(),
        case_id=case.case_id,
        code_sha="def456regression",
        checked_at="2026-02-06T00:00:00+00:00",
        expected_verdict=expected,
        actual_present=actual_present,
        outcome=outcome,
        notes=None,
    )


def make_history_event(
    *,
    entity_type: str,
    entity_id: str,
    event_type: str,
    previous_state: str | None,
    new_state: str | None,
) -> HistoryEvent:
    return HistoryEvent(
        event_id=make_history_event_id(),
        occurred_at="2026-02-04T00:00:01+00:00",
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        previous_state=previous_state,
        new_state=new_state,
        source_reference="synthetic-source-ref",
        code_sha=SYNTHETIC_CODE_SHA,
        notes=None,
    )
