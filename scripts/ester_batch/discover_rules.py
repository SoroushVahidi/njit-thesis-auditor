"""Discover currently implemented rules and build the batch manifest.

Reads the canonical, implemented rule catalog (data/processed/rules/
project_added_rules.json) -- never a hand-typed list -- and classifies each
rule as applicable to this PDF-only, seven-dissertation evaluation batch.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_JSON = REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "evaluation" / "ester_feedback" / "all_rules_batch_manifest.json"

# Phases that require input we do not have for this batch (compiled PDFs
# only -- no TeX source, no DOCX comment threads, no manual/human-only task).
_SKIP_PHASES = {
    "tex_source": "Requires TeX source files; only compiled PDFs are available for this batch.",
    "docx_comments": "Requires a DOCX comment thread; the seven dissertations are evaluated as PDFs.",
    "evaluation_task": "Not a PDF detector rule (internal evaluation/process task, not applicable to Ester review).",
}

ALREADY_DONE = {"P011"}


def _rule_ids_that_can_emit_findings() -> set[str]:
    """Rule IDs the source code can actually attach to an ``AuditFinding``.

    Ground truth from a static AST scan of the rule modules (see
    rule_source_scan.py's ``detector_emitted_pairs_by_static_scan``), not
    free-text catalog notes -- notes wording is inconsistent (e.g. P073/P081
    say "Reporting-only" without the "no standalone findings" phrase used
    elsewhere), so it is not a reliable applicability signal on its own.
    A rule absent from this set is internal plumbing (heading-gate
    infrastructure, triage/report reorganization for another rule's
    findings) that never emits its own standalone finding, so it can never
    have "a weakest surviving finding" of its own to select.
    """
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src"))
    from njit_auditor.rule_source_scan import detector_emitted_pairs_by_static_scan

    return {rule_id for rule_id, _issue_type in detector_emitted_pairs_by_static_scan()}


def discover() -> dict:
    rules = json.loads(RULES_JSON.read_text(encoding="utf-8"))
    rules_sorted = sorted(rules, key=lambda r: r["id"])
    emittable_ids = _rule_ids_that_can_emit_findings()

    entries = []
    for rule in rules_sorted:
        pid = rule["id"]
        rnum = pid[1:]
        rid = f"R{rnum}"
        phase = rule.get("phase")
        applicable = True
        skip_reason = None

        if rule.get("implementation_status") != "implemented":
            applicable = False
            skip_reason = f"implementation_status={rule.get('implementation_status')}"
        elif phase in _SKIP_PHASES:
            applicable = False
            skip_reason = _SKIP_PHASES[phase]
        elif pid not in emittable_ids:
            applicable = False
            skip_reason = (
                "Infrastructure/reporting-only rule: a static scan of the rule source "
                f"finds no code path where {pid} is attached to an AuditFinding -- it only "
                "reorganizes or localizes another rule's findings (e.g. heading-gate "
                "infrastructure or triage/report reorganization). There is no 'weakest "
                "surviving finding' of its own to select, so this rule cannot produce an "
                "Ester evaluation package."
            )

        entries.append(
            {
                "internal_id": pid,
                "ester_id": rid,
                "implementation_module": rule.get("implementation_module"),
                "phase": phase,
                "checkability": rule.get("checkability"),
                "priority": rule.get("priority"),
                "section": rule.get("section"),
                "applicable_to_batch": applicable,
                "skip_reason": skip_reason,
                "already_complete": pid in ALREADY_DONE,
                "evidence_strategy": "generic: reuse highlight_targeting.py bbox geometry + "
                "pdf_highlight.py single-page highlighted render; excerpt text extracted "
                "directly from the highlighted region(s) on the page",
            }
        )

    manifest = {
        "generated_at": None,  # filled by caller (batch_runner) with a real timestamp
        "source_catalog": str(RULES_JSON.relative_to(REPO_ROOT)),
        "total_rules_in_catalog": len(entries),
        "applicable_count": sum(1 for e in entries if e["applicable_to_batch"]),
        "skipped_count": sum(1 for e in entries if not e["applicable_to_batch"]),
        "already_complete": sorted(ALREADY_DONE),
        "rules": entries,
    }
    return manifest


if __name__ == "__main__":
    import datetime

    manifest = discover()
    manifest["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Discovered {manifest['total_rules_in_catalog']} rules: "
          f"{manifest['applicable_count']} applicable, {manifest['skipped_count']} skipped.")
    print(f"Manifest written to {MANIFEST_PATH}")
