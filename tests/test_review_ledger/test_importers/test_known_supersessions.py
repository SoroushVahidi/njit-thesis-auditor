"""Superseding adjudications for historical cases that existing authority settles.

Synthetic ledger and documents; the real curated entries are checked only as
data (no private text).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from njit_auditor.review_ledger.ground_truth import replay_ledger
from njit_auditor.review_ledger.importers.case_migration import (
    migrate_known_cases,
    migrate_known_supersessions,
)
from njit_auditor.review_ledger.importers.known_cases import (
    KNOWN_ADJUDICATION_SUPERSESSIONS,
    KNOWN_HISTORICAL_CASES,
    KnownAdjudicationSupersession,
    KnownHistoricalCase,
)
from njit_auditor.review_ledger.importers.thesis_registry import RegisteredDocument
from njit_auditor.review_ledger.models import AdjudicationVerdict
from njit_auditor.review_ledger.store import EsterReviewLedger


def _base_ledger_with_registration(tmp_path: Path):  # type: ignore[no-untyped-def]
    from njit_auditor.review_ledger.identifiers import make_thesis_id, make_thesis_version_id
    from njit_auditor.review_ledger.models import AuditorRun, ReviewRound, Thesis, ThesisVersion

    ledger = EsterReviewLedger(tmp_path / "ledger")
    thesis_id = make_thesis_id("SynthDoc")
    ledger.add_thesis(Thesis(thesis_id=thesis_id, display_label="SynthDoc"))
    version_id = make_thesis_version_id(thesis_id, "a" * 64)
    ledger.add_thesis_version(
        ThesisVersion(
            thesis_version_id=version_id,
            thesis_id=thesis_id,
            sha256="a" * 64,
            source_format="pdf",
            page_count=20,
            first_seen_at="2026-01-01T00:00:00+00:00",
        )
    )
    ledger.add_auditor_run(
        AuditorRun(
            run_id="RUN-synthetic",
            thesis_version_id=version_id,
            code_sha="synthcode",
            executed_at="2026-01-01T00:00:00+00:00",
        )
    )
    ledger.add_review_round(
        ReviewRound(
            review_round_id="ER-20260101-01",
            prepared_at="2026-01-01T00:00:00+00:00",
            code_sha="synthcode",
            status="test",
        )
    )
    registered = {
        "SynthDoc": RegisteredDocument(
            short_name="SynthDoc",
            pdf_path=tmp_path / "does-not-matter.pdf",
            thesis_id=thesis_id,
            thesis_version_id=version_id,
            sha256="a" * 64,
            available=True,
        )
    }
    return ledger, "ER-20260101-01", {"SynthDoc": "RUN-synthetic"}, registered

_NUANCED = KnownHistoricalCase(
    document_short_name="SynthDoc",
    internal_rule_id="P900",
    issue_type="synthetic_page_number_regime",
    physical_page=13,
    structural_location="page_footer:synthetic",
    volatile_detail="",
    summary="Synthetic page-number finding.",
    verdict=AdjudicationVerdict.NEEDS_CLARIFICATION,
    reviewer_comment="CORRECT, but the real error is a missing heading.",
    source_reference="tests/synthetic_source.md",
    decided_at="2026-01-01",
)
_TRUE_ELSEWHERE = KnownHistoricalCase(
    document_short_name="SynthDoc",
    internal_rule_id="P901",
    issue_type="synthetic_missing_heading",
    physical_page=13,
    structural_location="body_chapter:first_heading",
    volatile_detail="",
    summary="Synthetic missing first heading.",
    verdict=AdjudicationVerdict.TRUE_VIOLATION,
    reviewer_comment="True violation.",
    source_reference="tests/synthetic_source.md",
    decided_at="2026-01-01",
)
_SUPERSESSION = KnownAdjudicationSupersession(
    case=_NUANCED,
    superseded_verdict=AdjudicationVerdict.NEEDS_CLARIFICATION,
    verdict=AdjudicationVerdict.FALSE_POSITIVE,
    reviewer_comment="Normalized from the reviewer's existing explanation.",
    source_reference="tests/synthetic_resolution.md",
    decided_at="2026-01-02",
)


def _migrated(tmp_path: Path):  # type: ignore[no-untyped-def]
    ledger, round_id, run_ids, registered = _base_ledger_with_registration(tmp_path)
    migrate_known_cases(
        ledger,
        review_round_id=round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-02T00:00:00+00:00",
        known_cases=(_NUANCED, _TRUE_ELSEWHERE),
    )
    return ledger, registered


def _case_id(ledger, rule_id: str) -> str:  # type: ignore[no-untyped-def]
    (case,) = [c for c in ledger.review_cases.all() if c["internal_rule_id"] == rule_id]
    return str(case["case_id"])


def test_supersession_appends_false_positive_and_keeps_history(tmp_path: Path) -> None:
    ledger, registered = _migrated(tmp_path)
    summary = migrate_known_supersessions(
        ledger,
        registered_by_short_name=registered,
        imported_at="2026-01-03T00:00:00+00:00",
        supersessions=(_SUPERSESSION,),
    )
    assert (summary.applied, summary.already_applied, summary.skipped) == (1, 0, [])
    case_id = _case_id(ledger, "P900")
    adjudications = [a for a in ledger.adjudications.all() if a["case_id"] == case_id]
    assert [a["verdict"] for a in adjudications] == ["NEEDS_CLARIFICATION", "FALSE_POSITIVE"]
    assert adjudications[1]["supersedes_adjudication_id"] == adjudications[0]["adjudication_id"]
    assert ledger.current_adjudication_for_case(case_id)["verdict"] == "FALSE_POSITIVE"
    # Same case, no duplicate; the separate true issue is untouched.
    assert len(ledger.review_cases.all()) == 2
    other = ledger.current_adjudication_for_case(_case_id(ledger, "P901"))
    assert other["verdict"] == "TRUE_VIOLATION"


def test_supersession_is_idempotent(tmp_path: Path) -> None:
    ledger, registered = _migrated(tmp_path)
    for _ in range(2):
        summary = migrate_known_supersessions(
            ledger,
            registered_by_short_name=registered,
            imported_at="2026-01-03T00:00:00+00:00",
            supersessions=(_SUPERSESSION,),
        )
    assert (summary.applied, summary.already_applied) == (0, 1)
    assert len(ledger.adjudications.all()) == 3


def test_unexpected_current_verdict_is_reported_not_overwritten(tmp_path: Path) -> None:
    ledger, registered = _migrated(tmp_path)
    mismatched = replace(_SUPERSESSION, superseded_verdict=AdjudicationVerdict.TRUE_VIOLATION)
    summary = migrate_known_supersessions(
        ledger,
        registered_by_short_name=registered,
        imported_at="2026-01-03T00:00:00+00:00",
        supersessions=(mismatched,),
    )
    assert summary.applied == 0
    assert "is not TRUE_VIOLATION" in summary.skipped[0]
    case_id = _case_id(ledger, "P900")
    assert ledger.current_adjudication_for_case(case_id)["verdict"] == "NEEDS_CLARIFICATION"


def test_replay_scores_superseded_case_as_resolved_false_positive(tmp_path: Path) -> None:
    ledger, registered = _migrated(tmp_path)
    migrate_known_supersessions(
        ledger,
        registered_by_short_name=registered,
        imported_at="2026-01-03T00:00:00+00:00",
        supersessions=(_SUPERSESSION,),
    )
    cases = ledger.review_cases.all()
    current = {c["case_id"]: ledger.current_adjudication_for_case(c["case_id"]) for c in cases}
    report = replay_ledger(cases, current, current_findings=[])
    assert report.unresolved_policy_cases == 0
    assert report.ester_reviewed_fp_total == 1
    assert report.ester_fp_remaining == 0


def test_real_patrick_r028_supersession_targets_the_exact_case() -> None:
    (patrick,) = [
        s for s in KNOWN_ADJUDICATION_SUPERSESSIONS if s.case.document_short_name == "Patrick"
    ]
    case = patrick.case
    assert case in KNOWN_HISTORICAL_CASES
    assert (case.internal_rule_id, case.issue_type, case.physical_page) == (
        "P028",
        "arabic_number_on_frontmatter_page",
        13,
    )
    assert case.structural_location == "page_footer:page_number_regime"
    # The historical record keeps what was first migrated; the supersession
    # carries the settled verdict.
    assert case.verdict == AdjudicationVerdict.NEEDS_CLARIFICATION
    assert patrick.superseded_verdict == AdjudicationVerdict.NEEDS_CLARIFICATION
    assert patrick.verdict == AdjudicationVerdict.FALSE_POSITIVE
    assert "P085" in patrick.reviewer_comment
    assert Path(patrick.source_reference).name == "r028_patrick_ledger_resolution_20261006.md"
    # The missing CHAPTER 1 heading stays a separate true violation.
    p085 = [
        c
        for c in KNOWN_HISTORICAL_CASES
        if c.document_short_name == "Patrick" and c.internal_rule_id == "P085"
    ]
    assert [c.verdict for c in p085] == [AdjudicationVerdict.TRUE_VIOLATION]
    assert p085[0].issue_type == "missing_first_chapter_one_heading"
    assert p085[0].structural_location != case.structural_location
