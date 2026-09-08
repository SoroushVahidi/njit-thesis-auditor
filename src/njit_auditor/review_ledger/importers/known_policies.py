"""Importer for hand-curated, email-sourced rule-level policy guidance.

Some Ester authority arrives as a direct email rather than a sheet-tab
finding row or the dated ``ester_authority_matrix_20260902.json`` snapshot
(see ``importers.authority_matrix``). That snapshot's own docstring is
explicit that R024/R035/R036/R055 all read "NO ESTER DECISION FOUND" as of
2026-09-02 and were resolved afterward -- R024/R035/R036 turned out to have
concrete per-document pages and are migrated as case-level
``known_cases.py`` entries instead. R055 is different: the live sheet's
``R055`` tab has zero populated findings for any of the seven documents
(every row reads "No current auditor R055 finding.", verified against the
2026-09-08 live export -- not an adjudication, see
``docs/status/r055_ester_email_policy_20260904.md``), so there is no
document/page to attach a case to. The policy Ester stated over email is
real and rule-wide, not case-level, so it becomes a ``Resolution`` with
``case_id=None`` and ``policy_reference`` set -- exactly the same shape
``importers.authority_matrix`` uses for matrix-sourced policy, just sourced
from a different dated document. It is never turned into a
``TRUE_VIOLATION``/``FALSE_POSITIVE`` ``Adjudication`` tied to one
dissertation, because no case-level finding exists to adjudicate.

Per project convention (see ``known_cases.py``), this is a curated,
reviewable Python table, hand-transcribed from the cited dated
``docs/status/*.md`` record -- not machine-parsed from a raw mailbox -- and
never stores a raw Gmail message id in application code; the dated status
doc is the stable, reviewable provenance record.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from njit_auditor.review_ledger.identifiers import make_resolution_id
from njit_auditor.review_ledger.models import Resolution, ResolutionStatus
from njit_auditor.review_ledger.store import EsterReviewLedger


@dataclass(frozen=True)
class KnownPolicyGuidance:
    """One rule-wide (not case-level) policy statement from Ester, sourced
    from a direct communication rather than a sheet-tab finding row."""

    public_rule: str
    internal_rule: str
    reviewer: str
    source_type: str  # e.g. "EMAIL"
    source_date: str
    source_subject: str
    source_reference: str  # repo-relative path to the dated status doc
    policy_text: str


# -- R055/P055: no case-level sheet finding exists for any of the seven
# documents (see docs/status/r055_ester_email_policy_20260904.md for the
# cell-by-cell confirmation), but Ester stated an explicit rule-wide policy
# over email on 2026-09-04.
KNOWN_POLICIES: tuple[KnownPolicyGuidance, ...] = (
    KnownPolicyGuidance(
        public_rule="R055",
        internal_rule="P055",
        reviewer="Ester Flaim",
        source_type="EMAIL",
        source_date="2026-09-04",
        source_subject="Re: Thesis Auditor – Feedback on R035, R036, and R055",
        source_reference="docs/status/r055_ester_email_policy_20260904.md",
        policy_text=(
            "For List of Tables / List of Figures entry type, entries should "
            "always appear with the word 'Table' or 'Figure' before the X.x "
            "number."
        ),
    ),
)


@dataclass
class KnownPolicyImportSummary:
    total_known_policies: int = 0
    policies_created: int = 0
    policies_already_present: int = 0
    created_policy_references: list[str] = field(default_factory=list)


def _policy_reference_for(public_rule: str, source_type: str, source_date: str) -> str:
    return f"{public_rule}@{source_type.lower()}:{source_date}"


def _render_expected_behavior(policy: KnownPolicyGuidance) -> str:
    parts = [
        f"policy={policy.policy_text}",
        f"reviewer={policy.reviewer}",
        f"source_type={policy.source_type}",
        f"source_date={policy.source_date}",
        f"source_subject={policy.source_subject}",
    ]
    return " | ".join(parts)


def migrate_known_policies(
    ledger: EsterReviewLedger,
    *,
    imported_at: str,
    policies: tuple[KnownPolicyGuidance, ...] = KNOWN_POLICIES,
) -> KnownPolicyImportSummary:
    """Import curated email/manual-record policy guidance as policy-only
    ``Resolution`` rows (``case_id=None``).

    Idempotent the same way ``importers.authority_matrix`` is: re-import
    safety is checked by scanning existing resolutions for a matching
    ``policy_reference``, not by resolution id (which is not deterministic
    -- see ``identifiers.make_resolution_id``).
    """
    existing_policy_references = {
        r["policy_reference"] for r in ledger.resolutions.all() if r.get("policy_reference")
    }

    summary = KnownPolicyImportSummary(total_known_policies=len(policies))

    for policy in policies:
        policy_reference = _policy_reference_for(
            policy.public_rule, policy.source_type, policy.source_date
        )
        if policy_reference in existing_policy_references:
            summary.policies_already_present += 1
            continue

        resolution = Resolution(
            resolution_id=make_resolution_id(),
            case_id=None,
            policy_reference=policy_reference,
            status=ResolutionStatus.NOT_STARTED,
            resolution_commit_sha=None,
            implemented_at=imported_at,
            expected_behavior=_render_expected_behavior(policy),
        )
        ledger.add_resolution(resolution)
        summary.policies_created += 1
        summary.created_policy_references.append(policy_reference)

    return summary
