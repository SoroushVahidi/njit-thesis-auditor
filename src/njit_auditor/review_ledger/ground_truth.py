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

Matching first groups by thesis version, rule, qualified issue type and page.
Within a group, source-backed secondary locators distinguish individual
anchors without changing historical case IDs. Unresolved identity is reported
as ambiguity rather than scored as a detector regression or success.

For a handful of rules, plain ``issue_type`` is not fine-grained enough on
its own -- see ``qualify_issue_type()`` below, which both case migration
and current-run replay-input construction call to append a rule-specific
discriminator before it ever reaches this module. Two found during the
second migration pass:

- P011: "margin_boundary_violation" covers left/right/bottom margin
  overflow, each a genuinely different violation that can coexist on one
  page. A reviewed P011 right-margin false positive and an unrelated,
  unreviewed bottom-margin finding shared a page and would otherwise have
  matched as "the same case". Discriminated by the ``side`` details field.
- P024: "list_of_tables_title_case"/"list_of_figures_title_case" (formerly
  "list_of_figures_sentence_case", before 2026-10-05) can
  fire once per flagged word on the same List of Tables/Figures page --
  the specific word is not a structured details field, only embedded in
  the message (e.g. "'casein' may need to be capitalized"). Discriminated
  by extracting the single-quoted word from the message text.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite

from njit_auditor.review_ledger.locators import CaseLocator
from njit_auditor.review_ledger.models import AdjudicationVerdict, RegressionOutcome

_QUOTED_WORD_RE = re.compile(r"'([^']+)'")


def _p024_flagged_word(details: Mapping[str, object], message: str) -> str | None:
    match = _QUOTED_WORD_RE.search(message)
    return match.group(1) if match else None


# Rules whose generic issue_type collapses multiple, independently-adjudicable
# structural variants onto one page -- see module docstring for the two real
# cases this was found from. Each extractor takes (details, message) and
# returns the discriminator value, or None if it can't find one (in which
# case qualify_issue_type falls back to the plain issue_type).
_ISSUE_TYPE_DISCRIMINATORS: dict[str, Callable[[Mapping[str, object], str], object]] = {
    "P011": lambda details, message: details.get("side"),
    "P024": _p024_flagged_word,
}


def qualify_issue_type(
    rule_id: str, issue_type: str, details: Mapping[str, object], message: str = ""
) -> str:
    """Append a rule-specific discriminator to ``issue_type`` when one is
    needed to keep same-page findings distinguishable (see module
    docstring). Both case migration (``known_cases.py``) and current-run
    replay-input construction (``cli.py``) must call this the same way, or
    matching silently degrades back to the coarser, collision-prone form."""
    extractor = _ISSUE_TYPE_DISCRIMINATORS.get(rule_id)
    if extractor is None:
        return issue_type
    discriminator = extractor(details, message)
    if not discriminator:
        return issue_type
    return f"{issue_type}:{discriminator}"

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

# On the fixed PDF version, a five-point drift is below half a typical body
# line pitch. The known Youra anchors are 23.9 points apart. X is used only
# when both sides provide it; 12 points allows small extraction differences
# while still separating distinct columns or indentation positions.
ANCHOR_Y_TOLERANCE_PT = 5.0
ANCHOR_X_TOLERANCE_PT = 12.0


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    ABSENT = "ABSENT"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    NOT_EVALUATED = "NOT_EVALUATED"


def anchor_from_details(details: Mapping[str, object]) -> tuple[float | None, float | None]:
    """Read only the upper-left coordinates of a finding bbox, never text."""
    bbox = details.get("bbox")
    if isinstance(bbox, str):
        parts = bbox.split(",")
    elif isinstance(bbox, (list, tuple)):
        parts = list(bbox)
    else:
        return None, None
    if len(parts) != 4:
        return None, None
    try:
        x, y = float(parts[0]), float(parts[1])
    except (TypeError, ValueError):
        return None, None
    return (x, y) if isfinite(x) and isfinite(y) else (None, None)


@dataclass(frozen=True)
class CurrentFinding:
    thesis_version_id: str
    internal_rule_id: str
    issue_type: str
    physical_page: int | None
    anchor_x: float | None = None
    anchor_y: float | None = None
    structural_role: str | None = None


@dataclass(frozen=True)
class CaseReplayResult:
    case_id: str
    internal_rule_id: str
    thesis_version_id: str
    expected_verdict: AdjudicationVerdict
    equivalent_current_finding_present: bool
    outcome: RegressionOutcome
    excluded_reason: str | None
    match_status: MatchStatus = MatchStatus.NOT_EVALUATED


@dataclass
class RuleReplaySummary:
    fp_total: int = 0
    fp_regressions: int = 0
    tp_total: int = 0
    tp_regressions: int = 0
    unresolved: int = 0
    identity_ambiguous: int = 0

    @property
    def status(self) -> str:
        if self.identity_ambiguous and (self.fp_regressions or self.tp_regressions):
            return "REGRESSION_AND_AMBIGUITY"
        if self.identity_ambiguous:
            return "IDENTITY_AMBIGUOUS"
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
        return sum(1 for r in self.results if r.expected_verdict not in _PASS_FAIL_VERDICTS)

    @property
    def identity_ambiguous_cases(self) -> int:
        return sum(1 for r in self.results if r.match_status == MatchStatus.IDENTITY_AMBIGUOUS)


