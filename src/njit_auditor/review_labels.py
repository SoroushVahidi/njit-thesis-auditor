"""Typed human-review labels for evaluation findings.

Offline / labeling infrastructure only. Does not change detector behavior,
report generation, or web UI runtime paths.

Labels are intentionally coarse product judgments. Private dissertation text
must never be stored in label records — use stable sample IDs (for example
``ester_sample_b``) rather than filenames, and keep reviewer notes free of
quoted body text.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal

ReviewLabelKind = Literal[
    "true_positive",
    "false_positive",
    "false_negative",
    "correct_but_too_strict",
    "wrong_location",
    "wrong_highlight",
    "wrong_wording",
    "duplicate",
    "policy_decision_needed",
]

KNOWN_REVIEW_LABELS: frozenset[str] = frozenset(
    {
        "true_positive",
        "false_positive",
        "false_negative",
        "correct_but_too_strict",
        "wrong_location",
        "wrong_highlight",
        "wrong_wording",
        "duplicate",
        "policy_decision_needed",
    }
)


@dataclass(frozen=True)
class FindingReviewLabel:
    """One human review judgment for a finding or known miss.

    ``sample_id`` is required and must be a stable corpus ID, never a path.
    ``rule_id``, ``issue_type``, and ``page`` are optional so false-negative
    notes (no existing finding) can still be recorded.
    """

    sample_id: str
    label: str
    rule_id: str | None = None
    issue_type: str | None = None
    page: int | None = None
    finding_id: str | None = None
    reviewer_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReviewLabelValidationError(ValueError):
    """Raised when a review-label payload is incomplete or uses an unknown label."""


def validate_review_label_payload(payload: Mapping[str, Any]) -> FindingReviewLabel:
    """Validate and normalize one label record.

    Required keys: ``sample_id``, ``label``.
    Rejects unknown labels. Does not attempt to sanitize privacy risk in
    ``reviewer_note`` beyond type checking — callers must not store private text.
    """
    if not isinstance(payload, Mapping):
        raise ReviewLabelValidationError("label payload must be a mapping")

    sample_id = str(payload.get("sample_id") or "").strip()
    if not sample_id:
        raise ReviewLabelValidationError("sample_id is required")
    if "/" in sample_id or "\\" in sample_id or sample_id.lower().endswith(".pdf"):
        raise ReviewLabelValidationError(
            "sample_id must be a stable corpus ID, not a filesystem path or filename"
        )

    label = str(payload.get("label") or "").strip()
    if label not in KNOWN_REVIEW_LABELS:
        raise ReviewLabelValidationError(f"unknown review label: {label!r}")

    page_raw = payload.get("page", None)
    page: int | None
    if page_raw is None or page_raw == "":
        page = None
    else:
        try:
            page = int(page_raw)
        except (TypeError, ValueError) as exc:
            raise ReviewLabelValidationError("page must be an integer when provided") from exc
        if page < 1:
            raise ReviewLabelValidationError("page must be >= 1 when provided")

    rule_id = payload.get("rule_id", None)
    issue_type = payload.get("issue_type", None)
    finding_id = payload.get("finding_id", None)
    reviewer_note = payload.get("reviewer_note", None)

    return FindingReviewLabel(
        sample_id=sample_id,
        label=label,
        rule_id=None if rule_id in (None, "") else str(rule_id),
        issue_type=None if issue_type in (None, "") else str(issue_type),
        page=page,
        finding_id=None if finding_id in (None, "") else str(finding_id),
        reviewer_note=None if reviewer_note in (None, "") else str(reviewer_note),
    )


def validate_review_label_document(document: Mapping[str, Any]) -> list[FindingReviewLabel]:
    """Validate a document shaped like ``{"labels": [ ... ]}``."""
    if not isinstance(document, Mapping):
        raise ReviewLabelValidationError("document must be a mapping")
    raw_labels = document.get("labels")
    if not isinstance(raw_labels, list):
        raise ReviewLabelValidationError("document.labels must be a list")
    return [validate_review_label_payload(item) for item in raw_labels]
