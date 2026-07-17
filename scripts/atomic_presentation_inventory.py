#!/usr/bin/env python3
"""Diagnostic inventory: classify (rule_id, issue_type) pairs by presentation atomicity.

Answers, for every active, default-enabled `(rule_id, issue_type)` pair a
detector can emit: does the student-facing comment and explanation give this
*specific* issue type its own distinct wording, or does it fall through to
text shared with unrelated siblings (or the fully generic fallback)?

This is read-only analysis over the same modules the web/CLI pipeline already
imports (`polished_comments.build_polished_comment`,
`issue_type_explanations.explain_issue_type`, the rule catalog, and a static
source scan — see `njit_auditor.rule_source_scan`). It never runs a detector
against a PDF and never changes any runtime finding, wording dict, or
threshold; it only reports on the wording layer as it exists today.

Classification buckets:

- ATOMIC: has both a specific (non-generic-fallback) comment and explanation.
- PRESENTATION_SHOULD_BE_REFINED: comment and/or explanation still falls to a
  generic fallback sentence for this specific issue type — a wording-only fix
  (new dict entry or dispatch branch) would close this, no detector change.
- POTENTIALLY_REQUIRES_DETECTOR_RESTRUCTURING: reserved for cases where no
  wording-only fix could make the pair atomic because the underlying catalog
  `question` is inherently shared across logically-different issue types in a
  way no per-issue-type override can resolve. Deliberately left empty unless a
  real case is found — see docs/RULE_ARCHITECTURE.md and the audit that
  produced this script: a manual spot-check of the ~19 most fragmented rules
  found no genuinely ambiguous shared question, so nothing is force-fit into
  this bucket.

Usage:
  python scripts/atomic_presentation_inventory.py
  python scripts/atomic_presentation_inventory.py --md-out docs/status/inventory.md
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from njit_auditor.issue_type_explanations import explain_issue_type, issue_type_title
from njit_auditor.polished_comments import _resolve_remediation, build_polished_comment
from njit_auditor.rule_source_scan import detector_emitted_pairs_by_static_scan

_CATALOG_PATH = _REPO_ROOT / "data/processed/rules/project_added_rules.json"

_REPORTING_ONLY_TYPES = frozenset(
    {"infrastructure", "infrastructure_refinement", "reporting_refinement"}
)

_GENERIC_COMMENT_MARKER = "This automated check found a possible"
_GENERIC_EXPLANATION_MARKER = "was flagged by an automated check"


def _load_catalog() -> list[dict]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _active_pairs_with_question(catalog: list[dict]) -> tuple[set[tuple[str, str]], dict[str, str]]:
    """Return (active non-reporting/experimental/evaluation pairs, rule_id -> question)."""
    question_by_rule: dict[str, str] = {
        rule["id"]: str(rule.get("question") or "") for rule in catalog
    }
    excluded_rule_ids = {
        rule["id"]
        for rule in catalog
        if rule.get("rule_type") in _REPORTING_ONLY_TYPES
        or rule.get("rule_type") == "evaluation_task"
        or rule.get("phase") == "evaluation_task"
        or "experimental" in (rule.get("rule_type") or "")
    }
    known_rule_ids = {rule["id"] for rule in catalog}

    pairs: set[tuple[str, str]] = set()
    for rule in catalog:
        if rule["id"] in excluded_rule_ids:
            continue
        for issue_type in rule.get("issue_types") or []:
            pairs.add((rule["id"], issue_type))
    for rule_id, issue_type in detector_emitted_pairs_by_static_scan():
        if rule_id in excluded_rule_ids or rule_id not in known_rule_ids:
            continue
        pairs.add((rule_id, issue_type))
    return pairs, question_by_rule


def _classify(rule_id: str, issue_type: str) -> dict[str, object]:
    comment = build_polished_comment(rule_id=rule_id, issue_type=issue_type, page=1, details={})
    explanation = explain_issue_type(rule_id, issue_type)
    remediation = _resolve_remediation(rule_id, issue_type)
    title = issue_type_title(rule_id, issue_type)

    has_specific_comment = _GENERIC_COMMENT_MARKER not in comment
    has_specific_explanation = _GENERIC_EXPLANATION_MARKER not in explanation
    has_remediation = bool(remediation.strip())

    if has_specific_comment and has_specific_explanation:
        bucket = "ATOMIC"
    else:
        bucket = "PRESENTATION_SHOULD_BE_REFINED"

    return {
        "rule_id": rule_id,
        "issue_type": issue_type,
        "title": title,
        "has_specific_comment": has_specific_comment,
        "has_specific_explanation": has_specific_explanation,
        "has_remediation": has_remediation,
        "bucket": bucket,
    }


def build_inventory() -> list[dict[str, object]]:
    catalog = _load_catalog()
    pairs, _question_by_rule = _active_pairs_with_question(catalog)
    rows = [_classify(rule_id, issue_type) for rule_id, issue_type in sorted(pairs)]
    rows.sort(key=lambda row: (row["bucket"] != "ATOMIC", row["rule_id"], row["issue_type"]))
    return rows


def render_markdown(rows: list[dict[str, object]]) -> str:
    atomic = [r for r in rows if r["bucket"] == "ATOMIC"]
    refine = [r for r in rows if r["bucket"] == "PRESENTATION_SHOULD_BE_REFINED"]
    lines = [
        "# Atomic Presentation Inventory",
        "",
        "Diagnostic only — generated by `scripts/atomic_presentation_inventory.py`. "
        "Read-only analysis of existing wording coverage; does not change any "
        "runtime finding, threshold, or rule ID. Regenerate after any wording change "
        "to keep this snapshot current.",
        "",
        f"- **Atomic** (specific comment + specific explanation): {len(atomic)}",
        f"- **Presentation should be refined** (generic fallback somewhere): {len(refine)}",
        "- **Potentially requires detector restructuring**: 0 "
        "(none found in this pass — see script docstring)",
        "",
    ]
    if refine:
        lines.append("## Presentation should be refined")
        lines.append("")
        lines.append("| rule_id | issue_type | title | comment | explanation | remediation |")
        lines.append("|---|---|---|---|---|---|")
        for row in refine:
            lines.append(
                f"| {row['rule_id']} | {row['issue_type']} | {row['title']} | "
                f"{'specific' if row['has_specific_comment'] else 'GENERIC'} | "
                f"{'specific' if row['has_specific_explanation'] else 'GENERIC'} | "
                f"{'yes' if row['has_remediation'] else 'MISSING'} |"
            )
        lines.append("")
    lines.append(f"## Atomic ({len(atomic)} pairs)")
    lines.append("")
    lines.append("| rule_id | issue_type | title |")
    lines.append("|---|---|---|")
    for row in atomic:
        lines.append(f"| {row['rule_id']} | {row['issue_type']} | {row['title']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md-out", type=str, default=None, help="Path to write a markdown report.")
    parser.add_argument("--json-out", type=str, default=None, help="Path to write a JSON report.")
    args = parser.parse_args()

    rows = build_inventory()
    atomic_count = sum(1 for r in rows if r["bucket"] == "ATOMIC")
    refine_count = len(rows) - atomic_count
    print(f"{len(rows)} active (rule_id, issue_type) pairs classified.")
    print(f"  ATOMIC: {atomic_count}")
    print(f"  PRESENTATION_SHOULD_BE_REFINED: {refine_count}")
    if refine_count:
        print("\nPairs needing presentation refinement:")
        for row in rows:
            if row["bucket"] != "ATOMIC":
                print(f"  {row['rule_id']}/{row['issue_type']}: {row['title']}")

    if args.md_out:
        out_path = Path(args.md_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_markdown(rows), encoding="utf-8")
        print(f"\nWrote markdown report to {out_path}")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"Wrote JSON report to {out_path}")


if __name__ == "__main__":
    main()