def _coarse_key(item: dict | CurrentFinding) -> tuple[str, str, str, int | None]:
    if isinstance(item, CurrentFinding):
        return item.thesis_version_id, item.internal_rule_id, item.issue_type, item.physical_page
    return (
        str(item["thesis_version_id"]),
        str(item["internal_rule_id"]),
        str(item["issue_type"]),
        item.get("physical_page"),
    )


def _group_matches(
    cases: list[dict],
    findings: list[CurrentFinding],
    locators: Mapping[str, CaseLocator],
) -> dict[str, MatchStatus]:
    """Resolve a coarse group without assigning one finding to two cases."""
    candidates: dict[str, set[int] | None] = {}
    for case in cases:
        case_id = str(case["case_id"])
        locator = locators.get(case_id)
        if locator is None or locator.anchor_y is None:
            # Legacy coarse matching is safe only for a unique case/finding
            # pair. A missing current finding is unambiguously absent.
            candidates[case_id] = (
                set() if not findings else {0} if len(cases) == len(findings) == 1 else None
            )
            continue
        plausible: set[int] = set()
        unknown_location = False
        for index, finding in enumerate(findings):
            if finding.anchor_y is None:
                unknown_location = True
                continue
            if (
                locator.structural_role
                and finding.structural_role
                and locator.structural_role != finding.structural_role
            ):
                continue
            if abs(locator.anchor_y - finding.anchor_y) > ANCHOR_Y_TOLERANCE_PT:
                continue
            if (
                locator.anchor_x is not None
                and finding.anchor_x is not None
                and abs(locator.anchor_x - finding.anchor_x) > ANCHOR_X_TOLERANCE_PT
            ):
                continue
            plausible.add(index)
        candidates[case_id] = None if unknown_location else plausible

    reverse: dict[int, set[str]] = defaultdict(set)
    for case_id, possible in candidates.items():
        if possible is not None:
            for index in possible:
                reverse[index].add(case_id)
    uncertain_case_present = bool(findings) and any(
        possible is None for possible in candidates.values()
    )
    result: dict[str, MatchStatus] = {}
    for case_id, possible in candidates.items():
        if possible is None or len(possible) > 1:
            result[case_id] = MatchStatus.IDENTITY_AMBIGUOUS
        elif not possible:
            result[case_id] = MatchStatus.ABSENT
        else:
            result[case_id] = (
                MatchStatus.MATCHED
                if len(reverse[next(iter(possible))]) == 1 and not uncertain_case_present
                else MatchStatus.IDENTITY_AMBIGUOUS
            )
    return result


def replay_ledger(
    all_review_cases: list[dict],
    current_adjudication_by_case_id: dict[str, dict],
    current_findings: list[CurrentFinding],
    case_locators: Mapping[str, CaseLocator] | None = None,
) -> GroundTruthReport:
    """Replay every case that has a current (non-superseded) adjudication.

    ``all_review_cases`` / ``current_adjudication_by_case_id`` are plain
    dicts (as stored on disk / returned by ``EsterReviewLedger``), not
    dataclass instances -- this function is intentionally storage-shape
    agnostic so it can be unit tested without spinning up a real
    ``EsterReviewLedger``.
    """
    report = GroundTruthReport()
    locators = case_locators or {}
    cases_by_key: dict[tuple[str, str, str, int | None], list[dict]] = defaultdict(list)
    findings_by_key: dict[tuple[str, str, str, int | None], list[CurrentFinding]] = (
        defaultdict(list)
    )
    for case in all_review_cases:
        if case["case_id"] in current_adjudication_by_case_id:
            cases_by_key[_coarse_key(case)].append(case)
    for finding in current_findings:
        findings_by_key[_coarse_key(finding)].append(finding)
    matches: dict[str, MatchStatus] = {}
    for key, cases in cases_by_key.items():
        matches.update(_group_matches(cases, findings_by_key.get(key, []), locators))

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
                    match_status=MatchStatus.NOT_EVALUATED,
                )
            )
            summary.unresolved += 1
            continue

        match_status = matches[case_id]
        if match_status == MatchStatus.IDENTITY_AMBIGUOUS:
            report.results.append(
                CaseReplayResult(
                    case_id=case_id,
                    internal_rule_id=rule_id,
                    thesis_version_id=str(case["thesis_version_id"]),
                    expected_verdict=verdict,
                    equivalent_current_finding_present=False,
                    outcome=RegressionOutcome.NOT_APPLICABLE,
                    excluded_reason="identity_ambiguous",
                    match_status=match_status,
                )
            )
            summary.identity_ambiguous += 1
            continue
        present = match_status == MatchStatus.MATCHED

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
                match_status=match_status,
            )
        )

    return report
