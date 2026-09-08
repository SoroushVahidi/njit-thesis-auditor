"""Tests for the authority-matrix JSON importer. Uses a small synthetic
matrix (invented rule ids, never the real 85-rule file)."""

from __future__ import annotations

import json
from pathlib import Path

from njit_auditor.review_ledger.importers.authority_matrix import import_authority_matrix
from njit_auditor.review_ledger.models import ResolutionStatus
from njit_auditor.review_ledger.store import EsterReviewLedger

_SYNTHETIC_MATRIX = {
    "metadata": {"generated": "2026-01-01"},
    "rules": [
        {
            "public_rule": "R900",
            "internal_rule": "P900",
            "ester_decision_exists": "YES",
            "decision": "EXPLICIT - FALSE POSITIVE",
            "evidence_source": "synthetic test",
            "confidence_in_interpretation": "High",
            "current_detector_aligned": "YES",
            "action": "none needed",
        },
        {
            "public_rule": "R901",
            "internal_rule": "P901",
            "ester_decision_exists": "NO",
            "decision": "NO ESTER DECISION FOUND",
            "evidence_source": "synthetic test",
            "confidence_in_interpretation": "None",
            "current_detector_aligned": "Not established",
            "action": "none",
        },
        {
            "public_rule": "R902",
            "internal_rule": "P902",
            "ester_decision_exists": "ANALOGOUS",
            "decision": "ANALOGOUS - FALSE POSITIVE",
            "evidence_source": "synthetic test, inferred",
            "confidence_in_interpretation": "Medium",
            "current_detector_aligned": "Not established",
            "action": "monitor",
        },
    ],
}


def _write_matrix(path: Path) -> None:
    path.write_text(json.dumps(_SYNTHETIC_MATRIX), encoding="utf-8")


def test_imports_yes_and_analogous_skips_no(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.json"
    _write_matrix(matrix_path)
    ledger = EsterReviewLedger(tmp_path / "ledger")

    summary = import_authority_matrix(ledger, matrix_path, imported_at="2026-01-02T00:00:00+00:00")

    assert summary.rules_in_matrix == 3
    assert summary.resolutions_created == 2
    assert summary.skipped_no_decision == 1
    resolutions = ledger.resolutions.all()
    assert len(resolutions) == 2
    policy_refs = {r["policy_reference"] for r in resolutions}
    assert policy_refs == {"R900@2026-01-01", "R902@2026-01-01"}


def test_resolution_status_reflects_detector_alignment(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.json"
    _write_matrix(matrix_path)
    ledger = EsterReviewLedger(tmp_path / "ledger")
    import_authority_matrix(ledger, matrix_path, imported_at="2026-01-02T00:00:00+00:00")

    r900 = next(r for r in ledger.resolutions.all() if r["policy_reference"] == "R900@2026-01-01")
    r902 = next(r for r in ledger.resolutions.all() if r["policy_reference"] == "R902@2026-01-01")
    assert r900["status"] == ResolutionStatus.IMPLEMENTED.value
    assert r902["status"] == ResolutionStatus.NOT_STARTED.value


def test_reimporting_same_snapshot_is_idempotent(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.json"
    _write_matrix(matrix_path)
    ledger = EsterReviewLedger(tmp_path / "ledger")

    first = import_authority_matrix(ledger, matrix_path, imported_at="2026-01-02T00:00:00+00:00")
    second = import_authority_matrix(ledger, matrix_path, imported_at="2026-01-03T00:00:00+00:00")

    assert first.resolutions_created == 2
    assert second.resolutions_created == 0
    assert second.skipped_already_present == 2
    assert len(ledger.resolutions.all()) == 2
