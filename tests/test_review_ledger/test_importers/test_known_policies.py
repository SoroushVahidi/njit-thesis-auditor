"""Tests for the email/manual-record policy-guidance importer. Uses
synthetic policies (invented rule ids), never the real R055 record."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.review_ledger.cli import policy_guidance_total
from njit_auditor.review_ledger.ground_truth import GroundTruthReport, replay_ledger
from njit_auditor.review_ledger.importers.known_policies import (
    KnownPolicyGuidance,
    migrate_known_policies,
)
from njit_auditor.review_ledger.models import ResolutionStatus
from njit_auditor.review_ledger.store import EsterReviewLedger

_SYNTHETIC_POLICY = KnownPolicyGuidance(
    public_rule="R900",
    internal_rule="P900",
    reviewer="Ester Flaim",
    source_type="EMAIL",
    source_date="2026-01-05",
    source_subject="Re: synthetic test policy",
    source_reference="docs/status/does_not_exist_synthetic.md",
    policy_text="Synthetic rule-wide policy statement for testing.",
)


def test_creates_policy_only_resolution_no_case(tmp_path: Path) -> None:
    ledger = EsterReviewLedger(tmp_path / "ledger")

    summary = migrate_known_policies(
        ledger, imported_at="2026-01-06T00:00:00+00:00", policies=(_SYNTHETIC_POLICY,)
    )

    assert summary.total_known_policies == 1
    assert summary.policies_created == 1
    assert summary.policies_already_present == 0
    assert ledger.review_cases.all() == []

    resolutions = ledger.resolutions.all()
    assert len(resolutions) == 1
    resolution = resolutions[0]
    assert resolution["case_id"] is None
    assert resolution["policy_reference"] == "R900@email:2026-01-05"
    assert resolution["status"] == ResolutionStatus.NOT_STARTED.value
    assert "Synthetic rule-wide policy statement" in resolution["expected_behavior"]
    assert "Ester Flaim" in resolution["expected_behavior"]


def test_reimporting_same_policy_is_idempotent(tmp_path: Path) -> None:
    ledger = EsterReviewLedger(tmp_path / "ledger")

    first = migrate_known_policies(
        ledger, imported_at="2026-01-06T00:00:00+00:00", policies=(_SYNTHETIC_POLICY,)
    )
    second = migrate_known_policies(
        ledger, imported_at="2026-01-07T00:00:00+00:00", policies=(_SYNTHETIC_POLICY,)
    )

    assert first.policies_created == 1
    assert second.policies_created == 0
    assert second.policies_already_present == 1
    assert len(ledger.resolutions.all()) == 1


def test_policy_guidance_does_not_affect_case_level_replay_totals(tmp_path: Path) -> None:
    """An email-derived policy resolution with no case must never be
    confused with a case-level adjudication -- it must not appear in, or
    move, ESTER_REVIEWED_FP_TOTAL/ESTER_REVIEWED_TP_TOTAL, and it must be
    counted separately by ``policy_guidance_total``."""
    ledger = EsterReviewLedger(tmp_path / "ledger")
    migrate_known_policies(
        ledger, imported_at="2026-01-06T00:00:00+00:00", policies=(_SYNTHETIC_POLICY,)
    )

    # No review cases exist at all -- replay_ledger over an empty case list
    # must report all-zero case totals regardless of the policy resolution.
    report: GroundTruthReport = replay_ledger(
        all_review_cases=[], current_adjudication_by_case_id={}, current_findings=[]
    )
    assert report.ester_reviewed_fp_total == 0
    assert report.ester_reviewed_tp_total == 0
    assert report.unresolved_policy_cases == 0

    assert policy_guidance_total(ledger) == 1


def test_policy_guidance_total_counts_only_policy_level_resolutions(tmp_path: Path) -> None:
    """A case-level resolution (case_id set, policy_reference=None) must
    not be counted by ``policy_guidance_total`` -- only rule-wide
    (``case_id=None``) resolutions are policy guidance. Appended directly
    to the raw collection (bypassing ``add_resolution``'s referential-
    integrity check against a real ``ReviewCase``) since this test only
    needs to exercise ``policy_guidance_total``'s own filtering logic, not
    the full case/round/run/thesis-version object graph."""
    ledger = EsterReviewLedger(tmp_path / "ledger")
    migrate_known_policies(
        ledger, imported_at="2026-01-06T00:00:00+00:00", policies=(_SYNTHETIC_POLICY,)
    )
    ledger.resolutions.append(
        "RES-synthetic-case-level",
        {
            "resolution_id": "RES-synthetic-case-level",
            "case_id": "some-case-id",
            "policy_reference": None,
            "status": ResolutionStatus.NOT_STARTED.value,
            "resolution_commit_sha": None,
            "implemented_at": "2026-01-06T00:00:00+00:00",
            "expected_behavior": "case-level resolution, not policy guidance",
        },
    )

    assert len(ledger.resolutions.all()) == 2
    assert policy_guidance_total(ledger) == 1
