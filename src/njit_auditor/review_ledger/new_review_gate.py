"""Hard gate future new-review-round generation must call before running.

Fail-closed by default: if either metric is nonzero, generation is
blocked unless the caller passes an explicit ``override=True`` *and* a
non-empty ``override_reason`` (an unexplained override is rejected the
same as no override at all -- silence is not an acceptable justification
for shipping a new review round on top of an unresolved regression).

This module does not generate a review round itself (out of scope for
this phase -- see ``docs/evaluation/ESTER_FEEDBACK_MIGRATION.md``); it is
only the predicate a future generator is required to consult first.
"""

from __future__ import annotations

from dataclasses import dataclass

from njit_auditor.review_ledger.ground_truth import GroundTruthReport


@dataclass(frozen=True)
class NewReviewGateResult:
    allowed: bool
    reason: str
    fp_remaining: int
    tp_missing: int
    overridden: bool


def check_new_review_gate(
    report: GroundTruthReport,
    *,
    override: bool = False,
    override_reason: str = "",
) -> NewReviewGateResult:
    fp_remaining = report.ester_fp_remaining
    tp_missing = report.ester_tp_missing
    blocking = fp_remaining > 0 or tp_missing > 0

    if not blocking:
        return NewReviewGateResult(
            allowed=True,
            reason="ESTER_FP_REMAINING == 0 and ESTER_TP_MISSING == 0",
            fp_remaining=fp_remaining,
            tp_missing=tp_missing,
            overridden=False,
        )

    if override and override_reason.strip():
        return NewReviewGateResult(
            allowed=True,
            reason=f"blocked by ground truth but explicitly overridden: {override_reason.strip()}",
            fp_remaining=fp_remaining,
            tp_missing=tp_missing,
            overridden=True,
        )

    return NewReviewGateResult(
        allowed=False,
        reason=(
            f"blocked: ESTER_FP_REMAINING={fp_remaining}, ESTER_TP_MISSING={tp_missing} "
            "(pass override=True and a non-empty override_reason to bypass explicitly)"
        ),
        fp_remaining=fp_remaining,
        tp_missing=tp_missing,
        overridden=False,
    )
