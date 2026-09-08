"""Turns ``known_cases.KNOWN_HISTORICAL_CASES`` into real ledger records.

For each entry: resolve its document to a registered ``ThesisVersion``
(``thesis_registry.register_corpus``); if the PDF is not available on
disk, the case is reported as ``version_unresolved`` and nothing is
written (never silently attached to a different version). Otherwise
compute its fingerprint from the historically-recorded structural facts
(never re-derived from a fresh run -- these are the facts as originally
documented; the ground-truth replay gate, not this importer, is what
checks them against current behavior), create the ``ReviewCase`` if it
does not already exist, and record the ``Adjudication`` (and a
``HistoryEvent``) if this case has not already been adjudicated by this
importer.

Idempotent: ``ReviewCase.case_id`` is deterministic from the fingerprint's
equivalence key, so re-running against an already-populated ledger
recognizes the existing case and adjudication and skips both rather than
raising or duplicating.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from njit_auditor.report_outputs import public_display_rule_id
from njit_auditor.review_ledger.fingerprint import compute_case_fingerprint
from njit_auditor.review_ledger.identifiers import (
    make_adjudication_id,
    make_case_id,
    make_history_event_id,
)
from njit_auditor.review_ledger.importers.known_cases import (
    KNOWN_HISTORICAL_CASES,
    KnownHistoricalCase,
)
from njit_auditor.review_ledger.importers.thesis_registry import RegisteredDocument
from njit_auditor.review_ledger.models import (
    Adjudication,
    ConfidenceLevel,
    HistoryEvent,
    ReviewCase,
)
from njit_auditor.review_ledger.store import EsterReviewLedger

REVIEWER_NAME = "Ester"


@dataclass
class CaseMigrationSummary:
    total_known_cases: int = 0
    cases_created: int = 0
    cases_already_present: int = 0
    adjudications_created: int = 0
    adjudications_already_present: int = 0
    version_unresolved: list[str] = field(default_factory=list)


def migrate_known_cases(
    ledger: EsterReviewLedger,
    *,
    review_round_id: str,
    run_id_by_short_name: dict[str, str],
    registered_by_short_name: dict[str, RegisteredDocument],
    imported_at: str,
    known_cases: tuple[KnownHistoricalCase, ...] = KNOWN_HISTORICAL_CASES,
) -> CaseMigrationSummary:
    """Migrate ``known_cases`` (defaults to the real curated dataset) into
    the ledger. Tests pass a small synthetic tuple here instead."""
    summary = CaseMigrationSummary(total_known_cases=len(known_cases))

    for known_case in known_cases:
        registered = registered_by_short_name.get(known_case.document_short_name)
        if registered is None or not registered.available:
            summary.version_unresolved.append(
                f"{known_case.document_short_name}/{known_case.internal_rule_id}"
                f"@page{known_case.physical_page}: PDF not available on disk"
            )
            continue

        run_id = run_id_by_short_name.get(known_case.document_short_name)
        if run_id is None:
            summary.version_unresolved.append(
                f"{known_case.document_short_name}/{known_case.internal_rule_id}"
                f"@page{known_case.physical_page}: no AuditorRun recorded for this document"
            )
            continue

        case_id = _migrate_one_case(
            ledger,
            known_case,
            review_round_id=review_round_id,
            run_id=run_id,
            thesis_version_id=registered.thesis_version_id,
            imported_at=imported_at,
            summary=summary,
        )
        _migrate_adjudication(
            ledger, known_case, case_id=case_id, imported_at=imported_at, summary=summary
        )

    return summary


def _migrate_one_case(
    ledger: EsterReviewLedger,
    known_case: KnownHistoricalCase,
    *,
    review_round_id: str,
    run_id: str,
    thesis_version_id: str,
    imported_at: str,
    summary: CaseMigrationSummary,
) -> str:
    fingerprint = compute_case_fingerprint(
        thesis_version_id=thesis_version_id,
        internal_rule_id=known_case.internal_rule_id,
        issue_type=known_case.issue_type,
        physical_page=known_case.physical_page,
        structural_location=known_case.structural_location,
        volatile_detail=known_case.volatile_detail,
    )
    case_id = make_case_id(
        thesis_version_id, known_case.internal_rule_id, fingerprint.equivalence_key
    )

    if case_id in ledger.review_cases:
        summary.cases_already_present += 1
        return case_id

    case = ReviewCase(
        case_id=case_id,
        review_round_id=review_round_id,
        run_id=run_id,
        thesis_version_id=thesis_version_id,
        internal_rule_id=known_case.internal_rule_id,
        public_rule_id=public_display_rule_id(known_case.internal_rule_id),
        issue_type=known_case.issue_type,
        physical_page=known_case.physical_page,
        printed_page=None,
        structural_location=known_case.structural_location,
        summary=known_case.summary,
        measurement={"volatile_detail": known_case.volatile_detail},
        confidence=ConfidenceLevel.UNKNOWN,
        evidence_reference=known_case.source_reference,
        exact_fingerprint=fingerprint.exact_fingerprint,
        equivalence_key=fingerprint.equivalence_key,
    )
    ledger.add_review_case(case)
    summary.cases_created += 1
    ledger.record_history_event(
        HistoryEvent(
            event_id=make_history_event_id(),
            occurred_at=imported_at,
            entity_type="ReviewCase",
            entity_id=case_id,
            event_type="case_migrated_from_historical_source",
            previous_state=None,
            new_state="prepared",
            source_reference=known_case.source_reference,
            code_sha=None,
            notes=f"migrated from {known_case.source_reference}",
        )
    )
    return case_id


def _migrate_adjudication(
    ledger: EsterReviewLedger,
    known_case: KnownHistoricalCase,
    *,
    case_id: str,
    imported_at: str,
    summary: CaseMigrationSummary,
) -> None:
    current = ledger.current_adjudication_for_case(case_id)
    if current is not None:
        summary.adjudications_already_present += 1
        return

    adjudication = Adjudication(
        adjudication_id=make_adjudication_id(),
        case_id=case_id,
        reviewer=REVIEWER_NAME,
        verdict=known_case.verdict,
        reviewer_comment=known_case.reviewer_comment,
        source_reference=known_case.source_reference,
        decided_at=known_case.decided_at,
    )
    ledger.add_adjudication(adjudication)
    summary.adjudications_created += 1
    ledger.record_history_event(
        HistoryEvent(
            event_id=make_history_event_id(),
            occurred_at=imported_at,
            entity_type="Adjudication",
            entity_id=adjudication.adjudication_id,
            event_type="adjudication_migrated_from_historical_source",
            previous_state=None,
            new_state=known_case.verdict.value,
            source_reference=known_case.source_reference,
            code_sha=None,
            notes=f"migrated from {known_case.source_reference}, decided {known_case.decided_at}",
        )
    )
