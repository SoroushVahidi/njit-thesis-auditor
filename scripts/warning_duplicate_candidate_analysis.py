#!/usr/bin/env python3
"""Report duplicate-candidate clusters for a PDF's visible findings.

Runs the full audit pipeline on a PDF, builds the same ReportView the web
UI renders, and prints candidate clusters (bbox-overlap and shared
student-facing wording across different rule_ids) for human review. This
tool never suppresses or merges findings -- see
njit_auditor.duplicate_candidate_analysis for why that decision needs a
person, not just geometry.

Privacy defaults:
  - stdout summaries omit document text and filenames in written JSON;
  - optional JSON output defaults under ignored ``results/`` using a hash
    of the input path as the sample id (never the basename);
  - missing PDF paths fail clearly.

Usage:
  python scripts/warning_duplicate_candidate_analysis.py <path-to-pdf>
  python scripts/warning_duplicate_candidate_analysis.py <path-to-pdf> --json-out results/dupes.json
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.duplicate_candidate_analysis import (
    find_geometric_duplicate_candidates,
    find_same_page_normalized_wording_candidates,
)
from njit_auditor.pdf_highlight import get_pdf_page_sizes
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view, report_view_to_dict


def _privacy_safe_sample_id(pdf_path: Path) -> str:
    digest = hashlib.sha256(str(pdf_path.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"sample-{digest}"


def _candidate_rows(report) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for c in report.candidates:
        rows.append(
            {
                "page": c.page,
                "finding_id_a": c.finding_id_a,
                "finding_id_b": c.finding_id_b,
                "rule_id_a": c.rule_id_a,
                "issue_type_a": c.issue_type_a,
                "rule_id_b": c.rule_id_b,
                "issue_type_b": c.issue_type_b,
                "bbox_iou": round(c.bbox_iou, 4),
                "reasons": list(c.reasons),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path", type=Path, help="Path to a local PDF to analyze")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help=(
            "Optional privacy-safe JSON path. Defaults to "
            "results/duplicate_candidates_<sample-id>.json under the repo root."
        ),
    )
    parser.add_argument(
        "--write-json",
        action="store_true",
        help="Write privacy-safe JSON under results/ even when --json-out is omitted.",
    )
    args = parser.parse_args()
    pdf_path = args.pdf_path
    if not pdf_path.is_file():
        print(f"error: PDF not found: {pdf_path}", file=sys.stderr)
        raise SystemExit(2)

    findings = run_pdf_audit_full(pdf_path)
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    try:
        page_sizes = get_pdf_page_sizes(pdf_path)
    except Exception:
        page_sizes = None
    view = build_report_view(report, pdf_page_sizes=page_sizes)
    view_dict = report_view_to_dict(view)
    visible = view_dict.get("findings", [])

    geo = find_geometric_duplicate_candidates(visible)
    wording = find_same_page_normalized_wording_candidates(visible)

    print(f"{len(visible)} visible findings")
    print("All pairs below are CANDIDATES requiring human review, not confirmed duplicates.")
    print()
    print(f"{len(geo.candidates)} bbox-overlap candidate pairs (different rule/issue_type)")
    for pair, items in sorted(geo.by_rule_pair().items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(items):3d}x  {pair[0]}  <->  {pair[1]}")
    for c in geo.candidates:
        print(
            f"    page {c.page}: {c.finding_id_a} <-> {c.finding_id_b}  reasons={list(c.reasons)}"
        )

    print()
    print(f"{len(wording.candidates)} shared-wording candidate pairs (different rule_id)")
    for pair, items in sorted(wording.by_rule_pair().items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(items):3d}x  {pair[0]}  <->  {pair[1]}")
    for c in wording.candidates:
        print(
            f"    page {c.page}: {c.finding_id_a} <-> {c.finding_id_b}  reasons={list(c.reasons)}"
        )

    sample_id = _privacy_safe_sample_id(pdf_path)
    out_path = args.json_out
    if out_path is None and args.write_json:
        out_path = _REPO_ROOT / "results" / f"duplicate_candidates_{sample_id}.json"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sample_id": sample_id,
            "visible_finding_count": len(visible),
            "note": "Candidates require human review; no automatic suppress/merge.",
            "geometric_candidates": _candidate_rows(geo),
            "shared_wording_candidates": _candidate_rows(wording),
        }
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote privacy-safe JSON to {out_path}")


if __name__ == "__main__":
    main()
