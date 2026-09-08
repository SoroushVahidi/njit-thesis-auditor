"""Ground-truth replay: checks current auditor behavior against every
case-level ``Adjudication`` stored in the ledger.

Rules (see ``docs/evaluation/ESTER_FEEDBACK_MIGRATION.md`` for the full
write-up):

- ``FALSE_POSITIVE`` / ``ACCEPTABLE``: an equivalent current finding must
  be ABSENT. Present -> ``FP_REGRESSION``.
- ``TRUE_VIOLATION``: an equivalent current finding must be PRESENT.
  Absent -> ``TP_REGRESSION``.
- ``NEEDS_CLARIFICATION`` / ``UNRESOLVED`` / ``NOT_REVIEWED``: excluded
  from PASS/FAIL metrics, reported separately.
- ``POLICY_GUIDANCE``: this replay gate is case-level only -- rule-wide
  policy guidance lives in ``Resolution.policy_reference`` records (see
  ``importers.authority_matrix``), not as a case ``Adjudication``. A
  ``POLICY_GUIDANCE``-verdict ``Adjudication`` (if one is ever created) is
  excluded from case totals here rather than faked into a pass/fail.

**Matching granularity**: "equivalent current finding" is checked by
``(thesis_version_id, internal_rule_id, issue_type, physical_page)`` --
not the full fingerprint's ``structural_location``/``volatile_detail``.
A live auditor run does not reconstruct the same hand-written
``structural_location`` string a migrated historical case used, so
requiring an exact fingerprint match here would always report "absent"
even when the finding is genuinely still there. This granularity is
accurate for every case currently in the ledger (verified: no two
migrated cases share the same rule/issue_type/page for one thesis
version) but is a real, documented simplification a future phase should
tighten only if it starts producing false matches (see
``docs/evaluation/ESTER_FEEDBACK_MIGRATION.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from njit_auditor.review_ledger.models import AdjudicationVerdict, RegressionOutcome

_PASS_FAIL_VERDICTS = frozenset(
    {
        AdjudicationVerdict.FALSE_POSITIVE,
        AdjudicationVerdict.ACCEPTABLE,
        AdjudicationVerdict.TRUE_VIOLATION,
    }
)
_SUPPRESSION_VERDICTS = frozenset(
    {AdjudicationVerdict.FALSE_POSITIVE, AdjudicationVerdict.ACCEPTABLE}
)


@dataclass(frozen=True)
class CurrentFinding:
    thesis_version_id: str
    internal_rule_id: str
    issue_type: str
    physical_page: int | None


@dataclass(frozen=True)
class CaseReplayResult:
    case_id: str
    internal_rule_id: str
    thesis_version_id: str
    expected_verdict: AdjudicationVerdict
    equivalent_current_finding_present: bool
    outcome: RegressionOutcome
    excluded_reason: str | None


@dataclass
class RuleReplaySummary:
    fp_total: int = 0
    fp_regressions: int = 0
    tp_total: int = 0
    tp_regressions: int = 0
    unresolved: int = 0

    @property
    def status(self) -> str:
        if self.fp_regressions or self.tp_regressions:
            return "REGRESSION"
        if self.unresolved:
            return "PARTIAL"
        if self.fp_total or self.tp_total:
            return "CLEAN"
        return "NO_CASES"


@dataclass
class GroundTruthReport:
    results: list[CaseReplayResult] = field(default_factory=list)
    per_rule: dict[str, RuleReplaySummary] = field(default_factory=dict)

    @property
    def ester_reviewed_fp_total(self) -> int:
        return sum(
            1 for r in self.results if r.expected_verdict in _SUPPRESSION_VERDICTS
        )

    @property
    def ester_fp_remaining(self) -> int:
        return sum(
            1
            for r in self.results
            if r.expected_verdict in _SUPPRESSION_VERDICTS
            and r.outcome == RegressionOutcome.FAIL
        )

    @property
    def ester_reviewed_tp_total(self) -> int:
        return sum(
            1 for r in self.results if r.expected_verdict == AdjudicationVerdict.TRUE_VIOLATION
        )

    @property
    def ester_tp_missing(self) -> int:
        return sum(
            1
            for r in self.results
            if r.expected_verdict == AdjudicationVerdict.TRUE_VIOLATION
            and r.outcome == RegressionOutcome.FAIL
        )

    @property
    def unresolved_policy_cases(self) -> int:
        return sum(1 for r in self.results if r.excluded_reason is not None)


def _find_equivalent_current_finding(
    *,
    thesis_version_id: str,
    internal_rule_id: str,
    issue_type: str,
    physical_page: int | None,
    current_findings: list[CurrentFinding],
) -> bool:
    return any(
        f.thesis_version_id == thesis_version_id
        and f.internal_rule_id == internal_rule_id
        and f.issue_type == issue_type
        and f.physical_page == physical_page
        for f in current_findings
    )


def replay_ledger(
    all_review_cases: list[dict],
    current_adjudication_by_case_id: dict[str, dict],
    current_findings: list[CurrentFinding],
) -> GroundTruthReport:
    """Replay every case that has a current (non-superseded) adjudication.

    ``all_review_cases`` / ``current_adjudication_by_case_id`` are plain
    dicts (as stored on disk / returned by ``EsterReviewLedger``), not
    dataclass instances -- this function is intentionally storage-shape
    agnostic so it can be unit tested without spinning up a real
    ``EsterReviewLedger``.
    """
    report = GroundTruthReport()

    for case in all_review_cases:
        case_id = str(case["case_id"])
        adjudication = current_adjudication_by_case_id.get(case_id)
        if adjudication is None:
            continue

        verdict = AdjudicationVerdict(adjudication["verdict"])
        rule_id = str(case["internal_rule_id"])
        summary = report.per_rule.setdefault(rule_id, RuleReplaySummary())

        if verdict not in _PASS_FAIL_VERDICTS:
            report.results.append(
                CaseReplayResult(
                    case_id=case_id,
                    internal_rule_id=rule_id,
                    thesis_version_id=str(case["thesis_version_id"]),
                    expected_verdict=verdict,
                    equivalent_current_finding_present=False,
                    outcome=RegressionOutcome.NOT_APPLICABLE,
                    excluded_reason=f"verdict {verdict.value} is not scored pass/fail",
                )
            )
            summary.unresolved += 1
            continue

        present = _find_equivalent_current_finding(
            thesis_version_id=str(case["thesis_version_id"]),
            internal_rule_id=rule_id,
            issue_type=str(case["issue_type"]),
            physical_page=case.get("physical_page"),
            current_findings=current_findings,
        )

        if verdict in _SUPPRESSION_VERDICTS:
            outcome = RegressionOutcome.FAIL if present else RegressionOutcome.PASS
            summary.fp_total += 1
            if outcome == RegressionOutcome.FAIL:
                summary.fp_regressions += 1
        else:  # TRUE_VIOLATION
            outcome = RegressionOutcome.PASS if present else RegressionOutcome.FAIL
            summary.tp_total += 1
            if outcome == RegressionOutcome.FAIL:
                summary.tp_regressions += 1

        report.results.append(
            CaseReplayResult(
                case_id=case_id,
                internal_rule_id=rule_id,
                thesis_version_id=str(case["thesis_version_id"]),
                expected_verdict=verdict,
                equivalent_current_finding_present=present,
                outcome=outcome,
                excluded_reason=None,
            )
        )

    return report
