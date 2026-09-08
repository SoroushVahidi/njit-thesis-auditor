"""Serialization roundtrip and validation tests for review-ledger models."""

from __future__ import annotations

from njit_auditor.review_ledger.models import (
    Adjudication,
    AdjudicationVerdict,
    AuditorRun,
    ConfidenceLevel,
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

from .fixtures import (
    make_adjudication,
    make_false_positive_case,
    make_history_event,
    make_regression_result_for_case,
    make_resolution_for_case,
    make_synthetic_auditor_run,
    make_synthetic_review_round,
    make_synthetic_thesis,
    make_synthetic_thesis_versions,
)


def test_thesis_roundtrip() -> None:
    thesis = make_synthetic_thesis()
    assert Thesis.from_dict(thesis.to_dict()) == thesis


def test_thesis_version_roundtrip() -> None:
    thesis = make_synthetic_thesis()
    v1, _v2 = make_synthetic_thesis_versions(thesis)
    assert ThesisVersion.from_dict(v1.to_dict()) == v1


def test_auditor_run_roundtrip() -> None:
    thesis = make_synthetic_thesis()
    _v1, v2 = make_synthetic_thesis_versions(thesis)
    run = make_synthetic_auditor_run(v2)
    assert AuditorRun.from_dict(run.to_dict()) == run


def test_review_round_roundtrip() -> None:
    round_ = make_synthetic_review_round()
    assert ReviewRound.from_dict(round_.to_dict()) == round_


def test_review_case_roundtrip() -> None:
    thesis = make_synthetic_thesis()
    _v1, v2 = make_synthetic_thesis_versions(thesis)
    run = make_synthetic_auditor_run(v2)
    round_ = make_synthetic_review_round()
    case = make_false_positive_case(review_round=round_, run=run, thesis_version=v2)
    assert ReviewCase.from_dict(case.to_dict()) == case
    assert case.confidence == ConfidenceLevel.MEDIUM


def test_adjudication_roundtrip() -> None:
    thesis = make_synthetic_thesis()
    _v1, v2 = make_synthetic_thesis_versions(thesis)
    run = make_synthetic_auditor_run(v2)
    round_ = make_synthetic_review_round()
    case = make_false_positive_case(review_round=round_, run=run, thesis_version=v2)
    adjudication = make_adjudication(case, AdjudicationVerdict.FALSE_POSITIVE, "not a real issue")
    assert Adjudication.from_dict(adjudication.to_dict()) == adjudication


def test_resolution_roundtrip() -> None:
    thesis = make_synthetic_thesis()
    _v1, v2 = make_synthetic_thesis_versions(thesis)
    run = make_synthetic_auditor_run(v2)
    round_ = make_synthetic_review_round()
    case = make_false_positive_case(review_round=round_, run=run, thesis_version=v2)
    resolution = make_resolution_for_case(case)
    assert Resolution.from_dict(resolution.to_dict()) == resolution
    assert resolution.status == ResolutionStatus.IMPLEMENTED


def test_resolution_can_reference_a_policy_instead_of_a_case() -> None:
    resolution = Resolution(
        resolution_id="RES-test",
        case_id=None,
        policy_reference="R055-table-figure-prefix-policy",
        status=ResolutionStatus.IMPLEMENTED,
        resolution_commit_sha="abc123",
        implemented_at="2026-02-05T00:00:00+00:00",
        expected_behavior="Numeric-only LoT/LoF entries are flagged.",
    )
    assert Resolution.from_dict(resolution.to_dict()) == resolution


def test_regression_result_roundtrip() -> None:
    thesis = make_synthetic_thesis()
    _v1, v2 = make_synthetic_thesis_versions(thesis)
    run = make_synthetic_auditor_run(v2)
    round_ = make_synthetic_review_round()
    case = make_false_positive_case(review_round=round_, run=run, thesis_version=v2)
    result = make_regression_result_for_case(
        case,
        AdjudicationVerdict.FALSE_POSITIVE,
        actual_present=False,
        outcome=RegressionOutcome.PASS,
    )
    assert RegressionResult.from_dict(result.to_dict()) == result


def test_history_event_roundtrip() -> None:
    event = make_history_event(
        entity_type="ReviewCase",
        entity_id="CASE-test",
        event_type="case_created",
        previous_state=None,
        new_state="prepared",
    )
    assert HistoryEvent.from_dict(event.to_dict()) == event


def test_models_are_frozen() -> None:
    thesis = make_synthetic_thesis()
    try:
        thesis.display_label = "mutated"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("Thesis must be immutable (frozen dataclass)")
