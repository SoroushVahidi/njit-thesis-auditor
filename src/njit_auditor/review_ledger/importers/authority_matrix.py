"""Importer for the dated Ester authority-matrix JSON snapshot(s).

``docs/status/ester_authority_matrix_20260902.json`` records, per public
rule (``R001``-``R085``), whether an explicit Ester decision was found in
the live feedback workbook/Gmail as of that date, the decision text, and
its evidence source. This is *rule-level policy*, not a specific
document/page case -- there is no per-thesis, per-page granularity here
-- so each entry becomes a ``Resolution`` with ``policy_reference`` set
and ``case_id=None``, never a fabricated ``ReviewCase``/``Adjudication``.

Later, rule-specific refinements exist only as prose in dated
``docs/status/*.md`` files (this matrix predates several of them -- R024,
R035, R036, R055 all read "NO ESTER DECISION FOUND" here but were
resolved afterward). Those refinements are captured by hand in
``known_cases.py`` and are NOT re-derived here; this importer is
deliberately a faithful transcription of one dated snapshot, not an
attempt to reconcile every later delta programmatically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from njit_auditor.review_ledger.identifiers import make_resolution_id
from njit_auditor.review_ledger.models import Resolution, ResolutionStatus
from njit_auditor.review_ledger.store import EsterReviewLedger

# "YES" = an explicit decision was found; "ANALOGOUS" = inferred from a
# repeated, structurally similar Ester judgment on another rule (still a
# real, sourced decision, just weaker provenance -- recorded as such in
# the Resolution's expected_behavior text, never silently upgraded to the
# same confidence as an explicit "YES"). "NO" carries no decision to
# migrate.
_MIGRATABLE_DECISION_STATES = ("YES", "ANALOGOUS")


@dataclass
class AuthorityMatrixImportSummary:
    source_path: str = ""
    generated_date: str = ""
    rules_in_matrix: int = 0
    resolutions_created: int = 0
    skipped_no_decision: int = 0
    skipped_already_present: int = 0
    created_policy_references: list[str] = field(default_factory=list)


def import_authority_matrix(
    ledger: EsterReviewLedger,
    matrix_json_path: Path,
    *,
    imported_at: str,
) -> AuthorityMatrixImportSummary:
    """Import one dated authority-matrix JSON snapshot as policy Resolutions.

    Idempotent: ``policy_reference`` for a given matrix snapshot is
    ``"{public_rule}@{generated_date}"`` (see ``_policy_reference_for``),
    so re-importing the same file is a no-op the second time -- the
    resolution id itself is not deterministic (see
    ``identifiers.make_resolution_id``), so re-import safety is checked by
    scanning existing resolutions for a matching ``policy_reference``,
    not by id.
    """
    raw = json.loads(matrix_json_path.read_text(encoding="utf-8"))
    metadata = raw["metadata"]
    generated_date = str(metadata["generated"])
    rules = raw["rules"]

    existing_policy_references = {
        r["policy_reference"] for r in ledger.resolutions.all() if r.get("policy_reference")
    }

    summary = AuthorityMatrixImportSummary(
        source_path=str(matrix_json_path),
        generated_date=generated_date,
        rules_in_matrix=len(rules),
    )

    for rule_entry in rules:
        decision_state = rule_entry.get("ester_decision_exists", "NO")
        if decision_state not in _MIGRATABLE_DECISION_STATES:
            summary.skipped_no_decision += 1
            continue

        public_rule = str(rule_entry["public_rule"])
        policy_reference = _policy_reference_for(public_rule, generated_date)
        if policy_reference in existing_policy_references:
            summary.skipped_already_present += 1
            continue

        expected_behavior = _render_expected_behavior(rule_entry, decision_state)
        resolution = Resolution(
            resolution_id=make_resolution_id(),
            case_id=None,
            policy_reference=policy_reference,
            status=ResolutionStatus.IMPLEMENTED
            if rule_entry.get("current_detector_aligned") == "YES"
            else ResolutionStatus.NOT_STARTED,
            resolution_commit_sha=None,
            implemented_at=imported_at,
            expected_behavior=expected_behavior,
        )
        ledger.add_resolution(resolution)
        summary.resolutions_created += 1
        summary.created_policy_references.append(policy_reference)

    return summary


def _policy_reference_for(public_rule: str, generated_date: str) -> str:
    return f"{public_rule}@{generated_date}"


def _render_expected_behavior(rule_entry: dict[str, object], decision_state: str) -> str:
    parts = [
        f"decision={rule_entry.get('decision', '')}",
        f"decision_provenance={decision_state}",
        f"evidence_source={rule_entry.get('evidence_source', '')}",
        f"confidence_in_interpretation={rule_entry.get('confidence_in_interpretation', '')}",
        f"action={rule_entry.get('action', '')}",
    ]
    return " | ".join(str(p) for p in parts)
