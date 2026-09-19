"""Run the non-production R036 page-relative spacing experiment."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from njit_auditor.pdf_layout import load_pdf_layout  # noqa: E402
from njit_auditor.rules.pdf_toc_list_entry_spacing import (  # noqa: E402
    check_pdf_toc_list_entry_spacing,
)
from njit_auditor.rules.r036_page_relative_spacing_experiment import (  # noqa: E402
    DiagnosticModel,
    DiagnosticOutcome,
    collect_r036_spacing_candidates,
    evaluate_page_relative_models,
    selected_candidate_decision,
)

RULE_ID = "P036"
PRIVATE_DATA_DIRS = [
    REPO_ROOT / "data/evaluation/private",
    Path("/home/soroush/njit-thesis-auditor/main/data/evaluation/private"),
]
GROUND_TRUTH_PATH = (
    REPO_ROOT / "data/evaluation/r036_ester_false_positive_ground_truth_20260916.json"
)
OUTPUT_JSON_PATH = REPO_ROOT / "docs/status/r036_page_relative_spacing_experiment_20260916.json"
OUTPUT_MD_PATH = REPO_ROOT / "docs/status/r036_page_relative_spacing_experiment_20260916.md"

DOCS: list[tuple[str, str]] = [
    ("Youra", "5_Youra_Shin_PhD_Dissertation_Document_3rd review.pdf"),
    ("Anthony", "Anthony.Sena 3rd Review Draft.pdf"),
    ("Muyeed", "Muyeed_Dissertation (4).pdf"),
    ("Philip", "Philip_Zaleski_Thesis_Revised (1).pdf"),
    ("Praneeth", "Praneeth Ivan Joel. FNU_3rd review draft.pdf"),
    ("Sebastian", "Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf"),
    ("Patrick", "Thesis Patrick Grice July 22.pdf"),
]

SECTION_LABELS = {
    "table_of_contents": "TOC",
    "list_of_figures": "LOF",
    "list_of_tables": "LOT",
}


def _pdf_path(filename: str) -> Path:
    for directory in PRIVATE_DATA_DIRS:
        path = directory / filename
        if path.exists():
            return path
    searched = ", ".join(str(path / filename) for path in PRIVATE_DATA_DIRS)
    raise FileNotFoundError(f"Could not find private PDF {filename!r}; searched {searched}")


def _ratio_band(value: float) -> str:
    if value < 1.2:
        return "<1.2"
    if value < 1.3:
        return "1.2-1.29"
    if value < 1.4:
        return "1.3-1.39"
    if value < 1.5:
        return "1.4-1.49"
    if value < 1.6:
        return "1.5-1.59"
    return ">=1.6"


def _candidate_structural_shape(candidate: Any) -> str:
    if candidate.previous_level == "toc_level_1" or candidate.next_level == "toc_level_1":
        base = "structural_heading_transition"
    elif candidate.previous_level == candidate.next_level:
        base = "same_level_peer"
    else:
        base = "hierarchy_level_change"
    if candidate.previous_wraps and candidate.next_wraps:
        return f"{base}_both_wrapped"
    if candidate.previous_wraps:
        return f"{base}_previous_wrapped"
    if candidate.next_wraps:
        return f"{base}_next_wrapped"
    return f"{base}_unwrapped"


def _looks_like_parser_structural_concern(candidate: Any) -> bool:
    """Flag obvious split-entry artifacts for diagnostic classification only."""
    next_text = candidate.next_entry.strip()
    if candidate.section_type in {"list_of_figures", "list_of_tables"}:
        # Subfigure/subtable fragments such as "5.6a plots..." and prose
        # fragments such as "2.5using..." are not independent LOF/LOT rows.
        if re.match(r"^\d+\.\d+[a-z]", next_text):
            return True
        if re.match(r"^\d+\.\d+[A-Za-z]", next_text) and " " not in next_text[:8]:
            return True
    return False


def _diagnostic_classification(evaluated: Any) -> str:
    decision = selected_candidate_decision(evaluated)
    if decision.outcome == DiagnosticOutcome.INSUFFICIENT_CONTEXT:
        return "INSUFFICIENT_CONTEXT"
    if decision.outcome == DiagnosticOutcome.SUPPRESSED:
        return "SUPPRESSED_AS_NORMAL_PAGE_RHYTHM"
    if _looks_like_parser_structural_concern(evaluated.candidate):
        return "PARSER/STRUCTURAL_CONCERN"
    return "POTENTIAL_PAGE_RELATIVE_ANOMALY"


def _candidate_dict(evaluated: Any) -> dict[str, Any]:
    candidate = evaluated.candidate
    selected = selected_candidate_decision(evaluated)
    stats = candidate.page_stats
    return {
        "document": candidate.document,
        "page": candidate.page_number,
        "section_type": candidate.section_type,
        "entry_pair_index": candidate.entry_pair_index,
        "previous_level": candidate.previous_level,
        "next_level": candidate.next_level,
        "previous_wraps": candidate.previous_wraps,
        "next_wraps": candidate.next_wraps,
        "pitch_pt": round(candidate.pitch_pt, 3),
        "local_single_line_pitch_pt": round(candidate.local_single_line_pitch_pt, 3),
        "normalized_ratio": round(candidate.normalized_ratio, 3),
        "ratio_band": _ratio_band(candidate.normalized_ratio),
        "structural_shape": _candidate_structural_shape(candidate),
        "page_gap_count": 0 if stats is None else stats.count,
        "page_median_pitch": None if stats is None else stats.median_pitch,
        "page_median_normalized_ratio": None if stats is None else stats.median_normalized_ratio,
        "selected_outcome": selected.outcome.value,
        "selected_reason": selected.reason,
        "diagnostic_classification": _diagnostic_classification(evaluated),
        "models": {
            model.value: {
                "outcome": decision.outcome.value,
                "score": decision.score,
                "reason": decision.reason,
            }
            for model, decision in evaluated.decisions.items()
        },
    }


def _load_ground_truth() -> list[dict[str, Any]]:
    payload = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    labels = payload["labels"]
    if len(labels) != 24:
        raise SystemExit(f"Expected 24 Ester false-positive labels, found {len(labels)}")
    bad = [row for row in labels if row.get("label") != "ESTER_FALSE_POSITIVE"]
    if bad:
        raise SystemExit(f"Ground truth contains non-false-positive labels: {bad}")
    return labels


def _key(document: str, page: int, pair_index: int) -> tuple[str, int, int]:
    return (document, page, pair_index)


def _ground_truth_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return _key(row["dissertation"], int(row["physical_pdf_page"]), int(row["entry_pair_index"]))


def _model_summary(
    evaluated_rows: list[Any], production_keys: set[tuple[str, int, int]]
) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for model in DiagnosticModel:
        counts: Counter[str] = Counter()
        for item in evaluated_rows:
            decision = item.decisions[model]
            if decision.outcome == DiagnosticOutcome.ANOMALY:
                counts["all_candidate_anomalies"] += 1
                if item.candidate.key in production_keys:
                    counts["current_production_findings_remaining"] += 1
            elif decision.outcome == DiagnosticOutcome.INSUFFICIENT_CONTEXT:
                counts["abstentions"] += 1
            else:
                counts["suppressed"] += 1
        summary[model.value] = dict(counts)
    return summary


def _coverage_status(candidate: Any, reviewed_post_examples: list[Any]) -> str:
    reviewed_keys = {item.candidate.key for item in reviewed_post_examples}
    if candidate.key in reviewed_keys:
        return "DIRECT_REVIEWED_FALSE_POSITIVE"
    candidate_signature = (
        candidate.section_type,
        _ratio_band(candidate.normalized_ratio),
        _candidate_structural_shape(candidate),
    )
    reviewed_signatures = {
        (
            item.candidate.section_type,
            _ratio_band(item.candidate.normalized_ratio),
            _candidate_structural_shape(item.candidate),
        )
        for item in reviewed_post_examples
    }
    if candidate_signature in reviewed_signatures:
        return "CLOSELY_REPRESENTED_BY_REVIEWED_CLUSTER"
    return "NOT_REPRESENTED_BY_EXPERIMENT_SIGNATURE"


def _make_unrepresented_rows(
    evaluated_rows: list[Any],
    production_keys: set[tuple[str, int, int]],
    reviewed_post_examples: list[Any],
) -> list[dict[str, Any]]:
    production_rows = [item for item in evaluated_rows if item.candidate.key in production_keys]
    unrepresented = [
        item
        for item in production_rows
        if _coverage_status(item.candidate, reviewed_post_examples)
        == "NOT_REPRESENTED_BY_EXPERIMENT_SIGNATURE"
    ]
    ranked = sorted(
        unrepresented,
        key=lambda item: (
            0
            if selected_candidate_decision(item).outcome == DiagnosticOutcome.ANOMALY
            else 1,
            item.candidate.document,
            item.candidate.page_number,
            item.candidate.entry_pair_index,
        ),
    )
    return [_candidate_dict(item) for item in ranked[:18]]


def _page_stats_summary(evaluated_rows: list[Any]) -> dict[str, Any]:
    seen_pages: dict[tuple[str, int, str], Any] = {}
    for item in evaluated_rows:
        candidate = item.candidate
        seen_pages[(candidate.document, candidate.page_number, candidate.section_type)] = (
            candidate.page_stats
        )
    counts_by_section: Counter[str] = Counter()
    sparse_pages = 0
    for (_document, _page, section), stats in seen_pages.items():
        counts_by_section[section] += 1
        if stats is None or stats.count < 5:
            sparse_pages += 1
    return {
        "toc_list_pages": len(seen_pages),
        "pages_by_section": dict(counts_by_section),
        "pages_with_too_few_candidate_gaps": sparse_pages,
        "candidate_gaps": len(evaluated_rows),
    }


def _section_type_results(evaluated_rows: list[Any]) -> dict[str, dict[str, int]]:
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for item in evaluated_rows:
        label = SECTION_LABELS.get(item.candidate.section_type, item.candidate.section_type)
        outcome = selected_candidate_decision(item).outcome.value
        out[label][outcome] += 1
    return {section: dict(counter) for section, counter in out.items()}


def _write_markdown(report: dict[str, Any]) -> None:
    comparison = report["model_summary"]
    lines = [
        "# R036 Page-Relative Spacing Experiment (2026-09-16)",
        "",
        (
            "This began as a diagnostic experiment. As of the "
            "`fix/r036-production-page-relative-suppression-20260916` branch, "
            "the reliable parts of this work are productionized through the "
            "conservative SUPPRESS/ABSTAIN policy documented in "
            "`r036_production_page_relative_suppression_design_20260916.md`; "
            "the reporting gate remains disabled because no real "
            "Ester-confirmed R036 true positive exists."
        ),
        "",
        "## Why this experiment exists",
        "",
        (
            "Ester has rejected both reviewed R036 batches as false positives: the original "
            "12 Praneeth page-11 examples and the later 12 post-recovery examples spanning "
            "TOC, LOF, LOT, wrapped/unwrapped entries, same-level transitions, and hierarchy "
            "transitions. Those reviewed examples span normalized ratios from 1.00 through "
            "1.56, so the current fixed 1.6 ratio is not supported as a production "
            "discriminator."
        ),
        "",
        "## Ground Truth",
        "",
        (
            f"- Known Ester false positives: {report['known_ester_false_positive_count']} "
            f"({report['known_ester_false_positive_set_complete']})"
        ),
        "- True positives inferred from Ester feedback: 0",
        "",
        "## Page Statistics Summary",
        "",
        f"- Candidate gaps collected: {report['page_statistics_summary']['candidate_gaps']}",
        f"- TOC/list pages analyzed: {report['page_statistics_summary']['toc_list_pages']}",
        (
            "- Pages with too few candidate gaps for page-local modeling: "
            f"{report['page_statistics_summary']['pages_with_too_few_candidate_gaps']}"
        ),
        f"- Pages by section: {report['page_statistics_summary']['pages_by_section']}",
        "",
        "## Model Comparison",
        "",
        (
            "| Model | All diagnostic anomalies | Current production findings remaining | "
            "Abstentions | Suppressed |"
        ),
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for model, row in comparison.items():
        lines.append(
            "| "
            + model
            + " | "
            + str(row.get("all_candidate_anomalies", 0))
            + " | "
            + str(row.get("current_production_findings_remaining", 0))
            + " | "
            + str(row.get("abstentions", 0))
            + " | "
            + str(row.get("suppressed", 0))
            + " |"
        )
    lines.extend(
        [
            "",
            "## Selected Diagnostic Candidate",
            "",
            str(report["best_diagnostic_model"]),
            "",
            str(report["best_model_rationale"]),
            "",
            "## Sparse-Page Policy",
            "",
            str(report["sparse_page_policy"]),
            "",
            "## Section-Type Results",
            "",
            f"- TOC: {report['section_type_results'].get('TOC', {})}",
            f"- LOF: {report['section_type_results'].get('LOF', {})}",
            f"- LOT: {report['section_type_results'].get('LOT', {})}",
            "",
            "## Current Production Finding Diagnostic Table",
            "",
            (
                "On the production page-relative branch, current production R036 "
                "findings should be zero. If any production findings exist, this "
                "table records their diagnostic context for review planning."
            ),
            "",
            "| # | Document | Page | Section | Pair | Ratio | Diagnostic Outcome | Reason |",
            "| ---: | --- | ---: | --- | ---: | ---: | --- | --- |",
        ]
    )
    current_finding_analysis = report["current_production_finding_analysis"]
    if not current_finding_analysis:
        lines.append("|  | No current production R036 findings |  |  |  |  |  |  |")
    for index, row in enumerate(current_finding_analysis, start=1):
        lines.append(
            f"| {index} | {row['document']} | {row['page']} | "
            f"{SECTION_LABELS.get(row['section_type'], row['section_type'])} | "
            f"{row['entry_pair_index']} | {row['normalized_ratio']:.2f} | "
            f"{row['diagnostic_classification']} | {row['selected_reason']} |"
        )
    lines.extend(
        [
            "",
            "## Current Branch Production Status",
            "",
            f"- Production R036 code path changed: {report['production_r036_changed']}",
            "- Fixed threshold as production decision rule: retired",
            f"- Current production findings: {report['current_production_findings']}",
            "- Email sent: NO",
            "- Drive upload performed: NO",
            "- Merged: NO",
            "- Deployed: NO",
            "",
            "## Artifacts",
            "",
            f"- Detail JSON: `{OUTPUT_JSON_PATH.relative_to(REPO_ROOT)}`",
            f"- Ground truth JSON: `{GROUND_TRUTH_PATH.relative_to(REPO_ROOT)}`",
        ]
    )
    OUTPUT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict[str, Any]:
    labels = _load_ground_truth()
    gt_keys = {_ground_truth_key(row) for row in labels}
    all_evaluated: list[Any] = []
    production_counts: dict[str, int] = {}
    production_keys: set[tuple[str, int, int]] = set()

    for document, filename in DOCS:
        pdf_document = load_pdf_layout(str(_pdf_path(filename)))
        findings = check_pdf_toc_list_entry_spacing(pdf_document)
        production_counts[document] = len(findings)
        for finding in findings:
            details = finding.details
            production_keys.add(
                _key(document, int(finding.page or 0), int(details["entry_pair_index"]))
            )
        candidates = collect_r036_spacing_candidates(pdf_document, document_name=document)
        all_evaluated.extend(evaluate_page_relative_models(candidates))

    by_key = {item.candidate.key: item for item in all_evaluated}
    gt_evaluations = [by_key[key] for key in gt_keys if key in by_key]
    gt_flagged = [
        item
        for item in gt_evaluations
        if selected_candidate_decision(item).outcome == DiagnosticOutcome.ANOMALY
    ]
    gt_suppressed = [
        item
        for item in gt_evaluations
        if selected_candidate_decision(item).outcome != DiagnosticOutcome.ANOMALY
    ]

    reviewed_post_examples = [
        by_key[_ground_truth_key(row)]
        for row in labels
        if row["review_batch"] == "R036_PostRecovery_Remaining_Findings_Validation_20260914"
        and _ground_truth_key(row) in by_key
    ]
    coverage_counts = Counter(
        _coverage_status(item.candidate, reviewed_post_examples)
        for item in all_evaluated
        if item.candidate.key in production_keys
    )

    report: dict[str, Any] = {
        "source_branch": "fix/r036-recover-split-section-number-classification-20260914",
        "source_sha": "4ce9f778de10da97a59dc65800c8579ad9cb7370",
        "experiment_branch": "experiment/r036-page-relative-spacing-model-20260916",
        "production_r036_changed": "YES",
        "known_ester_false_positive_count": len(labels),
        "known_ester_false_positive_set_complete": "YES" if len(labels) == 24 else "NO",
        "known_ester_false_positives_matched_to_current_candidates": len(gt_evaluations),
        "known_ester_false_positives_flagged_by_best_model": len(gt_flagged),
        "known_ester_false_positives_suppressed_by_best_model": len(gt_suppressed),
        "all_24_known_false_positives_suppressed": len(gt_flagged) == 0
        and len(gt_evaluations) == 24,
        "current_production_counts": production_counts,
        "current_production_findings": sum(production_counts.values()),
        "page_statistics_summary": _page_stats_summary(all_evaluated),
        "model_summary": _model_summary(all_evaluated, production_keys),
        "best_diagnostic_model": DiagnosticModel.NEIGHBOR_RELATIVE.value,
        "best_model_rationale": (
            "Model E is the most interpretable diagnostic candidate: it compares a gap "
            "against nearby gaps on the same page, suppressing uniform page rhythm while "
            "still surfacing isolated lower-tail spacing dips. It abstains on sparse pages."
        ),
        "sparse_page_policy": (
            "Use page-local modeling only when a page has at least five eligible "
            "inter-entry gaps after reconstruction and structural exemptions; otherwise "
            "diagnostic outcome is INSUFFICIENT_CONTEXT rather than a finding."
        ),
        "section_type_results": _section_type_results(all_evaluated),
        "signature_coverage_counts_for_current_production_findings": dict(coverage_counts),
        "historical_authoritative_review_coverage_counts_for_former_96": {
            "directly_represented_by_ester_rejected_cluster": 31,
            "closely_represented": 47,
            "not_represented_or_genuinely_unreviewed": 18,
        },
        "candidate_detail_policy": (
            "Per-candidate extracted TOC/LOT/LOF text is omitted from the checked-in "
            "artifact because the source PDFs are private evaluation dissertations."
        ),
        "current_production_finding_analysis": _make_unrepresented_rows(
            all_evaluated, production_keys, reviewed_post_examples
        ),
    }

    OUTPUT_JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report)
    return report


def main() -> None:
    report = run()
    print(json.dumps({key: report[key] for key in (
        "current_production_counts",
        "current_production_findings",
        "known_ester_false_positives_flagged_by_best_model",
        "known_ester_false_positives_suppressed_by_best_model",
        "all_24_known_false_positives_suppressed",
        "model_summary",
    )}, indent=2))


if __name__ == "__main__":
    main()
