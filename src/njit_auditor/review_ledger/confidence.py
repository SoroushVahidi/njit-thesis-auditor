"""Confidence normalization for review-ledger storage/comparison only.

Mirrors the rank/parsing pattern already used by
``scripts/ester_batch/lib.py``'s ``finding_confidence()`` /
``CONFIDENCE_RANK`` (unreviewed detail: LOW < MEDIUM < HIGH; a rule that
never reports graded confidence is treated as HIGH there because every
surviving finding is equally certain). This module intentionally does not
import that one, since ``scripts/`` is standalone tooling, not an
installed package dependency of ``njit_auditor`` -- the mapping is small
enough to keep independently rather than restructure that script.

This module never alters a detector's own confidence calculation; it only
normalizes an already-computed raw string into a small ledger-storable
enum.
"""

from __future__ import annotations

from njit_auditor.review_ledger.models import ConfidenceLevel

CONFIDENCE_RANK: dict[ConfidenceLevel, int] = {
    ConfidenceLevel.LOW: 0,
    ConfidenceLevel.MEDIUM: 1,
    ConfidenceLevel.HIGH: 2,
    ConfidenceLevel.UNKNOWN: 3,
}


def normalize_confidence(raw: str | None) -> ConfidenceLevel:
    """Map a detector's raw confidence string to a canonical ``ConfidenceLevel``.

    Unrecognized or missing values normalize to ``UNKNOWN`` rather than
    guessing -- callers that need "no graded confidence means certain"
    semantics for one particular rule should apply that before calling
    this, the same way ``finding_confidence()`` does today.
    """
    if raw is None:
        return ConfidenceLevel.UNKNOWN
    value = str(raw).strip().upper()
    if value in ("LOW", "MEDIUM", "HIGH"):
        return ConfidenceLevel(value)
    return ConfidenceLevel.UNKNOWN


def is_weaker_or_equal(candidate: ConfidenceLevel, other: ConfidenceLevel) -> bool:
    """True when ``candidate`` ranks at or below ``other`` (LOW is weakest).

    Used by lowest-confidence selection logic in a later phase; kept here
    since it is purely a function of the rank table above.
    """
    return CONFIDENCE_RANK[candidate] <= CONFIDENCE_RANK[other]
