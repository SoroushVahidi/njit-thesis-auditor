"""Tests for turning historical-case entries into ledger records.

Uses a small synthetic ``KnownHistoricalCase`` tuple (invented rule/page/
document), never the real curated dataset in ``known_cases.py``.
"""

from __future__ import annotations

from njit_auditor.review_ledger.importers.case_migration import migrate_known_cases
from njit_auditor.review_ledger.importers.known_cases import KnownHistoricalCase
from njit_auditor.review_ledger.importers.thesis_registry import RegisteredDocument
from njit_auditor.review_ledger.models import AdjudicationVerdict
from njit_auditor.review_ledger.store import EsterReviewLedger

_SYNTHETIC_CASE = KnownHistoricalCase(
    document_short_name="SynthDoc",
    internal_rule_id="P900",
    issue_type="synthetic_issue",
    physical_page=7,
    structural_location="synthetic:location",
    volatile_detail="synthetic_detail=1",
    summary="Synthetic historical finding for testing.",
    verdict=AdjudicationVerdict.FALSE_POSITIVE,
    reviewer_comment="synthetic reviewer comment",
    source_reference="tests/synthetic_source.md",
    decided_at="2026-01-01",
)


def _base_ledger_with_registration(tmp_path, *, available: bool = True):
    ledger = EsterReviewLedger(tmp_path / "ledger")
    from njit_auditor.review_ledger.identifiers import make_thesis_id, make_thesis_version_id
    from njit_auditor.review_ledger.models import AuditorRun, ReviewRound, Thesis, ThesisVersion

    thesis_id = make_thesis_id("SynthDoc")
    ledger.add_thesis(Thesis(thesis_id=thesis_id, display_label="SynthDoc"))

    registered_by_short_name = {}
    run_id_by_short_name = {}
    if available:
        thesis_version_id = make_thesis_version_id(thesis_id, "a" * 64)
        ledger.add_thesis_version(
            ThesisVersion(
                thesis_version_id=thesis_version_id,
                thesis_id=thesis_id,
                sha256="a" * 64,
                source_format="pdf",
                page_count=10,
                first_seen_at="2026-01-01T00:00:00+00:00",
            )
        )
        run = AuditorRun(
            run_id="RUN-synthetic",
            thesis_version_id=thesis_version_id,
            code_sha="synthcode",
            executed_at="2026-01-01T00:00:00+00:00",
        )
        ledger.add_auditor_run(run)
        run_id_by_short_name["SynthDoc"] = run.run_id
        registered_by_short_name["SynthDoc"] = RegisteredDocument(
            short_name="SynthDoc",
            pdf_path=tmp_path / "does-not-matter.pdf",
            thesis_id=thesis_id,
            thesis_version_id=thesis_version_id,
            sha256="a" * 64,
            available=True,
        )

    review_round = ReviewRound(
        review_round_id="ER-20260101-01",
        prepared_at="2026-01-01T00:00:00+00:00",
        code_sha="synthcode",
        status="test",
    )
    ledger.add_review_round(review_round)
    return ledger, review_round.review_round_id, run_id_by_short_name, registered_by_short_name


def test_migrates_case_and_adjudication(tmp_path) -> None:
    ledger, review_round_id, run_ids, registered = _base_ledger_with_registration(tmp_path)

    summary = migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-02T00:00:00+00:00",
        known_cases=(_SYNTHETIC_CASE,),
    )

    assert summary.cases_created == 1
    assert summary.adjudications_created == 1
    assert summary.version_unresolved == []
    assert len(ledger.review_cases.all()) == 1
    assert len(ledger.adjudications.all()) == 1
    # Both a case-migrated and an adjudication-migrated history event.
    assert len(ledger.history_events.all()) == 2


def test_unavailable_document_is_version_unresolved_not_fabricated(tmp_path) -> None:
    ledger, review_round_id, run_ids, registered = _base_ledger_with_registration(
        tmp_path, available=False
    )

    summary = migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-02T00:00:00+00:00",
        known_cases=(_SYNTHETIC_CASE,),
    )

    assert summary.cases_created == 0
    assert summary.adjudications_created == 0
    assert len(summary.version_unresolved) == 1
    assert "SynthDoc" in summary.version_unresolved[0]
    assert len(ledger.review_cases.all()) == 0


