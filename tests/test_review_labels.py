"""Tests for offline human-review label schema (presentation/eval infra only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from njit_auditor.review_labels import (
    KNOWN_REVIEW_LABELS,
    ReviewLabelValidationError,
    validate_review_label_document,
    validate_review_label_payload,
)

FIXTURE = Path("tests/fixtures/review_labels/synthetic_example.json")


def test_known_labels_cover_required_vocabulary() -> None:
    required = {
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
    assert required <= KNOWN_REVIEW_LABELS


def test_validate_payload_accepts_minimal_and_full_records() -> None:
    minimal = validate_review_label_payload(
        {"sample_id": "synthetic_demo_a", "label": "duplicate"}
    )
    assert minimal.rule_id is None
    assert minimal.page is None

    full = validate_review_label_payload(
        {
            "sample_id": "synthetic_demo_a",
            "label": "wrong_wording",
            "rule_id": "P033",
            "issue_type": "title_page_mismatch",
            "page": 1,
            "finding_id": "problem-1",
            "reviewer_note": "Synthetic note only.",
        }
    )
    assert full.to_dict()["issue_type"] == "title_page_mismatch"


@pytest.mark.parametrize(
    "payload",
    [
        {"sample_id": "", "label": "true_positive"},
        {"sample_id": "synthetic_demo_a", "label": "not_a_real_label"},
        {"sample_id": "path/to/file.pdf", "label": "true_positive"},
        {"sample_id": "synthetic_demo_a.pdf", "label": "true_positive"},
        {"sample_id": "synthetic_demo_a", "label": "true_positive", "page": 0},
        {"sample_id": "synthetic_demo_a", "label": "true_positive", "page": "x"},
    ],
)
def test_validate_payload_rejects_invalid_records(payload: dict) -> None:
    with pytest.raises(ReviewLabelValidationError):
        validate_review_label_payload(payload)


def test_synthetic_fixture_document_validates() -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    labels = validate_review_label_document(document)
    assert len(labels) == 4
    assert {item.label for item in labels} >= {
        "true_positive",
        "false_positive",
        "false_negative",
        "policy_decision_needed",
    }
    # Privacy hardening: fixture must not look like a real filename-based sample id.
    assert all("/" not in item.sample_id for item in labels)
    assert all(not item.sample_id.endswith(".pdf") for item in labels)
