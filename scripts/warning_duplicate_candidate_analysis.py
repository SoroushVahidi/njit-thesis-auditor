#!/usr/bin/env python3
"""Report duplicate-candidate clusters for a PDF's visible findings.

Runs the full audit pipeline on a PDF, builds the same ReportView the web
UI renders, and prints candidate clusters (bbox-overlap and shared
student-facing wording across different rule_ids) for human review. This
tool never suppresses or merges findings -- see
njit_auditor.duplicate_candidate_analysis for why that decision needs a
person, not just geometry.

Usage: python scripts/warning_duplicate_candidate_analysis.py <path-to-pdf>
"""

# ruff: noqa: E402

from __future__ import annotations

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


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    pdf_path = Path(sys.argv[1])

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


if __name__ == "__main__":
    main()