def test_same_document_same_rule_different_page_are_distinct_cases(tmp_path) -> None:
    """Two genuinely different findings for the same document+rule (e.g. an
    initial-round case and a later follow-up-round case, or two separate
    false positives on the same rule) must not collapse into one case just
    because thesis+rule match -- only page/structural facts distinguish
    them, and migration must preserve both."""
    ledger, review_round_id, run_ids, registered = _base_ledger_with_registration(tmp_path)

    initial_round_case = KnownHistoricalCase(
        document_short_name="SynthDoc",
        internal_rule_id="P900",
        issue_type="synthetic_issue",
        physical_page=7,
        structural_location="synthetic:initial_round",
        volatile_detail="",
        summary="Initial-round synthetic finding.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="initial round comment",
        source_reference="tests/synthetic_source_initial.md",
        decided_at="2026-01-01",
    )
    follow_up_case = KnownHistoricalCase(
        document_short_name="SynthDoc",
        internal_rule_id="P900",
        issue_type="synthetic_issue",
        physical_page=42,
        structural_location="synthetic:follow_up_round",
        volatile_detail="",
        summary="Follow-up-round synthetic finding, different page.",
        verdict=AdjudicationVerdict.TRUE_VIOLATION,
        reviewer_comment="follow-up round comment",
        source_reference="tests/synthetic_source_followup.md",
        decided_at="2026-02-01",
    )

    summary = migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-02-02T00:00:00+00:00",
        known_cases=(initial_round_case, follow_up_case),
    )

    assert summary.cases_created == 2
    assert summary.adjudications_created == 2
    all_cases = ledger.review_cases.all()
    assert len(all_cases) == 2
    pages = {c["physical_page"] for c in all_cases}
    assert pages == {7, 42}
    case_ids = {c["case_id"] for c in all_cases}
    assert len(case_ids) == 2  # distinct fingerprints -> distinct case ids


def test_provenance_preserved_on_case_and_adjudication(tmp_path) -> None:
    """Source reference, reviewer comment, and decision date must survive
    migration unmodified -- these are the audit trail back to the original
    Ester judgment and must never be paraphrased or dropped."""
    ledger, review_round_id, run_ids, registered = _base_ledger_with_registration(tmp_path)

    migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-02T00:00:00+00:00",
        known_cases=(_SYNTHETIC_CASE,),
    )

    (case,) = ledger.review_cases.all()
    assert case["evidence_reference"] == "tests/synthetic_source.md"

    (adjudication,) = ledger.adjudications.all()
    assert adjudication["source_reference"] == "tests/synthetic_source.md"
    assert adjudication["reviewer_comment"] == "synthetic reviewer comment"
    assert adjudication["decided_at"] == "2026-01-01"
    assert adjudication["reviewer"] == "Ester"


def test_needs_clarification_verdict_migrates_without_forcing_true_violation(tmp_path) -> None:
    """A nuanced record (e.g. Ester marking something 'CORRECT' but
    explaining the real defect lives elsewhere) must migrate with whatever
    verdict was actually recorded -- NEEDS_CLARIFICATION here -- not be
    silently promoted to TRUE_VIOLATION just because the case exists."""
    ledger, review_round_id, run_ids, registered = _base_ledger_with_registration(tmp_path)

    nuanced_case = KnownHistoricalCase(
        document_short_name="SynthDoc",
        internal_rule_id="P900",
        issue_type="synthetic_issue",
        physical_page=13,
        structural_location="synthetic:nuanced",
        volatile_detail="",
        summary="Nuanced case: correct per se, real defect is elsewhere.",
        verdict=AdjudicationVerdict.NEEDS_CLARIFICATION,
        reviewer_comment="CORRECT, but the real error is a different rule's responsibility.",
        source_reference="tests/synthetic_source_nuanced.md",
        decided_at="2026-01-01",
    )

    migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-02T00:00:00+00:00",
        known_cases=(nuanced_case,),
    )

    (adjudication,) = ledger.adjudications.all()
    assert adjudication["verdict"] == AdjudicationVerdict.NEEDS_CLARIFICATION.value


def test_reimporting_is_idempotent(tmp_path) -> None:
    ledger, review_round_id, run_ids, registered = _base_ledger_with_registration(tmp_path)

    first = migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-02T00:00:00+00:00",
        known_cases=(_SYNTHETIC_CASE,),
    )
    second = migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-03T00:00:00+00:00",
        known_cases=(_SYNTHETIC_CASE,),
    )

    assert first.cases_created == 1
    assert second.cases_created == 0
    assert second.cases_already_present == 1
    assert second.adjudications_already_present == 1
    assert len(ledger.review_cases.all()) == 1
    assert len(ledger.adjudications.all()) == 1


def test_document_level_case_with_no_physical_page_migrates(tmp_path) -> None:
    """A genuinely document-level finding (e.g. P019's mixed_numbering_style,
    which the auditor itself reports with no page) must migrate with
    ``physical_page=None`` preserved, not rejected or coerced to a
    placeholder page number."""
    ledger, review_round_id, run_ids, registered = _base_ledger_with_registration(tmp_path)

    document_level_case = KnownHistoricalCase(
        document_short_name="SynthDoc",
        internal_rule_id="P019",
        issue_type="mixed_numbering_style",
        physical_page=None,
        structural_location="document_level:mixed_numbering_style",
        volatile_detail="",
        summary="Document-wide mixed page-numbering style warning.",
        verdict=AdjudicationVerdict.FALSE_POSITIVE,
        reviewer_comment="synthetic document-level reviewer comment",
        source_reference="tests/synthetic_source_document_level.md",
        decided_at="2026-01-01",
    )

    summary = migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_ids,
        registered_by_short_name=registered,
        imported_at="2026-01-02T00:00:00+00:00",
        known_cases=(document_level_case,),
    )

    assert summary.cases_created == 1
    assert summary.adjudications_created == 1
    (case,) = ledger.review_cases.all()
    assert case["physical_page"] is None
