"""Tests for confidence normalization used by the review ledger."""

from __future__ import annotations

from njit_auditor.review_ledger.confidence import is_weaker_or_equal, normalize_confidence
from njit_auditor.review_ledger.models import ConfidenceLevel


def test_normalizes_known_values_case_insensitively() -> None:
    assert normalize_confidence("low") == ConfidenceLevel.LOW
    assert normalize_confidence("Medium") == ConfidenceLevel.MEDIUM
    assert normalize_confidence("HIGH") == ConfidenceLevel.HIGH


def test_unknown_or_missing_values_normalize_to_unknown() -> None:
    assert normalize_confidence(None) == ConfidenceLevel.UNKNOWN
    assert normalize_confidence("") == ConfidenceLevel.UNKNOWN
    assert normalize_confidence("extremely-certain") == ConfidenceLevel.UNKNOWN


def test_rank_ordering() -> None:
    assert is_weaker_or_equal(ConfidenceLevel.LOW, ConfidenceLevel.HIGH)
    assert is_weaker_or_equal(ConfidenceLevel.LOW, ConfidenceLevel.LOW)
    assert not is_weaker_or_equal(ConfidenceLevel.HIGH, ConfidenceLevel.LOW)
    assert is_weaker_or_equal(ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH)
