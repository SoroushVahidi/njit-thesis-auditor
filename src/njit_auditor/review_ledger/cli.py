"""CLI entry point for the Ester review ledger's migration and replay steps.

    python -m njit_auditor.review_ledger.cli migrate
    python -m njit_auditor.review_ledger.cli replay

Both subcommands operate on the real, private ledger at
``data/evaluation/private/ester_review_ledger/`` (gitignored -- see
``.gitignore``'s existing ``data/evaluation/private/`` entry) and the real
private corpus at ``data/evaluation/private/``. Neither subcommand ever
prints dissertation body text; findings are summarized structurally
(rule, issue type, page).

``migrate`` populates the ledger from every source in
``njit_auditor.review_ledger.importers`` and prints the reconciliation
counts from Phase 14 of the migration task. ``replay`` (also run
automatically at the end of ``migrate``) re-runs the current auditor
against the real corpus and reports ground-truth metrics via
``njit_auditor.review_ledger.ground_truth``.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from njit_auditor.audit_runner import run_audit_for_uploaded_file
from njit_auditor.review_ledger.ground_truth import (
    CurrentFinding,
    GroundTruthReport,
    MatchStatus,
    anchor_from_details,
    qualify_issue_type,
    replay_ledger,
)
from njit_auditor.review_ledger.identifiers import (
    make_history_event_id,
    make_regression_result_id,
    make_review_round_id,
    make_run_id,
)
from njit_auditor.review_ledger.importers.authority_matrix import import_authority_matrix
from njit_auditor.review_ledger.importers.case_migration import (
    migrate_known_cases,
    migrate_known_supersessions,
)
from njit_auditor.review_ledger.importers.known_policies import migrate_known_policies
from njit_auditor.review_ledger.importers.thesis_registry import register_corpus
from njit_auditor.review_ledger.importers.xlsx_packages import scan_xlsx_packages
from njit_auditor.review_ledger.locators import locators_for_review_cases
from njit_auditor.review_ledger.models import (
    AuditorRun,
    HistoryEvent,
    RegressionResult,
    ReviewRound,
)
from njit_auditor.review_ledger.new_review_gate import check_new_review_gate
from njit_auditor.review_ledger.store import EsterReviewLedger

PRIVATE_LEDGER_ROOT = Path(
    "/home/soroush/njit-thesis-auditor/main/data/evaluation/private/ester_review_ledger"
)
AUTHORITY_MATRIX_PATH = Path(
    "/home/soroush/njit-thesis-auditor/main/docs/status/ester_authority_matrix_20260902.json"
)
ESTER_FEEDBACK_PACKAGES_DIR = Path(
    "/home/soroush/njit-thesis-auditor/main/docs/evaluation/ester_feedback"
)


def _current_code_sha() -> str:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd="/home/soroush/njit-thesis-auditor/main",
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_current_auditor_and_record(
    ledger: EsterReviewLedger, code_sha: str, imported_at: str
) -> tuple[dict[str, str], list[CurrentFinding]]:
    """Run the current auditor against every available corpus PDF.

    Returns (run_id_by_short_name, all_current_findings) -- the latter
    used directly by the ground-truth replay step so "current behavior"
    always means "what was actually just executed", never a stale cache.
    """
    registered = register_corpus(ledger, first_seen_at=imported_at)
    run_id_by_short_name: dict[str, str] = {}
    all_findings: list[CurrentFinding] = []

    for doc in registered:
        if not doc.available:
            continue
        result = run_audit_for_uploaded_file(doc.pdf_path)
        finding_counts: dict[str, int] = {}
        for finding in result.findings:
            finding_counts[finding.rule_id] = finding_counts.get(finding.rule_id, 0) + 1
            issue_type = qualify_issue_type(
                finding.rule_id,
                str(finding.details.get("issue_type", "")),
                finding.details,
                finding.message,
            )
            anchor_x, anchor_y = anchor_from_details(finding.details)
            role = finding.details.get("structural_role")
            all_findings.append(
                CurrentFinding(
                    thesis_version_id=doc.thesis_version_id,
                    internal_rule_id=finding.rule_id,
                    issue_type=issue_type,
                    physical_page=finding.page,
                    anchor_x=anchor_x,
                    anchor_y=anchor_y,
                    structural_role=str(role) if role else None,
                )
            )
        run = AuditorRun(
            run_id=make_run_id(code_sha),
            thesis_version_id=doc.thesis_version_id,
            code_sha=code_sha,
            executed_at=imported_at,
            tool_metadata={},
            finding_counts=finding_counts,
        )
        ledger.add_auditor_run(run)
        run_id_by_short_name[doc.short_name] = run.run_id

    return run_id_by_short_name, all_findings


def migrate(ledger_root: Path = PRIVATE_LEDGER_ROOT) -> GroundTruthReport:
    ledger_root.mkdir(parents=True, exist_ok=True)
    ledger = EsterReviewLedger(ledger_root)
    imported_at = _now_iso()
    code_sha = _current_code_sha()

    run_id_by_short_name, current_findings = run_current_auditor_and_record(
        ledger, code_sha, imported_at
    )
    registered = {
        doc.short_name: doc for doc in register_corpus(ledger, first_seen_at=imported_at)
    }

    review_date = dt.date.today()
    date_prefix = f"ER-{review_date:%Y%m%d}"
    sequence = ledger.next_review_round_sequence(date_prefix)
    review_round_id = make_review_round_id(review_date, sequence)
    ledger.add_review_round(
        ReviewRound(
            review_round_id=review_round_id,
            prepared_at=imported_at,
            code_sha=code_sha,
            status="migration_import",
            included_rule_ids=(),
            included_thesis_version_ids=tuple(
                d.thesis_version_id for d in registered.values() if d.available
            ),
            notes="Historical-feedback migration import round.",
        )
    )

    matrix_summary = import_authority_matrix(
        ledger, AUTHORITY_MATRIX_PATH, imported_at=imported_at
    )
    case_summary = migrate_known_cases(
        ledger,
        review_round_id=review_round_id,
        run_id_by_short_name=run_id_by_short_name,
        registered_by_short_name=registered,
        imported_at=imported_at,
    )
    supersession_summary = migrate_known_supersessions(
        ledger, registered_by_short_name=registered, imported_at=imported_at
    )
    xlsx_summary = scan_xlsx_packages(ESTER_FEEDBACK_PACKAGES_DIR)
    policy_summary = migrate_known_policies(ledger, imported_at=imported_at)

    print("=== Authority matrix import ===")
    print(f"  rules_in_matrix={matrix_summary.rules_in_matrix}")
    print(f"  resolutions_created={matrix_summary.resolutions_created}")
    print(f"  skipped_no_decision={matrix_summary.skipped_no_decision}")
    print(f"  skipped_already_present={matrix_summary.skipped_already_present}")
    print()
    print("=== Known case migration ===")
    print(f"  total_known_cases={case_summary.total_known_cases}")
    print(f"  cases_created={case_summary.cases_created}")
    print(f"  cases_already_present={case_summary.cases_already_present}")
    print(f"  adjudications_created={case_summary.adjudications_created}")
    print(f"  adjudications_already_present={case_summary.adjudications_already_present}")
    print(f"  version_unresolved={case_summary.version_unresolved}")
    print()
    print("=== Known adjudication supersessions ===")
    print(f"  total={supersession_summary.total}")
    print(f"  applied={supersession_summary.applied}")
    print(f"  already_applied={supersession_summary.already_applied}")
    print(f"  skipped={supersession_summary.skipped}")
    print()
    print("=== XLSX package scan (informational; no case rows migrated from these) ===")
    print(f"  packages_scanned={xlsx_summary.packages_scanned}")
    print(f"  rows_read={xlsx_summary.rows_read}")
    print(f"  rows_with_verdict={xlsx_summary.rows_with_verdict}")
    print(f"  rows_blank={xlsx_summary.rows_blank}")
    print(f"  rows_unparseable={xlsx_summary.rows_unparseable}")
    print()
    print("=== Known policy (email/manual-record) import ===")
    print(f"  total_known_policies={policy_summary.total_known_policies}")
    print(f"  policies_created={policy_summary.policies_created}")
    print(f"  policies_already_present={policy_summary.policies_already_present}")
    print()

    report = run_replay(ledger, current_findings, code_sha=code_sha, checked_at=imported_at)
    _print_replay_report(report, ledger)
    return report


def run_replay(
    ledger: EsterReviewLedger,
    current_findings: list[CurrentFinding],
    *,
    code_sha: str,
    checked_at: str,
) -> GroundTruthReport:
    """Replay every adjudicated case and persist a RegressionResult (plus a
    HistoryEvent) for each one -- this is what makes a replay run
    permanent, reviewable ground-truth history rather than a one-off
    terminal printout."""
    all_cases = ledger.review_cases.all()
    current_adjudication_by_case_id: dict[str, dict[str, object]] = {}
    for case in all_cases:
        case_id = str(case["case_id"])
        current = ledger.current_adjudication_for_case(case_id)
        if current is not None:
            current_adjudication_by_case_id[case_id] = current
    report = replay_ledger(
        all_cases,
        current_adjudication_by_case_id,
        current_findings,
        case_locators=locators_for_review_cases(
            all_cases,
            {str(version["thesis_version_id"]): str(version["thesis_id"])
             for version in ledger.thesis_versions.all()},
        ),
    )

    for result in report.results:
        if (
            result.excluded_reason is not None
            and result.match_status != MatchStatus.IDENTITY_AMBIGUOUS
        ):
            continue
        regression = RegressionResult(
            regression_result_id=make_regression_result_id(),
            case_id=result.case_id,
            code_sha=code_sha,
            checked_at=checked_at,
            expected_verdict=result.expected_verdict,
            actual_present=result.equivalent_current_finding_present,
            outcome=result.outcome,
            notes=result.excluded_reason,
        )
        ledger.add_regression_result(regression)
        ledger.record_history_event(
            HistoryEvent(
                event_id=make_history_event_id(),
                occurred_at=checked_at,
                entity_type="RegressionResult",
                entity_id=regression.regression_result_id,
                event_type="ground_truth_replay",
                previous_state=None,
                new_state=result.outcome.value,
                source_reference=None,
                code_sha=code_sha,
                notes=(
                    f"case={result.case_id} rule={result.internal_rule_id}"
                    f" reason={result.excluded_reason or 'none'}"
                ),
            )
        )

    return report


def policy_guidance_total(ledger: EsterReviewLedger) -> int:
    """Count of rule-wide (not case-level) policy ``Resolution`` rows --
    ``case_id=None`` and ``policy_reference`` set. Covers both the dated
    authority-matrix import (``importers.authority_matrix``) and hand-cited
    email/manual-record policy (``importers.known_policies``, e.g. R055) --
    it is a ledger-wide count, not tied to one importer."""
    return sum(
        1
        for r in ledger.resolutions.all()
        if r.get("case_id") is None and r.get("policy_reference")
    )


def _print_replay_report(report: GroundTruthReport, ledger: EsterReviewLedger) -> None:
    print("=== Ground-truth replay ===")
    print(f"  ESTER_REVIEWED_FP_TOTAL = {report.ester_reviewed_fp_total}")
    print(f"  ESTER_FP_REMAINING = {report.ester_fp_remaining}")
    print(f"  ESTER_REVIEWED_TP_TOTAL = {report.ester_reviewed_tp_total}")
    print(f"  ESTER_TP_MISSING = {report.ester_tp_missing}")
    print(f"  UNRESOLVED_POLICY_CASES = {report.unresolved_policy_cases}")
    print(f"  IDENTITY_AMBIGUOUS_CASES = {report.identity_ambiguous_cases}")
    print(f"  POLICY_GUIDANCE_TOTAL = {policy_guidance_total(ledger)}")
    print()
    print(
        "  RULE | FP_TOTAL | FP_REGRESSIONS | TP_TOTAL | TP_REGRESSIONS | "
        "UNRESOLVED | IDENTITY_AMBIGUOUS | STATUS"
    )
    for rule_id, s in sorted(report.per_rule.items()):
        print(
            f"  {rule_id} | {s.fp_total} | {s.fp_regressions} | {s.tp_total} | "
            f"{s.tp_regressions} | {s.unresolved} | {s.identity_ambiguous} | {s.status}"
        )
    print()
    gate = check_new_review_gate(report)
    print(f"=== New-review gate === allowed={gate.allowed} reason={gate.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ester review ledger CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Import historical feedback and run ground-truth replay")
    subparsers.add_parser("replay", help="Run ground-truth replay against the existing ledger")
    args = parser.parse_args()

    if args.command == "migrate":
        migrate()
    elif args.command == "replay":
        ledger = EsterReviewLedger(PRIVATE_LEDGER_ROOT)
        code_sha = _current_code_sha()
        imported_at = _now_iso()
        _run_id_by_short_name, current_findings = run_current_auditor_and_record(
            ledger, code_sha, imported_at
        )
        report = run_replay(ledger, current_findings, code_sha=code_sha, checked_at=imported_at)
        _print_replay_report(report, ledger)


if __name__ == "__main__":
    main()
