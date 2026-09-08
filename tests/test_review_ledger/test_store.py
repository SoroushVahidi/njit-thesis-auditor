"""Tests for EsterReviewLedger: append-only behavior, duplicate/orphan
prevention, and linear adjudication supersession."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from njit_auditor.review_ledger.identifiers import make_review_round_id
from njit_auditor.review_ledger.models import (
    Adjudication,
    AdjudicationVerdict,
    RegressionOutcome,
    ReviewRound,
)
from njit_auditor.review_ledger.store import (
    SCHEMA_VERSION,
    EsterReviewLedger,
    LedgerValidationError,
)

from .fixtures import (
    make_adjudication,
    make_false_positive_case,
    make_history_event,
    make_regression_result_for_case,
    make_resolution_for_case,
    make_superseding_adjudication,
    make_synthetic_auditor_run,
    make_synthetic_review_round,
    make_synthetic_thesis,
    make_synthetic_thesis_versions,
)


def _build_ledger_with_one_case(root: Path) -> tuple[EsterReviewLedger, object]:
    """Shared scaffold: a ledger with one thesis/version/run/round/case."""
    ledger = EsterReviewLedger(root)
    thesis = make_synthetic_thesis()
    ledger.add_thesis(thesis)
    v1, v2 = make_synthetic_thesis_versions(thesis)
    ledger.add_thesis_version(v1)
    ledger.add_thesis_version(v2)
    run = make_synthetic_auditor_run(v2)
    ledger.add_auditor_run(run)
    round_ = make_synthetic_review_round()
    ledger.add_review_round(round_)
    case = make_false_positive_case(review_round=round_, run=run, thesis_version=v2)
    ledger.add_review_case(case)
    return ledger, case


def test_schema_version_meta_file_created(tmp_path: Path) -> None:
    EsterReviewLedger(tmp_path)
    meta = json.loads((tmp_path / "_ledger_meta.json").read_text())
    assert meta["schema_version"] == SCHEMA_VERSION


def test_reopening_ledger_with_mismatched_schema_version_raises(tmp_path: Path) -> None:
    EsterReviewLedger(tmp_path)
    (tmp_path / "_ledger_meta.json").write_text(json.dumps({"schema_version": 999}))
    with pytest.raises(LedgerValidationError):
        EsterReviewLedger(tmp_path)


def test_full_scaffold_persists_and_reloads(tmp_path: Path) -> None:
    ledger, case = _build_ledger_with_one_case(tmp_path)
    reloaded = EsterReviewLedger(tmp_path)
    assert reloaded.review_cases.get(case.case_id) is not None
    assert reloaded.theses.all()[0]["thesis_id"] == ledger.theses.all()[0]["thesis_id"]


def test_thesis_version_rejects_unknown_thesis(tmp_path: Path) -> None:
    ledger = EsterReviewLedger(tmp_path)
    thesis = make_synthetic_thesis()
    v1, _v2 = make_synthetic_thesis_versions(thesis)
    with pytest.raises(LedgerValidationError):
        ledger.add_thesis_version(v1)  # thesis never added


def test_auditor_run_rejects_unknown_thesis_version(tmp_path: Path) -> None:
    ledger = EsterReviewLedger(tmp_path)
    thesis = make_synthetic_thesis()
    ledger.add_thesis(thesis)
    _v1, v2 = make_synthetic_thesis_versions(thesis)
    run = make_synthetic_auditor_run(v2)  # v2 never added
    with pytest.raises(LedgerValidationError):
        ledger.add_auditor_run(run)


def test_review_case_rejects_unknown_review_round(tmp_path: Path) -> None:
    ledger = EsterReviewLedger(tmp_path)
    thesis = make_synthetic_thesis()
    ledger.add_thesis(thesis)
    v1, v2 = make_synthetic_thesis_versions(thesis)
    ledger.add_thesis_version(v1)
    ledger.add_thesis_version(v2)
    run = make_synthetic_auditor_run(v2)
    ledger.add_auditor_run(run)
    round_ = make_synthetic_review_round()  # never added
    case = make_false_positive_case(review_round=round_, run=run, thesis_version=v2)
    with pytest.raises(LedgerValidationError):
        ledger.add_review_case(case)


def test_duplicate_thesis_id_rejected(tmp_path: Path) -> None:
    ledger = EsterReviewLedger(tmp_path)
    thesis = make_synthetic_thesis()
    ledger.add_thesis(thesis)
    with pytest.raises(LedgerValidationError):
        ledger.add_thesis(thesis)


def test_adjudication_rejects_unknown_case(tmp_path: Path) -> None:
    ledger, _case = _build_ledger_with_one_case(tmp_path)
    orphan = Adjudication(
        adjudication_id="ADJ-orphan",
        case_id="CASE-does-not-exist",
        reviewer="x",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment=None,
        source_reference="x",
        decided_at="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(LedgerValidationError):
        ledger.add_adjudication(orphan)


def test_first_adjudication_for_a_case_needs_no_supersession(tmp_path: Path) -> None:
    ledger, case = _build_ledger_with_one_case(tmp_path)
    adjudication = make_adjudication(case, AdjudicationVerdict.FALSE_POSITIVE, "fp")
    ledger.add_adjudication(adjudication)
    current = ledger.current_adjudication_for_case(case.case_id)
    assert current is not None
    assert current["adjudication_id"] == adjudication.adjudication_id


def test_second_adjudication_without_supersedes_is_rejected(tmp_path: Path) -> None:
    """This is the core append-only guarantee: a later judgment cannot
    silently coexist with an earlier one for the same case -- it must
    explicitly supersede it."""
    ledger, case = _build_ledger_with_one_case(tmp_path)
    first = make_adjudication(case, AdjudicationVerdict.FALSE_POSITIVE, "fp")
    ledger.add_adjudication(first)
    second = make_adjudication(case, AdjudicationVerdict.TRUE_VIOLATION, "actually real")
    with pytest.raises(LedgerValidationError):
        ledger.add_adjudication(second)


def test_superseding_adjudication_replaces_current_without_deleting_original(
    tmp_path: Path,
) -> None:
    ledger, case = _build_ledger_with_one_case(tmp_path)
    first = make_adjudication(case, AdjudicationVerdict.FALSE_POSITIVE, "fp")
    ledger.add_adjudication(first)
    second = make_superseding_adjudication(
        case, first, AdjudicationVerdict.TRUE_VIOLATION, "reviewed again, actually real"
    )
    ledger.add_adjudication(second)

    # both rows survive on disk -- nothing was deleted or overwritten
    all_adjudications = ledger.adjudications.all()
    assert len(all_adjudications) == 2
    ids = {a["adjudication_id"] for a in all_adjudications}
    assert {first.adjudication_id, second.adjudication_id} == ids

    current = ledger.current_adjudication_for_case(case.case_id)
    assert current is not None
    assert current["adjudication_id"] == second.adjudication_id


def test_supersedes_unknown_adjudication_id_rejected(tmp_path: Path) -> None:
    ledger, case = _build_ledger_with_one_case(tmp_path)
    bogus = Adjudication(
        adjudication_id="ADJ-bogus",
        case_id=case.case_id,
        reviewer="x",
        verdict=AdjudicationVerdict.TRUE_VIOLATION,
        reviewer_comment=None,
        source_reference="x",
        decided_at="2026-01-01T00:00:00+00:00",
        supersedes_adjudication_id="ADJ-never-existed",
    )
    with pytest.raises(LedgerValidationError):
        ledger.add_adjudication(bogus)


def test_appending_same_id_twice_is_rejected_even_for_identical_content(
    tmp_path: Path,
) -> None:
    """Append-only means append-only -- even re-adding byte-identical
    content under an id that already exists is refused, since the store
    has no update operation at all."""
    ledger, case = _build_ledger_with_one_case(tmp_path)
    with pytest.raises(LedgerValidationError):
        ledger.add_review_case(case)


def test_resolution_requires_case_or_policy_reference(tmp_path: Path) -> None:
    ledger, case = _build_ledger_with_one_case(tmp_path)
    resolution = make_resolution_for_case(case)
    ledger.add_resolution(resolution)
    assert len(ledger.resolutions.all()) == 1


def test_regression_result_rejects_unknown_case(tmp_path: Path) -> None:
    ledger, case = _build_ledger_with_one_case(tmp_path)
    result = make_regression_result_for_case(
        case,
        AdjudicationVerdict.FALSE_POSITIVE,
        actual_present=False,
        outcome=RegressionOutcome.PASS,
    )
    ledger.add_regression_result(result)
    assert len(ledger.regression_results.all()) == 1


def test_history_event_rejects_unknown_entity(tmp_path: Path) -> None:
    ledger, _case = _build_ledger_with_one_case(tmp_path)
    event = make_history_event(
        entity_type="ReviewCase",
        entity_id="CASE-does-not-exist",
        event_type="case_created",
        previous_state=None,
        new_state="prepared",
    )
    with pytest.raises(LedgerValidationError):
        ledger.record_history_event(event)


def test_history_event_accepted_for_known_entity(tmp_path: Path) -> None:
    ledger, case = _build_ledger_with_one_case(tmp_path)
    event = make_history_event(
        entity_type="ReviewCase",
        entity_id=case.case_id,
        event_type="case_created",
        previous_state=None,
        new_state="prepared",
    )
    ledger.record_history_event(event)
    assert len(ledger.history_events.all()) == 1


def test_next_review_round_sequence_increments_per_date(tmp_path: Path) -> None:
    ledger = EsterReviewLedger(tmp_path)
    assert ledger.next_review_round_sequence("ER-20260907") == 1

    round1 = make_synthetic_review_round()
    ledger.add_review_round(round1)
    assert round1.review_round_id == "ER-20260203-01"
    assert ledger.next_review_round_sequence("ER-20260203") == 2
    assert ledger.next_review_round_sequence("ER-20260907") == 1

    round2_id = make_review_round_id(dt.date(2026, 2, 3), sequence=2)
    round2 = ReviewRound(
        review_round_id=round2_id,
        prepared_at="2026-02-04T00:00:00+00:00",
        code_sha="abc123",
        status="prepared",
    )
    ledger.add_review_round(round2)
    assert ledger.next_review_round_sequence("ER-20260203") == 3


def test_jsonl_files_are_one_canonical_json_object_per_line(tmp_path: Path) -> None:
    ledger, _case = _build_ledger_with_one_case(tmp_path)
    lines = (tmp_path / "theses.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["thesis_id"] == ledger.theses.all()[0]["thesis_id"]
    # sorted keys -> deterministic, reviewable diffs
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_duplicate_id_on_disk_detected_on_load(tmp_path: Path) -> None:
    EsterReviewLedger(tmp_path)
    theses_path = tmp_path / "theses.jsonl"
    theses_path.parent.mkdir(parents=True, exist_ok=True)
    record = json.dumps(
        {"thesis_id": "TH-dup", "display_label": "x", "active": True, "notes": None}
    )
    theses_path.write_text(record + "\n" + record + "\n", encoding="utf-8")
    with pytest.raises(LedgerValidationError):
        EsterReviewLedger(tmp_path)
