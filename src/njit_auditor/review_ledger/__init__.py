"""Ester review ledger: the durable, privacy-safe source of truth for human
review history across theses, thesis versions, auditor runs, review
rounds, and rule feedback.

Foundation phase only -- see ``docs/evaluation/ESTER_REVIEW_DATA_MODEL.md``.
Historical-feedback migration, the ground-truth replay gate, and the
Excel/Google-Sheets workbook are later phases built on top of this module,
not part of it yet.
"""

from __future__ import annotations

from njit_auditor.review_ledger.confidence import normalize_confidence
from njit_auditor.review_ledger.fingerprint import (
    CaseFingerprint,
    classify_against_known,
    compute_case_fingerprint,
)
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
from njit_auditor.review_ledger.store import (
    SCHEMA_VERSION,
    EsterReviewLedger,
    LedgerValidationError,
)

__all__ = [
    "SCHEMA_VERSION",
    "Adjudication",
    "AdjudicationVerdict",
    "AuditorRun",
    "CaseFingerprint",
    "ConfidenceLevel",
    "EsterReviewLedger",
    "HistoryEvent",
    "LedgerValidationError",
    "RegressionOutcome",
    "RegressionResult",
    "Resolution",
    "ResolutionStatus",
    "ReviewCase",
    "ReviewRound",
    "Thesis",
    "ThesisVersion",
    "classify_against_known",
    "compute_case_fingerprint",
    "make_adjudication_id",
    "make_case_id",
    "make_history_event_id",
    "make_regression_result_id",
    "make_resolution_id",
    "make_review_round_id",
    "make_run_id",
    "make_thesis_id",
    "make_thesis_version_id",
    "normalize_confidence",
]
