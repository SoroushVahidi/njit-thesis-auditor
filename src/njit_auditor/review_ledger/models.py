"""Canonical domain model for the Ester review ledger.

This is the durable source of truth for human review history -- not a
spreadsheet, not a cache. See ``docs/evaluation/ESTER_REVIEW_DATA_MODEL.md``
for the full design rationale and invariants.

Every record here is a plain, immutable (frozen) dataclass with an explicit
``to_dict``/``from_dict`` pair for canonical JSON (de)serialization -- the
same pattern already used by ``njit_auditor.review_labels.FindingReviewLabel``.
Records are never mutated in place; the store (``njit_auditor.review_ledger.
store``) enforces append-only history on top of these shapes.

Privacy: nothing in this module accepts or stores raw dissertation body
text. Locations are structural descriptions (page numbers, issue types,
rule ids, coarse geometry buckets), never quoted prose. Thesis identity is
a caller-supplied stable alias (e.g. an existing corpus short name such as
``"praneeth"`` -- see ``DOCS`` in ``scripts/ester_batch/lib.py``), hashed
into an opaque id (see ``njit_auditor.review_ledger.identifiers``), never
stored verbatim as the identifier itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AdjudicationVerdict(str, Enum):
    """Normalized human verdict for one review case.

    The normalized value is deliberately coarse -- it drives suppression/
    detection logic. The reviewer's actual words are preserved separately
    in ``Adjudication.reviewer_comment`` / ``source_reference``; the enum
    is never a substitute for the original feedback.
    """

    TRUE_VIOLATION = "TRUE_VIOLATION"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ACCEPTABLE = "ACCEPTABLE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNRESOLVED = "UNRESOLVED"
    POLICY_GUIDANCE = "POLICY_GUIDANCE"
    NOT_REVIEWED = "NOT_REVIEWED"


class ConfidenceLevel(str, Enum):
    """Canonical confidence tier for ledger storage/comparison.

    This does not change or replace detector confidence calculation --
    see ``njit_auditor.review_ledger.confidence.normalize_confidence`` for
    the (one-way) mapping from a detector's raw confidence string.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class ResolutionStatus(str, Enum):
    """Implementation status of a case or policy resolution."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    IMPLEMENTED = "IMPLEMENTED"
    WONT_FIX = "WONT_FIX"
    SUPERSEDED = "SUPERSEDED"


class RegressionOutcome(str, Enum):
    """Result of replaying one case's expected verdict against a later run."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def _dict_field() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class Thesis:
    """Stable logical dissertation identity, independent of any one PDF."""

    thesis_id: str
    display_label: str
    active: bool = True
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "thesis_id": self.thesis_id,
            "display_label": self.display_label,
            "active": self.active,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Thesis:
        return Thesis(
            thesis_id=str(data["thesis_id"]),
            display_label=str(data["display_label"]),
            active=bool(data.get("active", True)),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class ThesisVersion:
    """One specific submitted PDF artifact for a Thesis."""

    thesis_version_id: str
    thesis_id: str
    sha256: str
    source_format: str
    page_count: int | None
    first_seen_at: str
    current: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "thesis_version_id": self.thesis_version_id,
            "thesis_id": self.thesis_id,
            "sha256": self.sha256,
            "source_format": self.source_format,
            "page_count": self.page_count,
            "first_seen_at": self.first_seen_at,
            "current": self.current,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ThesisVersion:
        return ThesisVersion(
            thesis_version_id=str(data["thesis_version_id"]),
            thesis_id=str(data["thesis_id"]),
            sha256=str(data["sha256"]),
            source_format=str(data["source_format"]),
            page_count=data.get("page_count"),
            first_seen_at=str(data["first_seen_at"]),
            current=bool(data.get("current", True)),
        )


@dataclass(frozen=True)
class AuditorRun:
    """One auditor execution against one ThesisVersion."""

    run_id: str
    thesis_version_id: str
    code_sha: str
    executed_at: str
    tool_metadata: dict[str, Any] = field(default_factory=_dict_field)
    finding_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "thesis_version_id": self.thesis_version_id,
            "code_sha": self.code_sha,
            "executed_at": self.executed_at,
            "tool_metadata": dict(self.tool_metadata),
            "finding_counts": dict(self.finding_counts),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> AuditorRun:
        return AuditorRun(
            run_id=str(data["run_id"]),
            thesis_version_id=str(data["thesis_version_id"]),
            code_sha=str(data["code_sha"]),
            executed_at=str(data["executed_at"]),
            tool_metadata=dict(data.get("tool_metadata") or {}),
            finding_counts=dict(data.get("finding_counts") or {}),
        )


@dataclass(frozen=True)
class ReviewRound:
    """One prepared human-review batch."""

    review_round_id: str
    prepared_at: str
    code_sha: str
    status: str
    included_rule_ids: tuple[str, ...] = ()
    included_thesis_version_ids: tuple[str, ...] = ()
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_round_id": self.review_round_id,
            "prepared_at": self.prepared_at,
            "code_sha": self.code_sha,
            "status": self.status,
            "included_rule_ids": list(self.included_rule_ids),
            "included_thesis_version_ids": list(self.included_thesis_version_ids),
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ReviewRound:
        return ReviewRound(
            review_round_id=str(data["review_round_id"]),
            prepared_at=str(data["prepared_at"]),
            code_sha=str(data["code_sha"]),
            status=str(data["status"]),
            included_rule_ids=tuple(data.get("included_rule_ids") or ()),
            included_thesis_version_ids=tuple(data.get("included_thesis_version_ids") or ()),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class ReviewCase:
    """One possible violation prepared for human review.

    ``structural_location`` and ``measurement`` are structural/numeric
    descriptions only (e.g. ``"list_of_tables:entry_index=3"``,
    ``"center_delta_pt=22.4"``) -- never quoted dissertation text.
    ``exact_fingerprint``/``equivalence_key`` come from
    ``njit_auditor.review_ledger.fingerprint.compute_case_fingerprint``.
    """

    case_id: str
    review_round_id: str
    run_id: str
    thesis_version_id: str
    internal_rule_id: str
    public_rule_id: str
    issue_type: str
    physical_page: int | None
    printed_page: str | None
    structural_location: str
    summary: str
    measurement: dict[str, Any] = field(default_factory=_dict_field)
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    evidence_reference: str | None = None
    exact_fingerprint: str = ""
    equivalence_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "review_round_id": self.review_round_id,
            "run_id": self.run_id,
            "thesis_version_id": self.thesis_version_id,
            "internal_rule_id": self.internal_rule_id,
            "public_rule_id": self.public_rule_id,
            "issue_type": self.issue_type,
            "physical_page": self.physical_page,
            "printed_page": self.printed_page,
            "structural_location": self.structural_location,
            "summary": self.summary,
            "measurement": dict(self.measurement),
            "confidence": self.confidence.value,
            "evidence_reference": self.evidence_reference,
            "exact_fingerprint": self.exact_fingerprint,
            "equivalence_key": self.equivalence_key,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ReviewCase:
        return ReviewCase(
            case_id=str(data["case_id"]),
            review_round_id=str(data["review_round_id"]),
            run_id=str(data["run_id"]),
            thesis_version_id=str(data["thesis_version_id"]),
            internal_rule_id=str(data["internal_rule_id"]),
            public_rule_id=str(data["public_rule_id"]),
            issue_type=str(data["issue_type"]),
            physical_page=data.get("physical_page"),
            printed_page=data.get("printed_page"),
            structural_location=str(data["structural_location"]),
            summary=str(data["summary"]),
            measurement=dict(data.get("measurement") or {}),
            confidence=ConfidenceLevel(data.get("confidence", ConfidenceLevel.UNKNOWN.value)),
            evidence_reference=data.get("evidence_reference"),
            exact_fingerprint=str(data.get("exact_fingerprint", "")),
            equivalence_key=str(data.get("equivalence_key", "")),
        )


@dataclass(frozen=True)
class Adjudication:
    """One human judgment for a ReviewCase.

    Preserves the reviewer's original comment/reference separately from
    the normalized ``verdict`` -- the normalized enum drives automation,
    the original text remains the record of what was actually said.
    ``supersedes_adjudication_id`` links a later judgment to the one it
    replaces; the earlier row is never deleted or edited in place.
    """

    adjudication_id: str
    case_id: str
    reviewer: str
    verdict: AdjudicationVerdict
    reviewer_comment: str | None
    source_reference: str
    decided_at: str
    supersedes_adjudication_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "adjudication_id": self.adjudication_id,
            "case_id": self.case_id,
            "reviewer": self.reviewer,
            "verdict": self.verdict.value,
            "reviewer_comment": self.reviewer_comment,
            "source_reference": self.source_reference,
            "decided_at": self.decided_at,
            "supersedes_adjudication_id": self.supersedes_adjudication_id,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Adjudication:
        return Adjudication(
            adjudication_id=str(data["adjudication_id"]),
            case_id=str(data["case_id"]),
            reviewer=str(data["reviewer"]),
            verdict=AdjudicationVerdict(data["verdict"]),
            reviewer_comment=data.get("reviewer_comment"),
            source_reference=str(data["source_reference"]),
            decided_at=str(data["decided_at"]),
            supersedes_adjudication_id=data.get("supersedes_adjudication_id"),
        )


@dataclass(frozen=True)
class Resolution:
    """Implementation record for a case's (or a policy's) adjudicated feedback."""

    resolution_id: str
    case_id: str | None
    policy_reference: str | None
    status: ResolutionStatus
    resolution_commit_sha: str | None
    implemented_at: str | None
    expected_behavior: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution_id": self.resolution_id,
            "case_id": self.case_id,
            "policy_reference": self.policy_reference,
            "status": self.status.value,
            "resolution_commit_sha": self.resolution_commit_sha,
            "implemented_at": self.implemented_at,
            "expected_behavior": self.expected_behavior,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Resolution:
        return Resolution(
            resolution_id=str(data["resolution_id"]),
            case_id=data.get("case_id"),
            policy_reference=data.get("policy_reference"),
            status=ResolutionStatus(data["status"]),
            resolution_commit_sha=data.get("resolution_commit_sha"),
            implemented_at=data.get("implemented_at"),
            expected_behavior=str(data["expected_behavior"]),
        )


@dataclass(frozen=True)
class RegressionResult:
    """Replay result: does a later auditor run still match a case's verdict?"""

    regression_result_id: str
    case_id: str
    code_sha: str
    checked_at: str
    expected_verdict: AdjudicationVerdict
    actual_present: bool
    outcome: RegressionOutcome
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "regression_result_id": self.regression_result_id,
            "case_id": self.case_id,
            "code_sha": self.code_sha,
            "checked_at": self.checked_at,
            "expected_verdict": self.expected_verdict.value,
            "actual_present": self.actual_present,
            "outcome": self.outcome.value,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RegressionResult:
        return RegressionResult(
            regression_result_id=str(data["regression_result_id"]),
            case_id=str(data["case_id"]),
            code_sha=str(data["code_sha"]),
            checked_at=str(data["checked_at"]),
            expected_verdict=AdjudicationVerdict(data["expected_verdict"]),
            actual_present=bool(data["actual_present"]),
            outcome=RegressionOutcome(data["outcome"]),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class HistoryEvent:
    """Append-only lifecycle event for any ledger entity."""

    event_id: str
    occurred_at: str
    entity_type: str
    entity_id: str
    event_type: str
    previous_state: str | None
    new_state: str | None
    source_reference: str | None
    code_sha: str | None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "event_type": self.event_type,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "source_reference": self.source_reference,
            "code_sha": self.code_sha,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> HistoryEvent:
        return HistoryEvent(
            event_id=str(data["event_id"]),
            occurred_at=str(data["occurred_at"]),
            entity_type=str(data["entity_type"]),
            entity_id=str(data["entity_id"]),
            event_type=str(data["event_type"]),
            previous_state=data.get("previous_state"),
            new_state=data.get("new_state"),
            source_reference=data.get("source_reference"),
            code_sha=data.get("code_sha"),
            notes=data.get("notes"),
        )
