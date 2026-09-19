"""Evaluate candidate R036 production designs across the 7 real dissertations.

Diagnostic only -- does not change production behavior. Compares:

  Design 0: suppression/abstain only (selected production gate)
  Design 1: Model E + strong local anomaly gate (extreme local ratio only)
  Design 2: Model E + local + page-tail confirmation
  Design 3: Model E + multi-signal reporting gate (selected strong gate)

For each design report: known Ester FPs reported, total real reports,
abstentions, suppressed, and classify any report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from njit_auditor.pdf_layout import load_pdf_layout  # noqa: E402
from njit_auditor.rules.r036_production_page_relative_spacing import (  # noqa: E402
    NEIGHBOR_RELATIVE_FLOOR,
    NORMAL_NEIGHBOR_FLOOR,
    PRODUCTION_REPORTING_GATE,
    ProductionOutcome,
    _clean_neighbor_pitches,
    _median,
    _rank_percentile,
    classify_r036_spacing_candidates,
)

DOCS = [
    ("Youra", "5_Youra_Shin_PhD_Dissertation_Document_3rd review.pdf"),
    ("Anthony", "Anthony.Sena 3rd Review Draft.pdf"),
    ("Muyeed", "Muyeed_Dissertation (4).pdf"),
    ("Philip", "Philip_Zaleski_Thesis_Revised (1).pdf"),
    ("Praneeth", "Praneeth Ivan Joel. FNU_3rd review draft.pdf"),
    ("Sebastian", "Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf"),
    ("Patrick", "Thesis Patrick Grice July 22.pdf"),
]

GT_PATH = REPO_ROOT / "data/evaluation/r036_ester_false_positive_ground_truth_20260916.json"
OUT_JSON = REPO_ROOT / "docs/status/r036_production_design_comparison_20260916.json"


def _gt_keys():
    payload = json.loads(GT_PATH.read_text(encoding="utf-8"))
    return {
        (r["dissertation"], int(r["physical_pdf_page"]), int(r["entry_pair_index"]))
        for r in payload["labels"]
    }


def _group_by_page(records: list[dict]) -> dict:
    by_page: dict[tuple, list[dict]] = {}
    for record in records:
        by_page.setdefault(
            (record["page_number"], record["section_type"]), []
        ).append(record)
    for page in by_page.values():
        page.sort(key=lambda r: r["entry_pair_index"])
    return by_page


def _strong_gate(
    record: dict, page_records: list[dict], index: int, design: int
) -> bool:
    """Return True when the candidate satisfies the design's reporting gate.

    All designs require the candidate to first be "materially tighter than
    reliable local rhythm" (the suppression/abstention boundary). Design 1
    adds an extreme local-ratio requirement; Design 2 adds page-tail
    confirmation; Design 3 adds two-sided + absolute sanity.
    """
    if record["outcome"].outcome is not ProductionOutcome.ABSTAIN:
        return False
    if record["outcome"].abstain_reason.value != "unreliable_neighborhood":
        return False  # only the "tight but gated" abstain is a report candidate
    neighbors = _clean_neighbor_pitches(page_records, index)
    neighbor_median = _median(neighbors)
    if neighbor_median is None or neighbor_median <= 0:
        return False
    local_ratio = record["pitch_pt"] / neighbor_median
    if local_ratio > NEIGHBOR_RELATIVE_FLOOR:
        return False
    if not (max(neighbors) / neighbor_median >= NORMAL_NEIGHBOR_FLOOR):
        return False
    # Extreme local deviation (Designs 1-3 all require materially tighter
    # than the 0.72 floor; use 0.60 as the "substantially below" bar).
    if local_ratio > 0.60:
        return False
    if design == 1:
        return True
    # Design 2: page-distribution lower-tail confirmation.
    page_pitches = [r["pitch_pt"] for r in page_records]
    page_tail = _rank_percentile(page_pitches, record["pitch_pt"])
    if page_tail > 0.05:
        return False
    if design == 2:
        return True
    # Design 3: two-sided clean neighbors + absolute sanity.
    two_sided = len([n for n in neighbors if n >= record["pitch_pt"]]) >= 2
    absolute_ok = (
        record["pitch_pt"]
        >= 0.85 * record["local_single_line_pitch_pt"]
    )
    return two_sided and absolute_ok


def evaluate_design(design: int, gt_keys: set) -> dict:
    totals = {
        "candidates": 0,
        "suppressed": 0,
        "abstained": 0,
        "reported": 0,
        "known_fp_reported": 0,
        "reports": [],
    }
    per_doc: dict[str, dict] = {}
    for document, filename in DOCS:
        pdf = load_pdf_layout(str(REPO_ROOT / "data/evaluation/private" / filename))
        records = classify_r036_spacing_candidates(pdf, document_name=document)
        by_page = _group_by_page(records)
        doc_reported = 0
        for key, page_records in by_page.items():
            for index, record in enumerate(page_records):
                if (
                    design > 0
                    and _strong_gate(record, page_records, index, design)
                ):
                    record["outcome"] = _reported_outcome(record)
        for record in records:
            outcome = record["outcome"].outcome
            totals["candidates"] += 1
            if outcome is ProductionOutcome.SUPPRESS:
                totals["suppressed"] += 1
            elif outcome is ProductionOutcome.ABSTAIN:
                totals["abstained"] += 1
            else:
                totals["reported"] += 1
                doc_reported += 1
                totals["reports"].append(
                    {
                        "document": document,
                        "page": record["page_number"],
                        "section": record["section_type"],
                        "pair": record["entry_pair_index"],
                        "pitch": round(record["pitch_pt"], 2),
                        "local_pitch": round(record["local_single_line_pitch_pt"], 2),
                        "ratio": round(record["normalized_ratio"], 3),
                    }
                )
                if (
                    document,
                    record["page_number"],
                    record["entry_pair_index"],
                ) in gt_keys:
                    totals["known_fp_reported"] += 1
        per_doc[document] = {
            "candidates": len(records),
            "suppressed": sum(
                1
                for r in records
                if r["outcome"].outcome is ProductionOutcome.SUPPRESS
            ),
            "abstained": sum(
                1
                for r in records
                if r["outcome"].outcome is ProductionOutcome.ABSTAIN
            ),
            "reported": doc_reported,
        }
    totals["per_doc"] = per_doc
    return totals


def _reported_outcome(record: dict):
    from njit_auditor.rules.r036_production_page_relative_spacing import (
        CandidateOutcome,
        ProductionOutcome,
        ReportReason,
    )

    return CandidateOutcome(
        ProductionOutcome.REPORT,
        entry_pair_index=record["entry_pair_index"],
        pitch_pt=record["pitch_pt"],
        local_single_line_pitch_pt=record["local_single_line_pitch_pt"],
        normalized_ratio=record["normalized_ratio"],
        report_reason=ReportReason.STRONG_MULTI_SIGNAL_ANOMALY,
    )


def main() -> None:
    gt_keys = _gt_keys()
    designs = {
        "Design 0 suppression/abstain only": 0,
        "Design 1 Model E + strong local anomaly gate": 1,
        "Design 2 Model E + local + page-tail confirmation": 2,
        "Design 3 Model E + multi-signal reporting gate": 3,
    }
    results = {}
    for name, design in designs.items():
        totals = evaluate_design(design, gt_keys)
        results[name] = totals
        print(
            f"{name}: known_fp_reported={totals['known_fp_reported']} "
            f"reports={totals['reported']} abstained={totals['abstained']} "
            f"suppressed={totals['suppressed']} candidates={totals['candidates']}"
        )
        for report in totals["reports"][:20]:
            print("   report:", report)
    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT_JSON}")
    print(f"selected production gate: {PRODUCTION_REPORTING_GATE}")


if __name__ == "__main__":
    main()
